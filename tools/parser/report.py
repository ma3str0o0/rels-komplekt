#!/usr/bin/env python3
"""
Парсер vsp74.ru — Этап 3: генерация отчёта конкурентного анализа
"""

import json
from datetime import date
from pathlib import Path

ENRICHED_FILE = Path(__file__).parent.parent.parent / "data" / "catalog_enriched.json"
RAW_FILE      = Path(__file__).parent.parent.parent / "data" / "competitor_raw.json"
REPORT_FILE   = Path(__file__).parent.parent.parent / "data" / "competitor_report.md"


def format_price(price: int | None) -> str:
    if price is None:
        return "—"
    return f"{price:,}".replace(",", " ") + " руб."


def format_diff(diff: int | None) -> str:
    if diff is None:
        return "—"
    sign = "+" if diff > 0 else ""
    return f"{sign}{diff:,}".replace(",", " ") + " руб."


def main():
    with open(ENRICHED_FILE, encoding="utf-8") as f:
        catalog = json.load(f)

    with open(RAW_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    # Статистика конкурента
    total_competitor = sum(len(v) for v in raw.values())

    # Анализ совпадений
    matched_items = [item for item in catalog if item.get("competitor")]
    total_matched = len(matched_items)

    # Ценовые сравнения (только там, где есть обе цены)
    price_comparable = [
        item for item in matched_items
        if item.get("competitor", {}).get("price_diff") is not None
    ]

    we_cheaper   = [i for i in price_comparable if i["competitor"]["price_diff"] < 0]
    they_cheaper = [i for i in price_comparable if i["competitor"]["price_diff"] > 0]

    avg_diff_they = (
        sum(i["competitor"]["price_diff"] for i in they_cheaper) // len(they_cheaper)
        if they_cheaper else 0
    )

    # Топ-10: конкурент дешевле нас (price_diff > 0 → мы дороже)
    top_they = sorted(they_cheaper, key=lambda i: i["competitor"]["price_diff"], reverse=True)[:10]

    # Топ-10: мы дешевле (price_diff < 0)
    top_we = sorted(we_cheaper, key=lambda i: i["competitor"]["price_diff"])[:10]

    # Таблица: что добавить на наш сайт
    missing_content = [
        item for item in matched_items
        if not (
            item.get("description")
            and item.get("competitor", {}).get("has_spec_table")
            and item.get("competitor", {}).get("has_photos")
        )
    ]

    today = date.today().strftime("%d.%m.%Y")

    lines = []
    lines.append(f"# Анализ конкурента vsp74.ru — {today}\n")

    lines.append("## Сводка\n")
    lines.append(f"- Товаров у конкурента найдено: **{total_competitor}**")
    lines.append(f"- Совпадений с нашим каталогом: **{total_matched} из {len(catalog)}**")
    lines.append(f"- Конкурент дешевле: **{len(they_cheaper)} позиций**"
                 + (f" (средняя разница: {format_diff(avg_diff_they)})" if they_cheaper else ""))
    lines.append(f"- Мы дешевле: **{len(we_cheaper)} позиций**")
    lines.append("")

    lines.append("## Что добавить на наш сайт\n")
    lines.append("| Наш товар | Описание | Табл. хар-к | Фото | URL конкурента |")
    lines.append("|-----------|----------|-------------|------|----------------|")
    for item in missing_content[:30]:
        comp = item.get("competitor", {})
        name = item.get("name", "")[:45]
        has_desc    = "✓" if item.get("description") else "✗"
        has_table   = "✓" if comp.get("has_spec_table") else "✗"
        has_photos  = "✓" if comp.get("has_photos") else "✗"
        url = comp.get("url", "—")
        lines.append(f"| {name} | {has_desc} | {has_table} | {has_photos} | {url} |")
    if len(missing_content) > 30:
        lines.append(f"\n_...и ещё {len(missing_content) - 30} позиций_")
    lines.append("")

    lines.append("## Топ-10: конкурент дешевле нас\n")
    lines.append("| Позиция | Наша цена | Цена конкурента | Разница | URL |")
    lines.append("|---------|-----------|-----------------|---------|-----|")
    for item in top_they:
        comp = item["competitor"]
        name = item.get("name", "")[:40]
        our_p = format_price(item.get("price"))
        their_p = format_price(comp.get("price"))
        diff = format_diff(comp.get("price_diff"))
        url = comp.get("url", "—")
        lines.append(f"| {name} | {our_p} | {their_p} | {diff} | {url} |")
    lines.append("")

    lines.append("## Топ-10: мы дешевле конкурента\n")
    lines.append("| Позиция | Наша цена | Цена конкурента | Разница | URL |")
    lines.append("|---------|-----------|-----------------|---------|-----|")
    for item in top_we:
        comp = item["competitor"]
        name = item.get("name", "")[:40]
        our_p = format_price(item.get("price"))
        their_p = format_price(comp.get("price"))
        diff = format_diff(comp.get("price_diff"))
        url = comp.get("url", "—")
        lines.append(f"| {name} | {our_p} | {their_p} | {diff} | {url} |")
    lines.append("")

    # Детальный раздел по уровням совпадений
    high_conf   = [i for i in matched_items if i["competitor"]["confidence"] == "high"]
    medium_conf = [i for i in matched_items if i["competitor"]["confidence"] == "medium"]
    low_conf    = [i for i in matched_items if i["competitor"]["confidence"] == "low"]

    lines.append("## Качество сопоставлений\n")
    lines.append(f"- Точные совпадения (high): **{len(high_conf)}**")
    lines.append(f"- По категории (medium): **{len(medium_conf)}**")
    lines.append(f"- Частичные (low): **{len(low_conf)}**")
    lines.append("")

    report_text = "\n".join(lines)
    REPORT_FILE.write_text(report_text, encoding="utf-8")
    print(f"Отчёт сохранён: {REPORT_FILE}")
    print(f"\nКраткая сводка:")
    print(f"  Товаров конкурента: {total_competitor}")
    print(f"  Совпадений: {total_matched} из {len(catalog)}")
    print(f"  Конкурент дешевле: {len(they_cheaper)} позиций")
    print(f"  Мы дешевле: {len(we_cheaper)} позиций")


if __name__ == "__main__":
    main()
