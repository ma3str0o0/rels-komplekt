"""
Хелперы для single-message UI: в чате всегда одно активное сообщение-панель.
"""
import logging
from telegram import Message, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Ключ в context.user_data для хранения ID последнего сообщения бота
LAST_MSG_KEY = "last_bot_message_id"


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
    Отправляет новый экран-панель. Используется из slash-команд.

    1. Удаляет сообщение пользователя (команду)
    2. Удаляет предыдущее сообщение бота
    3. Отправляет новое сообщение
    4. Запоминает его ID, возвращает объект Message
    """
    chat_id = update.effective_chat.id

    if update.message:
        await _delete_safe(context.bot, chat_id, update.message.message_id)

    old_id = context.user_data.get(LAST_MSG_KEY)
    if old_id:
        await _delete_safe(context.bot, chat_id, old_id)

    new_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
    context.user_data[LAST_MSG_KEY] = new_msg.message_id
    return new_msg


async def edit_screen(
    message: Message,
    text: str,
    reply_markup=None,
    parse_mode: str = "HTML",
) -> None:
    """
    Редактирует текущий экран-панель. Используется из callback-кнопок.
    Подавляет ошибку 'Message is not modified'.
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise
