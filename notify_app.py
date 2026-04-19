#!/usr/bin/env python3
"""
Рельс-Комплект — WSGI-приложение для /api/notify
Запускается через gunicorn; nginx обслуживает статику сам.
"""

import cgi
import html as _html
import os
import json
import re
import smtplib
import sqlite3
import threading
import ssl
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from io import BytesIO

import requests

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
    return f'{n:,.{decimals}f}'.replace(',', ' ')


def _esc(s) -> str:
    """HTML-экранирование пользовательских данных для email-шаблона."""
    return _html.escape(str(s or ''), quote=True)


def _tesc(s) -> str:
    """Экранирование для Telegram HTML-режима: <, >, &."""
    return _html.escape(str(s or ''), quote=False)


# ══════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════
def format_telegram(data: dict) -> str:
    lines = [
        '<b>📋 Новая заявка — Рельс-Комплект</b>',
        '',
        f'👤 Имя: {_tesc(data.get("name") or "—")}',
        f'📞 Контакт: {_tesc(data.get("contact") or data.get("phone") or "—")}',
    ]
    if data.get('message'):
        lines.append(f'💬 Комментарий: {_tesc(data["message"])}')

    items = data.get('items', [])
    if items:
        lines += ['', '<b>🛒 Состав заявки:</b>']
        total = 0
        for i, item in enumerate(items, 1):
            qty   = item.get('qty', 1)
            unit  = item.get('unit', 'т')
            price = item.get('price')
            if price:
                price_str = '{} ₽/{}'.format(_fmt(price), _tesc(unit))
                total += price * qty
            else:
                price_str = 'По запросу'
            lines.append('{i}. {name} — {qty} {unit} × {price}'.format(
                i=i, name=_tesc(item.get('name', '?')),
                qty=qty, unit=_tesc(unit), price=price_str
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
    name    = _esc(data.get('name') or '—')
    contact = _esc(data.get('contact') or data.get('phone') or '—')
    message = _esc(data.get('message') or '')
    items   = data.get('items', [])
    now     = datetime.now().strftime('%d.%m.%Y %H:%M')

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
              <td style="padding:8px 10px;border-bottom:1px solid #eee;">{_esc(item.get("name",""))}</td>
              <td style="padding:8px 10px;border-bottom:1px solid #eee;text-align:center;">{_esc(qty)}</td>
              <td style="padding:8px 10px;border-bottom:1px solid #eee;text-align:center;">{_esc(unit)}</td>
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
        <tr>
          <td style="background:#0A2463;padding:28px 32px;">
            <div style="font-size:22px;font-weight:700;color:#fff;letter-spacing:1px;">Рельс-Комплект</div>
            <div style="font-size:13px;color:rgba(255,255,255,.7);margin-top:4px;">Оптовый поставщик рельсовых материалов</div>
          </td>
        </tr>
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
        <tr>
          <td style="background:#f8f8f8;padding:16px 32px;border-top:1px solid #eee;">
            <p style="margin:0;font-size:12px;color:#999;line-height:1.6;">
              <strong style="color:#0A2463;">ООО «Рельс-Комплект»</strong> &nbsp;|&nbsp;
              +7 (343) 237-23-33 &nbsp;|&nbsp; ooorku@mail.ru<br>
              г. Екатеринбург, ул. Радищева, д. 6а, оф. 702б<br>
              <span style="color:#C44536;">Информация не является публичной офертой (ст. 437 ГК РФ).</span>
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
    buf     = BytesIO()
    now     = datetime.now()
    items   = data.get('items', [])
    name    = data.get('name') or '—'
    contact = data.get('contact') or data.get('phone') or '—'

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=18*mm,  bottomMargin=18*mm,
    )

    def _style(font=FONT_REG, size=10, color=C_DARK, leading=None, align=0):
        return ParagraphStyle(
            'x', fontName=font, fontSize=size, textColor=color,
            leading=leading or size * 1.35, alignment=align,
        )

    story = []

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
    story.append(Paragraph('СПЕЦИФИКАЦИЯ К ЗАЯВКЕ', _style(FONT_BOLD, 12, C_BLUE)))
    story.append(Spacer(1, 3*mm))

    client_data = [['Клиент:', name], ['Контакт:', contact]]
    if data.get('message'):
        client_data.append(['Комментарий:', data['message']])
    client_tbl = Table(client_data, colWidths=[35*mm, 135*mm])
    client_tbl.setStyle(TableStyle([
        ('FONTNAME',     (0,0), (0,-1), FONT_BOLD),
        ('FONTNAME',     (1,0), (1,-1), FONT_REG),
        ('FONTSIZE',     (0,0), (-1,-1), 9),
        ('TEXTCOLOR',    (0,0), (0,-1), C_BLUE),
        ('VALIGN',       (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING',   (0,0), (-1,-1), 2),
        ('BOTTOMPADDING',(0,0), (-1,-1), 2),
    ]))
    story.append(client_tbl)
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#DDE3EF')))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph('СОСТАВ ЗАЯВКИ', _style(FONT_BOLD, 10, C_BLUE)))
    story.append(Spacer(1, 3*mm))

    col_w = [8*mm, 68*mm, 16*mm, 12*mm, 18*mm, 20*mm, 28*mm]
    tbl_header = [
        Paragraph('№',            _style(FONT_BOLD, 8, colors.white, align=1)),
        Paragraph('Наименование', _style(FONT_BOLD, 8, colors.white)),
        Paragraph('Кол-во',       _style(FONT_BOLD, 8, colors.white, align=1)),
        Paragraph('Ед.',          _style(FONT_BOLD, 8, colors.white, align=1)),
        Paragraph('Вес, кг',      _style(FONT_BOLD, 8, colors.white, align=1)),
        Paragraph('Цена/т, ₽',    _style(FONT_BOLD, 8, colors.white, align=2)),
        Paragraph('Сумма, ₽',     _style(FONT_BOLD, 8, colors.white, align=2)),
    ]
    tbl_rows    = [tbl_header]
    total_sum   = 0
    total_weight = 0

    for i, item in enumerate(items, 1):
        qty    = float(item.get('qty', 1))
        unit   = item.get('unit', 'т')
        price  = item.get('price')
        item_id = item.get('id', '')
        weight_kg = qty * 1000
        cat_item  = catalog.get(item_id, {})
        weight_per_unit = cat_item.get('weight_per_unit')
        price_per_piece = None
        if price and weight_per_unit:
            price_per_piece = price * weight_per_unit / 1000
        summa = price * qty if price else None
        if summa:
            total_sum += summa
        total_weight += weight_kg
        bg = C_GREY if i % 2 == 0 else colors.white
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

    n = len(tbl_rows)
    tbl_rows.append([
        Paragraph('',                          _style(FONT_BOLD, 8)),
        Paragraph('ИТОГО',                     _style(FONT_BOLD, 9, colors.white)),
        Paragraph('',                          _style(FONT_BOLD, 8)),
        Paragraph('',                          _style(FONT_BOLD, 8)),
        Paragraph(_fmt(total_weight) + ' кг',  _style(FONT_BOLD, 8, colors.white, align=1)),
        Paragraph('',                          _style(FONT_BOLD, 8)),
        Paragraph(
            _fmt(total_sum) + ' ₽' if total_sum else 'По запросу',
            _style(FONT_BOLD, 9, colors.white, align=2)
        ),
    ])

    items_tbl = Table(tbl_rows, colWidths=col_w, repeatRows=1)
    items_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),   (-1,0),   C_BLUE),
        ('TEXTCOLOR',     (0,0),   (-1,0),   colors.white),
        ('TOPPADDING',    (0,0),   (-1,0),   6),
        ('BOTTOMPADDING', (0,0),   (-1,0),   6),
        ('FONTNAME',      (0,1),   (-1,-2),  FONT_REG),
        ('FONTSIZE',      (0,1),   (-1,-2),  8),
        ('TOPPADDING',    (0,1),   (-1,-2),  4),
        ('BOTTOMPADDING', (0,1),   (-1,-2),  4),
        ('ROWBACKGROUNDS',(0,1),   (-1,-2),  [colors.white, C_GREY]),
        ('BACKGROUND',    (0,n-1), (-1,n-1), C_BLUE),
        ('TOPPADDING',    (0,n-1), (-1,n-1), 7),
        ('BOTTOMPADDING', (0,n-1), (-1,n-1), 7),
        ('GRID',          (0,0),   (-1,-1),  0.3, colors.HexColor('#CCCCCC')),
        ('VALIGN',        (0,0),   (-1,-1),  'MIDDLE'),
        ('LEFTPADDING',   (0,0),   (-1,-1),  4),
        ('RIGHTPADDING',  (0,0),   (-1,-1),  4),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 6*mm))
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
def send_email(data: dict, file_bytes: bytes = None, file_name: str = None) -> None:
    if not SMTP_USER or not SMTP_PASS:
        log.warning('SMTP не настроен — email пропущен')
        return

    try:
        items     = data.get('items', [])
        has_items = bool(items)
        now_str   = datetime.now().strftime('%Y%m%d_%H%M%S')
        subject   = (
            f'Новая заявка ({len(items)} позиц.) — Рельс-Комплект'
            if has_items else
            'Новая заявка — Рельс-Комплект'
        )

        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From']    = SMTP_USER
        msg['To']      = NOTIFY_EMAIL
        msg.attach(MIMEText(build_email_html(data, has_items), 'html', 'utf-8'))

        if has_items:
            try:
                pdf_bytes  = build_pdf_spec(data, CATALOG)
                attachment = MIMEApplication(pdf_bytes, _subtype='pdf')
                attachment.add_header(
                    'Content-Disposition', 'attachment',
                    filename=f'specification_{now_str}.pdf',
                )
                msg.attach(attachment)
            except Exception as e:
                log.error('Ошибка генерации PDF: %s', e)

        if file_bytes and file_name:
            ext = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else 'bin'
            mime_map = {
                'pdf': 'pdf', 'doc': 'msword',
                'docx': 'vnd.openxmlformats-officedocument.wordprocessingml.document',
                'xls': 'vnd.ms-excel',
                'xlsx': 'vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png',
            }
            user_att = MIMEApplication(file_bytes, _subtype=mime_map.get(ext, 'octet-stream'))
            user_att.add_header('Content-Disposition', 'attachment', filename=file_name)
            msg.attach(user_att)

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=15) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.sendmail(SMTP_USER, NOTIFY_EMAIL, msg.as_bytes())
        log.info('Email отправлен на %s', NOTIFY_EMAIL)

    except Exception as e:
        log.error('Ошибка отправки email: %s', e)


