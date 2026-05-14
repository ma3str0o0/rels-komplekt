"""
CRUD-сервис каталога: чтение, поиск, обновление catalog.json.
"""
import csv
import io
import json
import logging
import re
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from bot.config import CATALOG_PATH

log = logging.getLogger(__name__)

_cache: list = []
_cache_mtime: float = 0.0

# Лог мутаций каталога (append-only)
AUDIT_LOG_PATH = CATALOG_PATH.parent / "catalog_audit.log"

# Количество уровней ротации .bak (catalog.json.bak, .bak.1 ... .bak.4)
_BACKUP_LEVELS = 5


# ── Загрузка / сохранение ─────────────────────────────────────────────────


def _load() -> list:
    global _cache, _cache_mtime
    try:
        mtime = CATALOG_PATH.stat().st_mtime
        if mtime != _cache_mtime:
            with open(CATALOG_PATH, encoding="utf-8") as f:
                _cache = json.load(f)
            _cache_mtime = mtime
    except Exception as e:
        log.error("Не удалось загрузить каталог: %s", e)
        if not _cache:
            _cache = []
    return _cache


def _rotate_backups() -> None:
    """Сдвигает .bak → .bak.1 → .bak.2 ... до _BACKUP_LEVELS уровней.
    Файлы вида catalog.json.bak-* (ручные снимки) не трогает.
    """
    base = CATALOG_PATH.with_suffix(".json.bak")
    # старшие → выкинуть, остальные сдвинуть
    oldest = Path(f"{base}.{_BACKUP_LEVELS - 1}")
    if oldest.exists():
        try:
            oldest.unlink()
        except Exception:
            pass
    for i in range(_BACKUP_LEVELS - 2, 0, -1):
        src = Path(f"{base}.{i}")
        dst = Path(f"{base}.{i + 1}")
        if src.exists():
            try:
                src.replace(dst)
            except Exception:
                pass
    # .bak → .bak.1
    if base.exists():
        try:
            base.replace(Path(f"{base}.1"))
        except Exception:
            pass


def _save(data: list) -> None:
    global _cache, _cache_mtime
    backup = CATALOG_PATH.with_suffix(".json.bak")
    try:
        _rotate_backups()
        shutil.copy2(CATALOG_PATH, backup)
    except Exception:
        pass
    tmp = CATALOG_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(CATALOG_PATH)
    _cache = data
    _cache_mtime = CATALOG_PATH.stat().st_mtime
    log.info("Каталог сохранён (%d позиций)", len(data))


# ── Audit log ─────────────────────────────────────────────────────────────


def _audit(op: str, pid: str, old, new, user_id: Optional[int] = None) -> None:
    """Пишет одну строку в append-only audit log.

    Формат: ISO8601(+TZ) user_id=X op=Y pid=Z old=... new=...
    Ошибки записи логируются, но не пробрасываются (не блокируют мутацию).
    """
    try:
        # +05:00 — Екатеринбург (бизнес-локаль проекта)
        tz = timezone(timedelta(hours=5))
        ts = datetime.now(tz).isoformat(timespec="seconds")
        uid = user_id if user_id is not None else "-"
        line = f"{ts} user_id={uid} op={op} pid={pid} old={old} new={new}\n"
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        log.error("audit log write failed: %s", e)


# ── Поиск ─────────────────────────────────────────────────────────────────


def find_products(query: str, limit: int = 10) -> list:
    """Поиск по id (артикулу), имени, категории, подкатегории. Регистр не важен."""
    q = query.strip().lower()
    if not q:
        return []
    results = []
    for item in _load():
        haystack = " ".join([
            item.get("id", "") or "",
            item.get("name", ""),
            item.get("category", ""),
            item.get("subcategory", "") or "",
        ]).lower()
        if q in haystack:
            results.append(item)
        if len(results) >= limit:
            break
    return results


def get_product(pid: str) -> Optional[dict]:
    for item in _load():
        if item.get("id") == pid:
            return item
    return None


def get_product_count() -> int:
    """Кол-во позиций в каталоге."""
    return len(_load())


def get_categories() -> list[str]:
    seen: set = set()
    cats: list = []
    for item in _load():
        c = item.get("category", "")
        if c and c not in seen:
            seen.add(c)
            cats.append(c)
    return cats


