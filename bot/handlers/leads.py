"""
CRM-lite: экраны заявок в боте.
"""
import json
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from bot.middleware.auth import admin_only
from bot.services.leads import (
    STATUS_LABELS, db_exists, get_lead, get_lead_stats,
    get_leads, update_lead_status,
)
from bot.utils.ui import edit_screen, send_screen

log = logging.getLogger(__name__)

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
    ts     = lead['ts'][:16].replace('T', ' ')
    icon   = _STATUS_ICON.get(lead['status'], '?')
    name   = (lead['name'] or '?')[:18]
    src    = _SOURCE_NAMES.get(lead.get('source', ''), lead.get('source', '') or '')
    src_tag = f'[{src}] ' if src else ''
    return f"{icon} <code>#{lead['id']}</code> {src_tag}<b>{name}</b> — {ts}"


def _build_leads_text(leads: list, status_filter) -> str:
    stats = get_lead_stats()
    header = (
        f"📬 <b>Заявки</b>  (всего: {stats['total']})\n"
        f"🆕{stats['new']}  📞{stats['called']}  📄{stats['kp']}  "
        f"✅{stats['done']}  ❌{stats['reject']}\n"
    )
    if not leads:
        label = STATUS_LABELS.get(status_filter, 'Все') if status_filter else 'Все'
        return header + f"\n<i>Нет заявок ({label})</i>"

    label = STATUS_LABELS.get(status_filter, 'Все') if status_filter else 'Все'
    rows  = '\n'.join(_fmt_row(l) for l in leads)
    return f"{header}\n<b>Фильтр: {label}</b>\n\n{rows}"


def _leads_list_keyboard(leads: list, status_filter) -> InlineKeyboardMarkup:
    # Кнопки фильтров
    filters = [('Все', None), ('Новые', 'new'), ('КП', 'kp'), ('✅', 'done')]
    filter_row = []
    for label, fval in filters:
        prefix = '• ' if fval == status_filter else ''
        filter_row.append(
            InlineKeyboardButton(prefix + label,
                                 callback_data=f"leads_filter_{fval or 'all'}")
        )

    # Кнопки для первых 5 заявок
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


def _build_lead_detail_text(lead: dict) -> str:
    ts           = lead['ts'][:16].replace('T', ' ')
    status_label = STATUS_LABELS.get(lead['status'], lead['status'])
    src          = _SOURCE_NAMES.get(lead.get('source', ''), lead.get('source', '') or 'Сайт')

    text = (
        f"📬 <b>Заявка #{lead['id']}</b>\n"
        f"🕐 {ts}  |  📍 {src}\n"
        f"Статус: {status_label}\n\n"
        f"👤 <b>{lead['name']}</b>\n"
        f"📞 {lead['contact']}"
    )
    if lead.get('message'):
        text += f"\n💬 {lead['message']}"

    if lead.get('items_json'):
        try:
            items = json.loads(lead['items_json'])
            if items:
                lines = [
                    f"  {i+1}. {it.get('name','?')} — {it.get('qty',1)} {it.get('unit','т')}"
                    for i, it in enumerate(items[:5])
                ]
                text += '\n\n🛒 <b>Состав:</b>\n' + '\n'.join(lines)
                if len(items) > 5:
                    text += f'\n  <i>...ещё {len(items)-5}</i>'
        except Exception:
            pass

    return text


# ── Экраны ─────────────────────────────────────────────────────────────────


async def show_leads(message: Message, status_filter=None) -> None:
    if not db_exists():
        await edit_screen(
            message,
            "📬 <b>Заявки</b>\n\n<i>База данных не найдена.</i>",
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
        lead_id = int(data[len("lead_view_"):])
        await show_lead_detail(msg, lead_id)

    elif data.startswith(("lead_called_", "lead_kp_", "lead_done_", "lead_reject_")):
        # Формат: lead_{status}_{id}
        _, status, raw_id = data.split("_", 2)
        lead_id = int(raw_id)
        update_lead_status(lead_id, status)
        await show_lead_detail(msg, lead_id)


# ── Slash-команда ───────────────────────────────────────────────────────────


@admin_only
async def leads_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await send_screen(update, context, "⏳ Загружаю заявки...")
    await show_leads(msg)
