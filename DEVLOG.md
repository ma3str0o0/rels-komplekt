# DEVLOG — Рельс-Комплект

Лог изменений проекта. Обновляется после каждой итерации разработки.

---

## [2026-03-24] — Коммит: MVP готов

Первоначальный запуск. Все 6 страниц, SEO, sitemap, robots.txt.

**Создано:**
- `index.html` — главная страница
- `catalog.html` — каталог с фильтрами и пагинацией
- `product.html` — карточка товара (`?id=UID`)
- `calculator.html` — калькулятор тоннажа
- `contacts.html` — контакты и реквизиты
- `order.html` — страница заявки (корзина)
- `assets/css/style.css` + `components.css`
- `assets/js/main.js`, `catalog.js`, `product.js`, `calculator.js`, `order.js`
- `data/catalog.json` — 158 позиций, 31 категория
- `sitemap.xml`, `robots.txt`

---

## [2026-03-27] — Итерация 1: Конкурентный анализ + HTML-отчёт

### tools/parser/viewer.py — новый файл

Генератор читаемого HTML-отчёта по конкурентному анализу.

- Читает `data/catalog_enriched.json` (158 позиций, 130 с данными конкурента)
- Генерирует `data/competitor_report.html` (~165 КБ, открывается без сервера)
- **Шапка KPI:** 4 карточки — всего товаров / совпадений / мы дешевле / конкурент дешевле
- **Таблица сравнения** с фильтрами (совпадение / цена) и поиском по названию
- **Сортировка** по любому столбцу (клик по заголовку)
- **Секция "Что добавить на сайт"** — товары где у конкурента есть описание / таблица хар-к / фото, которых нет у нас. Сортировка по количеству пробелов (убыв.)
- Стек: Bootstrap 5 через CDN, всё inline, без сервера

**Итоги анализа:**
- Совпадений найдено: 130 / 158
- Мы дешевле: 36 позиций
- Конкурент дешевле: 24 позиции

---

## [2026-03-27] — Итерация 2: Security review + исправления

Security audit выявил 8 проблем. Все исправлены.

### product.html
- **[CRITICAL → FIX]** XSS в `_renderCompetitorData`: данные `competitor_data.specs` вставлялись напрямую в `innerHTML` без экранирования.
  Добавлена функция `_escHtml()`, теперь ключи и значения таблицы экранируются.
- **[CRITICAL → FIX]** XSS через URL изображений из `cd.images[]`: `javascript:` URI мог выполниться.
  Добавлена функция `_isSafeUrl()` — допускаются только `http://` и `https://` протоколы. URL фильтруются до вставки в DOM.
- **[ALL]** Добавлен CSP мета-тег во все 6 HTML-страниц

### assets/js/order.js
- **[MEDIUM → FIX]** Удалён `console.log('[order.js] cart в localStorage:', ...)` — содержимое корзины утекало в консоль браузера

### assets/js/main.js
- **[MEDIUM → FIX]** В `console.warn` при незаполненном Telegram-токене убраны данные формы (`data`) — теперь выводится только нейтральное сообщение
- **[LOW → FIX]** Добавлен rate limiting на отправку форм: не чаще 1 раза в 30 секунд (`_submitThrottle`). Защита от спама в Telegram-бот.

### calculator.html
- **[INFO → FIX]** Добавлен SRI-хеш (`integrity="sha384-..."`) для jsPDF CDN. Защита от компрометации CDN.

### _headers (новый файл)
- Создан файл security headers для хостинга (Netlify/Nginx/Vercel):
  - `X-Frame-Options: DENY` — защита от clickjacking
  - `X-Content-Type-Options: nosniff` — защита от MIME sniffing
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: geolocation=(), microphone=(), camera=()`
  - `Content-Security-Policy` с `frame-ancestors 'none'`

---

## [2026-03-27] — Итерация 3: Калькулятор шт/кг/стоимость + конвертер валют

### assets/js/product.js — функция `renderPricing` переработана

**Было:** простой калькулятор "количество тонн → стоимость".

**Стало:** полноценный блок расчёта с двумя режимами:

**Режим "рельсы" (есть вес в таблице):**
- Поле `Кол-во, шт` ↔ `Кол-во, кг` — связаны двусторонне
- Изменение шт → пересчёт кг и стоимости
- Изменение кг → пересчёт шт (Math.ceil) и стоимости
- Начальные значения: 1 шт, вес 1 рельса (12.5 м), стоимость 1 рельса

**Режим "прочее" (нет веса):**
- Поле `Количество, т` → стоимость (как раньше, но с конвертером)

**Добавлена таблица весов `RAIL_WEIGHT_KG`** — 16 позиций по подкатегориям.
Вес = `кг/м × 12.5 м`:
- Р8→100кг, Р12→150кг, Р24→300кг, Р43→558кг, Р50→646кг, Р65→809кг
- КР70→875кг, КР80→1000кг, КР100→1250кг, КР120→1500кг, КР140→1750кг

**Переключатель валюты RUB / KZT:**
- Курс 1 RUB = 5.5 KZT (хардкод, константа `KZT` в `renderPricing`)
- Переключение мгновенно пересчитывает поле "Стоимость"
- Символ: ₽ / ₸

### assets/css/components.css — новые классы калькулятора

- `.calc-fields` — flex-строка для полей ввода
- `.calc-field` / `.calc-label` / `.calc-input` — структура одного поля
- `.calc-eq` — разделитель "="
- `.calc-result-row` / `.calc-result` — строка итога
- `.currency-toggle` / `.currency-opt` — pill-переключатель RUB/KZT

---

## [2026-03-27] — Итерация 4: Три баг-фикса

### Баг 1 — тёмный блок поверх поля "Стоимость" (product.html + components.css)

**Причина:** в `product.html` inline `<style>` определял `.product-specs { padding-block:48px; background }`, что коллизировало с компонентным `.product-specs { border-collapse:collapse }` и добавляло 48px padding на таблицу `id="productSpecs"`.

**Фиксы:**
- Переименован inline-класс: `.product-specs` → `.enriched-specs` (в CSS и в HTML `<section>`)
- В `.product-calculator` добавлены `position: relative; isolation: isolate` — создаётся новый stacking context, блокирующий z-index-конфликты из соседних блоков

### Баг 2 — кнопки калькулятора съехали (components.css)

- `.wizard__result-actions`: `gap: var(--space-md)` (16px) → `gap: 8px`
- `flex-wrap: wrap` и мобильный `width: 100%` уже были, остались без изменений

### Баг 3 — две колонки цены в order.html (order.js)

**Добавлена таблица весов `RAIL_WEIGHT_KG`** (зеркало из product.js, 16 позиций).

**Новая структура таблицы заявки:**
- `ЦЕНА/ЕД., ₽` — цена за 1 штуку = `(weight_kg / 1000) × price_per_ton`. Если вес неизвестен → "—"
- `ЦЕНА/Т, ₽` — цена за тонну = `item.price` из каталога
- `Сумма, ₽` — без изменений: `item.price × qty`
- `<tfoot>` — добавлена пустая ячейка под новый столбец (colspan остался 2)

---
