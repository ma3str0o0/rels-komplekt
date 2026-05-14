from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.config import ADMIN_IDS


def admin_only(func):
    """Декоратор: пропускает только пользователей из ADMIN_IDS."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id

        if not ADMIN_IDS:
            await update.message.reply_text(
                "⚠️ Бот в режиме настройки.\n\n"
                "1. Отправь /id чтобы узнать свой user_id\n"
                "2. Добавь в .env файл:\n"
                "   ADMIN_IDS=<твой_id>\n"
                "3. Перезапусти бота"
            )
            return

        if user_id not in ADMIN_IDS:
            print(f"[AUTH] Отказ: user_id={user_id}, username={update.effective_user.username}")
            await update.message.reply_text("🔒 Доступ запрещён.")
            return

        return await func(update, context, *args, **kwargs)
    return wrapper


def admin_only_cb(func):
    """Декоратор для callback/entry-point хэндлеров: проверяет ADMIN_IDS.

    При отказе вызывает answer() со show_alert и возвращает
    ConversationHandler.END — это безопасно и для простых callback-функций
    (они просто игнорируют return), и для entry-points ConversationHandler
    (диалог не начнётся).
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else None
        if ADMIN_IDS and (user_id is None or user_id not in ADMIN_IDS):
            if update.callback_query:
                try:
                    await update.callback_query.answer("🔒 Доступ запрещён.", show_alert=True)
                except Exception:
                    pass
            elif update.message:
                try:
                    await update.message.reply_text("🔒 Доступ запрещён.")
                except Exception:
                    pass
            return ConversationHandler.END
        return await func(update, context, *args, **kwargs)
    return wrapper
