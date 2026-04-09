#!/usr/bin/env python3
"""
Рельс-Комплект — единый сервер
Раздаёт статику + POST /api/notify → Telegram + Email (параллельно)
"""

import os
import json
import smtplib
import ssl
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from io import BytesIO
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

import requests

# reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.platypus import HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

# ──────────────────────────────────────
# Загрузка секретов из proxy/.env
# ──────────────────────────────────────
def load_env(path):
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())
    except FileNotFoundError:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_env(os.path.join(BASE_DIR, 'proxy', '.env'))

BOT_TOKEN    = os.environ.get('BOT_TOKEN', '')
CHAT_ID      = os.environ.get('CHAT_ID', '')
PORT         = int(os.environ.get('SITE_PORT', '8080'))
SMTP_HOST    = os.environ.get('SMTP_HOST', 'smtp.mail.ru')
SMTP_PORT    = int(os.environ.get('SMTP_PORT', '465'))
SMTP_USER    = os.environ.get('SMTP_USER', '')
SMTP_PASS    = os.environ.get('SMTP_PASS', '')
NOTIFY_EMAIL = os.environ.get('NOTIFY_EMAIL', 'ooorku@mail.ru')

# Цвета бренда
C_BLUE = colors.HexColor('#0A2463')
C_RED  = colors.HexColor('#C44536')
C_GREY = colors.HexColor('#F5F5F5')
C_DARK = colors.HexColor('#1A1A1A')

# ──────────────────────────────────────
# Регистрация шрифтов с поддержкой кириллицы
# ──────────────────────────────────────
_FONT_DIR = '/usr/share/fonts/truetype/dejavu'

