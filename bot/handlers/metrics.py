"""
Хэндлеры аналитики: /stats, топ товаров.
"""
import json
from datetime import datetime
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from bot.middleware.auth import admin_only
from bot.services.metrics import db_exists, get_stats, get_top_products
from bot.utils.ui import edit_screen, send_screen
from bot.config import PROJECT_DIR

_CATALOG_PATH = PROJECT_DIR / "data" / "catalog.json"
_catalog_cache: dict = {}


def _load_catalog() -> dict:
    if _catalog_cache:
        return _catalog_cache
    try:
        with open(_catalog_path := _CATALOG_PATH, encoding='utf-8') as f:
            for item in json.load(f):
                _catalog_cache[item['id']] = item.get('name', item['id'])
    except Exception:
        pass
    return _catalog_cache


def _product_name(pid: str, max_len: int = 35) -> str:
    name = _load_catalog().get(pid, pid)
    return name[:max_len] + '…' if len(name) > max_len else name


# ── Клавиатуры ────────────────────────────────────────────────────────────


def stats_keyboard(active_days: int = 1) -> InlineKeyboardMarkup:
    def label(days: int, text: str) -> InlineKeyboardButton:
        prefix = '• ' if days == active_days else ''
        return InlineKeyboardButton(prefix + text, callback_data=f"stats_{days}")
    return InlineKeyboardMarkup([
        [label(1, 'Сегодня'), label(7, 'Неделя'), label(30, 'Месяц')],
        [
            InlineKeyboardButton('🔄 Обновить',  callback_data=f'stats_{active_days}'),
            InlineKeyboardButton('◀️ Меню',       callback_data='menu'),
        ],
    ])


def top_products_keyboard(active_days: int = 7) -> InlineKeyboardMarkup:
    def label(days: int, text: str) -> InlineKeyboardButton:
        prefix = '• ' if days == active_days else ''
        return InlineKeyboardButton(prefix + text, callback_data=f"top_{days}")
    return InlineKeyboardMarkup([
        [label(7, 'Неделя'), label(30, 'Месяц')],
        [InlineKeyboardButton('◀️ Меню', callback_data='menu')],
    ])


# ── Builders ──────────────────────────────────────────────────────────────


def _build_stats_text(days: int) -> str:
    now = datetime.now().strftime('%H:%M')
    if not db_exists():
        return (
            f"📈 <b>Аналитика</b>  <i>{now}</i>\n\n"
            "<blockquote>⚠️ База метрик пока пуста.\n"
            "Данные появятся после первых визитов на сайт.</blockquote>"
        )
    s = get_stats(days)

    main_block = (
        f"👁 Просмотры: <b>{s['views']}</b>  |  уников: <b>{s['unique_ips']}</b>\n"
        f"📱 Заявки: <b>{s['forms']}</b>   📞 {s['phone_clicks']}   📄 PDF: {s['pdf_downloads']}\n"
        f"🔢 Калькулятор: {s['calc_uses']}"
    )

    parts = [
        f"📈 <b>Аналитика — {s['period']}</b>  <i>{now}</i>",
        '',
        f"<blockquote>{main_block}</blockquote>",
    ]

    if s['top_products']:
        rows = '\n'.join(
            f"  {i}. {_product_name(pid)} — <b>{cnt}</b>"
            for i, (pid, cnt) in enumerate(s['top_products'], 1)
        )
        parts.append(f"\n<blockquote>🏷 <b>Топ товары:</b>\n{rows}</blockquote>")

    if s['searches']:
        rows = '\n'.join(f"  · {q} <i>({n})</i>" for q, n in s['searches'])
        parts.append(f"\n<blockquote>🔍 <b>Искали:</b>\n{rows}</blockquote>")

    return '\n'.join(parts)


def _build_top_text(days: int) -> str:
    now   = datetime.now().strftime('%H:%M')
    label = '7 дней' if days == 7 else f'{days} дней'
    if not db_exists():
        return f"🏷 <b>Топ товаров — {label}</b>\n\n<blockquote>⚠️ База метрик пуста.</blockquote>"
    items = get_top_products(days=days, limit=10)
    if not items:
        return (
            f"🏷 <b>Топ товаров — {label}</b>  <i>{now}</i>\n\n"
            "<blockquote><i>Нет данных за период.</i></blockquote>"
        )
    rows = '\n'.join(
        f"  <b>{i:>2}.</b> {_product_name(pid)} — <b>{cnt}</b> просм."
        for i, (pid, cnt) in enumerate(items, 1)
    )
    return (
        f"🏷 <b>Топ-{len(items)} товаров — {label}</b>  <i>{now}</i>\n\n"
        f"<blockquote>{rows}</blockquote>"
    )


# ── Callback show-функции ──────────────────────────────────────────────────


async def show_stats(message: Message, days: int = 1) -> None:
    await edit_screen(message, _build_stats_text(days), reply_markup=stats_keyboard(days))


async def show_top_products(message: Message, days: int = 7) -> None:
    await edit_screen(message, _build_top_text(days), reply_markup=top_products_keyboard(days))


# ── Slash-команды ──────────────────────────────────────────────────────────


@admin_only
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await send_screen(update, context, "⏳ Загружаю статистику...")
    await edit_screen(msg, _build_stats_text(1), reply_markup=stats_keyboard(1))
