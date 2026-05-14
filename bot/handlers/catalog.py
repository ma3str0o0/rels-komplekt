"""
Хэндлеры управления каталогом: поиск, просмотр, редактирование цен, импорт CSV.
"""
import logging
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.config import ADMIN_IDS
from bot.middleware.auth import admin_only, admin_only_cb
from bot.services.catalog import (
    add_product, apply_markup, bulk_set_in_stock, bulk_update_prices,
    delete_product, find_products, get_categories, get_product,
    get_product_count, get_stock_summary, parse_csv_prices,
    quick_adjust_price, set_in_stock, set_price_request, update_price,
)
from bot.utils.formatting import format_price
from bot.utils.ui import SECT_MSG_KEY, edit_screen, send_screen

log = logging.getLogger(__name__)

# ── Состояния ConversationHandler ─────────────────────────────────────────
(
    PRICE_WAIT,
    FIND_WAIT,
    MARKUP_CAT_WAIT,
    MARKUP_PCT_WAIT,
    ADD_NAME,
    ADD_CAT,
    ADD_PRICE,
    ADD_UNIT,
    ADD_WEIGHT,
    ADD_LENGTH,
) = range(10)

# ── context.user_data ключи ────────────────────────────────────────────────
_PRICE_PID_KEY   = "cat_price_pid"
_MARKUP_CAT_KEY  = "cat_markup_cat"
_FIND_RESULTS    = "cat_find_results"


# ── Клавиатуры ────────────────────────────────────────────────────────────


def catalog_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Поиск товара",   callback_data="cat_find"),
            InlineKeyboardButton("📊 Склад",           callback_data="cat_stock"),
        ],
        [
            InlineKeyboardButton("➕ Добавить товар",  callback_data="cat_add"),
            InlineKeyboardButton("📥 Импорт CSV",      callback_data="cat_csv_info"),
        ],
        [InlineKeyboardButton("◀️ Меню", callback_data="menu")],
    ])


