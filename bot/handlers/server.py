"""
Хэндлеры управления сервером: команды и callback-кнопки.
"""
import asyncio
import io
import subprocess
from datetime import datetime

from telegram import Message, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot.middleware.auth import admin_only
from bot.config import ADMIN_IDS, CATALOG_PATH, NOTIFY_SERVICE_NAME, SERVE_SERVICE_NAME, SITE_URL
from bot.services.system_info import (
    get_catalog_count, get_cpu_percent, get_disk,
    get_last_commit, get_ram, get_serve_info, get_uptime,
)
from bot.services.server_monitor import ping_site
from bot.handlers.keyboards import (
    MENU_TEXT,
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


async def safe_edit(message: Message, text: str, reply_markup=None, parse_mode: str = "HTML") -> None:
    """edit_text с тихой обработкой 'Message is not modified'."""
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise


# ── Builders (чистые функции, возвращают текст) ────────────────────────────


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
            return f"✅ работает (PID {info['pid']}{uptime_str})"
        return "❌ не работает"

    return (
        f"📊 <b>Статус сервера</b>\n"
        f"<i>обновлено {now}</i>\n\n"
        "🖥 <b>Система:</b>\n"
        f"  Uptime: {uptime}\n"
        f"  CPU: {cpu}  ·  RAM: {ram_pct}%  ·  Диск: {disk_pct}%\n\n"
        "🌐 <b>Сервисы:</b>\n"
        f"  nginx (статика :8080): {svc_line(SERVE_SERVICE_NAME)}\n"
        f"  rels-notify (API):     {svc_line(NOTIFY_SERVICE_NAME)}\n\n"
        "📁 <b>Проект:</b>\n"
        f"  catalog.json: {count} позиций\n"
        f"  Последний коммит: {commit}"
    )


def _build_ping_text() -> str:
    now = datetime.now().strftime("%H:%M")
    res = ping_site(SITE_URL)
    if res["ok"]:
        body = f"✅ {SITE_URL} — {res['code']} OK ({res['time_s']:.3f}s)"
    else:
        err  = f" ({res['error']})" if res["error"] else f" (код {res['code']})"
        body = f"❌ Сайт не отвечает!{err}"
    return f"🏓 <b>Пинг сайта</b>\n\n{body}\n<i>Проверено: {now}</i>"


def _build_logs_raw(n: int) -> str:
    output = _run(
        f"journalctl -u {SERVE_SERVICE_NAME} -u {NOTIFY_SERVICE_NAME} "
        f"--no-pager -n {n} --output=short-monotonic 2>&1"
    )
    return output or "(нет логов)"


# ── Callback show-функции (редактируют существующее сообщение) ─────────────


async def show_menu(message: Message) -> None:
    await safe_edit(message, MENU_TEXT, reply_markup=main_menu_keyboard())


async def show_status(message: Message) -> None:
    await safe_edit(message, _build_status_text(), reply_markup=status_keyboard())


async def show_ping(message: Message) -> None:
    await safe_edit(message, _build_ping_text(), reply_markup=ping_keyboard())


async def show_restart_confirm(message: Message) -> None:
    text = "🔄 <b>Перезапуск сервера</b>\n\nВы уверены? Сайт будет недоступен несколько секунд."
    await safe_edit(message, text, reply_markup=restart_confirm_keyboard())


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
    await safe_edit(message, "🔄 Перезапускаю nginx + rels-notify...")
    result = await _execute_restart()
    await safe_edit(message, result, reply_markup=restart_done_keyboard())


async def show_logs(message: Message, n: int = 30) -> None:
    output = _build_logs_raw(n)
    header = f"📋 <b>Логи nginx + rels-notify</b>\n<i>последние {n} строк</i>\n\n"
    text   = header + f"<pre>{_escape(output)}</pre>"
    if len(text) <= 4096:
        await safe_edit(message, text, reply_markup=logs_keyboard())
    else:
        await safe_edit(
            message,
            f"📋 <b>Логи nginx + rels-notify</b>\n\nЛог отправлен файлом ⬇️",
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

    if data == "menu":
        await show_menu(msg)
    elif data in ("status", "refresh_status"):
        await show_status(msg)
    elif data in ("ping", "refresh_ping"):
        await show_ping(msg)
    elif data == "restart":
        await show_restart_confirm(msg)
    elif data == "restart_yes":
        await do_restart(msg)
    elif data == "logs":
        await show_logs(msg, n=30)
    elif data == "logs_100":
        await show_logs(msg, n=100)


# ── Slash-команды (отправляют новое сообщение) ─────────────────────────────


@admin_only
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Собираю данные...")
    await msg.edit_text(_build_status_text(), reply_markup=status_keyboard(), parse_mode="HTML")


@admin_only
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text(f"🔍 Пингую {SITE_URL}...")
    await msg.edit_text(_build_ping_text(), reply_markup=ping_keyboard(), parse_mode="HTML")


@admin_only
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg    = await update.message.reply_text("🔄 Перезапускаю nginx + rels-notify...")
    result = await _execute_restart()
    await msg.edit_text(result, reply_markup=restart_done_keyboard(), parse_mode="HTML")


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
        await update.message.reply_text(text, reply_markup=logs_keyboard(), parse_mode="HTML")
    else:
        await update.message.reply_text(
            "📋 <b>Логи nginx + rels-notify</b>\n\nЛог отправлен файлом ⬇️",
            reply_markup=logs_keyboard(), parse_mode="HTML",
        )
        buf      = io.BytesIO(output.encode())
        buf.name = f"logs_{n}.txt"
        await update.message.reply_document(buf, caption=f"Лог: последние {n} строк")
