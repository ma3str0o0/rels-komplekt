import subprocess
from telegram import Update
from telegram.ext import ContextTypes
from bot.middleware.auth import admin_only
from bot.config import SITE_URL, SERVE_SERVICE_NAME, CATALOG_PATH
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


@admin_only
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Собираю данные...")

    uptime  = get_uptime()
    cpu     = get_cpu_percent()
    ram_u, ram_t = get_ram()
    disk_u, disk_t = get_disk()
    serve   = get_serve_info(SERVE_SERVICE_NAME)
    count   = get_catalog_count(CATALOG_PATH)
    commit  = get_last_commit()

    ram_pct  = round(100 * ram_u / ram_t) if ram_t else 0
    disk_pct = round(100 * disk_u / disk_t) if disk_t else 0

    serve_line = (
        f"✅ работает (PID {serve['pid']})"
        if serve["active"]
        else "❌ не работает"
    )
    serve_uptime = f"\n  Время работы: {serve['uptime']}" if serve["uptime"] else ""

    text = (
        "📊 <b>Статус сервера</b>\n\n"
        "🖥 <b>Система:</b>\n"
        f"  Uptime: {uptime}\n"
        f"  CPU: {cpu}\n"
        f"  RAM: {ram_u} / {ram_t} MB ({ram_pct}%)\n"
        f"  Диск: {disk_u} / {disk_t} GB ({disk_pct}%)\n\n"
        "🌐 <b>serve.py:</b>\n"
        f"  Статус: {serve_line}\n"
        f"  Порт: 8080{serve_uptime}\n\n"
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
    msg = await update.message.reply_text("🔄 Перезапускаю serve.py...")
    _run(f"sudo systemctl restart {SERVE_SERVICE_NAME}")

    import asyncio
    await asyncio.sleep(3)

    active = _run(f"systemctl is-active {SERVE_SERVICE_NAME}").strip()
    res = ping_site(SITE_URL, timeout=10)

    if active == "active" and res["ok"]:
        text = f"✅ Сервер перезапущен, сайт отвечает ({res['time_s']:.3f}s)"
    elif active == "active":
        text = "⚠️ Сервер перезапущен, но сайт не отвечает — проверь /logs"
    else:
        text = "❌ Сервис не запустился — проверь /logs"
    await msg.edit_text(text)


@admin_only
async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    n = 30
    if context.args:
        try:
            n = int(context.args[0])
        except ValueError:
            pass

    output = _run(f"journalctl -u {SERVE_SERVICE_NAME} --no-pager -n {n} --output=short-monotonic 2>&1")
    if not output:
        output = f"(нет логов от сервиса {SERVE_SERVICE_NAME})"

    if len(output) <= 4000:
        await update.message.reply_text(f"<pre>{_escape(output)}</pre>", parse_mode="HTML")
    else:
        # отправляем файлом
        import io
        buf = io.BytesIO(output.encode())
        buf.name = f"logs_{n}.txt"
        await update.message.reply_document(buf, caption=f"Лог: последние {n} строк")


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