# ══════════════════════════════════════
# Трекинг аналитики — SQLite
# ══════════════════════════════════════
_DB_PATH   = os.path.join(BASE_DIR, 'data', 'metrics.db')
_db_conn   = None
_db_lock   = threading.Lock()
# Rate limiting: {ip: (count, minute_ts)}
_rl_track  : dict = {}
_rl_lock   = threading.Lock()
_BOT_UA_RE = re.compile(r'bot|crawl|spider|googlebot|yandex|bingbot|baiduspider', re.I)


def _get_db() -> sqlite3.Connection:
    global _db_conn
    if _db_conn is None:
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        _db_conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _db_conn.execute('PRAGMA journal_mode=WAL')
        _db_conn.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         TEXT NOT NULL DEFAULT (strftime(\'%Y-%m-%dT%H:%M:%S\',\'now\')),
                event      TEXT NOT NULL,
                page       TEXT,
                product_id TEXT,
                ip         TEXT,
                referrer   TEXT,
                user_agent TEXT,
                extra      TEXT
            )
        ''')
        _db_conn.execute('CREATE INDEX IF NOT EXISTS idx_events_ts    ON events(ts)')
        _db_conn.execute('CREATE INDEX IF NOT EXISTS idx_events_event ON events(event)')
        _db_conn.execute('CREATE INDEX IF NOT EXISTS idx_events_page  ON events(page)')
        _db_conn.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
                source     TEXT,
                name       TEXT NOT NULL,
                contact    TEXT NOT NULL,
                message    TEXT,
                items_json TEXT,
                status     TEXT NOT NULL DEFAULT 'new',
                tg_msg_id  INTEGER,
                ip         TEXT,
                comment    TEXT
            )
        ''')
        _db_conn.execute('CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)')
        _db_conn.execute('CREATE INDEX IF NOT EXISTS idx_leads_ts     ON leads(ts)')
        try:
            _db_conn.execute("ALTER TABLE leads ADD COLUMN comment TEXT")
        except Exception:
            pass
        _db_conn.commit()
    return _db_conn


