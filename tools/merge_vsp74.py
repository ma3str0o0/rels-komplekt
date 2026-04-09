#!/usr/bin/env python3
"""
Вливает данные из vsp74_scrape.json в catalog.json:

  • weight_per_meter  — добавляет по типу рельса (Р65 → 64.88 кг/м)
                        только для рельсовых категорий
  • price             — заполняет только там, где null; берёт min по типу
  • competitor_data.gost
  • competitor_data.spec_tables  — технические таблицы с vsp74 (по категории)
  • competitor_data.description  — заполняет только там, где null

Запуск: python3 tools/merge_vsp74.py
"""

import json
import re
from pathlib import Path

CATALOG_PATH = Path('data/catalog.json')
VSP74_PATH   = Path('data/vsp74_scrape.json')

# ─── Маппинг vsp74-ключей → catalog-категорий ───────────────────

CAT_MAP: dict[str, list[str]] = {
    'rails_wide': [
        'Рельсы широкой колеи',
        'Рельсы Р43', 'Рельсы Р50',
    ],
    'rails_crane': [
        'Рельсы крановые',
        'Рельсы КР 70', 'Рельсы КР 80', 'Рельсы КР 100',
        'Рельсы КР 120', 'Рельсы КР 140',
        'Международный стандарт рельс DIN 536',
    ],
    'rails_narrow': [
        'Рельсы узкоколейные',
        'Рельсы Р8', 'Рельс Р12', 'Рельсы Р15', 'Рельсы Р18',
        'Рельсы Р24', 'Рельсы Р33', 'Рельсы Р38',
    ],
    'sleepers_wood': [
        'Шпалы деревянные',
        'Брус для стрелочного перевода',
    ],
    'sleepers_concrete': [
        'Шпалы железобетонные',
    ],
    'nakladki': [
        'Накладки рельсовые',
    ],
    'podkladki': [
        'Подкладки',
        'Прокладки резиновые',
    ],
    'fasteners': [
        'Крепеж железнодорожный',
        'Болты закладные', 'Болты клеммные', 'Болты стыковые',
        'Костыль путевой', 'Шурупы путевые',
        'Противоугон', 'Крановый крепеж',
    ],
}

# Категории, для которых имеет смысл weight_per_meter (рельсы)
RAIL_VSP_KEYS = {'rails_wide', 'rails_crane', 'rails_narrow'}
RAIL_CATS = {c for k in RAIL_VSP_KEYS for c in CAT_MAP[k]}

# Обратный маппинг: catalog_category → vsp74_key
REVERSE_MAP: dict[str, str] = {
    c: k for k, cats in CAT_MAP.items() for c in cats
}


# ─── Извлечение типа рельса ──────────────────────────────────────

def rail_type(text: str) -> str | None:
    """
    Извлекает нормализованный тип рельса из строки.
    'Рельсы КР-70 новые' → 'КР70'
    'Рельсы Р65 ДТ350'   → 'Р65'
    """
    t = text.upper()
    # Крановые — проверяем первыми (содержат Р внутри КР)
    m = re.search(r'КР[-\s]?(\d+)', t)
    if m:
        return f'КР{m.group(1)}'
    # Обычные (широкая, узкая, стандарт): Р65, Р50, Р43, Р33 и т.д.
    m = re.search(r'(?<![А-ЯA-Z\d])Р(\d+)', t)
    if m:
        return f'Р{m.group(1)}'
    return None


# ─── Загрузка данных ─────────────────────────────────────────────

catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
vsp74   = json.loads(VSP74_PATH.read_text(encoding='utf-8'))


# ─── Построение индексов из vsp74 ────────────────────────────────

weight_idx: dict[str, float] = {}   # тип → kg/m (только рельсы)
price_idx:  dict[str, int]   = {}   # тип → min price_per_ton
gost_idx:   dict[str, str]   = {}   # тип → ГОСТ
cat_extra:  dict[str, dict]  = {}   # catalog_category → {description, spec_tables}