def product_keyboard(pid: str, item: Optional[dict] = None, show_delete: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура карточки товара с быстрыми корректировками цены.

    Если item передан и price is None — quick-adjust кнопки скрываются.
    Если item не передан — пытаемся подгрузить (back-compat для старого кода).
    """
    if item is None:
        item = get_product(pid) or {}
    has_price = item.get("price") is not None
    in_stock  = bool(item.get("in_stock"))

    rows: list = []

    # Ряд быстрых корректировок (только если цена задана)
    if has_price:
        rows.append([
            InlineKeyboardButton("−5%",  callback_data=f"cat_adj_{pid}_-5"),
            InlineKeyboardButton("−1%",  callback_data=f"cat_adj_{pid}_-1"),
            InlineKeyboardButton("+1%",  callback_data=f"cat_adj_{pid}_1"),
            InlineKeyboardButton("+5%",  callback_data=f"cat_adj_{pid}_5"),
            InlineKeyboardButton("+10%", callback_data=f"cat_adj_{pid}_10"),
        ])

    # Своя цена / наличие / по запросу
    stock_btn = (
        InlineKeyboardButton("🔴 Снять с наличия", callback_data=f"cat_stock_{pid}")
        if in_stock else
        InlineKeyboardButton("🟢 В наличии",       callback_data=f"cat_stock_{pid}")
    )
    rows.append([
        InlineKeyboardButton("💯 Своя цена",  callback_data=f"cat_price_{pid}"),
        stock_btn,
        InlineKeyboardButton("По запросу",    callback_data=f"cat_req_{pid}"),
    ])

    # Fallback: явная кнопка ручного ввода (та же что и «Своя цена», для совместимости)
    rows.append([InlineKeyboardButton("✏️ Изменить вручную", callback_data=f"cat_price_{pid}")])

    if show_delete:
        rows.append([InlineKeyboardButton("🗑 Удалить товар", callback_data=f"cat_del_{pid}")])
        rows.append([InlineKeyboardButton("✅ Да, удалить",   callback_data=f"cat_del_confirm_{pid}")])

    rows.append([
        InlineKeyboardButton("◀️ К результатам", callback_data="cat_find_back"),
        InlineKeyboardButton("◀️ Меню",           callback_data="menu"),
    ])
    return InlineKeyboardMarkup(rows)


def _back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Меню", callback_data="menu")]])


def _cancel_kb(back: str = "cat_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data=back)]])


# ── Builders ──────────────────────────────────────────────────────────────


def _product_text(item: dict) -> str:
    price_str = format_price(item.get("price"))
    stock_icon = "✅" if item.get("in_stock") else "❌"
    cat = item.get("category", "—")
    sub = item.get("subcategory") or ""
    cat_line = f"{cat}" + (f" / {sub}" if sub else "")
    lines = [
        f"📦 <b>{item['name']}</b>",
        f"<code>{item['id']}</code>",
        "",
        f"<blockquote>💰 Цена: <b>{price_str}</b> / {item.get('unit','т')}\n"
        f"📁 {cat_line}\n"
        f"{stock_icon} {'В наличии' if item.get('in_stock') else 'Нет в наличии'}</blockquote>",
    ]
    # Подсказка, если цена не задана — quick-adjust кнопки скрыты
    if item.get("price") is None:
        lines.append("\n<i>Цена не задана — установите вручную</i>")
    return "\n".join(lines)


def _stock_text() -> str:
    s = get_stock_summary()
    cat_rows = "\n".join(
        f"  · {name}: <b>{cnt}</b>" for name, cnt in s["by_category"]
    )
    return (
        f"📊 <b>Склад — сводка</b>\n\n"
        f"<blockquote>"
        f"Всего позиций: <b>{s['total']}</b>\n"
        f"В наличии: <b>{s['in_stock']}</b>\n"
        f"Без цены: <b>{s['no_price']}</b>"
        f"</blockquote>\n\n"
        f"<blockquote><b>По категориям (топ-8):</b>\n{cat_rows}</blockquote>"
    )


# ── Экраны (show_*) ────────────────────────────────────────────────────────


async def show_catalog_menu(message: Message) -> None:
    await edit_screen(
        message,
        "📦 <b>Управление каталогом</b>\n\nВыберите действие:",
        reply_markup=catalog_menu_keyboard(),
    )


async def show_stock(message: Message) -> None:
    await edit_screen(message, _stock_text(), reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Каталог", callback_data="cat_menu"),
         InlineKeyboardButton("◀️ Меню",    callback_data="menu")],
    ]))


async def show_find_results(message: Message, results: list) -> None:
    if not results:
        text = "🔍 <b>Поиск</b>\n\n<blockquote><i>Ничего не найдено.</i></blockquote>"
    else:
        rows_text = "\n".join(
            f"  <code>{i['id']}</code> {i['name'][:40]}"
            + (f" — {format_price(i.get('price'))}" if i.get('price') else "")
            for i in results
        )
        text = f"🔍 <b>Результаты поиска</b> ({len(results)} шт.)\n\n<blockquote>{rows_text}</blockquote>"

    buttons = [
        [InlineKeyboardButton(
            f"{i['name'][:30]}", callback_data=f"cat_view_{i['id']}"
        )]
        for i in results[:8]
    ]
    buttons.append([
        InlineKeyboardButton("🔍 Новый поиск", callback_data="cat_find"),
        InlineKeyboardButton("◀️ Меню",         callback_data="menu"),
    ])
    await edit_screen(message, text, reply_markup=InlineKeyboardMarkup(buttons))


async def show_product(message: Message, pid: str) -> None:
    item = get_product(pid)
    if not item:
        await edit_screen(message, f"❌ Товар <code>{pid}</code> не найден.", reply_markup=_back_to_menu_kb())
        return
    await edit_screen(message, _product_text(item), reply_markup=product_keyboard(pid, item))


# ── ConversationHandler: поиск (/find + callback) ──────────────────────────


@admin_only_cb
async def find_start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = await send_screen(update, context, "🔍 <b>Поиск товара</b>\n\nВведите запрос:")
    context.user_data["_find_msg"] = msg.message_id
    return FIND_WAIT


@admin_only_cb
async def find_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    msg = query.message
    await edit_screen(
        msg,
        "🔍 <b>Поиск товара</b>\n\n<blockquote>Введите название, категорию или артикул:</blockquote>",
        reply_markup=_cancel_kb("cat_menu"),
    )
    context.user_data["_find_msg_id"] = msg.message_id
    context.user_data["_find_chat_id"] = msg.chat_id
    return FIND_WAIT


async def find_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if ADMIN_IDS and update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    query_text = (update.message.text or "").strip()
    try:
        await update.message.delete()
    except Exception:
        pass

    results = find_products(query_text, limit=10)
    context.user_data[_FIND_RESULTS] = [i["id"] for i in results]

    chat_id = context.user_data.pop("_find_chat_id", None)
    msg_id  = context.user_data.pop("_find_msg_id", None)

    if chat_id and msg_id:
        try:
            msg = await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text="⏳", parse_mode="HTML",
            )
        except Exception:
            msg = await context.bot.send_message(chat_id=chat_id, text="⏳", parse_mode="HTML")
    else:
        msg = await context.bot.send_message(
            chat_id=update.effective_chat.id, text="⏳", parse_mode="HTML"
        )

    await show_find_results(msg, results)
    return ConversationHandler.END


async def find_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        await show_catalog_menu(query.message)
    return ConversationHandler.END


# ── ConversationHandler: редактирование цены ─────────────────────────────


@admin_only_cb
async def price_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    pid = query.data[len("cat_price_"):]
    item = get_product(pid)
    if not item:
        await query.message.reply_text("❌ Товар не найден.")
        return ConversationHandler.END

    context.user_data[_PRICE_PID_KEY]    = pid
    context.user_data["_price_msg_id"]   = query.message.message_id
    context.user_data["_price_chat_id"]  = query.message.chat_id

    current = format_price(item.get("price"))
    await edit_screen(
        query.message,
        f"✏️ <b>Изменить цену</b>\n\n"
        f"<blockquote>Товар: {item['name'][:50]}\n"
        f"Текущая цена: <b>{current}</b> / {item.get('unit','т')}</blockquote>\n\n"
        f"Введите новую цену в ₽ (или <code>0</code> → «По запросу»):",
        reply_markup=_cancel_kb(f"cat_view_{pid}"),
    )
    return PRICE_WAIT


async def price_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if ADMIN_IDS and update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END

    text = (update.message.text or "").strip()
    try:
        await update.message.delete()
    except Exception:
        pass

    pid = context.user_data.pop(_PRICE_PID_KEY, None)
    chat_id = context.user_data.pop("_price_chat_id", None)
    msg_id  = context.user_data.pop("_price_msg_id", None)

    try:
        val = int(text.replace(" ", "").replace(",", ""))
        new_price = None if val == 0 else val
        if new_price is not None and new_price < 0:
            raise ValueError
    except ValueError:
        if chat_id and msg_id:
            try:
                m = await context.bot.send_message(chat_id, "❌ Неверный формат. Введите число (₽).")
                import asyncio; await asyncio.sleep(3); await m.delete()
            except Exception:
                pass
        return ConversationHandler.END

    if pid:
        update_price(pid, new_price, user_id=update.effective_user.id)
        item = get_product(pid)
        result_text = (
            f"✅ Цена обновлена: <b>{format_price(new_price)}</b>"
            + (f" / {item['unit']}" if item else "")
        )
    else:
        result_text = "❌ Ошибка: товар не найден."

    if chat_id and msg_id:
        try:
            msg = await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=result_text, parse_mode="HTML",
            )
            if pid and item:
                await show_product(msg, pid)
        except Exception:
            pass
    return ConversationHandler.END


async def price_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.pop(_PRICE_PID_KEY, None)
    pid = query.data[len("cat_view_"):]
    await show_product(query.message, pid)
    return ConversationHandler.END


# ── ConversationHandler: добавление товара ────────────────────────────────


@admin_only_cb
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["_add_chat_id"] = query.message.chat_id
    context.user_data["_add_msg_id"]  = query.message.message_id
    await edit_screen(
        query.message,
        "➕ <b>Добавить товар</b>\n\n<blockquote>Шаг 1/6: Введите название товара:</blockquote>",
        reply_markup=_cancel_kb("cat_menu"),
    )
    return ADD_NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if ADMIN_IDS and update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    name = (update.message.text or "").strip()
    try:
        await update.message.delete()
    except Exception:
        pass
    if not name:
        return ADD_NAME
    context.user_data["_add_name"] = name

    cats = get_categories()[:12]
    cat_buttons = [
        [InlineKeyboardButton(c[:40], callback_data=f"add_cat_{i}")]
        for i, c in enumerate(cats)
    ]
    context.user_data["_add_cats"] = cats
    cat_buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="cat_menu")])

    chat_id = context.user_data.get("_add_chat_id")
    msg_id  = context.user_data.get("_add_msg_id")
    try:
        msg = await context.bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id,
            text=(
                f"➕ <b>Добавить товар</b>\n\n"
                f"<blockquote>Шаг 2/6: Выберите категорию:</blockquote>"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(cat_buttons),
        )
    except Exception:
        pass
    return ADD_CAT


async def add_cat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    idx = int(query.data[len("add_cat_"):])
    cats = context.user_data.get("_add_cats", [])
    if idx < len(cats):
        context.user_data["_add_cat"] = cats[idx]
    await edit_screen(
        query.message,
        "➕ <b>Добавить товар</b>\n\n<blockquote>Шаг 3/6: Введите цену в ₽ (или <code>0</code> → «По запросу»):</blockquote>",
        reply_markup=_cancel_kb("cat_menu"),
    )
    return ADD_PRICE


async def add_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if ADMIN_IDS and update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    text = (update.message.text or "").strip()
    try:
        await update.message.delete()
    except Exception:
        pass
    try:
        val = int(text.replace(" ", "").replace(",", ""))
        context.user_data["_add_price"] = None if val == 0 else val
    except ValueError:
        return ADD_PRICE

    chat_id = context.user_data.get("_add_chat_id")
    msg_id  = context.user_data.get("_add_msg_id")
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id,
            text="➕ <b>Добавить товар</b>\n\n<blockquote>Шаг 4/6: Единица измерения (т / шт / м / комп):</blockquote>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("т",    callback_data="add_unit_т"),
                    InlineKeyboardButton("шт",   callback_data="add_unit_шт"),
                    InlineKeyboardButton("м",    callback_data="add_unit_м"),
                    InlineKeyboardButton("комп", callback_data="add_unit_комп"),
                ],
                [InlineKeyboardButton("❌ Отмена", callback_data="cat_menu")],
            ]),
        )
    except Exception:
        pass
    return ADD_UNIT


async def add_unit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    unit = query.data[len("add_unit_"):]
    context.user_data["_add_unit"] = unit

    await edit_screen(
        query.message,
        "➕ <b>Добавить товар</b>\n\n"
        "<blockquote>Шаг 5/6: Вес за единицу (кг). "
        "Пустая строка / 0 / <code>skip</code> — пропустить.</blockquote>",
        reply_markup=_cancel_kb("cat_menu"),
    )
    return ADD_WEIGHT


def _parse_optional_float(text: str) -> Optional[float]:
    """Парсит вход для weight/length. Пустая строка / '0' / 'skip' → None."""
    t = (text or "").strip().lower().replace(",", ".")
    if t in ("", "0", "skip", "-"):
        return None
    try:
        val = float(t)
        if val <= 0:
            return None
        return val
    except ValueError:
        return None


async def add_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if ADMIN_IDS and update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    text = (update.message.text or "").strip()
    try:
        await update.message.delete()
    except Exception:
        pass
    context.user_data["_add_weight"] = _parse_optional_float(text)

    chat_id = context.user_data.get("_add_chat_id")
    msg_id  = context.user_data.get("_add_msg_id")
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id,
            text=(
                "➕ <b>Добавить товар</b>\n\n"
                "<blockquote>Шаг 6/6: Длина (м). "
                "Пустая строка / 0 / <code>skip</code> — пропустить.</blockquote>"
            ),
            parse_mode="HTML",
            reply_markup=_cancel_kb("cat_menu"),
        )
    except Exception:
        pass
    return ADD_LENGTH


async def add_length(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if ADMIN_IDS and update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    text = (update.message.text or "").strip()
    try:
        await update.message.delete()
    except Exception:
        pass
    length_m = _parse_optional_float(text)

    name   = context.user_data.pop("_add_name",   "Без названия")
    cat    = context.user_data.pop("_add_cat",    "—")
    price  = context.user_data.pop("_add_price",  None)
    unit   = context.user_data.pop("_add_unit",   "т")
    weight = context.user_data.pop("_add_weight", None)
    context.user_data.pop("_add_cats", None)

    item = add_product(
        name, cat, price, unit,
        weight_per_unit=weight,
        length_m=length_m,
        user_id=update.effective_user.id,
    )

    chat_id = context.user_data.get("_add_chat_id")
    msg_id  = context.user_data.get("_add_msg_id")
    extras = []
    if weight is not None:
        extras.append(f"Вес: {weight} кг/{unit}")
    if length_m is not None:
        extras.append(f"Длина: {length_m} м")
    extras_str = ("\n" + "\n".join(extras)) if extras else ""

    result = (
        f"✅ <b>Товар добавлен</b>\n\n"
        f"<blockquote>ID: <code>{item['id']}</code>\n"
        f"Название: {name}\n"
        f"Категория: {cat}\n"
        f"Цена: {format_price(price)} / {unit}"
        f"{extras_str}</blockquote>"
    )
    try:
        if chat_id and msg_id:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=result, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👁 Открыть",  callback_data=f"cat_view_{item['id']}")],
                    [InlineKeyboardButton("◀️ Каталог", callback_data="cat_menu")],
                ]),
            )
    except Exception:
        pass
    return ConversationHandler.END


# ── Удаление товара ───────────────────────────────────────────────────────


async def _show_delete_confirm(message: Message, pid: str) -> None:
    item = get_product(pid)
    name = item["name"] if item else pid
    await edit_screen(
        message,
        f"🗑 <b>Удалить товар?</b>\n\n<blockquote>{name}\n<code>{pid}</code></blockquote>",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Удалить", callback_data=f"cat_del_confirm_{pid}"),
                InlineKeyboardButton("❌ Отмена",  callback_data=f"cat_view_{pid}"),
            ],
        ]),
    )


# ── CSV импорт ────────────────────────────────────────────────────────────


async def csv_info(message: Message) -> None:
    text = (
        "📥 <b>Импорт цен из CSV</b>\n\n"
        "<blockquote>Отправьте .csv файл с колонками:\n"
        "<code>id,price</code>  или  <code>name,price</code>\n\n"
        "price = 0 → «По запросу»\n"
        "Разделитель: запятая или точка с запятой</blockquote>"
    )
    await edit_screen(message, text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Каталог", callback_data="cat_menu")],
    ]))


async def handle_csv_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if ADMIN_IDS and update.effective_user.id not in ADMIN_IDS:
        return
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".csv"):
        return

    # P10: лимит размера CSV — 5 MB
    if doc.file_size and doc.file_size > 5 * 1024 * 1024:
        await update.message.reply_text("❌ Файл слишком большой (макс 5 MB).")
        return

    await update.message.reply_text("⏳ Обрабатываю CSV...")
    try:
        file = await context.bot.get_file(doc.file_id)
        raw = await file.download_as_bytearray()
        content = raw.decode("utf-8-sig")
        # нормализуем разделитель
        if ";" in content.split("\n")[0]:
            content = content.replace(";", ",")
        updates, errors = parse_csv_prices(content)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка чтения файла: {e}")
        return

    if errors and not updates:
        await update.message.reply_text("❌ " + "\n".join(errors[:5]))
        return

    count = bulk_update_prices(updates, user_id=update.effective_user.id)
    result = (
        f"✅ <b>Импорт завершён</b>\n\n"
        f"<blockquote>Обновлено цен: <b>{count}</b>\n"
        f"Строк в файле: {len(updates)}</blockquote>"
    )
    if errors:
        result += "\n\n<blockquote>⚠️ Ошибки:\n" + "\n".join(f"  · {e}" for e in errors[:5]) + "</blockquote>"
    await update.message.reply_text(result, parse_mode="HTML")


# ── Callback роутер каталога ──────────────────────────────────────────────


async def handle_catalog_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data  = query.data
    msg   = query.message
    user_id = query.from_user.id if query.from_user else None

    if data == "cat_menu":
        await show_catalog_menu(msg)

    elif data == "cat_stock":
        await show_stock(msg)

    elif data == "cat_csv_info":
        await csv_info(msg)

    elif data.startswith("cat_view_"):
        pid = data[len("cat_view_"):]
        await show_product(msg, pid)

    elif data == "cat_find_back":
        pids = context.user_data.get(_FIND_RESULTS, [])
        from bot.services.catalog import get_product as _gp
        results = [_gp(p) for p in pids if _gp(p)]
        await show_find_results(msg, results)

    # ── Quick-adjust цены: cat_adj_<pid>_<pct> ────────────────────────────
    elif data.startswith("cat_adj_"):
        rest = data[len("cat_adj_"):]
        # pct — последний токен после последнего '_', может быть отрицательным
        idx = rest.rfind("_")
        if idx == -1:
            await query.answer("❌ Неверный формат.", show_alert=False)
            return
        pid = rest[:idx]
        try:
            pct = float(rest[idx + 1:])
        except ValueError:
            await query.answer("❌ Неверный процент.", show_alert=False)
            return
        ok, old, new = quick_adjust_price(pid, pct, user_id=user_id)
        if not ok:
            await query.answer("⚠️ Цена не задана или товар не найден.", show_alert=True)
            return
        await query.answer(f"✅ {format_price(old)} → {format_price(new)}")
        await show_product(msg, pid)

    # ── По запросу (цена → None): cat_req_<pid> ───────────────────────────
    elif data.startswith("cat_req_"):
        pid = data[len("cat_req_"):]
        ok = set_price_request(pid, user_id=user_id)
        if not ok:
            await query.answer("❌ Товар не найден.", show_alert=True)
            return
        await query.answer("✅ Цена сброшена → «По запросу»")
        await show_product(msg, pid)

    # ── Toggle in_stock: cat_stock_<pid> ──────────────────────────────────
    elif data.startswith("cat_stock_"):
        pid = data[len("cat_stock_"):]
        item = get_product(pid)
        if not item:
            await query.answer("❌ Товар не найден.", show_alert=True)
            return
        new_val = not bool(item.get("in_stock"))
        set_in_stock(pid, new_val, user_id=user_id)
        await query.answer("🟢 В наличии" if new_val else "🔴 Снят с наличия")
        await show_product(msg, pid)

    elif data.startswith("cat_del_"):
        if data.startswith("cat_del_confirm_"):
            pid = data[len("cat_del_confirm_"):]
            ok = delete_product(pid, user_id=user_id)
            text = f"✅ Товар <code>{pid}</code> удалён." if ok else f"❌ Товар <code>{pid}</code> не найден."
            await edit_screen(msg, text, reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Каталог", callback_data="cat_menu")],
            ]))
        else:
            pid = data[len("cat_del_"):]
            await _show_delete_confirm(msg, pid)


# ── /markup команда ───────────────────────────────────────────────────────


@admin_only
async def markup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Использование: /markup <категория> <процент>"""
    args = context.args or []
    if len(args) < 2:
        msg = await send_screen(update, context,
            "ℹ️ Использование: <code>/markup &lt;категория&gt; &lt;процент&gt;</code>\n\n"
            "Пример: <code>/markup «Рельсы широкой колеи» 5</code>"
        )
        return
    try:
        pct = float(args[-1])
        cat = " ".join(args[:-1])
    except ValueError:
        await send_screen(update, context, "❌ Неверный процент.")
        return
    count = apply_markup(cat, pct, user_id=update.effective_user.id)
    if count == 0:
        # P8: возможно опечатка в категории — покажем существующие
        cats_list = "\n".join(f"  · {c}" for c in get_categories()[:8]) or "  (нет категорий)"
        await send_screen(update, context,
            f"⚠️ <b>Предупреждение</b>: ни одна позиция не обновлена.\n"
            f"Возможно, опечатка в названии категории «{cat}» либо у всех её товаров цена не задана.\n\n"
            f"<blockquote><b>Существующие категории (топ-8):</b>\n{cats_list}</blockquote>"
        )
        return
    await send_screen(update, context,
        f"✅ <b>Наценка применена</b>\n\n"
        f"<blockquote>Категория: {cat}\n"
        f"Наценка: +{pct}%\n"
        f"Обновлено позиций: <b>{count}</b></blockquote>"
    )


@admin_only
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Использование: /price <id> <цена>"""
    args = context.args or []
    if len(args) < 2:
        await send_screen(update, context,
            "ℹ️ Использование: <code>/price &lt;id&gt; &lt;цена&gt;</code>\n"
            "Цена 0 = «По запросу»"
        )
        return
    pid = args[0]
    try:
        val = int(args[1])
        new_price = None if val == 0 else val
    except ValueError:
        await send_screen(update, context, "❌ Неверная цена.")
        return
    ok = update_price(pid, new_price, user_id=update.effective_user.id)
    if ok:
        await send_screen(update, context,
            f"✅ <code>{pid}</code> → {format_price(new_price)}"
        )
    else:
        await send_screen(update, context, f"❌ Товар <code>{pid}</code> не найден.")


# ── ConversationHandlers (фабрики) ────────────────────────────────────────


def make_find_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("find", find_start_cmd),
            CallbackQueryHandler(find_start_cb, pattern="^cat_find$"),
        ],
        states={
            FIND_WAIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, find_input),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(find_cancel, pattern="^cat_menu$"),
        ],
        per_chat=True,
        per_user=True,
    )


def make_price_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(price_edit_start, pattern=r"^cat_price_.+$"),
        ],
        states={
            PRICE_WAIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, price_input),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(price_cancel, pattern=r"^cat_view_.+$"),
        ],
        per_chat=True,
        per_user=True,
    )


def make_add_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_start, pattern="^cat_add$"),
        ],
        states={
            ADD_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_CAT:    [CallbackQueryHandler(add_cat_callback, pattern=r"^add_cat_\d+$")],
            ADD_PRICE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_price)],
            ADD_UNIT:   [CallbackQueryHandler(add_unit_callback, pattern=r"^add_unit_")],
            ADD_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_weight)],
            ADD_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_length)],
        },
        fallbacks=[
            CallbackQueryHandler(find_cancel, pattern="^cat_menu$"),
        ],
        per_chat=True,
        per_user=True,
    )


# ── /instock команда ──────────────────────────────────────────────────────


def _parse_bool(s: str) -> Optional[bool]:
    """Парсит true/false/1/0/yes/no/да/нет."""
    s = s.strip().lower()
    if s in ("true", "1", "yes", "y", "да", "+"):
        return True
    if s in ("false", "0", "no", "n", "нет", "-"):
        return False
    return None


@admin_only
async def instock_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Использование:
      /instock <id> <true|false>           — одиночный
      /instock all <true|false>            — массово все позиции
      /instock «Категория» <true|false>    — массово в категории
    """
    args = context.args or []
    if len(args) < 2:
        await send_screen(update, context,
            "ℹ️ Использование:\n"
            "<code>/instock &lt;id&gt; true|false</code>\n"
            "<code>/instock all true|false</code>\n"
            "<code>/instock «Категория» true|false</code>"
        )
        return

    # последний аргумент — bool, всё что слева — id или категория
    value = _parse_bool(args[-1])
    if value is None:
        await send_screen(update, context, "❌ Последний аргумент должен быть true/false.")
        return

    target = " ".join(args[:-1]).strip().strip("«»\"'")
    user_id = update.effective_user.id

    # all → массовая операция без фильтра по категории
    if target.lower() == "all":
        count = bulk_set_in_stock(value, category=None, user_id=user_id)
        await send_screen(update, context,
            f"✅ <b>Массовое обновление</b>\n\n"
            f"<blockquote>Установлено in_stock={value}\n"
            f"Изменено позиций: <b>{count}</b></blockquote>"
        )
        return

    # Одиночный товар? — пробуем как id
    item = get_product(target)
    if item:
        ok = set_in_stock(target, value, user_id=user_id)
        if ok:
            await send_screen(update, context,
                f"✅ <code>{target}</code> → in_stock={value}"
            )
        else:
            await send_screen(update, context, f"❌ Товар <code>{target}</code> не найден.")
        return

    # Иначе — трактуем как название категории
    cats = get_categories()
    if target not in cats:
        cats_list = "\n".join(f"  · {c}" for c in cats[:8]) or "  (нет категорий)"
        await send_screen(update, context,
            f"❌ Товар или категория «{target}» не найдены.\n\n"
            f"<blockquote><b>Существующие категории (топ-8):</b>\n{cats_list}</blockquote>"
        )
        return

    count = bulk_set_in_stock(value, category=target, user_id=user_id)
    await send_screen(update, context,
        f"✅ <b>Массовое обновление по категории</b>\n\n"
        f"<blockquote>Категория: {target}\n"
        f"in_stock={value}\n"
        f"Изменено позиций: <b>{count}</b></blockquote>"
    )
