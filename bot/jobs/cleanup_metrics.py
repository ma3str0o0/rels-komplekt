"""
Еженедельная очистка метрик старше 90 дней (воскресенье 03:00 UTC).
"""
import logging
from telegram.ext import ContextTypes
from bot.services.metrics import DB_PATH, db_exists

log = logging.getLogger(__name__)


async def cleanup_old_metrics(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not db_exists():
        return
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.execute("DELETE FROM events WHERE ts < datetime('now', '-90 days')")
        deleted = cur.rowcount
        conn.execute('VACUUM')
        conn.commit()
        conn.close()
        log.info('Очистка метрик: удалено %d записей старше 90 дней', deleted)
    except Exception as e:
        log.error('Ошибка очистки метрик: %s', e)
