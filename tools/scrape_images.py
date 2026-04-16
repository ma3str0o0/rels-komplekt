#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrape_images.py — Парсинг фотографий товаров с сайта rels-komplekt.ru
Скачивает фото и сопоставляет с позициями data/catalog.json.
Результат → data/image_map.json, файлы → assets/img/products/
"""

import json
import os
import re
import sys
import time
import difflib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ─── Пути ──────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
CATALOG_PATH  = ROOT / "data" / "catalog.json"
IMAGE_MAP_PATH = ROOT / "data" / "image_map.json"
PRODUCTS_DIR  = ROOT / "assets" / "img" / "products"
CATEGORIES_DIR = ROOT / "assets" / "img" / "categories"

PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
CATEGORIES_DIR.mkdir(parents=True, exist_ok=True)

# ─── Настройки ─────────────────────────────────────────────────────────
BASE_URL = "https://rels-komplekt.ru"
DELAY    = 0.5      # секунд между запросами
TIMEOUT  = 15       # таймаут на один запрос
FUZZY_THRESHOLD = 0.82

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RelsKomplektBot/1.0)",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

CATEGORY_URLS = [
    "https://rels-komplekt.ru/store/relsy/",
    "https://rels-komplekt.ru/store/relsy-kranovye/",
    "https://rels-komplekt.ru/store/relsy-uzkoy-kolei/",
    "https://rels-komplekt.ru/store/kranovyy-krepezh/",
    "https://rels-komplekt.ru/store/shpaly-derevyannye-propitannye/",
    "https://rels-komplekt.ru/store/brus-perevodnoy/",
    "https://rels-komplekt.ru/store/shpaly-zhelezobetonnye/",
    "https://rels-komplekt.ru/store/mezhdunarodnyy-standart-rels-din-536/",
    "https://rels-komplekt.ru/store/krepezh-zhd/",
]


# ─── HTTP-хелпер ───────────────────────────────────────────────────────
session = requests.Session()
session.headers.update(HEADERS)

def get(url):
    """GET с задержкой и обработкой ошибок. Возвращает BeautifulSoup или None."""
    try:
        time.sleep(DELAY)
        r = session.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        r.encoding = "utf-8"
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  [!] Ошибка GET {url}: {e}", file=sys.stderr)
        return None


# ─── Сбор ссылок на товарные страницы ──────────────────────────────────
def is_product_url(url):
    """Ссылка ведёт на товарную страницу (4 сегмента: /store/cat/subcat/product/)."""
    parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
    return len(parts) >= 3 and parts[0] == "store"

def store_depth(url):
    """Возвращает количество сегментов пути после /store/: 1=кат, 2=субкат, 3=товар."""
    parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
    # parts[0] == 'store', далее сегменты
    return len(parts) - 1  # 1=кат, 2=субкат, 3=товар

def collect_product_urls():
    """Обходит категории → подкатегории → товарные страницы. Возвращает list[str]."""
    visited      = set()
    product_urls = []
    category_pages = []

    def crawl(url):
        if url in visited:
            return
        visited.add(url)

        soup = get(url)
        if not soup:
            return

        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Принимаем и абсолютные, и относительные /store/…
            abs_url = urljoin(BASE_URL, href).rstrip("/") + "/"
            # Отфильтровываем не-store и внешние домены
            parsed = urlparse(abs_url)
            if parsed.netloc != "rels-komplekt.ru":
                continue
            if not parsed.path.startswith("/store/"):
                continue
            if abs_url in visited:
                continue

            d = store_depth(abs_url)
            if d == 3:
                # Товарная страница
                if abs_url not in product_urls:
                    product_urls.append(abs_url)
                visited.add(abs_url)
            elif d in (1, 2):
                # Категория или подкатегория — рекурсируем
                crawl(abs_url)

    print("Шаг 1: сбор ссылок на товарные страницы...")
    for cat_url in CATEGORY_URLS:
        print(f"  Категория: {cat_url}")
        category_pages.append(cat_url)
        crawl(cat_url)

    print(f"  Найдено товарных страниц: {len(product_urls)}")
    return product_urls, category_pages


# ─── Парсинг одной товарной страницы ───────────────────────────────────
def parse_product_page(url):
    """
    Возвращает dict:
      slug, cms_name, image_url, thumb_url
    """
    parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
    slug  = parts[-1] if parts else ""

    soup = get(url)
    if not soup:
        return {"slug": slug, "cms_name": "", "image_url": None, "thumb_url": None}

    # Название товара
    h1 = soup.find("h1")
    cms_name = h1.get_text(strip=True) if h1 else ""

    # Изображение: ищем <a href="/uploadedFiles/eshopimages/big/...">
    image_url = None
    thumb_url = None

    # Вариант 1: стандартный блок с ссылкой на big
    for a in soup.find_all("a", href=re.compile(r"/uploadedFiles/eshopimages/big/")):
        href = a.get("href", "")
        img  = a.find("img")
        if not img:
            continue
        # Фильтр заглушек
        src = img.get("src", "")
        alt = img.get("alt", "")
        if "no_cover" in src or "Нет изображения" in alt or "no_cover" in href:
            continue
        image_url = urljoin(BASE_URL, href)
        thumb_url = urljoin(BASE_URL, src)
        break

    # Вариант 2: просто <img> в блоке товара (без ссылки на big)
    if not image_url:
        for img in soup.find_all("img", src=re.compile(r"/uploadedFiles/eshopimages/")):
            src = img.get("src", "")
            alt = img.get("alt", "")
            if "no_cover" in src or "Нет изображения" in alt:
                continue
            # Пробуем сконструировать big-URL из src
            big_src = re.sub(r"/icons/\d+x\d+(?:_cropped)?(?:/watermarked)?/", "/big/", src)
            big_src = re.sub(r"/thumbs/", "/big/", big_src)
            image_url = urljoin(BASE_URL, big_src)
            thumb_url = urljoin(BASE_URL, src)
            break

    return {
        "slug":      slug,
        "cms_name":  cms_name,
        "image_url": image_url,
        "thumb_url": thumb_url,
    }


# ─── Парсинг обложек категорий ─────────────────────────────────────────
def parse_category_covers():
    """Парсит главную магазина, собирает обложки категорий. Возвращает list[dict]."""
    print("\nШаг 3: парсинг обложек категорий...")
    store_url = BASE_URL + "/store/"
    soup = get(store_url)
    if not soup:
        return []

    cats = []
    for a in soup.find_all("a", href=re.compile(r"^/store/[^/]+/$")):
        img = a.find("img")
        if not img:
            continue
        src = img.get("src", "")
        alt = img.get("alt", "") or a.get_text(strip=True)
        if "no_cover" in src:
            continue
        cats.append({
            "name":         alt,
            "original_url": urljoin(BASE_URL, src),
            "image_file":   None,
        })

    print(f"  Категорий с фото: {len(cats)}")
    return cats


# ─── Нормализация имени для fuzzy-сравнения ─────────────────────────────
_NORM_RE = re.compile(r"[\s\-–—,./\\()]+")

def normalize(s):
    s = s.lower().strip()
    s = _NORM_RE.sub(" ", s)
    return s.strip()


# ─── Маппинг CMS-товаров → catalog.json ────────────────────────────────
def match_catalog(cms_products, catalog):
    """
    Для каждого cms-товара находит запись в catalog.
    Возвращает list[dict] с полями matched/*.
    """
    # Строим индексы
    by_page_name = {}
    by_name_norm = {}
    for item in catalog:
        pn = item.get("page_name", "")
        if pn:
            by_page_name[normalize(pn)] = item
        nn = normalize(item.get("name", ""))
        if nn:
            by_name_norm[nn] = item

    all_norm_names = list(by_name_norm.keys())

    matched = []
    unmatched = []
    stats = {"exact_page_name": 0, "exact_name": 0, "fuzzy": 0}

    for cms in cms_products:
        slug_norm = normalize(cms["slug"])
        name_norm = normalize(cms["cms_name"])

        found_item = None
        match_type = None

        # 1. Точное совпадение page_name
        if slug_norm in by_page_name:
            found_item = by_page_name[slug_norm]
            match_type = "exact_page_name"

        # 2. Совпадение нормализованного имени
        if not found_item and name_norm in by_name_norm:
            found_item = by_name_norm[name_norm]
            match_type = "exact_name"

        # 3. Fuzzy по имени
        if not found_item and name_norm and all_norm_names:
            best = difflib.get_close_matches(name_norm, all_norm_names, n=1, cutoff=FUZZY_THRESHOLD)
            if best:
                found_item = by_name_norm[best[0]]
                match_type = "fuzzy"

        if found_item:
            stats[match_type] += 1
            matched.append({
                "catalog_id":   found_item["id"],
                "catalog_name": found_item["name"],
                "cms_slug":     cms["slug"],
                "cms_name":     cms["cms_name"],
                "match_type":   match_type,
                "has_image":    cms["image_url"] is not None,
                "image_file":   None,  # заполнится после скачивания
                "original_url": cms["image_url"],
            })
        else:
            if cms["image_url"]:
                unmatched.append({
                    "cms_slug":  cms["slug"],
                    "cms_name":  cms["cms_name"],
                    "image_url": cms["image_url"],
                })

    return matched, unmatched, stats


# ─── Скачивание файлов ──────────────────────────────────────────────────
_TRANSLIT_MAP = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh',
    'з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o',
    'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts',
    'ч':'ch','ш':'sh','щ':'shch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
}

def safe_filename(s):
    """Транслитерирует и очищает строку для использования как имя файла."""
    s = s.lower()
    s = ''.join(_TRANSLIT_MAP.get(c, c) for c in s)
    s = re.sub(r"[^a-z0-9._-]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:80]

def download_file(url, dest_path):
    """Скачивает файл по URL в dest_path. Возвращает размер в байтах или 0."""
    try:
        time.sleep(DELAY)
        r = session.get(url, timeout=TIMEOUT, stream=True)
        r.raise_for_status()
        size = 0
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
                size += len(chunk)
        return size
    except Exception as e:
        print(f"  [!] Ошибка скачивания {url}: {e}", file=sys.stderr)
        if dest_path.exists():
            dest_path.unlink()
        return 0


def download_product_images(matched):
    """Скачивает изображения для сматченных товаров. Возвращает (файлов, байт)."""
    print("\nШаг 4: скачивание изображений товаров...")
    total_files = 0
    total_bytes = 0

    for entry in matched:
        if not entry["has_image"] or not entry["original_url"]:
            continue

        url = entry["original_url"]
        ext = Path(urlparse(url).path).suffix.lower() or ".jpg"
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            ext = ".jpg"

        fname = safe_filename(entry["catalog_id"]) + ext
        dest  = PRODUCTS_DIR / fname

        if dest.exists():
            # Уже скачан
            entry["image_file"] = f"assets/img/products/{fname}"
            total_files += 1
            continue

        print(f"  Скачиваю: {fname} ← {url}")
        size = download_file(url, dest)
        if size > 0:
            entry["image_file"] = f"assets/img/products/{fname}"
            total_files += 1
            total_bytes += size
        else:
            entry["has_image"] = False

    return total_files, total_bytes


def download_category_images(categories):
    """Скачивает обложки категорий. Возвращает количество скачанных файлов."""
    print("\nШаг 5: скачивание обложек категорий...")
    count = 0

    for cat in categories:
        url = cat.get("original_url")
        if not url:
            continue

        ext   = Path(urlparse(url).path).suffix.lower() or ".png"
        fname = safe_filename(cat["name"]) + ext
        dest  = CATEGORIES_DIR / fname

        if dest.exists():
            cat["image_file"] = f"assets/img/categories/{fname}"
            count += 1
            continue

        print(f"  Скачиваю категорию: {fname}")
        size = download_file(url, dest)
        if size > 0:
            cat["image_file"] = f"assets/img/categories/{fname}"
            count += 1

    return count


# ─── Главная функция ───────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("ПАРСИНГ ИЗОБРАЖЕНИЙ — rels-komplekt.ru")
    print("=" * 50)

    # Загружаем каталог
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = json.load(f)
    print(f"Каталог загружен: {len(catalog)} позиций")

    # 1. Сбор ссылок
    product_urls, category_urls_found = collect_product_urls()

    # 2. Парсинг товарных страниц
    print(f"\nШаг 2: парсинг {len(product_urls)} товарных страниц...")
    cms_products = []
    pages_with_images = 0

    for i, url in enumerate(product_urls, 1):
        if i % 10 == 0:
            print(f"  [{i}/{len(product_urls)}]...")
        info = parse_product_page(url)
        cms_products.append(info)
        if info["image_url"]:
            pages_with_images += 1

    pages_without = len(cms_products) - pages_with_images

    # 3. Обложки категорий
    categories = parse_category_covers()

    # 4. Маппинг
    print("\nШаг 3 (маппинг): сопоставление с catalog.json...")
    matched, unmatched, match_stats = match_catalog(cms_products, catalog)
    print(f"  Сопоставлено: {len(matched)}, не сопоставлено: {len(unmatched)}")

    # 5. Скачивание
    dl_files, dl_bytes = download_product_images(matched)
    cat_count = download_category_images(categories)

    # 6. Сохранение image_map.json
    image_map = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total_product_pages":   len(cms_products),
            "pages_with_images":     pages_with_images,
            "pages_without_images":  pages_without,
            "matched_to_catalog":    len(matched),
            "unmatched":             len(unmatched),
        },
        "products":      matched,
        "categories":    categories,
        "unmatched_cms": unmatched,
    }

    with open(IMAGE_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(image_map, f, ensure_ascii=False, indent=2)
    print(f"\nСохранено: {IMAGE_MAP_PATH}")

    # 7. Отчёт
    print("\n" + "=" * 50)
    print("=== ОТЧЁТ ПАРСИНГА ИЗОБРАЖЕНИЙ ===")
    print(f"Всего товарных страниц: {len(cms_products)}")
    print(f"  С фотографиями:  {pages_with_images}")
    print(f"  Без фотографий:  {pages_without}")
    print(f"Сопоставлено с каталогом: {len(matched)} / {len(catalog)}")
    print(f"  По page_name: {match_stats['exact_page_name']}")
    print(f"  По имени:     {match_stats['exact_name']}")
    print(f"  По fuzzy:     {match_stats['fuzzy']}")
    print(f"Не сопоставлено (только на CMS): {len(unmatched)}")
    print(f"Скачано файлов: {dl_files} ({dl_bytes / 1024 / 1024:.1f} MB)")
    print(f"Категорий с фото: {cat_count}")
    print("=" * 50)


if __name__ == "__main__":
    main()