def get_stock_summary() -> dict:
    """Возвращает сводку: {total, in_stock, no_price, by_category: {name: count}}."""
    data = _load()
    total = len(data)
    in_stock = sum(1 for i in data if i.get("in_stock"))
    no_price = sum(1 for i in data if i.get("price") is None)
    by_cat: dict = {}
    for item in data:
        c = item.get("category", "—")
        by_cat[c] = by_cat.get(c, 0) + 1
    top = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)[:8]
    return {"total": total, "in_stock": in_stock, "no_price": no_price, "by_category": top}


# ── Редактирование ────────────────────────────────────────────────────────


def update_price(pid: str, price: Optional[int], user_id: Optional[int] = None) -> bool:
    data = _load()
    for item in data:
        if item.get("id") == pid:
            old = item.get("price")
            item["price"] = price
            _save(data)
            _audit("price", pid, old, price, user_id)
            return True
    return False


def bulk_update_prices(updates: dict, user_id: Optional[int] = None) -> int:
    """updates: {pid: price_or_None}. Возвращает кол-во обновлённых."""
    data = _load()
    idx = {item["id"]: item for item in data}
    count = 0
    changes: list[tuple[str, object, object]] = []
    for pid, price in updates.items():
        if pid in idx:
            old = idx[pid].get("price")
            idx[pid]["price"] = price
            changes.append((pid, old, price))
            count += 1
    if count:
        _save(data)
        for pid, old, new in changes:
            _audit("bulk_price", pid, old, new, user_id)
    return count


def apply_markup(category: str, pct: float, user_id: Optional[int] = None) -> int:
    """Увеличивает цены товаров категории на pct%. Пропускает null-цены.

    Возвращает кол-во обновлённых позиций. Возвращает 0, если категория не найдена
    или у всех её товаров price is None — handler должен это обработать (показать warning).
    """
    data = _load()
    count = 0
    changes: list[tuple[str, int, int]] = []
    for item in data:
        if item.get("category") == category and item.get("price") is not None:
            old = item["price"]
            new = round(old * (1 + pct / 100))
            item["price"] = new
            changes.append((item["id"], old, new))
            count += 1
    if count:
        _save(data)
        for pid, old, new in changes:
            _audit("markup", pid, old, new, user_id)
    return count


def quick_adjust_price(
    pid: str, pct: float, user_id: Optional[int] = None
) -> tuple[bool, Optional[int], Optional[int]]:
    """Корректирует цену товара на процент.

    Возвращает (success, old_price, new_price). Если товар не найден или
    price is None — (False, None, None).
    """
    data = _load()
    for item in data:
        if item.get("id") == pid:
            old = item.get("price")
            if old is None:
                return (False, None, None)
            new = round(old * (1 + pct / 100))
            item["price"] = new
            _save(data)
            _audit("quick_adjust", pid, old, new, user_id)
            return (True, old, new)
    return (False, None, None)


def set_price_request(pid: str, user_id: Optional[int] = None) -> bool:
    """Устанавливает цену = None («По запросу»). Тонкая обёртка над update_price."""
    return update_price(pid, None, user_id=user_id)


def set_in_stock(pid: str, value: bool, user_id: Optional[int] = None) -> bool:
    """Выставляет in_stock у одного товара. Возвращает True если найден."""
    data = _load()
    for item in data:
        if item.get("id") == pid:
            old = item.get("in_stock")
            item["in_stock"] = bool(value)
            _save(data)
            _audit("in_stock", pid, old, bool(value), user_id)
            return True
    return False


def bulk_set_in_stock(
    value: bool, category: Optional[str] = None, user_id: Optional[int] = None
) -> int:
    """Массово выставляет in_stock. Если category=None — для всех, иначе в указанной категории.

    Возвращает кол-во обновлённых позиций (включая те, у которых значение не изменилось,
    но фактически переписано — учитываем только реально изменённые).
    """
    data = _load()
    count = 0
    changes: list[tuple[str, object, bool]] = []
    target = bool(value)
    for item in data:
        if category is not None and item.get("category") != category:
            continue
        old = item.get("in_stock")
        if old == target:
            continue
        item["in_stock"] = target
        changes.append((item["id"], old, target))
        count += 1
    if count:
        _save(data)
        for pid, old, new in changes:
            _audit("bulk_in_stock", pid, old, new, user_id)
    return count


