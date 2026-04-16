from telegram import Update
from telegram.ext import ContextTypes
from bot.middleware.auth import admin_only
from bot.handlers.keyboards import MENU_TEXT, main_menu_keyboard
from bot.utils.ui import MENU_MSG_KEY, SECT_MSG_KEY, _delete_safe


async def _send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет постоянное меню, удаляя старое меню и секцию."""
    chat_id = update.effective_chat.id
    if update.message:
        await _delete_safe(context.bot, chat_id, update.message.message_id)
    for key in (MENU_MSG_KEY, SECT_MSG_KEY):
        old = context.user_data.pop(key, None)
        if old:
            await _delete_safe(context.bot, chat_id, old)
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=MENU_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode='HTML',
    )
    context.user_data[MENU_MSG_KEY] = msg.message_id


@admin_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_menu(update, context)


@admin_only
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_menu(update, context)


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Без удаления сообщений — пользователю нужно скопировать свой ID."""
    uid = update.effective_user.id
    await update.message.reply_text(
        f"👤 Ваш Telegram ID: <code>{uid}</code>\n\n"
        "Чтобы стать админом, добавьте в .env:\n"
        f"<code>ADMIN_IDS={uid}</code>",
        parse_mode="HTML",
    )
