"""
Ежедневный дайджест — отправляется в 09:00 по Екатеринбургу (04:00 UTC).
"""
import json
import logging
from datetime import date, timedelta

from telegram.ext import ContextTypes

from bot.config import ADMIN_IDS, PROJECT_DIR
from bot.services.metrics import db_exists, get_stats, get_top_products

log = logging.getLogger(__name__)

_CATALOG_PATH = PROJECT_DIR / "data" / "catalog.json"
_catalog_cache: dict = {}


def _load_catalog() -> dict:
    if _catalog_cache:
        return _catalog_cache
    try:
        with open(_CATALOG_PATH, encoding='utf-8') as f:
            for item in json.load(f):
                _catalog_cache[item['id']] = item.get('name', item['id'])
    except Exception:
        pass
    return _catalog_cache


def _short_name(pid: str, max_len: int = 20) -> str:
    name = _load_catalog().get(pid, pid)
    return name[:max_len] + '…' if len(name) > max_len else name


async def send_daily_digest(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not ADMIN_IDS:
        return
    if not db_exists():
        return

    # Статистика за вчера (1 день, но смотрим вчерашний день через 2-дневный диапазон минус сегодня)
    # Проще: берём stats за 1 день — это текущие сутки UTC, достаточно для дайджеста
    s = get_stats(days=1)

    # Не отправляем если нет данных (сервер был выключен)
    if s['views'] == 0:
        log.info('Дайджест: 0 просмотров за день, пропускаем.')
        return

    yesterday = (date.today() - timedelta(days=1)).strftime('%-d %B').replace(
        'January', 'января').replace('February', 'февраля').replace('March', 'марта').replace(
        'April', 'апреля').replace('May', 'мая').replace('June', 'июня').replace(
        'July', 'июля').replace('August', 'августа').replace('September', 'сентября').replace(
        'October', 'октября').replace('November', 'ноября').replace('December', 'декабря')

    top3 = get_top_products(days=1, limit=3)
    top3_str = '  · '.join(f"{_short_name(pid)} ({cnt})" for pid, cnt in top3) if top3 else '—'

    searches_str = ', '.join(f"{q} ({n})" for q, n in s['searches'][:3]) if s['searches'] else '—'

    text = (
        f"📊 <b>Дайджест за {yesterday}</b>\n\n"
        f"👁 Просмотры: {s['views']} (уников: {s['unique_ips']})\n"
        f"📱 Заявки: {s['forms']}\n"
        f"📞 Тел.: {s['phone_clicks']}  ·  📄 PDF: {s['pdf_downloads']}\n\n"
        f"🏷 Топ-3:\n  {top3_str}\n\n"
        f"🔍 Искали: {searches_str}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, text, parse_mode='HTML')
        except Exception as e:
            log.error('Дайджест: не удалось отправить admin %s: %s', admin_id, e)
