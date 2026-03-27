#!/usr/bin/env python3
"""
Парсер сайта vsp74.ru — Этап 1: сбор данных о товарах конкурента
"""

import json
import time
import sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Базовый URL конкурента
BASE_URL = "https://www.vsp74.ru"

# Категории для парсинга
CATEGORIES = [
    {"name": "Рельсы железнодорожные", "url": f"{BASE_URL}/relsy-zheleznodorozhnye.html"},
    {"name": "Рельсы крановые",         "url": f"{BASE_URL}/relsy-kranovye.html"},
    {"name": "Рельсы узкоколейные",     "url": f"{BASE_URL}/relsy-uzkokoleynye.html"},
    {"name": "Шпалы деревянные",        "url": f"{BASE_URL}/shpaly-brus-derevyannyj.html"},
    {"name": "Шпалы железобетонные",    "url": f"{BASE_URL}/shpaly-brus-zhelezobetonnyj.html"},
    {"name": "Накладки",                "url": f"{BASE_URL}/nakladki.html"},
    {"name": "Подкладки",               "url": f"{BASE_URL}/podkladki.html"},
    {"name": "Прокладки",               "url": f"{BASE_URL}/prokladki-rti-izolyatsiya.html"},
    {"name": "Костыль, шуруп, противоугон", "url": f"{BASE_URL}/protivougony.html"},
    {"name": "Болты, гайки, шайбы",    "url": f"{BASE_URL}/bolty-putevye.html"},
    {"name": "Крановый крепеж",         "url": f"{BASE_URL}/kranovyj-krepezh.html"},
    {"name": "Комплекты скреплений",    "url": f"{BASE_URL}/komplekt-skreplenij-relsov.html"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

OUTPUT_FILE = Path(__file__).parent.parent.parent / "data" / "competitor_raw.json"


def get_page(url: str, timeout: int = 10) -> BeautifulSoup | None:
    """Загрузить страницу и вернуть BeautifulSoup объект или None при ошибке."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code != 200:
            print(f"  [WARN] HTTP {resp.status_code}: {url}", file=sys.stderr)
            return None
        resp.encoding = resp.apparent_encoding
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"  [ERROR] {url}: {e}", file=sys.stderr)
        return None


def extract_product_links(soup: BeautifulSoup, category_url: str) -> list[str]:
    """Найти ссылки на товары на странице категории."""
    links = set()

    # Ищем ссылки в карточках товаров — перебираем типичные паттерны
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()

        # Пропускаем якоря, внешние ссылки, технические страницы
        if (
            href.startswith("#")
            or href.startswith("mailto:")
            or href.startswith("tel:")
            or "vk.com" in href
            or "whatsapp" in href
            or href in ("/", "")
        ):
            continue

        # Строим абсолютный URL
        if href.startswith("http"):
            full_url = href
        elif href.startswith("/"):
            full_url = BASE_URL + href
        else:
            full_url = BASE_URL + "/" + href

        # Берём только страницы того же сайта с .html
        if full_url.startswith(BASE_URL) and full_url.endswith(".html"):
            # Исключаем страницы-категории и служебные
            skip_fragments = [
                "relsy-zheleznodorozhnye", "relsy-kranovye", "relsy-uzkokoleynye",
                "shpaly-brus-derevyannyj", "shpaly-brus-zhelezobetonnyj",
                "nakladki", "podkladki", "prokladki-rti-izolyatsiya",
                "protivougony", "bolty-putevye", "kranovyj-krepezh",
                "komplekt-skreplenij-relsov",
                "index", "kontakty", "dostavka", "oplata", "o-kompanii",
                "politika", "news", "blog",
            ]
            page_slug = full_url.rsplit("/", 1)[-1].replace(".html", "")
            if page_slug not in skip_fragments:
                links.add(full_url)

    return list(links)


def parse_price(soup: BeautifulSoup) -> int | None:
    """Извлечь цену из страницы товара."""
    # Ищем элементы с ценой
    price_selectors = [
        {"class_": lambda c: c and any("price" in cls.lower() for cls in (c if isinstance(c, list) else [c]))},
    ]

    # Поиск по тексту — ищем числа рядом с руб/₽
    import re
    text = soup.get_text(" ", strip=True)

    # Паттерны цены: "142 000 руб", "142000 ₽", "от 142 000 руб/т"
    patterns = [
        r"(\d[\d\s]{2,8}\d)\s*руб",
        r"(\d[\d\s]{2,8}\d)\s*₽",
        r"(\d[\d\s]{2,8}\d)\s*р\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            raw = match.group(1).replace(" ", "").replace("\u00a0", "")
            try:
                val = int(raw)
                if 100 <= val <= 10_000_000:  # адекватный диапазон цен
                    return val
            except ValueError:
                continue

    # Поиск по классам/id
    for selector in ["price", "product-price", "cost", "tovar-price"]:
        el = soup.find(class_=lambda c: c and selector in " ".join(c if isinstance(c, list) else [c]).lower())
        if el:
            raw = re.sub(r"[^\d]", "", el.get_text())
            if raw and 100 <= int(raw) <= 10_000_000:
                return int(raw)

    return None


def parse_specs(soup: BeautifulSoup) -> dict:
    """Извлечь таблицу характеристик."""
    specs = {}

    # Вариант 1: таблица с двумя колонками
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) == 2:
                key = cells[0].get_text(strip=True)
                val = cells[1].get_text(strip=True)
                if key and val and len(key) < 80:
                    specs[key] = val

    # Вариант 2: definition list
    if not specs:
        for dl in soup.find_all("dl"):
            terms = dl.find_all("dt")
            defs = dl.find_all("dd")
            for dt, dd in zip(terms, defs):
                key = dt.get_text(strip=True)
                val = dd.get_text(strip=True)
                if key and val:
                    specs[key] = val

    return specs


def parse_product(url: str) -> dict | None:
    """Собрать данные одного товара."""
    soup = get_page(url)
    if not soup:
        return None

    # Название
    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else ""

    # Описание — первый крупный текстовый блок
    description = ""
    for tag in soup.find_all(["p", "div"]):
        text = tag.get_text(strip=True)
        # Берём первый достаточно длинный абзац, не являющийся навигацией
        if len(text) > 100 and text != name:
            description = text[:500]
            break

    # Цена
    price = parse_price(soup)

    # Характеристики
    specs = parse_specs(soup)

    # Наличие фото (исключаем логотипы и иконки)
    images = soup.find_all("img", src=True)
    has_photos = any(
        img["src"] for img in images
        if not any(kw in img.get("src", "").lower() for kw in ["logo", "icon", "banner", "footer", "header"])
        and img.get("width", "100") not in ["16", "32", "48"]
    )

    # Наличие PDF
    pdf_links = [a["href"] for a in soup.find_all("a", href=True) if a["href"].lower().endswith(".pdf")]
    has_pdf = len(pdf_links) > 0

    return {
        "url": url,
        "name": name,
        "price": price,
        "description": description,
        "specs": specs,
        "has_photos": has_photos,
        "has_pdf": has_pdf,
        "has_spec_table": len(specs) > 0,
        "pdf_links": pdf_links,
    }


def main():
    result = {}
    total_products = 0

    for idx, cat in enumerate(CATEGORIES, 1):
        print(f"[{idx}/{len(CATEGORIES)}] Парсинг: {cat['name']}...")
        soup = get_page(cat["url"])
        if not soup:
            print(f"  Пропуск категории (ошибка загрузки)")
            result[cat["name"]] = []
            continue

        product_links = extract_product_links(soup, cat["url"])
        print(f"  Найдено ссылок на товары: {len(product_links)}")

        products = []
        for link in product_links:
            time.sleep(2)
            product = parse_product(link)
            if product and product["name"]:
                products.append(product)
                print(f"  + {product['name'][:60]}" + (f" — {product['price']} руб." if product["price"] else ""))

        result[cat["name"]] = products
        total_products += len(products)
        print(f"  Собрано товаров: {len(products)}")

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nГотово! Всего товаров: {total_products}")
    print(f"Сохранено в: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
