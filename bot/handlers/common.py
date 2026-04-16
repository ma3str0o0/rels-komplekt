from telegram import Update
from telegram.ext import ContextTypes
from bot.middleware.auth import admin_only
from bot.handlers.keyboards import MENU_TEXT, main_menu_keyboard


@admin_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(MENU_TEXT, reply_markup=main_menu_keyboard(), parse_mode="HTML")


@admin_only
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(MENU_TEXT, reply_markup=main_menu_keyboard(), parse_mode="HTML")


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Работает без авторизации — нужна для первоначальной настройки."""
    uid = update.effective_user.id
    await update.message.reply_text(
        f"👤 Ваш Telegram ID: <code>{uid}</code>\n\n"
        "Чтобы стать админом, добавьте в .env:\n"
        f"<code>ADMIN_IDS={uid}</code>",
        parse_mode="HTML",
    )
