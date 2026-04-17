"""
CRUD-сервис каталога: чтение, поиск, обновление catalog.json.
"""
import csv
import io
import json
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from bot.config import CATALOG_PATH

log = logging.getLogger(__name__)

_cache: list = []
_cache_mtime: float = 0.0


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


def _save(data: list) -> None:
    global _cache, _cache_mtime
    backup = CATALOG_PATH.with_suffix(".json.bak")
    try:
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


# ── Поиск ─────────────────────────────────────────────────────────────────


def find_products(query: str, limit: int = 10) -> list:
    """Поиск по имени, категории, подкатегории. Регистр не важен."""
    q = query.strip().lower()
    if not q:
        return []
    results = []
    for item in _load():
        haystack = " ".join([
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


def update_price(pid: str, price: Optional[int]) -> bool:
    data = _load()
    for item in data:
        if item.get("id") == pid:
            item["price"] = price
            _save(data)
            return True
    return False


def bulk_update_prices(updates: dict) -> int:
    """updates: {pid: price_or_None}. Возвращает кол-во обновлённых."""
    data = _load()
    idx = {item["id"]: item for item in data}
    count = 0
    for pid, price in updates.items():
        if pid in idx:
            idx[pid]["price"] = price
            count += 1
    if count:
        _save(data)
    return count


def apply_markup(category: str, pct: float) -> int:
    """Увеличивает цены товаров категории на pct%. Пропускает null-цены."""
    data = _load()
    count = 0
    for item in data:
        if item.get("category") == category and item.get("price") is not None:
            item["price"] = round(item["price"] * (1 + pct / 100))
            count += 1
    if count:
        _save(data)
    return count


def delete_product(pid: str) -> bool:
    data = _load()
    new_data = [i for i in data if i.get("id") != pid]
    if len(new_data) == len(data):
        return False
    _save(new_data)
    return True


def add_product(name: str, category: str, price: Optional[int], unit: str = "т") -> dict:
    data = _load()
    pid = _make_id(name, data)
    item = {
        "id": pid,
        "name": name,
        "page_name": name,
        "category": category,
        "subcategory": None,
        "price": price,
        "unit": unit,
        "in_stock": True,
        "competitor_data": {},
        "weight_per_unit": None,
        "image": None,
    }
    data.append(item)
    _save(data)
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
    table = str.maketrans(
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ",
        "abvgdeyozhiyklmnoprstufhtschshsyeuyaABVGDEYOZHIYKLMNOPRSTUFHTSCHSHSYEUYA",
    )
    return text.translate(table)


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
    name_idx = {i["name"].lower(): i["id"] for i in data}

    for row in reader:
        row = {k.strip().lower(): v.strip() for k, v in row.items()}
        raw_price = row.get("price", "").strip()

        try:
            price: Optional[int] = None if raw_price in ("", "-", "null") else int(float(raw_price))
        except ValueError:
            errors.append(f"Неверная цена: {raw_price!r}")
            continue

        if has_id:
            pid = row.get("id", "").strip()
            if pid:
                updates[pid] = price
        elif has_name:
            nm = row.get("name", "").strip().lower()
            pid = name_idx.get(nm)
            if pid:
                updates[pid] = price
            else:
                errors.append(f"Товар не найден: {nm!r}")

    return updates, errors
