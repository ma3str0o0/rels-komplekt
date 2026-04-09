"""
Парсер сайта vsp74.ru — цены, технические характеристики, описания.
Результат: data/vsp74_scrape.json

Запуск: python3 tools/parse_vsp74.py
"""

import json
import re
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ─── Конфигурация ────────────────────────────────────────────────

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; research bot)'}
DELAY   = 1.5  # секунд между запросами

TARGET_PAGES = [
    {"url": "https://vsp74.ru/relsy-zheleznodorozhnye.html",         "category": "rails_wide",        "pages": 3},
    {"url": "https://vsp74.ru/relsy-kranovye.html",                  "category": "rails_crane",       "pages": 2},
    {"url": "https://vsp74.ru/relsy-uzkokoleynye.html",              "category": "rails_narrow",      "pages": 1},
    {"url": "https://vsp74.ru/shpaly-brus-derevyannyj.html",         "category": "sleepers_wood",     "pages": 1},
    {"url": "https://vsp74.ru/shpaly-brus-zhelezobetonnyj.html",     "category": "sleepers_concrete", "pages": 1},
    {"url": "https://vsp74.ru/nakladki.html",                        "category": "nakladki",          "pages": 1},
    {"url": "https://vsp74.ru/podkladki.html",                       "category": "podkladki",         "pages": 1},
    {"url": "https://vsp74.ru/komplekt-skreplenij-relsov.html",      "category": "fasteners",         "pages": 2},
]

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "vsp74_scrape.json"

# Мусорные строки в описаниях (навигация сайта)
JUNK_MARKERS = ['Покупателю', 'Личный кабинет', 'Корзина', 'Каталог', 'Поиск', 'В наличии', 'Заказы']


# ─── HTTP ────────────────────────────────────────────────────────

