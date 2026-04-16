"""
Хэндлеры управления сервером: команды и callback-кнопки.
"""
import asyncio
import io
import subprocess
from datetime import datetime

from telegram import Message, Update
from telegram.ext import ContextTypes

from bot.middleware.auth import admin_only
from bot.config import ADMIN_IDS, CATALOG_PATH, NOTIFY_SERVICE_NAME, SERVE_SERVICE_NAME, SITE_URL
from bot.utils.ui import MENU_MSG_KEY, SECT_MSG_KEY, _delete_safe
from bot.services.system_info import (
    get_catalog_count, get_cpu_percent, get_disk,
    get_last_commit, get_ram, get_serve_info, get_uptime,
)
from bot.services.server_monitor import ping_site
from bot.utils.ui import edit_screen, send_screen
from bot.handlers.metrics import show_stats, show_top_products
from bot.handlers.leads import handle_lead_callback, show_leads
from bot.handlers.keyboards import (
    logs_keyboard, main_menu_keyboard, ping_keyboard,
    restart_confirm_keyboard, restart_done_keyboard, status_keyboard,
)


# ── Утилиты ────────────────────────────────────────────────────────────────


def _run(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip()
    except Exception as e:
        return str(e)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── Builders ────────────────────────────────────────────────────────────────


def _build_status_text() -> str:
    now            = datetime.now().strftime("%H:%M")
    uptime         = get_uptime()
    cpu            = get_cpu_percent()
    ram_u, ram_t   = get_ram()
    disk_u, disk_t = get_disk()
    count          = get_catalog_count(CATALOG_PATH)
    commit         = get_last_commit()

    ram_pct  = round(100 * ram_u / ram_t)  if ram_t  else 0
    disk_pct = round(100 * disk_u / disk_t) if disk_t else 0

    def svc_line(name: str) -> str:
        info = get_serve_info(name)
        if info["active"]:
            uptime_str = f", {info['uptime']}" if info["uptime"] else ""
            return f"✅ работает  <code>PID {info['pid']}</code>{uptime_str}"
        return "❌ не работает"

    return (
        f"📊 <b>Статус сервера</b>  <i>{now}</i>\n\n"
        f"<blockquote>"
        f"🖥  CPU: <b>{cpu}</b>  ·  RAM: <b>{ram_pct}%</b>  ·  Диск: <b>{disk_pct}%</b>\n"
        f"⏱  Uptime: {uptime}"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"🌐 nginx (статика):     {svc_line(SERVE_SERVICE_NAME)}\n"
        f"🔧 rels-notify (API): {svc_line(NOTIFY_SERVICE_NAME)}"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"📁 Каталог: <b>{count}</b> позиций\n"
        f"📝 Коммит: {commit}"
        f"</blockquote>"
    )


def _build_ping_text() -> str:
    now = datetime.now().strftime("%H:%M")
    res = ping_site(SITE_URL)
    if res["ok"]:
        body = f"✅ Сайт отвечает  <code>{res['code']}</code>  {res['time_s']:.3f}s\n{SITE_URL}"
    else:
        err  = f" ({res['error']})" if res["error"] else f" (код {res['code']})"
        body = f"❌ Сайт не отвечает{err}\n{SITE_URL}"
    return f"🏓 <b>Пинг сайта</b>  <i>{now}</i>\n\n<blockquote>{body}</blockquote>"


def _build_logs_raw(n: int) -> str:
    output = _run(
        f"journalctl -u {SERVE_SERVICE_NAME} -u {NOTIFY_SERVICE_NAME} "
        f"--no-pager -n {n} --output=short-monotonic 2>&1"
    )
    return output or "(нет логов)"


# ── Callback show-функции (редактируют текущее сообщение) ──────────────────


async def show_status(message: Message) -> None:
    await edit_screen(message, _build_status_text(), reply_markup=status_keyboard())


async def show_ping(message: Message) -> None:
    await edit_screen(message, _build_ping_text(), reply_markup=ping_keyboard())


async def show_restart_confirm(message: Message) -> None:
    text = "🔄 <b>Перезапуск сервера</b>\n\nВы уверены? Сайт будет недоступен несколько секунд."
    await edit_screen(message, text, reply_markup=restart_confirm_keyboard())


async def _execute_restart() -> str:
    """Перезапускает сервисы, возвращает текст результата."""
    _run(f"sudo systemctl restart {SERVE_SERVICE_NAME}")
    _run(f"sudo systemctl restart {NOTIFY_SERVICE_NAME}")
    await asyncio.sleep(3)
    nginx_ok  = _run(f"systemctl is-active {SERVE_SERVICE_NAME}").strip() == "active"
    notify_ok = _run(f"systemctl is-active {NOTIFY_SERVICE_NAME}").strip() == "active"
    res       = ping_site(SITE_URL, timeout=10)
    if nginx_ok and res["ok"]:
        result = f"✅ Сервер перезапущен, сайт отвечает ({res['time_s']:.3f}s)"
        if not notify_ok:
            result += "\n⚠️ rels-notify не поднялся — проверь /logs"
    elif nginx_ok:
        result = "⚠️ nginx запущен, но сайт не отвечает — проверь /logs"
    else:
        result = "❌ nginx не запустился — проверь /logs"
    return result


async def do_restart(message: Message) -> None:
    await edit_screen(message, "🔄 Перезапускаю nginx + rels-notify...")
    result = await _execute_restart()
    await edit_screen(message, result, reply_markup=restart_done_keyboard())


async def show_logs(message: Message, n: int = 30) -> None:
    output = _build_logs_raw(n)
    header = f"📋 <b>Логи nginx + rels-notify</b>\n<i>последние {n} строк</i>\n\n"
    text   = header + f"<pre>{_escape(output)}</pre>"
    if len(text) <= 4096:
        await edit_screen(message, text, reply_markup=logs_keyboard())
    else:
        await edit_screen(
            message,
            "📋 <b>Логи nginx + rels-notify</b>\n\nЛог отправлен файлом ⬇️",
            reply_markup=logs_keyboard(),
        )
        buf      = io.BytesIO(output.encode())
        buf.name = f"logs_{n}.txt"
        await message.reply_document(buf, caption=f"Лог: последние {n} строк")


# ── Callback роутер ────────────────────────────────────────────────────────


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if ADMIN_IDS and update.effective_user.id not in ADMIN_IDS:
        await query.message.reply_text("🔒 Доступ запрещён.")
        return

    data = query.data
    msg  = query.message

    # ── «Меню» — закрываем секцию, постоянное меню остаётся ──────────────
    if data == "menu":
        context.user_data.pop(SECT_MSG_KEY, None)
        try:
            await msg.delete()
        except Exception:
            pass
        return

    # ── Хелпер: из меню — открываем новое сообщение; внутри секции — редактируем
    is_menu = context.user_data.get(MENU_MSG_KEY) == msg.message_id

    async def _open(loading: str) -> Message:
        if is_menu:
            old = context.user_data.pop(SECT_MSG_KEY, None)
            if old:
                try:
                    await context.bot.delete_message(msg.chat_id, old)
                except Exception:
                    pass
            new_msg = await msg.chat.send_message(loading, parse_mode='HTML')
            context.user_data[SECT_MSG_KEY] = new_msg.message_id
            return new_msg
        return msg

    # ── Роутинг ────────────────────────────────────────────────────────────
    if data in ("status", "refresh_status"):
        m = await _open("⏳ Собираю данные...")
        await show_status(m)
    elif data in ("ping", "refresh_ping"):
        m = await _open(f"🔍 Пингую {SITE_URL}...")
        await show_ping(m)
    elif data == "restart":
        m = await _open("🔄 Подтверждение перезапуска...")
        await show_restart_confirm(m)
    elif data == "restart_yes":
        await do_restart(msg)
    elif data == "logs":
        m = await _open("📋 Загружаю логи...")
        await show_logs(m, n=30)
    elif data == "logs_100":
        await show_logs(msg, n=100)
    elif data.startswith("stats_"):
        days = int(data.split("_")[1])
        m = await _open("📈 Загружаю аналитику...")
        await show_stats(m, days=days)
    elif data.startswith("top_"):
        days = int(data.split("_")[1])
        m = await _open("🏷 Загружаю топ товаров...")
        await show_top_products(m, days=days)
    elif data == "leads":
        m = await _open("📬 Загружаю заявки...")
        await show_leads(m)
    elif data.startswith("leads_") or data.startswith("lead_"):
        await handle_lead_callback(update, context)


# ── Slash-команды (удаляют команду + старое сообщение, отправляют новое) ───


@admin_only
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await send_screen(update, context, "⏳ Собираю данные...")
    await edit_screen(msg, _build_status_text(), reply_markup=status_keyboard())


@admin_only
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await send_screen(update, context, f"🔍 Пингую {SITE_URL}...")
    await edit_screen(msg, _build_ping_text(), reply_markup=ping_keyboard())


@admin_only
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg    = await send_screen(update, context, "🔄 Перезапускаю nginx + rels-notify...")
    result = await _execute_restart()
    await edit_screen(msg, result, reply_markup=restart_done_keyboard())


@admin_only
async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    n = 30
    if context.args:
        try:
            n = int(context.args[0])
        except ValueError:
            pass
    output = _build_logs_raw(n)
    header = f"📋 <b>Логи nginx + rels-notify</b>\n<i>последние {n} строк</i>\n\n"
    text   = header + f"<pre>{_escape(output)}</pre>"
    if len(text) <= 4096:
        await send_screen(update, context, text, reply_markup=logs_keyboard())
    else:
        await send_screen(
            update, context,
            "📋 <b>Логи nginx + rels-notify</b>\n\nЛог отправлен файлом ⬇️",
            reply_markup=logs_keyboard(),
        )
        buf      = io.BytesIO(output.encode())
        buf.name = f"logs_{n}.txt"
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=buf,
            caption=f"Лог: последние {n} строк",
        )
