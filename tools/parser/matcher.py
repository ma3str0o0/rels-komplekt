#!/usr/bin/env python3
"""
Парсер vsp74.ru — Этап 2: сопоставление с нашим каталогом
"""

import json
import re
from pathlib import Path

CATALOG_FILE  = Path(__file__).parent.parent.parent / "data" / "catalog.json"
RAW_FILE      = Path(__file__).parent.parent.parent / "data" / "competitor_raw.json"
OUTPUT_FILE   = Path(__file__).parent.parent.parent / "data" / "catalog_enriched.json"

# Ключевые слова для извлечения из названий товаров
RAIL_TYPES    = ["Р65", "Р50", "Р43", "Р33", "Р24", "Р18", "Р15", "Р12", "Р8", "Р38"]
CRANE_TYPES   = ["КР70", "КР80", "КР100", "КР120", "КР140"]
NARROW_TYPES  = ["УК", "Р8", "Р11"]
SLEEPER_TYPES = ["тип 1", "тип 2", "Ш1", "Ш3"]
JOINT_TYPES   = ["двухголов", "четырёхдырн", "четырехдырн", "шестидырн"]
BOLT_TYPES    = ["М22", "М24", "М27"]

# Категориальные ключевые слова (нижний регистр)
CATEGORY_KEYWORDS = {
    "рельс":     ["рельс"],
    "шпала":     ["шпал"],
    "накладка":  ["накладк"],
    "подкладка": ["подкладк"],
    "прокладка": ["прокладк"],
    "болт":      ["болт", "гайк", "шайб"],
    "костыль":   ["костыл", "шуруп", "противоугон"],
    "крепеж":    ["крепеж", "скреплени"],
}


def extract_keywords(name: str) -> dict:
    """Извлечь ключевые слова из названия нашего товара."""
    name_upper = name.upper()
    name_lower = name.lower()

    found = {
        "rail_type":   next((t for t in RAIL_TYPES  if t.upper() in name_upper), None),
        "crane_type":  next((t for t in CRANE_TYPES if t.upper() in name_upper), None),
        "narrow_type": next((t for t in NARROW_TYPES if t.upper() in name_upper), None),
        "sleeper":     next((t for t in SLEEPER_TYPES if t.lower() in name_lower), None),
        "joint":       next((t for t in JOINT_TYPES if t.lower() in name_lower), None),
        "bolt":        next((t for t in BOLT_TYPES if t.upper() in name_upper), None),
        "category":    None,
    }

    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            found["category"] = cat
            break

    return found


def match_confidence(our_kw: dict, competitor_name: str) -> str | None:
    """
    Вернуть уровень совпадения: 'high', 'medium', 'low' или None.
    """
    comp_upper = competitor_name.upper()
    comp_lower = competitor_name.lower()

    # Высокая: точное совпадение типа
    specific_matches = [
        our_kw.get("rail_type"),
        our_kw.get("crane_type"),
        our_kw.get("narrow_type"),
        our_kw.get("bolt"),
    ]
    for val in specific_matches:
        if val and val.upper() in comp_upper:
            return "high"

    if our_kw.get("sleeper") and our_kw["sleeper"].lower() in comp_lower:
        return "high"

    if our_kw.get("joint") and our_kw["joint"].lower() in comp_lower:
        return "high"

    # Средняя: совпадение категории
    if our_kw.get("category"):
        cat_kws = CATEGORY_KEYWORDS[our_kw["category"]]
        if any(kw in comp_lower for kw in cat_kws):
            return "medium"

    # Низкая: частичное совпадение по общим словам
    our_words = set(re.findall(r"[а-яёА-ЯЁa-zA-Z0-9]+", our_kw.get("category", "") or ""))
    comp_words = set(re.findall(r"[а-яёА-ЯЁa-zA-Z0-9]+", comp_lower))
    if len(our_words & comp_words) >= 1 and our_words:
        return "low"

    return None


def find_best_match(our_item: dict, all_competitor_products: list[dict]) -> dict | None:
    """Найти лучшее совпадение среди всех товаров конкурента."""
    our_kw = extract_keywords(our_item.get("name", ""))

    candidates = []
    for product in all_competitor_products:
        confidence = match_confidence(our_kw, product.get("name", ""))
        if confidence:
            candidates.append((confidence, product))

    if not candidates:
        return None

    # Приоритет: high > medium > low
    priority = {"high": 0, "medium": 1, "low": 2}
    candidates.sort(key=lambda x: priority[x[0]])
    best_confidence, best_product = candidates[0]

    our_price = our_item.get("price")
    comp_price = best_product.get("price")
    price_diff = None
    if our_price and comp_price:
        price_diff = our_price - comp_price  # >0: мы дороже, <0: мы дешевле

    return {
        "url":           best_product["url"],
        "price":         comp_price,
        "price_diff":    price_diff,
        "description":   best_product.get("description", ""),
        "specs":         best_product.get("specs", {}),
        "has_photos":    best_product.get("has_photos", False),
        "has_pdf":       best_product.get("has_pdf", False),
        "has_spec_table": best_product.get("has_spec_table", False),
        "confidence":    best_confidence,
    }


def main():
    # Загрузка данных
    with open(CATALOG_FILE, encoding="utf-8") as f:
        our_catalog = json.load(f)

    with open(RAW_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    # Собрать плоский список всех товаров конкурента
    all_products = []
    for category_products in raw.values():
        all_products.extend(category_products)

    print(f"Наш каталог: {len(our_catalog)} позиций")
    print(f"Товаров конкурента: {len(all_products)}")

    # Сопоставление
    matched = 0
    enriched = []

    for item in our_catalog:
        competitor = find_best_match(item, all_products)
        enriched_item = dict(item)
        enriched_item["competitor"] = competitor
        enriched.append(enriched_item)

        if competitor:
            matched += 1
            conf = competitor["confidence"]
            print(f"  [{conf}] {item.get('name', '')[:50]} → {competitor['url'].rsplit('/', 1)[-1]}")

    print(f"\nСопоставлено: {matched} из {len(our_catalog)}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    print(f"Сохранено в: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
