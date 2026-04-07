#!/usr/bin/env python3
"""
Рельс-Комплект — единый сервер
Раздаёт статику И обрабатывает POST /api/notify → Telegram
Запускать: python3 serve.py
"""

import os
import json
import requests
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

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

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHAT_ID   = os.environ.get('CHAT_ID', '')
PORT      = int(os.environ.get('SITE_PORT', '8080'))


# ──────────────────────────────────────
# Форматирование Telegram сообщения
# ──────────────────────────────────────
def format_message(data: dict) -> str:
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
                price_str = '{:,} ₽/{}'.format(int(price), unit).replace(',', ' ')
                total += price * qty
            else:
                price_str = 'По запросу'
            lines.append('{i}. {name} — {qty} {unit} × {price}'.format(
                i=i, name=item.get('name', '?'),
                qty=qty, unit=unit, price=price_str
            ))
        if total:
            lines.append('\n💰 Итого: {:,} ₽'.format(int(total)).replace(',', ' '))

    return '\n'.join(lines)


# ──────────────────────────────────────
# Обработчик запросов
# ──────────────────────────────────────
class Handler(SimpleHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print('[server] %s - %s' % (self.address_string(), fmt % args))

    # ── API: POST /api/notify ──────────
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

        if not body.get('name') or not body.get('phone'):
            self._json(400, {'ok': False, 'error': 'Missing name or phone'})
            return

        if not BOT_TOKEN or not CHAT_ID:
            self._json(500, {'ok': False, 'error': 'Telegram not configured'})
            return

        try:
            r = requests.post(
                'https://api.telegram.org/bot{}/sendMessage'.format(BOT_TOKEN),
                json={'chat_id': CHAT_ID, 'text': format_message(body), 'parse_mode': 'HTML'},
                timeout=10,
            )
            self._json(r.status_code, r.json())
        except Exception as e:
            self._json(502, {'ok': False, 'error': str(e)})

    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    # ── Статика: GET любой файл ────────
    def do_GET(self):
        # Отдаём index.html для корневого пути
        if self.path == '/':
            self.path = '/index.html'
        super().do_GET()

    def end_headers(self):
        # Запрещаем кэширование JS, CSS и HTML — браузер всегда берёт свежую версию
        path = self.path.split('?')[0]
        if path.endswith(('.js', '.css', '.html')):
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        super().end_headers()


# ──────────────────────────────────────
# Запуск
# ──────────────────────────────────────
if __name__ == '__main__':
    os.chdir(BASE_DIR)
    if not BOT_TOKEN:
        print('[server] WARNING: BOT_TOKEN not set — Telegram уведомления отключены')
    print('[server] Starting on http://0.0.0.0:{}'.format(PORT))
    HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
