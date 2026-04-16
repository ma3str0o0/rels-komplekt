#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_images.py — Обновление data/catalog.json: добавляет поле "image"
из data/image_map.json. Не затрагивает существующие поля.
"""

import json
from pathlib import Path

ROOT          = Path(__file__).parent.parent
CATALOG_PATH  = ROOT / "data" / "catalog.json"
IMAGE_MAP_PATH = ROOT / "data" / "image_map.json"

def main():
    # Загружаем данные
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = json.load(f)

    with open(IMAGE_MAP_PATH, encoding="utf-8") as f:
        image_map = json.load(f)

    # Строим индекс: catalog_id → image_file
    image_index = {}
    for entry in image_map.get("products", []):
        cid = entry.get("catalog_id")
        img = entry.get("image_file")  # None если фото нет
        if cid:
            image_index[cid] = img

    # Обновляем каталог
    updated = 0
    already  = 0
    no_photo = 0

    for item in catalog:
        cid = item["id"]
        if cid in image_index:
            new_val = image_index[cid]
            if item.get("image") == new_val:
                already += 1
            else:
                item["image"] = new_val
                updated += 1
                if new_val:
                    print(f"  ✓ {cid}: {new_val}")
                else:
                    no_photo += 1
        else:
            # Позиция не найдена в image_map → оставляем image: null
            if "image" not in item:
                item["image"] = None

    # Сохраняем
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"\nОбновлён catalog.json:")
    print(f"  Позиций в каталоге:    {len(catalog)}")
    print(f"  Получили фото:         {updated - no_photo}")
    print(f"  Явно без фото (null):  {no_photo}")
    print(f"  Уже были актуальны:    {already}")
    print(f"  Не найдено в image_map:{len(catalog) - len(image_index)}")

if __name__ == "__main__":
    main()
