"""
Миграция catalog.json: удаление дубликатов + добавление полей condition, availability.

Запуск:
    python3 tools/migrate_condition_avail.py --dry-run     # показать что произойдёт
    python3 tools/migrate_condition_avail.py --apply       # применить

Бэкап делается ДО изменений — `data/catalog.json.bak-<timestamp>-pre-migration`.
"""
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

CATALOG = Path(__file__).resolve().parent.parent / 'data' / 'catalog.json'

# Дубликаты на удаление (согласовано с пользователем 2026-05-14)
TO_DELETE = {
    '00011763105_2',   # Рельс Р24 новый ГОСТ 6368-82 — дубль 00011763105 (без картинки)
    '00011766138',     # Накладка 1Р-65 новая — дубль 00011766138_3 (без картинки)
    '00011779137',     # Рельс Р24 хранение за 80000 — зомби-карточка без картинки
}

# Категории крепежа/шпал/спец-рельсов: по умолчанию condition='new', если в имени нет маркеров
CREPEZH_CATS = {
    'Накладки рельсовые', 'Подкладки', 'Болты закладные', 'Болты клеммные',
    'Болты стыковые', 'Костыль путевой', 'Шурупы путевые',
    'Противоугон', 'Прокладки резиновые', 'Крепеж железнодорожный',
    'Крановый крепеж', 'Шпалы деревянные', 'Шпалы железобетонные',
    'Брус для стрелочного перевода',
    'Международный стандарт рельс DIN 536',
    'Рельсы крановые', 'Рельсы КР 80', 'Рельсы КР 100', 'Рельсы КР 120', 'Рельсы КР 140',
    'Рельсы Р8', 'Рельсы Р12', 'Рельсы Р15', 'Рельсы Р18',
    'Рельсы Р24', 'Рельсы Р33', 'Рельсы Р38', 'Рельсы Р43', 'Рельсы Р50',
    'Рельсы узкоколейные',
}


def classify_condition(name: str, category: str) -> str:
    """Возвращает 'new' | 'storage' | 'restored' | 'used'. Приоритет: used > restored > storage > new."""
    n = name.lower()
    # used: б/у, старогодные, с/г, группа износа
    if re.search(r'\bб/у\b|старогодн|с/г|групп[аы]?\s*износа', n):
        return 'used'
    # restored: восстановленные
    if re.search(r'восстановлен', n):
        return 'restored'
    # storage: хранение
    if re.search(r'хранени', n):
        return 'storage'
    # new: новый, новые, новая
    if re.search(r'\bнов[ыйеаяуо]', n):
        return 'new'
    # Без маркера в имени — для крепежа/шпал/спец-рельсов считаем 'new' по дефолту
    if category in CREPEZH_CATS:
        return 'new'
    return 'unknown'


def migrate(apply: bool) -> None:
    with open(CATALOG, encoding='utf-8') as f:
        data = json.load(f)

    n_before = len(data)

    # Удаление дубликатов
    deleted = [it for it in data if it['id'] in TO_DELETE]
    data = [it for it in data if it['id'] not in TO_DELETE]

    # Присвоение полей
    stats = {'new': 0, 'storage': 0, 'restored': 0, 'used': 0, 'unknown': 0}
    for it in data:
        cond = classify_condition(it.get('name', ''), it.get('category', ''))
        it['condition'] = cond
        it['availability'] = 'in_stock'   # дефолт: всё в наличии (согласовано)
        it['in_stock'] = True             # синхронизируем для обратной совместимости с фронтом/notify_app
        stats[cond] += 1

    print(f"\n=== Удаления ({len(deleted)}) ===")
    for it in deleted:
        print(f"  - id={it['id']}  name='{it['name']}'  price={it.get('price')}")

    print(f"\n=== Распределение condition ({len(data)} итого) ===")
    for k, v in stats.items():
        print(f"  {k:10s} {v}")
    if stats['unknown']:
        print("  ⚠️ Есть unknown — нужно поправить classify_condition")

    print(f"\n=== Полный список (для глазной проверки) ===")
    by_cond: dict[str, list] = {k: [] for k in stats}
    for it in data:
        by_cond[it['condition']].append(it)

    for cond in ('new', 'storage', 'restored', 'used', 'unknown'):
        items = by_cond[cond]
        if not items:
            continue
        print(f"\n--- {cond.upper()} ({len(items)}) ---")
        for it in items:
            print(f"  [{it.get('category','')[:25]:25s}] {it['name']}")

    if not apply:
        print("\n*** Dry-run. Чтобы применить — запусти с --apply ***")
        return

    # Бэкап и сохранение
    backup = CATALOG.with_suffix(f'.json.bak-{datetime.now().strftime("%Y-%m-%d-%H%M%S")}-pre-cond-migr')
    shutil.copy2(CATALOG, backup)
    print(f"\nBackup: {backup.name}")

    with open(CATALOG, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Записано {len(data)} позиций (было {n_before})")


if __name__ == '__main__':
    apply = '--apply' in sys.argv
    migrate(apply)
