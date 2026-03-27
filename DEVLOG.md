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

## [2026-03-27] — Итерация 5: Фикс тёмного фона .calc-result (git push)

**Причина:** `--color-primary: #0F172A` (near-black) использовался как `background` в двух местах калькулятора:
1. `.currency-opt input:checked + span { background: var(--color-primary) }` — активная кнопка RUB/KZT была почти чёрной
2. `.calc-result strong/span { color: var(--color-primary) }` — текст был тёмно-синим вместо акцентного

**По дизайн-системе** (`MASTER.md`): `--color-primary` (#0F172A) = текст/границы, `--color-cta` (#0369A1) = акцент/CTA.

**Фиксы в `components.css`:**
- `.calc-result` — добавлен `background: transparent`, убраны dark-primary цвета
- `.calc-result strong` — `color: var(--color-cta, #0369A1)` (синий акцент)
- `.calc-result span` — `color: var(--color-text, #020617)` (читаемый тёмный)
- `.currency-opt :checked + span` — `background/border-color: var(--color-cta)` вместо `var(--color-primary)`

**Коммит:** `8f3c27c` — запушено в `origin/main`

---

## [2026-03-27] — Итерация 6: Кнопки калькулятора + колонки цены в заявке

### Промпт 1 — `components.css`: `.wizard__result-actions`
- Добавлен `width: 100%` — исправлен width:0 (кнопки схлопывались)
- `gap: 8px` → `gap: 12px`
- `justify-content: flex-start`
- `.btn`: `flex: 1 1 auto`, `min-width: 200px`, `white-space: nowrap`
- Мобильный брейкпойнт `480px` → `600px`; кнопкам добавлен `flex: none`
- **Коммит:** `3574399`

### Промпт 2 — `order.js`: две колонки цены

**Архитектурное изменение:** `render()` стал `async`, при старте подгружает `data/catalog.json`. Данные из LocalStorage не содержат `subcategory`/`category` — их берём из каталога по `item.id`.

**Новый порядок колонок:** `# | Наименование | Кол-во | Ед. | ЦЕНА/Т | ЦЕНА/ШТ | Сумма | [del]`

**Логика `ЦЕНА/Т` / `ЦЕНА/ШТ`:**
- `unit === 'т'` → ЦЕНА/Т = `item.price` (цена уже в тоннах); ЦЕНА/ШТ = `price × weight_kg / 1000` (если вес известен)
- `unit === 'шт'` → ЦЕНА/ШТ = `item.price`; ЦЕНА/Т = `(price / weight_kg) × 1000` (если вес известен)
- Вес неизвестен → "—"

**Стиль:** заголовок ЦЕНА/Т стилизован как вторичный (`color: --color-text-muted`, `font-size: --font-size-sm`); ЦЕНА/ШТ — основной с `font-weight:600`

**Коммит:** `b61c19b`

---

## [2026-03-27] — Итерация 11: Тёмная тема

### assets/css/style.css
- В `:root` добавлены `--color-tint-blue: #EFF6FF` и `--color-surface-muted: #F1F5F9`
- Добавлен блок `[data-theme="dark"]` с полной палитрой (фон, поверхность, текст, границы, тени)
- `html { transition: background-color 0.3s ease, color 0.3s ease }` — плавное переключение
- CSS `.theme-toggle` — кнопка как у `.cart-btn`
- Замены хардкодов: `#EFF6FF` → `var(--color-tint-blue)` (nav, mobile menu, section__label), `#F1F5F9` → `var(--color-surface-muted)` (`.section--muted`), `#F8F9FA` → `var(--color-surface-muted)` (`.section--form-cta`)

### assets/css/components.css
- `#EFF6FF` → `var(--color-tint-blue)` в `.category-card__icon`, `.feature-card__icon`, `.cart-btn:hover`
- `#94A3B8` → `var(--color-text-muted)` в placeholder
- Добавлен блок `[data-theme="dark"]` в конце файла: оверрайды для `.stock-badge--in/out` и `.badge--blue/green/orange` (rgba-фоны, светлые цвета текста)

### assets/js/main.js
- Кнопка `.theme-toggle#themeToggle` добавлена в `_tplHeader()` перед "Свяжитесь с нами"
- Иконка: луна (светлая тема) / солнце (тёмная тема) — SVG меняется через `_updateThemeIcon()`
- `initTheme()` — читает `localStorage.getItem('theme')`, применяет `data-theme` на `<html>`, вешает обработчик клика
- Вызывается сразу после `loadComponents()` в DOMContentLoaded

### index/catalog/product/calculator/contacts/order .html
- Anti-FOUC inline-скрипт в `<head>` (первый элемент): применяет тему до загрузки CSS

**Коммит:** `b9743fc`

---

## [2026-03-27] — Итерация 10: Кнопка отправки спецификации в Telegram

### calculator.html
- Кнопка "Отправить в Telegram" после "Скачать PDF"
- Модальное окно: одно поле — Telegram username или номер телефона

### assets/js/calculator.js
- Константы `TELEGRAM_BOT_TOKEN = 'DEMO'` и `TELEGRAM_CHAT_ID = 'DEMO'`
- `openTgModal()` / `closeTgModal()` — открытие, закрытие, сброс формы
- Escape теперь закрывает оба модальных окна (Telegram и Email)
- Валидация: `@username` (regex `@\w{3,}`) или телефон (`[\d\s+()−]{7,}`)
- `handleSendTelegram()`:
  - При `TELEGRAM_BOT_TOKEN === 'DEMO'` → задержка 800мс, toast "Запрос принят. Наш менеджер напишет вам в Telegram в течение часа."
  - При реальных ключах → POST `https://api.telegram.org/bot{TOKEN}/sendMessage` с HTML-форматированным сообщением
  - Тело сообщения: контакт пользователя, параметры пути (тип рельса / длина / нити), список позиций с ценами, итоговая сумма
  - Спиннер на кнопке во время отправки

**Коммит:** `18d6525`

---

## [2026-03-27] — Итерация 8: Брендовый PDF через HTML print

### assets/js/calculator.js — `handleDownloadPdf()` полностью переписана

**Было:** jsPDF с транслитом (`Specifikaciya`, `Naimenovanie`, `Po zaprosu`), без цветов бренда, без логотипа и контактов. Кириллица не поддерживалась без embed-шрифтов.

**Стало:** генерация скрытого HTML-блока + `window.print()`. Браузер сохраняет как PDF через стандартный диалог.

**Структура документа (A4, книжная):**
- Шапка: фон `#1A56A0`, SVG-логотип (рельс со шпалами), название, контакты справа
- Заголовок: «СПЕЦИФИКАЦИЯ № YYYYMMDD-HHMM», дата, параметры пути
- Карточки: тоннаж / кол-во рельсов / кол-во шпал
- Таблица с границами, заголовки на `#E8F0F8`, строка итого с `border-top: 2px solid #1A56A0`
- Сноска и футер с контактами

**Технические детали:**
- `@media print { body * { visibility: hidden; } #rkPrintSpec, #rkPrintSpec * { visibility: visible; } }` — скрываем страницу, показываем только спецификацию
- `@page { size: A4 portrait; margin: 10mm 12mm; }`
- После `afterprint` событие — div автоматически удаляется из DOM
- Шрифт Arial — кириллица работает нативно без embed

**Удалено:** `fmtPricePlain()` — была нужна только для jsPDF

**Коммит:** `1792175`

---

## [2026-03-27] — Итерация 9: Кнопка отправки спецификации на email

### calculator.html
- Добавлена кнопка "Отправить на email" (рядом с "Скачать PDF")
- Модальное окно с полями: Email получателя (обязательный), Имя, Комментарий
- EmailJS SDK `@emailjs/browser@4` подключён через CDN
- CSP расширен: `cdn.jsdelivr.net` (script-src), `api.emailjs.com` (connect-src)

### assets/js/calculator.js
- Константы `EMAILJS_SERVICE_ID/TEMPLATE_ID/PUBLIC_KEY = 'DEMO'`
- `openEmailModal()` / `closeEmailModal()` — открытие, закрытие, сброс формы
- Закрытие по Escape и клику по оверлею
- Валидация email через regex
- `handleSendEmail()`:
  - При `EMAILJS_SERVICE_ID === 'DEMO'` — задержка 800мс, toast "Функция отправки будет доступна после настройки"
  - При реальных ключах — `emailjs.send()` с полными данными расчёта
  - Спиннер на кнопке во время отправки (использует существующий `@keyframes spin`)
- `templateParams` содержит: тип рельса, длину пути, нити, тоннаж, кол-во рельсов, шпалы, скрепления, итоговую сумму

**Коммит:** `95cd205`

---

## [2026-03-27] — Итерация 7: Вливка данных конкурента в catalog.json

### merge_catalog.py — новый скрипт

- Читает `data/catalog.json` (158 позиций) и `data/catalog_enriched.json`
- Сопоставляет позиции по `id`
- Заполняет поле `competitor_data` в `catalog.json`:
  - `description` — текст со страницы конкурента
  - `specs` — таблица характеристик (объект ключ→значение)
  - `has_drawing` — наличие PDF (из `competitor.has_pdf`)
  - `has_photos` — наличие фотографий
  - `images` — пустой массив (URL фото не парсились)

**Итог:** 130 / 158 позиций получили `competitor_data`, 28 остались без данных.

**Коммит:** `e73d74e`

---
