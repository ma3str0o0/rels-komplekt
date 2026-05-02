"""
Точка входа Telegram админ-бота Рельс-Комплект.
Запуск: python3 -m bot.main
"""
import logging
from datetime import time as dtime
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from bot.config import ADMIN_IDS, BOT_TOKEN
from bot.handlers.common import get_id, help_cmd, start
from bot.handlers.server import handle_callback, logs, ping, restart, status
from bot.handlers.metrics import stats_command
from bot.handlers.leads import leads_command, handle_comment_reply
from bot.handlers.catalog import (
    handle_csv_document, make_add_conv, make_find_conv, make_price_conv,
    markup_command, price_command,
)
from bot.jobs.watchdog import watchdog_ping
from bot.jobs.daily_digest import send_daily_digest
from bot.jobs.cleanup_metrics import cleanup_old_metrics

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)

# Подавляем httpx INFO-логи: они печатают URL с bot<TOKEN>/getUpdates
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger("admin_bot")


def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден! Проверь .env")
        return

    if not ADMIN_IDS:
        logger.warning(
            "ADMIN_IDS пустой — бот в режиме настройки. "
            "Отправь /id боту чтобы узнать свой user_id"
        )

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("help",    help_cmd))
    app.add_handler(CommandHandler("id",      get_id))
    app.add_handler(CommandHandler("status",  status))
    app.add_handler(CommandHandler("ping",    ping))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CommandHandler("logs",    logs))
    app.add_handler(CommandHandler("stats",   stats_command))
    app.add_handler(CommandHandler("leads",   leads_command))
    app.add_handler(CommandHandler("price",   price_command))
    app.add_handler(CommandHandler("markup",  markup_command))

    # ConversationHandlers должны быть до общего CallbackQueryHandler
    app.add_handler(make_find_conv())   # включает /find command
    app.add_handler(make_price_conv())
    app.add_handler(make_add_conv())

    app.add_handler(MessageHandler(filters.Document.FileExtension("csv"), handle_csv_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_comment_reply))
    app.add_handler(CallbackQueryHandler(handle_callback))

    if ADMIN_IDS:
        app.job_queue.run_repeating(watchdog_ping, interval=300, first=10)
        logger.info("Watchdog запущен (интервал: 5 мин)")
        # Дайджест в 09:00 Екатеринбург (04:00 UTC)
        app.job_queue.run_daily(send_daily_digest, time=dtime(hour=4, minute=0))
        logger.info("Дайджест запланирован на 04:00 UTC (09:00 Екб)")
        # Очистка метрик каждое воскресенье в 03:00 UTC
        app.job_queue.run_daily(
            cleanup_old_metrics,
            time=dtime(hour=3, minute=0),
            days=(6,),  # 6 = воскресенье
        )

    logger.info(f"Бот запущен. Админы: {ADMIN_IDS or 'НЕ НАСТРОЕНЫ'}")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
