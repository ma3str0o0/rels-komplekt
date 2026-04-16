#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalize_images.py — Приводит все фото товаров к единому формату:
  • Квадрат 600×600 пикселей
  • Исходное изображение вписывается с сохранением пропорций
  • Отступы заполняются белым (#FFFFFF)
  • Результат сохраняется как JPEG качество 88
  • Оригинальные файлы заменяются; GIF/PNG → .jpg
"""

import sys
from pathlib import Path
from PIL import Image, UnidentifiedImageError

SIZE   = 600          # целевой размер квадрата, px
QUAL   = 88           # качество JPEG
BG     = (255, 255, 255)  # белый фон
EXTS   = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

ROOT        = Path(__file__).parent.parent
PRODUCTS_DIR = ROOT / 'assets' / 'img' / 'products'


def normalize(path: Path) -> bool:
    """Нормализует один файл. Возвращает True при успехе."""
    try:
        img = Image.open(path)
    except UnidentifiedImageError:
        print(f'  [!] Не удалось открыть: {path.name}', file=sys.stderr)
        return False

    # GIF — берём первый кадр
    if getattr(img, 'is_animated', False):
        img.seek(0)

    # Конвертируем в RGB (удаляет прозрачность, заменяя на белый)
    if img.mode in ('RGBA', 'LA', 'P'):
        bg = Image.new('RGB', img.size, BG)
        alpha = img.convert('RGBA').split()[-1]
        bg.paste(img.convert('RGBA'), mask=alpha)
        img = bg
    else:
        img = img.convert('RGB')

    # Вписываем в SIZE×SIZE с сохранением пропорций
    img.thumbnail((SIZE, SIZE), Image.LANCZOS)

    # Центрируем на белом фоне
    canvas = Image.new('RGB', (SIZE, SIZE), BG)
    x = (SIZE - img.width)  // 2
    y = (SIZE - img.height) // 2
    canvas.paste(img, (x, y))

    # Сохраняем как .jpg (переименовываем если нужно)
    dest = path.with_suffix('.jpg')
    canvas.save(dest, 'JPEG', quality=QUAL, optimize=True)

    if dest != path:
        path.unlink()   # удаляем оригинал с другим расширением

    return True


def main():
    files = [p for p in PRODUCTS_DIR.iterdir() if p.suffix.lower() in EXTS]
    total = len(files)
    ok = 0

    print(f'Нормализация {total} файлов → {SIZE}×{SIZE} JPEG...')

    for p in sorted(files):
        if normalize(p):
            ok += 1
            print(f'  ✓ {p.name}')

    print(f'\nГотово: {ok}/{total} файлов обработано.')

    # Обновляем пути в image_map.json (все расширения → .jpg)
    import json
    map_path = ROOT / 'data' / 'image_map.json'
    if map_path.exists():
        data = json.loads(map_path.read_text(encoding='utf-8'))
        for entry in data.get('products', []):
            f = entry.get('image_file')
            if f:
                entry['image_file'] = str(Path(f).with_suffix('.jpg'))
        map_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print('image_map.json — пути обновлены.')

    # Обновляем пути в catalog.json
    cat_path = ROOT / 'data' / 'catalog.json'
    if cat_path.exists():
        catalog = json.loads(cat_path.read_text(encoding='utf-8'))
        for item in catalog:
            f = item.get('image')
            if f:
                item['image'] = str(Path(f).with_suffix('.jpg'))
        cat_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
        print('catalog.json — пути обновлены.')


if __name__ == '__main__':
    main()
