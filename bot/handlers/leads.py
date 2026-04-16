"""
CRM-lite: экраны заявок в боте.
"""
import json
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from bot.config import ADMIN_IDS
from bot.middleware.auth import admin_only
from bot.services.leads import (
    STATUS_LABELS, db_exists, get_lead, get_lead_stats,
    get_leads, save_comment, update_lead_status,
)
from bot.utils.ui import SECT_MSG_KEY, edit_screen, send_screen

log = logging.getLogger(__name__)

# user_data key для ожидания текстового комментария
COMMENT_KEY = "comment_pending"

_SOURCE_NAMES = {
    'order':      '📋 Заявка',
    'modal':      '📋 Форма',
    'callback':   '📞 Перезвоните',
    'contacts':   '📬 Контакты',
    'calculator': '🔢 Калькулятор',
    'cart':       '🛒 Корзина',
    'quick':      '⚡ Быстрый',
}

_STATUS_ICON = {
    'new': '🆕', 'called': '📞', 'kp': '📄', 'done': '✅', 'reject': '❌',
}


# ── Builders ───────────────────────────────────────────────────────────────


def _fmt_row(lead: dict) -> str:
    ts   = lead['ts'][5:16].replace('T', ' ')
    icon = _STATUS_ICON.get(lead['status'], '?')
    name = (lead['name'] or '?')[:18]
    src  = _SOURCE_NAMES.get(lead.get('source', ''), '')
    src_tag = f'<i>[{src}]</i> ' if src else ''
    return f"{icon} <code>#{lead['id']}</code> {src_tag}<b>{name}</b>  <i>{ts}</i>"


def _build_leads_text(leads: list, status_filter) -> str:
    stats = get_lead_stats()
    label = STATUS_LABELS.get(status_filter, 'Все') if status_filter else 'Все'

    counts_line = (
        f"Всего: <b>{stats['total']}</b>   "
        f"🆕 {stats['new']}  📞 {stats['called']}  "
        f"📄 {stats['kp']}  ✅ {stats['done']}  ❌ {stats['reject']}"
    )
    header = f"📬 <b>Заявки</b>\n\n<blockquote>{counts_line}</blockquote>\n"

    if not leads:
        return header + f"\n<i>Нет заявок — {label}</i>"

    rows = '\n'.join(_fmt_row(l) for l in leads)
    return f"{header}\n<b>Фильтр: {label}</b>\n\n{rows}"


def _build_lead_detail_text(lead: dict) -> str:
    ts           = lead['ts'][:16].replace('T', ' ')
    status_label = STATUS_LABELS.get(lead['status'], lead['status'])
    src          = _SOURCE_NAMES.get(lead.get('source', ''), lead.get('source', '') or 'Сайт')

    meta = f"🕐 {ts}  |  📍 {src}\nСтатус: {status_label}"
    text = (
        f"📬 <b>Заявка <code>#{lead['id']}</code></b>\n\n"
        f"<blockquote>{meta}</blockquote>\n\n"
        f"👤 <b>{lead['name']}</b>\n"
        f"📞 {lead['contact']}"
    )

    if lead.get('message'):
        text += f"\n💬 <i>{lead['message']}</i>"

    if lead.get('items_json'):
        try:
            items = json.loads(lead['items_json'])
            if items:
                lines = [
                    f"  {i+1}. {it.get('name','?')} — <b>{it.get('qty',1)}</b> {it.get('unit','т')}"
                    for i, it in enumerate(items[:5])
                ]
                block = '\n'.join(lines)
                if len(items) > 5:
                    block += f'\n  <i>...ещё {len(items)-5}</i>'
                text += f"\n\n<blockquote>🛒 <b>Состав:</b>\n{block}</blockquote>"
        except Exception:
            pass

    if lead.get('comment'):
        text += f"\n\n<blockquote>📝 <b>Комментарий:</b>\n{lead['comment']}</blockquote>"

    return text


# ── Клавиатуры ─────────────────────────────────────────────────────────────


def _leads_list_keyboard(leads: list, status_filter) -> InlineKeyboardMarkup:
    filters = [('Все', None), ('Новые', 'new'), ('КП', 'kp'), ('✅', 'done')]
    filter_row = []
    for label, fval in filters:
        prefix = '• ' if fval == status_filter else ''
        filter_row.append(
            InlineKeyboardButton(prefix + label,
                                 callback_data=f"leads_filter_{fval or 'all'}")
        )

    lead_rows = []
    for lead in leads[:5]:
        icon  = _STATUS_ICON.get(lead['status'], '?')
        short = (lead['name'] or '?')[:14]
        lead_rows.append([InlineKeyboardButton(
            f"{icon} #{lead['id']} {short}",
            callback_data=f"lead_view_{lead['id']}",
        )])

    return InlineKeyboardMarkup(
        lead_rows + [filter_row, [InlineKeyboardButton("◀️ Меню", callback_data="menu")]]
    )


def _lead_detail_keyboard(lead_id: int, current_status: str) -> InlineKeyboardMarkup:
    actions = [
        ('📞 Позвонил',  'called'),
        ('📄 Выслал КП', 'kp'),
        ('✅ Сделка',    'done'),
        ('❌ Отказ',     'reject'),
    ]
    row = [
        InlineKeyboardButton(lbl, callback_data=f"lead_{st}_{lead_id}")
        for lbl, st in actions
        if st != current_status
    ]
    return InlineKeyboardMarkup([
        row[:2],
        row[2:],
        [
            InlineKeyboardButton("◀️ Список", callback_data="leads_filter_all"),
            InlineKeyboardButton("◀️ Меню",   callback_data="menu"),
        ],
    ])


