#!/usr/bin/env python3
"""
Вливает данные конкурента из catalog_enriched.json в catalog.json.
Поле competitor_data: { description, specs, has_drawing, has_photos, images }
"""
import json

CATALOG_PATH = 'data/catalog.json'
ENRICHED_PATH = 'data/catalog_enriched.json'

with open(CATALOG_PATH, encoding='utf-8') as f:
    catalog = json.load(f)

with open(ENRICHED_PATH, encoding='utf-8') as f:
    enriched = json.load(f)

# Индекс по id
enriched_by_id = {item['id']: item for item in enriched}

matched = 0
for item in catalog:
    enriched_item = enriched_by_id.get(item['id'])
    if not enriched_item:
        continue
    comp = enriched_item.get('competitor')
    if not comp:
        continue

    item['competitor_data'] = {
        'description': comp.get('description') or '',
        'specs': comp.get('specs') or {},
        'has_drawing': bool(comp.get('has_pdf')),
        'has_photos': bool(comp.get('has_photos')),
        'images': [],
    }
    matched += 1

print(f'Совпадений: {matched} / {len(catalog)}')
print(f'Без данных: {len(catalog) - matched}')

with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)

print(f'Сохранено: {CATALOG_PATH}')
