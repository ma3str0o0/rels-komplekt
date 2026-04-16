"""
Сбор системных метрик через стандартные Linux-утилиты (без psutil).
"""
import subprocess
import json
from pathlib import Path


def _run(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def get_uptime() -> str:
    raw = _run("cat /proc/uptime")
    if not raw:
        return "неизвестно"
    secs = int(float(raw.split()[0]))
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    parts = []
    if days:
        parts.append(f"{days}д")
    if hours:
        parts.append(f"{hours}ч")
    parts.append(f"{mins}мин")
    return " ".join(parts)


def get_cpu_percent() -> str:
    # среднее из /proc/stat за 0.1с
    try:
        with open("/proc/stat") as f:
            line1 = f.readline().split()
        import time; time.sleep(0.1)
        with open("/proc/stat") as f:
            line2 = f.readline().split()
        idle1 = int(line1[4]); total1 = sum(int(x) for x in line1[1:])
        idle2 = int(line2[4]); total2 = sum(int(x) for x in line2[1:])
        dt = total2 - total1
        di = idle2 - idle1
        pct = round(100 * (dt - di) / dt) if dt else 0
        return f"{pct}%"
    except Exception:
        return "?"


def get_ram() -> tuple[int, int]:
    """Возвращает (used_mb, total_mb)."""
    raw = _run("free -m")
    for line in raw.splitlines():
        if line.startswith("Mem:"):
            parts = line.split()
            total = int(parts[1])
            used  = int(parts[2])
            return used, total
    return 0, 0


def get_disk() -> tuple[float, float]:
    """Возвращает (used_gb, total_gb) для /."""
    raw = _run("df -BM /")
    for line in raw.splitlines()[1:]:
        parts = line.split()
        total = int(parts[1].rstrip("M")) / 1024
        used  = int(parts[2].rstrip("M")) / 1024
        return round(used, 1), round(total, 1)
    return 0, 0


def get_serve_info(service_name: str) -> dict:
    """PID и время работы serve.py через systemd или pgrep."""
    pid = _run(f"systemctl show -p MainPID --value {service_name} 2>/dev/null")
    if not pid or pid == "0":
        pid = _run("pgrep -f serve.py")

    active_time = ""
    status_line = _run(f"systemctl is-active {service_name} 2>/dev/null")
    if status_line == "active":
        # uptime сервиса через systemctl show
        raw = _run(f"systemctl show -p ActiveEnterTimestamp --value {service_name}")
        if raw:
            from datetime import datetime, timezone
            import time
            try:
                # формат: "Thu 2025-04-10 10:00:00 UTC"
                dt = datetime.strptime(raw, "%a %Y-%m-%d %H:%M:%S %Z").replace(tzinfo=timezone.utc)
                diff = int(time.time()) - int(dt.timestamp())
                days, rem = divmod(diff, 86400)
                hours, rem = divmod(rem, 3600)
                mins = rem // 60
                parts = []
                if days: parts.append(f"{days}д")
                if hours: parts.append(f"{hours}ч")
                parts.append(f"{mins}мин")
                active_time = " ".join(parts)
            except Exception:
                pass

    return {
        "pid": pid or "—",
        "active": status_line == "active",
        "uptime": active_time,
    }


def get_catalog_count(catalog_path: Path) -> int:
    try:
        with open(catalog_path) as f:
            data = json.load(f)
        return len(data)
    except Exception:
        return 0


def get_last_commit() -> str:
    return _run('git log -1 --format="%ar — %s"') or "нет данных"