def _track_event(event: str, page, product_id, ip, referrer, user_agent, extra):
    try:
        conn = _get_db()
        with _db_lock:
            conn.execute(
                'INSERT INTO events (event, page, product_id, ip, referrer, user_agent, extra) '
                'VALUES (?,?,?,?,?,?,?)',
                (event, page, product_id, ip, referrer, user_agent, extra)
            )
            conn.commit()
    except Exception as e:
        log.error('Ошибка записи в metrics.db: %s', e)


def _check_rate_limit(ip: str) -> bool:
    """True — запрос разрешён, False — лимит превышен (100 req/min)."""
    import time
    now_min = int(time.time() // 60)
    with _rl_lock:
        entry = _rl_track.get(ip)
        if entry and entry[1] == now_min:
            if entry[0] >= 100:
                return False
            _rl_track[ip] = (entry[0] + 1, now_min)
        else:
            _rl_track[ip] = (1, now_min)
            # Чистим старые записи раз в ~1000 проверок
            if len(_rl_track) > 5000:
                stale = [k for k, v in _rl_track.items() if v[1] != now_min]
                for k in stale:
                    del _rl_track[k]
    return True


def _handle_track(environ, start_response):
    """POST /api/track — запись событий аналитики."""
    # User-Agent фильтр
    ua = environ.get('HTTP_USER_AGENT', '')
    if _BOT_UA_RE.search(ua):
        start_response('204 No Content', [])
        return [b'']

    # IP из заголовков
    ip = (
        environ.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
        or environ.get('HTTP_X_REAL_IP', '')
        or environ.get('REMOTE_ADDR', '')
    )

    # Rate limit (дополнительный уровень поверх nginx)
    if not _check_rate_limit(ip):
        start_response('429 Too Many Requests', [('Content-Type', 'text/plain')])
        return [b'Too Many Requests']

    # Парсинг тела (макс 4 KB)
    try:
        length = int(environ.get('CONTENT_LENGTH', 0) or 0)
        if length > 4096:
            start_response('413 Request Entity Too Large', [])
            return [b'']
        raw = environ['wsgi.input'].read(length)
        data = json.loads(raw)
    except Exception:
        start_response('400 Bad Request', [])
        return [b'']

    # Валидация
    event = str(data.get('event', ''))[:50]
    if not event:
        start_response('400 Bad Request', [])
        return [b'']

    page       = str(data.get('page', '') or '')[:200] or None
    product_id = str(data.get('product_id', '') or '')[:100] or None
    referrer   = str(data.get('referrer', '') or environ.get('HTTP_REFERER', '') or '')[:500] or None
    extra_raw  = data.get('extra')
    extra      = json.dumps(extra_raw, ensure_ascii=False) if isinstance(extra_raw, dict) else None

    threading.Thread(
        target=_track_event,
        args=(event, page, product_id, ip, referrer, ua[:500], extra),
        daemon=True,
    ).start()

    start_response('204 No Content', [])
    return [b'']


# ══════════════════════════════════════
# /api/lead — CRM-lite
# ══════════════════════════════════════
_rl_lead      : dict = {}
_rl_lead_lock = threading.Lock()

_LEAD_SOURCE_NAMES = {
    'order':      '📋 Заявка',
    'modal':      '📋 Форма',
    'callback':   '📞 Перезвоните',
    'contacts':   '📬 Контакты',
    'calculator': '🔢 Калькулятор',
    'cart':       '🛒 Корзина',
    'quick':      '⚡ Быстрый',
}


def _check_lead_rate_limit(ip: str) -> bool:
    """True — разрешён, False — превышен (3 req/min)."""
    import time
    now_min = int(time.time() // 60)
    with _rl_lead_lock:
        entry = _rl_lead.get(ip)
        if entry and entry[1] == now_min:
            if entry[0] >= 3:
                return False
            _rl_lead[ip] = (entry[0] + 1, now_min)
        else:
            _rl_lead[ip] = (1, now_min)
    return True


def _format_lead_tg(lead_id: int, data: dict) -> str:
    src_raw   = data.get('source', '') or ''
    src_label = _LEAD_SOURCE_NAMES.get(src_raw, _tesc(src_raw) or 'Сайт')
    lines = [
        f'📋 <b>Заявка #{lead_id}</b> — {src_label}',
        '',
        f'👤 {_tesc(data.get("name") or "—")}',
        f'📞 {_tesc(data.get("contact") or "—")}',
    ]
    if data.get('message'):
        lines.append(f'💬 {_tesc(data["message"])}')
    items = data.get('items') or []
    if items:
        lines.append(f'\n🛒 {len(items)} поз.:')
        for item in items[:3]:
            lines.append(
                f'  · {_tesc(item.get("name","?"))} — '
                f'{item.get("qty",1)} {_tesc(item.get("unit","т"))}'
            )
        if len(items) > 3:
            lines.append(f'  · ...ещё {len(items) - 3}')
    return '\n'.join(lines)


def _send_lead_thread(lead_id: int, data: dict) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '📞 Позвонил',  'callback_data': f'lead_called_{lead_id}'},
                    {'text': '📄 Выслал КП', 'callback_data': f'lead_kp_{lead_id}'},
                ],
                [
                    {'text': '✅ Сделка',    'callback_data': f'lead_done_{lead_id}'},
                    {'text': '❌ Отказ',     'callback_data': f'lead_reject_{lead_id}'},
                ],
            ]
        }
        r = requests.post(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json={
                'chat_id':      CHAT_ID,
                'text':         _format_lead_tg(lead_id, data),
                'parse_mode':   'HTML',
                'reply_markup': keyboard,
            },
            timeout=10,
        )
        if r.ok:
            msg_id = r.json().get('result', {}).get('message_id')
            if msg_id:
                conn = _get_db()
                with _db_lock:
                    conn.execute('UPDATE leads SET tg_msg_id=? WHERE id=?', (msg_id, lead_id))
                    conn.commit()
    except Exception as e:
        log.error('Ошибка отправки lead уведомления: %s', e)