def _lead_close_keyboard(lead_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✍️ Комментарий",      callback_data=f"lead_comment_{lead_id}"),
            InlineKeyboardButton("🗑 Без комментария",   callback_data=f"lead_nocomment_{lead_id}"),
        ],
        [InlineKeyboardButton("◀️ Детали", callback_data=f"lead_view_{lead_id}")],
    ])


# ── Экраны ─────────────────────────────────────────────────────────────────


async def show_leads(message: Message, status_filter=None) -> None:
    if not db_exists():
        await edit_screen(
            message,
            "📬 <b>Заявки</b>\n\n<blockquote>⚠️ База данных не найдена.</blockquote>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("◀️ Меню", callback_data="menu")]]
            ),
        )
        return
    leads = get_leads(status=status_filter, limit=15)
    await edit_screen(
        message,
        _build_leads_text(leads, status_filter),
        reply_markup=_leads_list_keyboard(leads, status_filter),
    )


async def show_lead_detail(message: Message, lead_id: int) -> None:
    lead = get_lead(lead_id)
    if not lead:
        await edit_screen(
            message,
            f"❌ Заявка #{lead_id} не найдена.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("◀️ Список", callback_data="leads_filter_all")]]
            ),
        )
        return
    await edit_screen(
        message,
        _build_lead_detail_text(lead),
        reply_markup=_lead_detail_keyboard(lead_id, lead['status']),
    )


async def show_lead_close_screen(message: Message, lead_id: int) -> None:
    text = (
        f"✅ <b>Заявка <code>#{lead_id}</code> закрыта — Сделка</b>\n\n"
        "<blockquote>Добавьте комментарий или архивируйте без него.\n"
        "Сообщение будет удалено из ленты.</blockquote>"
    )
    await edit_screen(message, text, reply_markup=_lead_close_keyboard(lead_id))


async def show_lead_comment_prompt(
    message: Message, lead_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    context.user_data[COMMENT_KEY] = {
        'lead_id': lead_id,
        'chat_id': message.chat_id,
        'msg_id':  message.message_id,
    }
    text = (
        f"✍️ <b>Комментарий к заявке <code>#{lead_id}</code></b>\n\n"
        "<blockquote>Отправьте следующим сообщением.\n"
        "После этого сообщение будет удалено из ленты.</blockquote>"
    )
    await edit_screen(
        message, text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Отмена", callback_data=f"lead_view_{lead_id}")]]
        ),
    )


# ── Callback роутер ─────────────────────────────────────────────────────────


async def handle_lead_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = update.callback_query.data
    msg  = update.callback_query.message

    if data == "leads" or data == "leads_filter_all":
        await show_leads(msg)

    elif data.startswith("leads_filter_"):
        fval = data[len("leads_filter_"):]
        await show_leads(msg, None if fval == 'all' else fval)

    elif data.startswith("lead_view_"):
        context.user_data.pop(COMMENT_KEY, None)
        lead_id = int(data[len("lead_view_"):])
        await show_lead_detail(msg, lead_id)

    elif data.startswith("lead_done_"):
        lead_id = int(data[len("lead_done_"):])
        update_lead_status(lead_id, 'done')
        await show_lead_close_screen(msg, lead_id)

    elif data.startswith(("lead_called_", "lead_kp_", "lead_reject_")):
        _, status, raw_id = data.split("_", 2)
        lead_id = int(raw_id)
        update_lead_status(lead_id, status)
        await show_lead_detail(msg, lead_id)

    elif data.startswith("lead_nocomment_"):
        lead_id = int(data[len("lead_nocomment_"):])
        context.user_data.pop(SECT_MSG_KEY, None)
        try:
            await msg.delete()
        except Exception:
            pass

    elif data.startswith("lead_comment_"):
        lead_id = int(data[len("lead_comment_"):])
        await show_lead_comment_prompt(msg, lead_id, context)


# ── Обработчик текстового комментария ──────────────────────────────────────


async def handle_comment_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Перехватывает следующее текстовое сообщение после нажатия '✍️ Комментарий'."""
    if ADMIN_IDS and update.effective_user.id not in ADMIN_IDS:
        return

    pending = context.user_data.get(COMMENT_KEY)
    if not pending:
        return

    lead_id  = pending['lead_id']
    chat_id  = pending['chat_id']
    msg_id   = pending['msg_id']
    comment  = (update.message.text or '').strip()[:500]

    if comment:
        save_comment(lead_id, comment)

    # Удаляем сообщение с инструкцией
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        context.user_data.pop(SECT_MSG_KEY, None)
    except Exception:
        pass

    # Удаляем сообщение пользователя с комментарием
    try:
        await update.message.delete()
    except Exception:
        pass

    context.user_data.pop(COMMENT_KEY, None)


# ── Slash-команда ───────────────────────────────────────────────────────────


@admin_only
async def leads_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await send_screen(update, context, "⏳ Загружаю заявки...")
    await show_leads(msg)
