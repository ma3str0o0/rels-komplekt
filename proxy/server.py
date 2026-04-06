#!/usr/bin/env python3
"""
Рельс-Комплект — Telegram Proxy
Принимает POST /api/notify от фронтенда, отправляет в Telegram.
"""

import os
import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

def load_env(path='.env'):
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())
    except FileNotFoundError:
        pass

load_env(os.path.join(os.path.dirname(__file__), '.env'))

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
CHAT_ID   = os.environ.get('CHAT_ID', '')
PORT      = int(os.environ.get('PROXY_PORT', '3001'))


def format_message(data: dict) -> str:
    lines = [
        '<b>📋 Новая заявка — Рельс-Комплект</b>',
        '',
        f'👤 Имя: {data.get("name") or "—"}',
        f'📞 Телефон: {data.get("phone") or "—"}',
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
                price_str = f'{int(price):,} ₽/{unit}'.replace(',', ' ')
                total += price * qty
            else:
                price_str = 'По запросу'
            lines.append(f'{i}. {item.get("name", "?")} — {qty} {unit} × {price_str}')
        if total:
            lines.append(f'\n💰 Итого: {int(total):,} ₽'.replace(',', ' '))

    return '\n'.join(lines)


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f'[proxy] {self.address_string()} - {format % args}')

    def _send_cors(self):
        # Разрешаем любой origin — proxy не хранит секреты клиента
        origin = self.headers.get('Origin', '*')
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        if path != '/api/notify':
            self.send_response(404)
            self.end_headers()
            return

        try:
            length = int(self.headers.get('Content-Length', 0))
            body   = json.loads(self.rfile.read(length))
        except Exception:
            self._respond(400, {'ok': False, 'error': 'Invalid JSON'})
            return

        if not body.get('name') or not body.get('phone'):
            self._respond(400, {'ok': False, 'error': 'Missing name or phone'})
            return

        if not BOT_TOKEN or not CHAT_ID:
            self._respond(500, {'ok': False, 'error': 'Bot not configured'})
            return

        text = format_message(body)
        try:
            r = requests.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
                json={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'},
                timeout=10,
            )
            self._respond(r.status_code, r.json())
        except Exception as e:
            self._respond(502, {'ok': False, 'error': str(e)})

    def _respond(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self._send_cors()
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    if not BOT_TOKEN:
        print('[proxy] ERROR: BOT_TOKEN not set in proxy/.env')
        exit(1)
    print(f'[proxy] Starting on port {PORT}')
    HTTPServer(('0.0.0.0', PORT), ProxyHandler).serve_forever()
