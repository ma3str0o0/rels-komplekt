"""
Пинг сайта через curl.
"""
import subprocess


def ping_site(url: str, timeout: int = 15) -> dict:
    """Возвращает {ok, code, time_s, error}."""
    try:
        out = subprocess.check_output(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code} %{time_total}", "--max-time", str(timeout), url],
            text=True, stderr=subprocess.DEVNULL, timeout=timeout + 2
        ).strip()
        code, t = out.split()
        ok = code == "200"
        return {"ok": ok, "code": code, "time_s": float(t), "error": None}
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": "—", "time_s": 0, "error": f"таймаут {timeout}с"}
    except Exception as e:
        return {"ok": False, "code": "—", "time_s": 0, "error": str(e)}