def fetch(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or 'utf-8'
        return BeautifulSoup(resp.text, 'html.parser')
    except Exception as e:
        print(f"  [WARN] Не удалось получить {url}: {e}")
        return None


# ─── Парсинг цены / веса ─────────────────────────────────────────

def parse_price(raw: str) -> int | None:
    """Очищает строку цены: '171 145 ₽' → 171145, '—' → None"""
    cleaned = raw.replace('\xa0', '').replace(' ', '').replace('₽', '').replace('—', '').strip()
    if not cleaned or cleaned == '0':
        return None
    try:
        return int(re.sub(r'[^\d]', '', cleaned)) or None
    except ValueError:
        return None


def parse_weight(raw: str) -> float | None:
    """Очищает строку веса: '64,88' → 64.88, '' → None"""
    cleaned = raw.replace(',', '.').strip()
    # берём первое число (иногда 'XX.XX кг/м')
    match = re.search(r'[\d]+\.?[\d]*', cleaned)
    if match:
        try:
            return float(match.group())
        except ValueError:
            pass
    return None


# ─── Парсинг одной строки таблицы цен ───────────────────────────

def _clean_price(s: str) -> int | None:
    """'171 145 ₽' → 171145, '—' / '' → None"""
    s = s.replace('\xa0', '').replace(' ', '').replace('₽', '').replace('—', '0').strip()
    try:
        return int(s) if s and s != '0' else None
    except ValueError:
        return None


def parse_price_row(row) -> dict | None:
    """
    Реальная структура vsp74.ru (проверено инспекцией HTML):

    TD[0] — class="product-item-cell"
            div.product-item-name >
              a[data-entity=image-wrapper] title="..."  ← чистое имя
              div.product-item-title >
                div.product-item-info-container > div.item_gost
                div.product-item-info-container > div.item_weight
    TD[1] — ГОСТ (дублируется из TD[0], берём отсюда как строку)
    TD[2] — Вес кг/м (дублируется из TD[0])
    TD[3] — div.product-item-price-container >
              span.product-item-price-current  ← цена/шт
              span.product-item-price-old      ← старая цена (hidden, дубль)
    TD[4] — то же самое → цена/тн
    TD[5] — кнопка "В корзину" (игнорируем)

    ВАЖНО: get_text() на TD[4] даёт "171 145 ₽171 145 ₽" из-за скрытого span.
    Нужно брать только span.product-item-price-current.
    """
    cells = row.find_all('td')
    if len(cells) < 5:
        return None

    # Имя — из title атрибута ссылки-обёртки изображения (не get_text!)
    name_a = cells[0].find('a', attrs={'data-entity': 'image-wrapper'})
    name = name_a.get('title', '').strip() if name_a else ''
    if not name:
        # Фолбэк: текст <a> внутри div.product-item-title
        title_div = cells[0].find('div', class_='product-item-title')
        if title_div:
            link = title_div.find('a')
            name = link.get_text(strip=True) if link else ''
    if not name or name in ('Название', 'Наименование'):
        return None

    # ГОСТ — из TD[1] (отдельная ячейка)
    gost_div = cells[1].find('div', class_='item_gost')
    gost = gost_div.get_text(strip=True) if gost_div else cells[1].get_text(strip=True)

    # Вес — из TD[2] (отдельная ячейка)
    weight_div = cells[2].find('div', class_='item_weight')
    weight_str = weight_div.get_text(strip=True) if weight_div else cells[2].get_text(strip=True)
    weight_str = weight_str.replace(',', '.').split()[0] if weight_str else ''
    try:
        weight = float(weight_str)
    except (ValueError, IndexError):
        weight = None

    # Цена — берём span.product-item-price-current (один, без дублей из price-old)
    def get_price(cell) -> int | None:
        span = cell.find('span', class_='product-item-price-current')
        raw = span.get_text(strip=True) if span else cell.get_text(strip=True)
        return _clean_price(raw)

    return {
        'name':             name,
        'gost':             gost,
        'weight_per_meter': weight,
        'price_per_piece':  get_price(cells[3]),
        'price_per_ton':    get_price(cells[4]),
    }


# ─── Парсинг таблицы цен ─────────────────────────────────────────

def parse_price_table(table) -> list[dict]:
    """Первая таблица на странице — таблица цен."""
    items = []
    for row in table.find_all('tr'):
        # Пропускаем строки заголовков
        if row.find('th'):
            continue
        item = parse_price_row(row)
        if item:
            items.append(item)
    return items


# ─── Парсинг технических таблиц ──────────────────────────────────

def parse_spec_tables(tables) -> list[dict]:
    """
    Остальные таблицы (индекс 1+) — технические характеристики.
    """
    result = []
    for table in tables:
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue

        headers = []
        data_rows = []

        for i, row in enumerate(rows):
            ths = row.find_all('th')
            tds = row.find_all('td')

            if ths and not tds:
                # Строка заголовков
                headers = [th.get_text(strip=True) for th in ths]
            elif tds:
                row_data = [td.get_text(strip=True) for td in tds]
                if any(row_data):  # пропускаем пустые строки
                    data_rows.append(row_data)

        if data_rows:
            result.append({
                "headers": headers,
                "rows":    data_rows,
            })

    return result


# ─── Парсинг описания ────────────────────────────────────────────

def parse_description(soup: BeautifulSoup) -> str | None:
    """
    Ищет текстовое описание категории.
    Приоритет: <article>, div.detail-text, main p, любой длинный блок.
    """
    candidates = []

    # Стратегия 1: article
    article = soup.find('article')
    if article:
        candidates.append(article.get_text(separator='\n'))

    # Стратегия 2: div.detail-text
    detail = soup.find('div', class_=re.compile(r'detail.?text', re.I))
    if detail:
        candidates.append(detail.get_text(separator='\n'))

    # Стратегия 3: main → все параграфы
    main = soup.find('main') or soup.find('div', id='content') or soup.find('div', class_=re.compile(r'content', re.I))
    if main:
        paragraphs = main.find_all('p')
        candidates.append('\n'.join(p.get_text(strip=True) for p in paragraphs))

    for raw in candidates:
        lines = raw.splitlines()
        clean_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if any(marker in line for marker in JUNK_MARKERS):
                continue
            if len(line) < 20:  # слишком короткие строки — навигация
                continue
            clean_lines.append(line)

        text = ' '.join(clean_lines)
        if len(text) >= 200:
            return text[:1500]

    return None


# ─── Основной парсинг одной категории ────────────────────────────

def scrape_category(target: dict) -> dict:
    base_url  = target['url']
    category  = target['category']
    num_pages = target['pages']

    print(f"\n[{category}] {base_url}")

    all_items      = []
    spec_tables    = []
    description    = None
    first_page     = True

    for page_num in range(1, num_pages + 1):
        url = base_url if page_num == 1 else f"{base_url}?PAGEN_1={page_num}"
        print(f"  → стр. {page_num}: {url}")

        soup = fetch(url)
        if not soup:
            continue

        tables = soup.find_all('table')

        # Таблица цен — всегда первая
        if tables:
            items = parse_price_table(tables[0])
            print(f"     позиций в таблице цен: {len(items)}")
            all_items.extend(items)
        else:
            print("     [WARN] таблиц не найдено")

        # Технические таблицы — только с первой страницы (описание не дублируется)
        if first_page:
            if len(tables) > 1:
                spec_tables = parse_spec_tables(tables[1:])
                print(f"     тех. таблиц: {len(spec_tables)}")

            description = parse_description(soup)
            if description:
                print(f"     описание: {len(description)} символов")
            else:
                print("     описание: не найдено")

            first_page = False

        if page_num < num_pages:
            time.sleep(DELAY)

    return {
        "source_url":  base_url,
        "items":       all_items,
        "spec_tables": spec_tables,
        "description": description,
    }


# ─── Сводка ──────────────────────────────────────────────────────

def print_summary(categories: dict) -> None:
    print("\n" + "═" * 60)
    print("СВОДКА ПАРСИНГА")
    print("═" * 60)

    for cat_key, data in categories.items():
        items = data['items']
        n     = len(items)

        weights = sorted({i['weight_per_meter'] for i in items if i['weight_per_meter'] is not None})
        prices  = [i['price_per_ton'] for i in items if i['price_per_ton'] is not None]

        price_range = (
            f"{min(prices):,} – {max(prices):,} ₽/т".replace(',', ' ')
            if prices else "нет цен"
        )
        weight_str = ', '.join(str(w) for w in weights) if weights else "нет весов"

        desc = data['description']
        desc_info = f"да ({len(desc)} симв.)" if desc else "нет"

        print(f"\n[{cat_key}]")
        print(f"  Позиций:      {n}")
        print(f"  Веса (кг/м):  {weight_str}")
        print(f"  Цены:         {price_range}")
        print(f"  Описание:     {desc_info}")
        print(f"  Тех. таблиц: {len(data['spec_tables'])}")


# ─── Точка входа ─────────────────────────────────────────────────

def main() -> None:
    result = {
        "scraped_at": str(date.today()),
        "categories": {},
    }

    for target in TARGET_PAGES:
        cat_key = target['category']
        result['categories'][cat_key] = scrape_category(target)
        time.sleep(DELAY)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(f"\n✓ Сохранено: {OUTPUT_PATH}")
    print(f"  Размер файла: {OUTPUT_PATH.stat().st_size / 1024:.1f} КБ")

    print_summary(result['categories'])


if __name__ == '__main__':
    main()
