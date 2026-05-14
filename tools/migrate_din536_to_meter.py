"""
Миграция DIN 536: unit='шт' → 'м'. Цены и weight_per_unit остаются.
Цены изначально вводились как ₽/м, индикатор был ошибочно 'шт'.

Запуск:
    python3 tools/migrate_din536_to_meter.py            # dry-run
    python3 tools/migrate_din536_to_meter.py --apply    # применить
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

CATALOG = Path(__file__).resolve().parent.parent / 'data' / 'catalog.json'

DIN536_CATEGORY = 'Международный стандарт рельс DIN 536'


def migrate(apply: bool) -> None:
    with open(CATALOG, encoding='utf-8') as f:
        data = json.load(f)

    changed = []
    for it in data:
        if it.get('category') == DIN536_CATEGORY and it.get('unit') == 'шт':
            changed.append({
                'id': it['id'],
                'name': it['name'],
                'old_unit': it['unit'],
                'price': it.get('price'),
                'weight_per_unit': it.get('weight_per_unit'),
                'length_m': it.get('length_m'),
            })
            it['unit'] = 'м'

    print(f"=== Изменения ({len(changed)}) ===")
    for c in changed:
        wpm = (c['weight_per_unit'] / c['length_m']) if (c['weight_per_unit'] and c['length_m']) else None
        wpm_str = f"{wpm:.2f} кг/м" if wpm else "—"
        price_str = f"{c['price']} ₽/м" if c['price'] is not None else "—"
        print(f"  id={c['id']:24s}  {c['name']:30s}  unit: шт→м  price={price_str}  ({wpm_str})")

    if not apply:
        print("\n*** Dry-run. Чтобы применить — запусти с --apply ***")
        return

    backup = CATALOG.with_suffix(f'.json.bak-{datetime.now().strftime("%Y-%m-%d-%H%M%S")}-din536-meter')
    shutil.copy2(CATALOG, backup)
    print(f"\nBackup: {backup.name}")

    with open(CATALOG, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Записано {len(data)} позиций, изменено {len(changed)}")


if __name__ == '__main__':
    apply = '--apply' in sys.argv
    migrate(apply)