def delete_product(pid: str, user_id: Optional[int] = None) -> bool:
    data = _load()
    new_data = [i for i in data if i.get("id") != pid]
    if len(new_data) == len(data):
        return False
    _save(new_data)
    _audit("delete", pid, "exists", "deleted", user_id)
    return True


def add_product(
    name: str,
    category: str,
    price: Optional[int],
    unit: str = "т",
    weight_per_unit: Optional[float] = None,
    length_m: Optional[float] = None,
    user_id: Optional[int] = None,
) -> dict:
    data = _load()
    pid = _make_id(name, data)
    item = {
        "id": pid,
        "name": name,
        "page_name": _slugify_page_name(name) or f"item-{len(data) + 1}",
        "category": category,
        "subcategory": None,
        "price": price,
        "unit": unit,
        "in_stock": True,
        "competitor_data": {},
        "weight_per_unit": weight_per_unit,
        "length_m": length_m,
        "image": None,
    }
    data.append(item)
    _save(data)
    _audit("add", pid, None, name, user_id)
    return item


def _make_id(name: str, existing: list) -> str:
    existing_ids = {i["id"] for i in existing}
    base = re.sub(r"[^a-z0-9]", "", _transliterate(name).lower())[:12]
    if not base:
        base = "item"
    candidate = base
    n = 1
    while candidate in existing_ids:
        candidate = f"{base}{n}"
        n += 1
    return candidate


def _transliterate(text: str) -> str:
    """Транслит русских букв → латиница (поддержка много-символьных замен: ё→yo, ж→zh и т.п.)."""
    mapping = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e",
        "ё": "yo", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k",
        "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
        "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
        "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
        "э": "e", "ю": "yu", "я": "ya",
    }
    out: list[str] = []
    for ch in text:
        lower = ch.lower()
        if lower in mapping:
            rep = mapping[lower]
            out.append(rep.upper() if ch.isupper() and rep else rep)
        else:
            out.append(ch)
    return "".join(out)


def _slugify_page_name(name: str) -> str:
    """Транслит русских букв → латиница, нижний регистр,
    пробелы/спец-символы → дефис, схлопывание дублей, без trailing/leading дефиса.
    """
    s = _transliterate(name).lower()
    # всё, что не a-z0-9 — в дефис
    s = re.sub(r"[^a-z0-9]+", "-", s)
    # схлопнуть дубли (уже сделано выше, но на всякий)
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    return s


# ── CSV импорт ────────────────────────────────────────────────────────────


def parse_csv_prices(content: str) -> tuple[dict, list]:
    """
    Парсит CSV с колонками id,price (или name,price).
    Возвращает (updates_dict, errors_list).
    """
    updates: dict = {}
    errors: list = []
    reader = csv.DictReader(io.StringIO(content))
    fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]

    has_id   = "id"    in fieldnames
    has_name = "name"  in fieldnames
    has_price = "price" in fieldnames

    if not has_price or not (has_id or has_name):
        return {}, ["Нужны колонки: id (или name) + price"]

    data = _load()
    id_set = {i["id"] for i in data}
    name_idx = {i["name"].lower(): i["id"] for i in data}

    for row in reader:
        row = {k.strip().lower(): v.strip() for k, v in row.items()}
        raw_price = row.get("price", "").strip()

        try:
            if raw_price in ("", "-", "null"):
                price: Optional[int] = None
            else:
                val = int(float(raw_price))
                price = None if val == 0 else val  # 0 → «По запросу» (как в UI)
        except ValueError:
            errors.append(f"Неверная цена: {raw_price!r}")
            continue

        if has_id:
            pid = row.get("id", "").strip()
            if not pid:
                continue
            if pid in id_set:
                updates[pid] = price
            else:
                errors.append(f"Товар не найден: {pid!r}")
        elif has_name:
            nm = row.get("name", "").strip().lower()
            pid = name_idx.get(nm)
            if pid:
                updates[pid] = price
            else:
                errors.append(f"Товар не найден: {nm!r}")

    return updates, errors