def _save_lead(name: str, contact: str, source: str, message: str,
               items: list, ip: str) -> int:
    items_json = json.dumps(items, ensure_ascii=False) if items else None
    conn = _get_db()
    with _db_lock:
        cur = conn.execute(
            'INSERT INTO leads (name, contact, source, message, items_json, ip) '
            'VALUES (?,?,?,?,?,?)',
            (name, contact, source, message, items_json, ip),
        )
        conn.commit()
        return cur.lastrowid


def _handle_lead(environ, start_response):
    """POST /api/lead — сохранение заявки в CRM + Telegram с inline-кнопками."""
    ip = (
        environ.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
        or environ.get('HTTP_X_REAL_IP', '')
        or environ.get('REMOTE_ADDR', '')
    )

    if not _check_lead_rate_limit(ip):
        start_response('429 Too Many Requests', [('Content-Type', 'text/plain')])
        return [b'Too Many Requests']

    try:
        length = int(environ.get('CONTENT_LENGTH', 0) or 0)
        if length > _MAX_JSON_BODY:
            return _json_response(start_response, '413 Request Entity Too Large',
                                  {'ok': False, 'error': 'Request too large'})
        raw  = environ['wsgi.input'].read(length)
        data = json.loads(raw)
    except Exception:
        return _json_response(start_response, '400 Bad Request',
                              {'ok': False, 'error': 'Invalid JSON'})

    name    = str(data.get('name',    '') or '').strip()[:200]
    contact = str(data.get('contact', '') or '').strip()[:200]
    message = str(data.get('message', '') or '').strip()[:1000]
    source  = str(data.get('source',  '') or '').strip()[:50]

    if not name or not contact:
        return _json_response(start_response, '400 Bad Request',
                              {'ok': False, 'error': 'Missing name or contact'})
    if not _CONTACT_RE.match(contact):
        return _json_response(start_response, '400 Bad Request',
                              {'ok': False, 'error': 'Invalid contact format'})

    items_raw = data.get('items')
    items = []
    if isinstance(items_raw, list):
        for item in items_raw[:50]:
            if isinstance(item, dict):
                items.append({
                    'id':    str(item.get('id',   '') or '')[:100],
                    'name':  str(item.get('name', '') or '')[:200],
                    'qty':   item.get('qty')  if isinstance(item.get('qty'),  (int, float)) else 1,
                    'unit':  str(item.get('unit', 'т') or 'т')[:10],
                    'price': item.get('price') if isinstance(item.get('price'), (int, float)) else None,
                })

    lead_id = _save_lead(name, contact, source, message, items, ip)
    threading.Thread(
        target=_send_lead_thread,
        args=(lead_id, {'name': name, 'contact': contact, 'source': source,
                        'message': message, 'items': items}),
        daemon=True,
    ).start()

    return _json_response(start_response, '200 OK', {'ok': True, 'lead_id': lead_id})


