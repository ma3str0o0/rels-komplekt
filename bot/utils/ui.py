"""
Хелперы для UI бота.

Архитектура сообщений:
  MENU_MSG_KEY  — ID постоянного сообщения-меню (никогда не удаляется автоматически)
  SECT_MSG_KEY  — ID текущего сообщения-секции (статус, логи, заявки и т.д.)

Из меню (is_menu=True) → открывается НОВОЕ сообщение-секция.
Внутри секции (is_menu=False) → редактируем то же сообщение.
«◀️ Меню» → удаляем сообщение-секцию, меню остаётся.
"""
import logging
from telegram import Message, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

MENU_MSG_KEY = "menu_msg_id"   # постоянное меню
SECT_MSG_KEY = "sect_msg_id"   # текущая секция
LAST_MSG_KEY = SECT_MSG_KEY    # backward compat alias


async def _delete_safe(bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except BadRequest:
        pass


async def send_screen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup=None,
    parse_mode: str = "HTML",
) -> Message:
    """
    Из slash-команды: удаляет команду + старую секцию, отправляет новую секцию.
    Меню НЕ трогает.
    """
    chat_id = update.effective_chat.id

    if update.message:
        await _delete_safe(context.bot, chat_id, update.message.message_id)

    old_sect = context.user_data.get(SECT_MSG_KEY)
    if old_sect:
        await _delete_safe(context.bot, chat_id, old_sect)

    new_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
    context.user_data[SECT_MSG_KEY] = new_msg.message_id
    return new_msg


async def edit_screen(
    message: Message,
    text: str,
    reply_markup=None,
    parse_mode: str = "HTML",
) -> None:
    """Редактирует сообщение-секцию. Подавляет 'Message is not modified'."""
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise
