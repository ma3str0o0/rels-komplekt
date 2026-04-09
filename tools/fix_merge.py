#!/usr/bin/env python3
"""
Исправляет три проблемы в catalog.json после merge_vsp74.py:

  1. weight_per_meter → weight_per_unit (кг/м × 12.5 м)
     убирает поле weight_per_meter и weight_unit
  2. competitor_data.spec_tables → competitor_data.gost_tables
  3. описания из vsp74_scrape.json (если есть)

Запуск: python3 tools/fix_merge.py
"""

import json
from pathlib import Path

CATALOG_PATH = Path('data/catalog.json')
VSP74_PATH   = Path('data/vsp74_scrape.json')

catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
scrape  = json.loads(VSP74_PATH.read_text(encoding='utf-8'))


# ─── Проблема 3: описания из vsp74_scrape.json ───────────────────
# Маппинг: ключевые слова в catalog.category → vsp74 ключ
DESC_MAP = [
    ('rails_wide',        ['широкой колеи', 'Рельсы Р43', 'Рельсы Р50',
                           'Рельсы Р65', 'Рельсы Р33', 'Рельсы Р24', 'Рельсы Р18']),
    ('rails_crane',       ['крановые', ' КР ']),
    ('rails_narrow',      ['узкоколейные', 'Рельс Р12', 'Рельсы Р8',
                           'Рельсы Р15', 'Рельсы Р18', 'Рельсы Р24', 'Рельсы Р33',
                           'Рельсы Р38']),
    ('sleepers_wood',     ['деревянн', 'Брус для стрелочного']),
    ('sleepers_concrete', ['железобетон']),
    ('nakladki',          ['Накладки']),
    ('podkladki',         ['Подкладки', 'Прокладки']),
    ('fasteners',         ['Крепеж', 'Болты', 'Костыль', 'Шурупы', 'Противоугон', 'Крановый крепеж']),
]

def vsp74_desc_for_category(cat_name: str) -> str | None:
    for vsp_key, keywords in DESC_MAP:
        if any(kw in cat_name for kw in keywords):
            return scrape['categories'].get(vsp_key, {}).get('description') or None
    return None

# Проверяем, есть ли вообще непустые описания
has_any_desc = any(
    v.get('description') for v in scrape['categories'].values()
)
print(f"Описаний в vsp74_scrape.json: {'есть' if has_any_desc else '0 — пропускаем проблему 3'}")


# ─── Счётчики ────────────────────────────────────────────────────
cnt_weight_converted  = 0   # weight_per_meter → weight_per_unit
cnt_weight_meter_left = 0   # weight_per_meter осталось после исправления
cnt_weight_unit_total = 0   # итого позиций с weight_per_unit
cnt_gost_tables       = 0   # spec_tables → gost_tables
cnt_desc_filled       = 0   # description заполнено


# ─── Проход по catalog ───────────────────────────────────────────
for item in catalog:
    # Проблема 1: weight_per_meter → weight_per_unit
    wpm = item.get('weight_per_meter')
    if wpm is not None:
        item['weight_per_unit'] = round(wpm * 12.5, 2)
        del item['weight_per_meter']
        cnt_weight_converted += 1

    if 'weight_unit' in item:
        del item['weight_unit']

    # Проблема 2: spec_tables → gost_tables
    cd = item.get('competitor_data')
    if not isinstance(cd, dict):
        item['competitor_data'] = {}
        cd = item['competitor_data']

    if cd.get('spec_tables'):
        cd['gost_tables'] = cd.pop('spec_tables')
        cnt_gost_tables += 1

    # Проблема 3: description из vsp74 (только если есть данные)
    if has_any_desc and not cd.get('description'):
        desc = vsp74_desc_for_category(item.get('category', ''))
        if desc:
            cd['description'] = desc
            cnt_desc_filled += 1

    # Статистика weight_per_unit
    if item.get('weight_per_unit'):
        cnt_weight_unit_total += 1

# Контрольная проверка: не осталось ли weight_per_meter
cnt_weight_meter_left = sum(1 for i in catalog if 'weight_per_meter' in i)


# ─── Сохранение ──────────────────────────────────────────────────
CATALOG_PATH.write_text(
    json.dumps(catalog, ensure_ascii=False, indent=2),
    encoding='utf-8',
)

print()
print('═' * 52)
print('РЕЗУЛЬТАТ FIX')
print('═' * 52)
print(f'  weight_per_unit заполнен:   {cnt_weight_unit_total} / {len(catalog)}')
print(f'  weight_per_meter осталось:  {cnt_weight_meter_left}  (должно быть 0)')
print(f'  gost_tables заполнено:      {cnt_gost_tables}')
print(f'  description заполнено:      {cnt_desc_filled}')
print(f'  Сохранено: {CATALOG_PATH}')
