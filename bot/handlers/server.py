import asyncio
import subprocess
from telegram import Update
from telegram.ext import ContextTypes
from bot.middleware.auth import admin_only
from bot.config import SITE_URL, SERVE_SERVICE_NAME, NOTIFY_SERVICE_NAME, CATALOG_PATH
from bot.services.system_info import (
    get_uptime, get_cpu_percent, get_ram, get_disk,
    get_serve_info, get_catalog_count, get_last_commit
)
from bot.services.server_monitor import ping_site


def _run(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip()
    except Exception as e:
        return str(e)


def _svc_line(name: str) -> str:
    info = get_serve_info(name)
    if info["active"]:
        uptime = f", {info['uptime']}" if info["uptime"] else ""
        return f"✅ работает (PID {info['pid']}{uptime})"
    return "❌ не работает"


@admin_only
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Собираю данные...")

    uptime   = get_uptime()
    cpu      = get_cpu_percent()
    ram_u, ram_t   = get_ram()
    disk_u, disk_t = get_disk()
    count    = get_catalog_count(CATALOG_PATH)
    commit   = get_last_commit()

    ram_pct  = round(100 * ram_u / ram_t)  if ram_t  else 0
    disk_pct = round(100 * disk_u / disk_t) if disk_t else 0

    text = (
        "📊 <b>Статус сервера</b>\n\n"
        "🖥 <b>Система:</b>\n"
        f"  Uptime: {uptime}\n"
        f"  CPU: {cpu}\n"
        f"  RAM: {ram_u} / {ram_t} MB ({ram_pct}%)\n"
        f"  Диск: {disk_u} / {disk_t} GB ({disk_pct}%)\n\n"
        "🌐 <b>Сервисы:</b>\n"
        f"  nginx (статика :8080): {_svc_line(SERVE_SERVICE_NAME)}\n"
        f"  rels-notify (API):     {_svc_line(NOTIFY_SERVICE_NAME)}\n\n"
        "📁 <b>Проект:</b>\n"
        f"  catalog.json: {count} позиций\n"
        f"  Последний коммит: {commit}"
    )
    await msg.edit_text(text, parse_mode="HTML")


@admin_only
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(f"🔍 Пингую {SITE_URL}...")
    res = ping_site(SITE_URL)
    if res["ok"]:
        text = f"✅ Сайт отвечает: {res['code']} OK ({res['time_s']:.3f}s)"
    else:
        err = f" ({res['error']})" if res["error"] else f" (код {res['code']})"
        text = f"❌ Сайт не отвечает!{err}"
    await msg.edit_text(text)


@admin_only
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔄 Перезапускаю nginx + rels-notify...")
    _run(f"sudo systemctl restart {SERVE_SERVICE_NAME}")
    _run(f"sudo systemctl restart {NOTIFY_SERVICE_NAME}")

    await asyncio.sleep(3)

    nginx_ok  = _run(f"systemctl is-active {SERVE_SERVICE_NAME}").strip()  == "active"
    notify_ok = _run(f"systemctl is-active {NOTIFY_SERVICE_NAME}").strip() == "active"
    res       = ping_site(SITE_URL, timeout=10)

    if nginx_ok and res["ok"]:
        text = f"✅ Сервер перезапущен, сайт отвечает ({res['time_s']:.3f}s)"
        if not notify_ok:
            text += "\n⚠️ rels-notify не поднялся — проверь /logs"
    elif nginx_ok:
        text = "⚠️ nginx запущен, но сайт не отвечает — проверь /logs"
    else:
        text = "❌ nginx не запустился — проверь /logs"
    await msg.edit_text(text)


@admin_only
async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    n = 30
    if context.args:
        try:
            n = int(context.args[0])
        except ValueError:
            pass

    # nginx + rels-notify логи вместе
    output = _run(
        f"journalctl -u {SERVE_SERVICE_NAME} -u {NOTIFY_SERVICE_NAME} "
        f"--no-pager -n {n} --output=short-monotonic 2>&1"
    )
    if not output:
        output = "(нет логов)"

    if len(output) <= 4000:
        await update.message.reply_text(f"<pre>{_escape(output)}</pre>", parse_mode="HTML")
    else:
        import io
        buf = io.BytesIO(output.encode())
        buf.name = f"logs_{n}.txt"
        await update.message.reply_document(buf, caption=f"Лог: последние {n} строк")


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