# ══════════════════════════════════════
# Константы валидации
# ══════════════════════════════════════
_MAX_JSON_BODY   = 512 * 1024          # 512 KB для JSON без файла
_MAX_ITEMS_RAW   = 100 * 1024          # 100 KB для поля items
_MAX_FILE_BYTES  = 10 * 1024 * 1024    # 10 MB для вложения
_ALLOWED_EXTS    = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png'}
_CONTACT_RE      = re.compile(
    r'^(\+?[0-9][0-9\s\-\(\)]{6,20}[0-9]'        # телефон
    r'|[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'    # email
    r'|@[a-zA-Z][a-zA-Z0-9_]{2,31})$'                         # telegram @username
)


# ══════════════════════════════════════
# WSGI-приложение
# ══════════════════════════════════════
def _json_response(start_response, status: str, data: dict):
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    start_response(status, [
        ('Content-Type', 'application/json; charset=utf-8'),
        ('Content-Length', str(len(body))),
    ])
    return [body]


def _dispatch_notifications(body, file_bytes, file_name, name, contact):
    """Отправка Telegram + Email в фоне — не блокирует HTTP-ответ."""
    # Telegram — текст заявки
    try:
        send_telegram(body)
    except Exception as e:
        log.error('Telegram error: %s', e)

    # Telegram — файл (отдельным сообщением)
    if file_bytes and file_name and BOT_TOKEN and CHAT_ID:
        try:
            requests.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument',
                data={'chat_id': CHAT_ID, 'caption': f'📎 Файл от {name} ({contact})'},
                files={'document': (file_name, file_bytes)},
                timeout=20,
            )
        except Exception as e:
            log.error('Telegram sendDocument error: %s', e)

    # Email
    try:
        send_email(body, file_bytes=file_bytes, file_name=file_name)
    except Exception as e:
        log.error('Email error: %s', e)


