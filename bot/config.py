"""
Конфигурация админ-бота. Читает креды из .env в корне проекта.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")   or os.getenv("CHAT_ID")

_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [int(x.strip()) for x in _raw.split(",") if x.strip().isdigit()]

CATALOG_PATH        = PROJECT_DIR / "data" / "catalog.json"
SITE_URL            = os.getenv("SITE_URL", "http://202.148.53.107:8080")
SERVE_SERVICE_NAME  = "nginx"        # статика
NOTIFY_SERVICE_NAME = "rels-notify"  # gunicorn API
