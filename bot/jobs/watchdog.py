"""
Фоновый watchdog: пингует сайт каждые 5 минут.
Алерт если 2 подряд неудачи; уведомление о восстановлении.
"""
import logging
from datetime import datetime, timezone
from telegram.ext import ContextTypes
from bot.config import SITE_URL, ADMIN_IDS
from bot.services.server_monitor import ping_site

logger = logging.getLogger("watchdog")

_fail_count    = 0
_was_down      = False
_down_since: datetime | None = None


async def watchdog_ping(context: ContextTypes.DEFAULT_TYPE):
    global _fail_count, _was_down, _down_since

    res = ping_site(SITE_URL, timeout=10)

    if res["ok"]:
        if _was_down and _down_since:
            diff = int((datetime.now(timezone.utc) - _down_since).total_seconds())
            mins = diff // 60
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        admin_id,
                        f"✅ Сайт снова работает (был недоступен {mins} мин)"
                    )
                except Exception as e:
                    logger.error(f"Не удалось отправить алерт {admin_id}: {e}")
        _fail_count = 0
        _was_down   = False
        _down_since = None
    else:
        _fail_count += 1
        logger.warning(f"Watchdog: сайт не ответил (попытка {_fail_count}), ошибка: {res['error'] or res['code']}")

        if _fail_count == 2:
            _was_down   = True
            _down_since = datetime.now(timezone.utc)
            now_str     = datetime.now(timezone.utc).strftime("%H:%M")
            err_str     = res["error"] or f"HTTP {res['code']}"
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        admin_id,
                        f"🚨 <b>САЙТ НЕ ОТВЕЧАЕТ!</b>\n\n"
                        f"Последняя проверка: {now_str}\n"
                        f"Ошибка: {err_str}\n\n"
                        "Попробуй: /restart или /logs",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Не удалось отправить алерт {admin_id}: {e}")