def application(environ, start_response):
    method = environ.get('REQUEST_METHOD', '')
    path   = environ.get('PATH_INFO', '/')

    if method == 'POST' and path == '/api/track':
        return _handle_track(environ, start_response)

    if method == 'POST' and path == '/api/lead':
        return _handle_lead(environ, start_response)

    if method != 'POST' or path != '/api/notify':
        return _json_response(start_response, '404 Not Found',
                              {'ok': False, 'error': 'Not found'})

    # ── Парсинг тела ──────────────────────────────────────────────
    try:
        content_type = environ.get('CONTENT_TYPE', '')

        if 'multipart/form-data' in content_type:
            form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
            body = {
                'name':    form.getvalue('name', '').strip(),
                'contact': form.getvalue('contact', '').strip(),
                'message': form.getvalue('message', '').strip(),
            }
            # Items — JSON строка с ограничением размера
            items_raw = form.getvalue('items', '')
            if items_raw:
                if len(items_raw) > _MAX_ITEMS_RAW:
                    return _json_response(start_response, '400 Bad Request',
                                          {'ok': False, 'error': 'Items payload too large'})
                try:
                    body['items'] = json.loads(items_raw)
                except json.JSONDecodeError:
                    return _json_response(start_response, '400 Bad Request',
                                          {'ok': False, 'error': 'Invalid items JSON'})

            # Файл — валидация расширения и размера
            file_field = form['file'] if 'file' in form else None
            file_bytes = None
            file_name  = None
            if file_field and file_field.filename:
                raw_name = os.path.basename(file_field.filename)  # path traversal guard
                ext = raw_name.rsplit('.', 1)[-1].lower() if '.' in raw_name else ''
                if ext not in _ALLOWED_EXTS:
                    return _json_response(start_response, '400 Bad Request',
                                          {'ok': False, 'error': 'File type not allowed'})
                file_bytes = file_field.file.read()
                if len(file_bytes) > _MAX_FILE_BYTES:
                    return _json_response(start_response, '413 Request Entity Too Large',
                                          {'ok': False, 'error': 'File exceeds 10 MB'})
                file_name = raw_name
        else:
            # JSON без файла — лимит размера
            length = int(environ.get('CONTENT_LENGTH', 0) or 0)
            if length > _MAX_JSON_BODY:
                return _json_response(start_response, '413 Request Entity Too Large',
                                      {'ok': False, 'error': 'Request too large'})
            body   = json.loads(environ['wsgi.input'].read(length))
            file_bytes = None
            file_name  = None

    except Exception as e:
        log.error('Parse error: %s', e)
        return _json_response(start_response, '400 Bad Request',
                              {'ok': False, 'error': 'Invalid request'})

    # ── Валидация обязательных полей ──────────────────────────────
    name    = body.get('name', '').strip()[:200]
    contact = (body.get('contact') or body.get('phone') or '').strip()[:200]
    if not name or not contact:
        return _json_response(start_response, '400 Bad Request',
                              {'ok': False, 'error': 'Missing name or contact'})
    if not _CONTACT_RE.match(contact):
        return _json_response(start_response, '400 Bad Request',
                              {'ok': False, 'error': 'Invalid phone or email format'})

    # ── Отправка в фоновом потоке — воркер не блокируется ─────────
    threading.Thread(
        target=_dispatch_notifications,
        args=(body, file_bytes, file_name, name, contact),
        daemon=True,
    ).start()

    return _json_response(start_response, '200 OK', {'ok': True})
