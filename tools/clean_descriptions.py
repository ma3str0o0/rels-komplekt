import json

TRASH_MARKERS = [
    'Покупателю', 'Личный кабинет', 'Заказы', 'В наличии',
    'Поиск', 'Каталог', 'КомплектыскреплениЙ', 'Рельсыжелезнодорожные'
]

with open('data/catalog.json', encoding='utf-8') as f:
    catalog = json.load(f)

cleaned = 0
for item in catalog:
    cd = item.get('competitor_data')
    if not cd or not cd.get('description'):
        continue
    desc = cd['description']
    is_trash = any(marker in desc for marker in TRASH_MARKERS)
    if is_trash or len(desc) > 2000:
        cd['description'] = None
        cleaned += 1

with open('data/catalog.json', 'w', encoding='utf-8') as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)

print(f'Очищено: {cleaned} товаров')
