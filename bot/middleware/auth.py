from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
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