for vsp_key, vsp_data in vsp74['categories'].items():
    desc   = vsp_data.get('description')
    specs  = vsp_data.get('spec_tables', [])
    items  = vsp_data.get('items', [])

    # Сохраняем доп. данные по категориям
    for cat in CAT_MAP.get(vsp_key, []):
        cat_extra[cat] = {'description': desc, 'spec_tables': specs}

    for item in items:
        t = rail_type(item['name'])
        if not t:
            continue

        w = item.get('weight_per_meter')
        if w is not None and t not in weight_idx and vsp_key in RAIL_VSP_KEYS:
            weight_idx[t] = w

        p = item.get('price_per_ton')
        if p:
            if t not in price_idx or p < price_idx[t]:
                price_idx[t] = p

        g = item.get('gost', '').strip()
        if g and t not in gost_idx:
            gost_idx[t] = g

print(f"Весовой индекс ({len(weight_idx)} типов): "
      + ', '.join(f'{k}={v}' for k, v in sorted(weight_idx.items())))
print(f"Ценовой индекс ({len(price_idx)} типов): "
      + ', '.join(f'{k}={v:,}₽' for k, v in sorted(price_idx.items())))
print(f"ГОСТ-индекс: {len(gost_idx)} типов")


# ─── Merge ───────────────────────────────────────────────────────

stats = {
    'weight_added':  0,
    'price_filled':  0,
    'desc_filled':   0,
    'gost_filled':   0,
    'specs_added':   0,
    'no_type_match': 0,   # в рельсовых категориях тип не определён
}

for item in catalog:
    cat  = item.get('category', '')
    name = item.get('name', '')

    # Тип рельса: сначала из имени, потом из названия категории
    t = rail_type(name) or rail_type(cat)

    # weight_per_meter — только для рельсовых категорий
    if cat in RAIL_CATS and t and t in weight_idx:
        if not item.get('weight_per_meter'):
            item['weight_per_meter'] = weight_idx[t]
            stats['weight_added'] += 1
    elif cat in RAIL_CATS and not t:
        stats['no_type_match'] += 1

    # price — заполняем только null/0
    if not item.get('price') and t and t in price_idx:
        item['price'] = price_idx[t]
        stats['price_filled'] += 1

    # competitor_data (может быть null в исходном JSON)
    if not item.get('competitor_data'):
        item['competitor_data'] = {}
    cd = item['competitor_data']

    # gost
    if t and t in gost_idx and not cd.get('gost'):
        cd['gost'] = gost_idx[t]
        stats['gost_filled'] += 1

    # description и spec_tables из категории vsp74
    extra = cat_extra.get(cat)
    if extra:
        if not cd.get('description') and extra['description']:
            cd['description'] = extra['description']
            stats['desc_filled'] += 1
        if not cd.get('spec_tables') and extra['spec_tables']:
            cd['spec_tables'] = extra['spec_tables']
            stats['specs_added'] += 1


# ─── Сохранение ──────────────────────────────────────────────────

CATALOG_PATH.write_text(
    json.dumps(catalog, ensure_ascii=False, indent=2),
    encoding='utf-8',
)

print()
print('═' * 52)
print('РЕЗУЛЬТАТ MERGE')
print('═' * 52)
print(f'  weight_per_meter добавлено: {stats["weight_added"]}')
print(f'  price заполнено:            {stats["price_filled"]}')
print(f'  description добавлено:      {stats["desc_filled"]}')
print(f'  gost добавлено:             {stats["gost_filled"]}')
print(f'  spec_tables добавлено:      {stats["specs_added"]}')
print(f'  Рельс. позиций без матча:   {stats["no_type_match"]}')
print(f'  Итого позиций в catalog:    {len(catalog)}')
print(f'  Сохранено: {CATALOG_PATH}')

# ─── Spot-check ──────────────────────────────────────────────────
print()
print('SPOT-CHECK (первые 4 позиции с weight_per_meter):')
shown = 0
for item in catalog:
    if item.get('weight_per_meter') and shown < 4:
        print(f'  {item["name"][:55]:<55}  '
              f'w={item["weight_per_meter"]}  '
              f'p={item.get("price")}')
        shown += 1