def _register_fonts():
    try:
        pdfmetrics.registerFont(TTFont('DejaVu',      os.path.join(_FONT_DIR, 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('DejaVu-Bold', os.path.join(_FONT_DIR, 'DejaVuSans-Bold.ttf')))
        return 'DejaVu', 'DejaVu-Bold'
    except Exception as e:
        log.warning('Не удалось загрузить шрифт DejaVu: %s. Используется Helvetica.', e)
        return 'Helvetica', 'Helvetica-Bold'

FONT_REG, FONT_BOLD = _register_fonts()

# ──────────────────────────────────────
# Загрузка каталога для расчёта веса
# ──────────────────────────────────────
def _load_catalog() -> dict:
    """Возвращает dict id → item для быстрого поиска."""
    try:
        with open(os.path.join(BASE_DIR, 'data', 'catalog.json'), encoding='utf-8') as f:
            return {item['id']: item for item in json.load(f)}
    except Exception as e:
        log.warning('Не удалось загрузить catalog.json: %s', e)
        return {}

CATALOG = _load_catalog()

# ──────────────────────────────────────
# Форматирование числа
# ──────────────────────────────────────
def _fmt(n, decimals=0):
    if n is None:
        return '—'
    fmt = f'{n:,.{decimals}f}'
    return fmt.replace(',', ' ')


# ══════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════
def format_telegram(data: dict) -> str:
    lines = [
        '<b>📋 Новая заявка — Рельс-Комплект</b>',
        '',
        f'👤 Имя: {data.get("name") or "—"}',
        f'📞 Контакт: {data.get("contact") or data.get("phone") or "—"}',
    ]
    if data.get('message'):
        lines.append(f'💬 Комментарий: {data["message"]}')

    items = data.get('items', [])
    if items:
        lines += ['', '<b>🛒 Состав заявки:</b>']
        total = 0
        for i, item in enumerate(items, 1):
            qty   = item.get('qty', 1)
            unit  = item.get('unit', 'т')
            price = item.get('price')
            if price:
                price_str = '{} ₽/{}'.format(_fmt(price), unit)
                total += price * qty
            else:
                price_str = 'По запросу'
            lines.append('{i}. {name} — {qty} {unit} × {price}'.format(
                i=i, name=item.get('name', '?'),
                qty=qty, unit=unit, price=price_str
            ))
        if total:
            lines.append(f'\n💰 Итого: {_fmt(total)} ₽')

    return '\n'.join(lines)


def send_telegram(data: dict):
    if not BOT_TOKEN or not CHAT_ID:
        log.warning('Telegram не настроен — пропускаем')
        return
    r = requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        json={'chat_id': CHAT_ID, 'text': format_telegram(data), 'parse_mode': 'HTML'},
        timeout=10,
    )
    r.raise_for_status()


# ══════════════════════════════════════
# EMAIL — HTML-шаблон
# ══════════════════════════════════════
def build_email_html(data: dict, has_items: bool) -> str:
    name    = data.get('name') or '—'
    contact = data.get('contact') or data.get('phone') or '—'
    message = data.get('message') or ''
    items   = data.get('items', [])
    now     = datetime.now().strftime('%d.%m.%Y %H:%M')

    # Блок клиента
    client_rows = f'''
      <tr><td style="padding:6px 0;color:#666;width:120px;">Имя</td>
          <td style="padding:6px 0;font-weight:600;">{name}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Контакт</td>
          <td style="padding:6px 0;font-weight:600;">{contact}</td></tr>
    '''
    if message:
        client_rows += f'''
      <tr><td style="padding:6px 0;color:#666;vertical-align:top;">Сообщение</td>
          <td style="padding:6px 0;">{message}</td></tr>
        '''

    # Блок товаров
    items_section = ''
    if has_items:
        rows_html = ''
        total_sum = 0
        for i, item in enumerate(items, 1):
            qty   = item.get('qty', 1)
            unit  = item.get('unit', 'т')
            price = item.get('price')
            summa = price * qty if price else None
            if summa:
                total_sum += summa
            bg = '#F9F9F9' if i % 2 == 0 else '#FFFFFF'
            rows_html += f'''
            <tr style="background:{bg};">
              <td style="padding:8px 10px;border-bottom:1px solid #eee;">{i}</td>
              <td style="padding:8px 10px;border-bottom:1px solid #eee;">{item.get("name","")}</td>
              <td style="padding:8px 10px;border-bottom:1px solid #eee;text-align:center;">{qty}</td>
              <td style="padding:8px 10px;border-bottom:1px solid #eee;text-align:center;">{unit}</td>
              <td style="padding:8px 10px;border-bottom:1px solid #eee;text-align:right;">
                {"По запросу" if not price else _fmt(price) + " ₽"}
              </td>
              <td style="padding:8px 10px;border-bottom:1px solid #eee;text-align:right;font-weight:600;">
                {"По запросу" if not summa else _fmt(summa) + " ₽"}
              </td>
            </tr>'''

        total_row = f'''
            <tr style="background:#0A2463;color:#fff;">
              <td colspan="5" style="padding:10px;font-weight:700;">ИТОГО</td>
              <td style="padding:10px;text-align:right;font-weight:700;">
                {_fmt(total_sum) + " ₽" if total_sum else "По запросу"}
              </td>
            </tr>'''

        items_section = f'''
        <h3 style="color:#0A2463;margin:24px 0 12px;">Состав заявки</h3>
        <table width="100%" cellpadding="0" cellspacing="0"
               style="border-collapse:collapse;font-size:14px;border:1px solid #ddd;">
          <thead>
            <tr style="background:#0A2463;color:#fff;">
              <th style="padding:10px;text-align:left;width:30px;">№</th>
              <th style="padding:10px;text-align:left;">Наименование</th>
              <th style="padding:10px;text-align:center;width:60px;">Кол-во</th>
              <th style="padding:10px;text-align:center;width:40px;">Ед.</th>
              <th style="padding:10px;text-align:right;width:120px;">Цена/ед.</th>
              <th style="padding:10px;text-align:right;width:120px;">Сумма</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
            {total_row}
          </tbody>
        </table>
        <p style="font-size:12px;color:#999;margin-top:8px;">
          ✉ К письму приложена PDF-спецификация для печати.
        </p>'''

    return f'''<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f5;padding:24px 0;">
    <tr><td align="center">
      <table width="620" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1);">

        <!-- ШАПКА -->
        <tr>
          <td style="background:#0A2463;padding:28px 32px;">
            <div style="font-size:22px;font-weight:700;color:#fff;letter-spacing:1px;">
              Рельс-Комплект
            </div>
            <div style="font-size:13px;color:rgba(255,255,255,.7);margin-top:4px;">
              Оптовый поставщик рельсовых материалов
            </div>
          </td>
        </tr>

        <!-- ТЕЛО -->
        <tr>
          <td style="padding:28px 32px;">
            <h2 style="margin:0 0 6px;color:#0A2463;font-size:18px;">
              {'Новая заявка с товарами' if has_items else 'Новая заявка'}
            </h2>
            <p style="margin:0 0 20px;font-size:13px;color:#999;">{now}</p>

            <h3 style="color:#0A2463;margin:0 0 12px;font-size:15px;">Данные клиента</h3>
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="font-size:14px;border-top:1px solid #eee;">
              {client_rows}
            </table>

            {items_section}
          </td>
        </tr>

        <!-- ПОДВАЛ -->
        <tr>
          <td style="background:#f8f8f8;padding:16px 32px;border-top:1px solid #eee;">
            <p style="margin:0;font-size:12px;color:#999;line-height:1.6;">
              <strong style="color:#0A2463;">ООО «Рельс-Комплект»</strong> &nbsp;|&nbsp;
              +7 (343) 237-23-33 &nbsp;|&nbsp; ooorku@mail.ru<br>
              г. Екатеринбург, ул. Радищева, д. 6а, оф. 702б<br>
              <span style="color:#C44536;">
                Информация не является публичной офертой (ст. 437 ГК РФ).
              </span>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>'''


# ══════════════════════════════════════
# PDF-спецификация (reportlab)
# ══════════════════════════════════════
def build_pdf_spec(data: dict, catalog: dict) -> bytes:
    buf   = BytesIO()
    now   = datetime.now()
    items = data.get('items', [])
    name  = data.get('name') or '—'
    contact = data.get('contact') or data.get('phone') or '—'

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=18*mm,  bottomMargin=18*mm,
    )

    # Стили параграфов
    def _style(font=FONT_REG, size=10, color=C_DARK, leading=None, align=0):
        return ParagraphStyle(
            'x', fontName=font, fontSize=size, textColor=color,
            leading=leading or size * 1.35, alignment=align,
        )

    story = []

    # ── Шапка ──────────────────────────────────────────────────────
    header_data = [[
        Paragraph('<b>Рельс-Комплект</b>', _style(FONT_BOLD, 16, colors.white, 20)),
        Paragraph(
            'Коммерческое предложение<br/>'
            f'<font size="9">{now.strftime("%d.%m.%Y")}</font>',
            _style(FONT_REG, 11, colors.HexColor('#BBCFEF'), align=2),
        ),
    ]]
    header_tbl = Table(header_data, colWidths=[110*mm, 60*mm])
    header_tbl.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), C_BLUE),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',   (0,0), (-1,-1), 12),
        ('BOTTOMPADDING',(0,0), (-1,-1), 12),
        ('LEFTPADDING',  (0,0), (0,-1),  12),
        ('RIGHTPADDING', (-1,0),(-1,-1), 12),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 6*mm))

    # ── Подзаголовок ───────────────────────────────────────────────
    story.append(Paragraph('СПЕЦИФИКАЦИЯ К ЗАЯВКЕ', _style(FONT_BOLD, 12, C_BLUE)))
    story.append(Spacer(1, 3*mm))

    # ── Данные клиента ─────────────────────────────────────────────
    client_data = [
        ['Клиент:', name],
        ['Контакт:', contact],
    ]
    if data.get('message'):
        client_data.append(['Комментарий:', data['message']])

    client_tbl = Table(client_data, colWidths=[35*mm, 135*mm])
    client_tbl.setStyle(TableStyle([
        ('FONTNAME',  (0,0), (0,-1), FONT_BOLD),
        ('FONTNAME',  (1,0), (1,-1), FONT_REG),
        ('FONTSIZE',  (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (0,-1), C_BLUE),
        ('VALIGN',    (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING',(0,0), (-1,-1), 2),
        ('BOTTOMPADDING',(0,0),(-1,-1), 2),
    ]))
    story.append(client_tbl)
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#DDE3EF')))
    story.append(Spacer(1, 4*mm))

    # ── Таблица товаров ────────────────────────────────────────────
    story.append(Paragraph('СОСТАВ ЗАЯВКИ', _style(FONT_BOLD, 10, C_BLUE)))
    story.append(Spacer(1, 3*mm))

    col_w = [8*mm, 68*mm, 16*mm, 12*mm, 18*mm, 20*mm, 28*mm]
    tbl_header = [
        Paragraph('№',           _style(FONT_BOLD, 8, colors.white, align=1)),
        Paragraph('Наименование',_style(FONT_BOLD, 8, colors.white)),
        Paragraph('Кол-во',      _style(FONT_BOLD, 8, colors.white, align=1)),
        Paragraph('Ед.',         _style(FONT_BOLD, 8, colors.white, align=1)),
        Paragraph('Вес, кг',     _style(FONT_BOLD, 8, colors.white, align=1)),
        Paragraph('Цена/т, ₽',   _style(FONT_BOLD, 8, colors.white, align=2)),
        Paragraph('Сумма, ₽',    _style(FONT_BOLD, 8, colors.white, align=2)),
    ]

    tbl_rows = [tbl_header]
    total_sum = 0
    total_weight = 0

    for i, item in enumerate(items, 1):
        qty    = float(item.get('qty', 1))
        unit   = item.get('unit', 'т')
        price  = item.get('price')       # ₽ за тонну
        item_id = item.get('id', '')

        # Вес: qty в тоннах → вес в кг
        weight_kg = qty * 1000

        # Цена за штуку (если weight_per_unit известен)
        cat_item       = catalog.get(item_id, {})
        weight_per_unit = cat_item.get('weight_per_unit')  # кг за 1 шт
        price_per_piece = None
        if price and weight_per_unit:
            price_per_piece = price * weight_per_unit / 1000   # цена * (кг/1000) = ₽ за шт

        summa = price * qty if price else None
        if summa:
            total_sum += summa
        total_weight += weight_kg

        bg = C_GREY if i % 2 == 0 else colors.white

        # Цена/т: если weight_per_unit есть — показываем и цену за штуку в скобках
        price_cell = '—'
        if price:
            price_cell = _fmt(price)
            if price_per_piece:
                price_cell += f'\n({_fmt(price_per_piece)}/шт)'

        row = [
            Paragraph(str(i),               _style(FONT_REG, 8, align=1)),
            Paragraph(item.get('name', ''), _style(FONT_REG, 8)),
            Paragraph(_fmt(qty, 2),          _style(FONT_REG, 8, align=1)),
            Paragraph(unit,                  _style(FONT_REG, 8, align=1)),
            Paragraph(_fmt(weight_kg),       _style(FONT_REG, 8, align=1)),
            Paragraph(price_cell,            _style(FONT_REG, 8, align=2)),
            Paragraph(
                _fmt(summa) if summa else 'По запросу',
                _style(FONT_BOLD if summa else FONT_REG, 8, align=2)
            ),
        ]
        tbl_rows.append(row)

    # Строка итого
    tbl_rows.append([
        Paragraph('',                                    _style(FONT_BOLD, 8)),
        Paragraph('ИТОГО',                               _style(FONT_BOLD, 9, colors.white)),
        Paragraph('',                                    _style(FONT_BOLD, 8)),
        Paragraph('',                                    _style(FONT_BOLD, 8)),
        Paragraph(_fmt(total_weight) + ' кг',           _style(FONT_BOLD, 8, colors.white, align=1)),
        Paragraph('',                                    _style(FONT_BOLD, 8)),
        Paragraph(
            _fmt(total_sum) + ' ₽' if total_sum else 'По запросу',
            _style(FONT_BOLD, 9, colors.white, align=2)
        ),
    ])

    n = len(tbl_rows)
    items_tbl = Table(tbl_rows, colWidths=col_w, repeatRows=1)
    items_tbl.setStyle(TableStyle([
        # Шапка
        ('BACKGROUND',    (0,0), (-1,0),    C_BLUE),
        ('TEXTCOLOR',     (0,0), (-1,0),    colors.white),
        ('TOPPADDING',    (0,0), (-1,0),    6),
        ('BOTTOMPADDING', (0,0), (-1,0),    6),
        # Строки данных
        ('FONTNAME',      (0,1), (-1,-2),   FONT_REG),
        ('FONTSIZE',      (0,1), (-1,-2),   8),
        ('TOPPADDING',    (0,1), (-1,-2),   4),
        ('BOTTOMPADDING', (0,1), (-1,-2),   4),
        ('ROWBACKGROUNDS',(0,1), (-1,-2),   [colors.white, C_GREY]),
        # Строка итого
        ('BACKGROUND',    (0,n-1), (-1,n-1), C_BLUE),
        ('TOPPADDING',    (0,n-1), (-1,n-1), 7),
        ('BOTTOMPADDING', (0,n-1), (-1,n-1), 7),
        # Общее
        ('GRID',          (0,0), (-1,-1),   0.3, colors.HexColor('#CCCCCC')),
        ('VALIGN',        (0,0), (-1,-1),   'MIDDLE'),
        ('LEFTPADDING',   (0,0), (-1,-1),   4),
        ('RIGHTPADDING',  (0,0), (-1,-1),   4),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 6*mm))

    # ── Подвал ─────────────────────────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#CCCCCC')))
    story.append(Spacer(1, 3*mm))
    footer_data = [[
        Paragraph(
            'ООО «Рельс-Комплект»  |  +7 (343) 237-23-33  |  ooorku@mail.ru\n'
            'г. Екатеринбург, ул. Радищева, д. 6а, оф. 702б',
            _style(FONT_REG, 8, colors.HexColor('#555555')),
        ),
        Paragraph(
            'Не является публичной офертой (ст. 437 ГК РФ)',
            _style(FONT_REG, 7, C_RED, align=2),
        ),
    ]]
    footer_tbl = Table(footer_data, colWidths=[120*mm, 50*mm])
    footer_tbl.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(footer_tbl)

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════
# EMAIL — отправка
# ══════════════════════════════════════
def send_email(data: dict) -> None:
    """Отправляет HTML-письмо + PDF-вложение (если есть товары). Не бросает исключений."""
    if not SMTP_USER or not SMTP_PASS:
        log.warning('SMTP не настроен (нет SMTP_USER / SMTP_PASS) — email пропущен')
        return

    try:
        items    = data.get('items', [])
        has_items = bool(items)
        now_str  = datetime.now().strftime('%Y%m%d_%H%M%S')

        subject = (
            f'Новая заявка ({len(items)} позиц.) — Рельс-Комплект'
            if has_items else
            'Новая заявка — Рельс-Комплект'
        )

        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From']    = SMTP_USER
        msg['To']      = NOTIFY_EMAIL

        # HTML-тело
        html_body = build_email_html(data, has_items)
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        # PDF-вложение (только если есть товары)
        if has_items:
            try:
                pdf_bytes = build_pdf_spec(data, CATALOG)
                attachment = MIMEApplication(pdf_bytes, _subtype='pdf')
                attachment.add_header(
                    'Content-Disposition', 'attachment',
                    filename=f'specification_{now_str}.pdf',
                )
                msg.attach(attachment)
            except Exception as e:
                log.error('Ошибка генерации PDF: %s', e)

        # Отправка через SSL
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=15) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.sendmail(SMTP_USER, NOTIFY_EMAIL, msg.as_bytes())

        log.info('Email отправлен на %s', NOTIFY_EMAIL)

    except Exception as e:
        log.error('Ошибка отправки email: %s', e)


# ══════════════════════════════════════
# HTTP-обработчик
# ══════════════════════════════════════
class Handler(SimpleHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print('[server] %s - %s' % (self.address_string(), fmt % args))

    # ── API: POST /api/notify ──────────────────────────────────────
    def do_POST(self):
        if urlparse(self.path).path != '/api/notify':
            self.send_error(404)
            return

        try:
            length = int(self.headers.get('Content-Length', 0))
            body   = json.loads(self.rfile.read(length))
        except Exception:
            self._json(400, {'ok': False, 'error': 'Invalid JSON'})
            return

        # Принимаем phone или contact
        name    = body.get('name', '').strip()
        contact = (body.get('contact') or body.get('phone') or '').strip()
        if not name or not contact:
            self._json(400, {'ok': False, 'error': 'Missing name or contact'})
            return

        # ── Telegram ──────────────────────────────────────────────
        tg_ok  = False
        tg_err = None
        try:
            send_telegram(body)
            tg_ok = True
        except Exception as e:
            tg_err = str(e)
            log.error('Telegram error: %s', e)

        # ── Email (параллельно, не блокирует ответ) ───────────────
        try:
            send_email(body)
        except Exception as e:
            log.error('Email error (unexpected): %s', e)

        # ── Ответ клиенту ─────────────────────────────────────────
        if tg_ok:
            self._json(200, {'ok': True})
        else:
            self._json(502, {'ok': False, 'error': tg_err or 'Telegram failed'})

    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    # ── Статика: GET любой файл ────────────────────────────────────
    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        super().do_GET()

    def end_headers(self):
        # Запрещаем кэширование JS, CSS и HTML
        path = self.path.split('?')[0]
        if path.endswith(('.js', '.css', '.html', '.json')):
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        super().end_headers()


# ══════════════════════════════════════
# Запуск
# ══════════════════════════════════════
if __name__ == '__main__':
    os.chdir(BASE_DIR)
    if not BOT_TOKEN:
        log.warning('BOT_TOKEN не задан — Telegram уведомления отключены')
    if not SMTP_USER:
        log.warning('SMTP_USER не задан — Email уведомления отключены')
    log.info('Starting on http://0.0.0.0:%d', PORT)
    HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
