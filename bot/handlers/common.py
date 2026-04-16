from telegram import Update
from telegram.ext import ContextTypes
from bot.middleware.auth import admin_only

HELP_TEXT = (
    "🤖 <b>Админ-панель — Рельс-Комплект</b>\n\n"
    "📡 <b>Сервер:</b>\n"
    "  /status — статус VPS и serve.py\n"
    "  /ping — проверить доступность сайта\n"
    "  /restart — перезапустить serve.py\n"
    "  /logs — последние 30 строк лога\n"
    "  /logs 100 — последние N строк\n\n"
    "ℹ️ <b>Прочее:</b>\n"
    "  /id — мой Telegram user_id\n"
    "  /help — эта справка"
)


@admin_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="HTML")


@admin_only
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="HTML")


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Работает без авторизации — нужна для первоначальной настройки."""
    uid = update.effective_user.id
    await update.message.reply_text(
        f"👤 Ваш Telegram ID: <code>{uid}</code>\n\n"
        "Чтобы стать админом, добавьте в .env:\n"
        f"<code>ADMIN_IDS={uid}</code>",
        parse_mode="HTML"
    )
