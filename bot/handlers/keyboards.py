"""
Inline-клавиатуры для всех экранов бота.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

MENU_TEXT = (
    "🤖 <b>Рельс-Комплект — Админ-панель</b>\n\n"
    "Выберите действие:"
)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Статус",     callback_data="status"),
            InlineKeyboardButton("🏓 Пинг",       callback_data="ping"),
        ],
        [
            InlineKeyboardButton("🔄 Рестарт",    callback_data="restart"),
            InlineKeyboardButton("📋 Логи",       callback_data="logs"),
        ],
        [
            InlineKeyboardButton("📈 Аналитика",  callback_data="stats_1"),
            InlineKeyboardButton("🏷 Топ товары", callback_data="top_7"),
        ],
        [
            InlineKeyboardButton("📬 Заявки",     callback_data="leads"),
        ],
    ])


def status_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Обновить", callback_data="refresh_status"),
        InlineKeyboardButton("◀️ Меню",     callback_data="menu"),
    ]])


def ping_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Повторить", callback_data="ping"),
        InlineKeyboardButton("◀️ Меню",      callback_data="menu"),
    ]])


def restart_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Да, перезапустить", callback_data="restart_yes"),
        InlineKeyboardButton("◀️ Отмена",            callback_data="menu"),
    ]])


def restart_done_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📊 Статус", callback_data="status"),
        InlineKeyboardButton("◀️ Меню",   callback_data="menu"),
    ]])


def logs_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("30 строк",  callback_data="logs"),
        InlineKeyboardButton("100 строк", callback_data="logs_100"),
        InlineKeyboardButton("◀️ Меню",   callback_data="menu"),
    ]])
