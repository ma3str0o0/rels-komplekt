"""
Хэндлеры управления каталогом: поиск, просмотр, редактирование цен, импорт CSV.
"""
import logging

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
from bot.middleware.auth import admin_only
from bot.services.catalog import (
    add_product, apply_markup, bulk_update_prices, delete_product,
    find_products, get_categories, get_product, get_stock_summary,
    parse_csv_prices, update_price,
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
) = range(8)

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


def product_keyboard(pid: str, show_delete: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("✏️ Изменить цену", callback_data=f"cat_price_{pid}")],
    ]
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
    await edit_screen(message, _product_text(item), reply_markup=product_keyboard(pid))


# ── ConversationHandler: поиск (/find + callback) ──────────────────────────


async def find_start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = await send_screen(update, context, "🔍 <b>Поиск товара</b>\n\nВведите запрос:")
    context.user_data["_find_msg"] = msg.message_id
    return FIND_WAIT


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
        update_price(pid, new_price)
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


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["_add_chat_id"] = query.message.chat_id
    context.user_data["_add_msg_id"]  = query.message.message_id
    await edit_screen(
        query.message,
        "➕ <b>Добавить товар</b>\n\n<blockquote>Шаг 1/4: Введите название товара:</blockquote>",
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
                f"<blockquote>Шаг 2/4: Выберите категорию:</blockquote>"
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
        "➕ <b>Добавить товар</b>\n\n<blockquote>Шаг 3/4: Введите цену в ₽ (или <code>0</code> → «По запросу»):</blockquote>",
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
            text="➕ <b>Добавить товар</b>\n\n<blockquote>Шаг 4/4: Единица измерения (т / шт / м / комп):</blockquote>",
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
    name  = context.user_data.pop("_add_name", "Без названия")
    cat   = context.user_data.pop("_add_cat",  "—")
    price = context.user_data.pop("_add_price", None)
    context.user_data.pop("_add_cats", None)

    item = add_product(name, cat, price, unit)
    result = (
        f"✅ <b>Товар добавлен</b>\n\n"
        f"<blockquote>ID: <code>{item['id']}</code>\n"
        f"Название: {name}\n"
        f"Категория: {cat}\n"
        f"Цена: {format_price(price)} / {unit}</blockquote>"
    )
    await edit_screen(
        query.message, result,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"👁 Открыть", callback_data=f"cat_view_{item['id']}")],
            [InlineKeyboardButton("◀️ Каталог",  callback_data="cat_menu")],
        ]),
    )
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

    count = bulk_update_prices(updates)
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

    elif data.startswith("cat_del_"):
        if data.startswith("cat_del_confirm_"):
            pid = data[len("cat_del_confirm_"):]
            ok = delete_product(pid)
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
    count = apply_markup(cat, pct)
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
    ok = update_price(pid, new_price)
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
            ADD_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_CAT:   [CallbackQueryHandler(add_cat_callback, pattern=r"^add_cat_\d+$")],
            ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_price)],
            ADD_UNIT:  [CallbackQueryHandler(add_unit_callback, pattern=r"^add_unit_")],
        },
        fallbacks=[
            CallbackQueryHandler(find_cancel, pattern="^cat_menu$"),
        ],
        per_chat=True,
        per_user=True,
    )
