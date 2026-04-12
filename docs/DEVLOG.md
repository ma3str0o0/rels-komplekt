# DEVLOG — Рельс-Комплект

Лог изменений проекта. Обновляется после каждой итерации разработки.

---

## [2026-04-12] — Итерация 33: Фикс тёмной темы — полный аудит и оверрайды

**Коммит:** `a755b17`  
**Файлы:** `assets/css/style.css`

### Изменения

**Расширен блок `[data-theme="dark"]` переменных:**
- Добавлены новые переменные: `--color-bg`, `--color-surface-2`, `--color-text-subtle`, `--color-nav-bg`, `--color-input-bg`, `--color-input-border`, `--color-badge-bg`, `--color-section-alt`, `--color-card-bg`
- `--color-primary` исправлен с `#1A56A0` → `#58A6FF` (был почти невидим на тёмном фоне)

**Добавлен блок DARK THEME OVERRIDES (~200 строк) в конец style.css:**
- Заголовки `h1–h6`: `color: var(--color-text)` — раньше наследовали `--color-primary` (#0F172A = чёрный, невидим)
- Секции, `.section--alt`, `.section--muted`
- Product: buy-box, цена, calculator tabs/inputs/hints
- Catalog: таблица, sidebar, cat-tree, search-box
- Badges: gray, green, orange
- Формы: инпуты, placeholder, CTA-карточка
- Кнопки: btn-secondary, btn-outline
- About: stat-card, partner-card, cert-card, timeline
- Хлебные крошки, контакты, каталог-хэдеры

**Python-аудит хардкоженных цветов выявил:**
- `components.css`: `#E2E8F0` (33x), `#fff` (29x), `#F8FAFC` (18x), `#64748B` (20x)
- `style.css`: `#fff` (15x), `#64748B` (5x), `#94A3B8` (4x)
- Глобальная замена не производилась (сломала бы светлую тему) — исправлено точечно через `[data-theme="dark"]`

---

## [2026-04-12] — Итерация 32: Удаление телефона из хэдера

**Коммит:** `02db14f`  
**Файлы:** `assets/js/main.js`

### Изменения

- Из `_tplHeader()` удалён блок `.header__phones` с номером телефона и расписанием
- Изменение автоматически применяется ко всем страницам (хэдер централизован)

---

## [2026-04-12] — Итерация 31: Полный адаптивный аудит и фикс

**Коммит:** `af89faa`  
**Файлы:** `assets/css/components.css`, `assets/css/style.css`

### Изменения

**Аудит показал — уже реализовано ранее:**
- Бургер-меню (`.burger` + `.mobile-menu` + `initMobileMenu()`) — работало
- Каталог mobile drawer (`#openFiltersBtn`, bottom sheet, `openDrawer()`/`closeDrawer()`) — работало
- Скрытие колонок таблицы каталога на мобиле — было

**Добавлено:**

`components.css`:
- Заменён breakpoint 600px → 640px для product layout
- Добавлены mobile-стили: `position: static` у buy-box, `aspect-ratio: 4/3` у фото, меньшие шрифты цены/названия/calc-tabs

`style.css`:
- Добавлен блок `@media (max-width: 640px)`: секции 32px/24px padding, hero 48px, `.hero__actions` в колонку, меньше section-title
- Добавлен блок `@media (max-width: 480px)`: container 12px, ещё меньше заголовки

---

## [2026-04-12] — Итерация 30: Трёхколоночный layout карточки товара

**Коммит:** `ece570f`  
**Файлы:** `product.html`, `assets/js/product.js`, `assets/css/components.css`

### Изменения

**`product.html`:**
- Старый 2-колоночный layout заменён на 3-колоночный: `[ФОТО] | [ИНФО] | [КАЛЬКУЛЯТОР+КНОПКИ]`
- Новые классы: `.product-col--media`, `.product-col--info`, `.product-col--buy`
- Цена вынесена в отдельный `#productPriceDisplay` в buy-box
- Тех. характеристики конкурента — отдельная секция ниже hero с `#enrichedSpecsWrap`

**`assets/js/product.js`:**
- Добавлена функция `renderPriceDisplay(item)` — рендерит цену крупно в buy-box
- Из `renderSpecs()` убрана строка «Цена»
- `_renderCompetitorData()` переведён на `#enrichedSpecsWrap` + `classList.remove('hidden')`

**`assets/css/components.css`:**
- `.product-layout`: 3-col grid `300px 1fr 300px`, `align-items: start`
- Breakpoints: 1100px (260px), 860px (2-col + buy-box full width), 640px (1-col)
- Новые классы: `.product-col--media .product-image`, `.product-col--info`, `.product-buy-box`, `.product-buy-box__price`, `.product-hero__actions`

---

## [2026-04-12] — Итерация 29: Двухрежимный калькулятор «По метражу / По весу»

**Коммит:** `d2fefb1`  
**Файлы:** `assets/js/product.js`

### Изменения

**`renderPricing(item)` полностью переработана:**
- Два режима переключаются табами: «По метражу» и «По весу»
- Вкладка «По метражу»: вводишь метры → показывает кг и стоимость
- Вкладка «По весу»: вводишь кг → показывает метры и стоимость
- Fallback «По тоннам» для позиций без `weight_per_unit`
- Переключатель валюты RUB / KZT (1 RUB = 5.5 KZT)
- `wpm = weight_per_unit / 12.5` (кг/м из кг/рельс 12.5м)
- `pricePerMeter = (wpm / 1000) * price` (₽/м)

---

## [2026-04-11] — Итерация 28: Страница «О компании» + справочник рельсов + фиксы хэдера

**Коммиты:** `4ee019b`, `4cd3c7d`, `649be8e`, `aa806a5`, `84627b9`, `d94aa1b`  
**Файлы:** `about.html`, `rails-reference.html`, `assets/js/main.js`, `assets/css/style.css`, `sitemap.xml`, `tools/build_rails_guide.py`

### Изменения

**`about.html` — новая страница (8 секций):**
- Hero с кнопками «Каталог» и «Связаться с нами»
- Цифры компании (stat-cards): год основания, количество позиций, регионов, лет
- История (таймлайн по годам)
- Партнёры и поставщики (карточки с логотипами)
- Раздел сделок / крупных проектов
- Сертификаты качества (cert-cards с изображениями ТМК, TenderPro)
- CTA-секция и форма обратной связи
- Добавлена в навигацию всех страниц (позиция 4, перед «Контакты»)
- Добавлена в `sitemap.xml` (priority 0.8)

**`rails-reference.html` — новая страница:**
- Генерируется `tools/build_rails_guide.py`
- Справочник по ГОСТам, допускам, весам рельсов
- Таблицы со стилями инлайн (хардкоженный hex) — иначе CSS переменные давали чёрный фон в thead
- Кнопка «Справочник по рельсам» добавлена в шапку каталога

**`assets/js/main.js` — фиксы хэдера:**
- `align-items: center` вместо `flex-end` у `.header__phones`
- Два телефона заменены одним: `+7 (343) 345-13-33`
- Порядок навигации: Главная / Каталог / Калькулятор / **О компании** / Контакты

**`product.html` / `product.js` — удалена секция `gost_tables`:**
- Таблицы ГОСТ перенесены на `rails-reference.html`
- Из product.js удалена функция отрисовки gost_tables

---

## [2026-04-06] — Итерация 27: Умное поле «телефон или email» + кнопка «Получить КП»

**Файлы:** `index.html`, `assets/js/main.js`, `assets/css/components.css`, `serve.py`

### Изменения

**`index.html`:**
- `#inlineRequestForm`: поле `input[type="tel"]#il-phone` заменено на `.smart-contact-wrap` с `input.smart-contact-input#il-contact` (`name="contact"`)
- Иконка телефона слева, хинт-подпись справа (тип определяется автоматически)
- Кнопка submit: `Отправить заявку` → `Получить КП`

**`assets/js/main.js`:**
- `_tplModal()`: поле `req-phone` заменено на `.smart-contact-wrap#req-contact-wrap`; кнопка `Отправить` → `Получить КП`
- `initInlineForm()`: полностью переписана — работает с `name="contact"`, валидирует через `isValidContact()`, передаёт `phone`/`email` в зависимости от типа ввода, сбрасывает хинт при reset
- `handleRequestSubmit()`: после получения данных формы определяет тип контакта и проставляет `data.phone`/`data.email`
- `validateForm()`: добавлена ветка `field.name === 'contact'` с вызовом `isValidContact()`
- `initPhoneMask()`: добавлен вызов `initSmartContactFields()` в конце
- Добавлены функции `initSmartContactFields()` и `isValidContact()`

**`initSmartContactFields()`:**
- `detectType(val)`: если содержит `@` → email; если цифр > 2 → phone; иначе empty
- `formatPhone()`: авто-форматирование в `+7 (XXX) XXX-XX-XX` при вводе
- `update()`: переключает иконку (телефон / конверт), подпись «Телефон» / «Email», `wrap.dataset.type`
- Keydown: блокирует нецифровые символы только когда тип уже определён как `phone`
- Paste: очищает и перегоняет через `input` event

**`assets/css/components.css`:**
- Добавлены стили `.smart-contact-wrap`, `.smart-contact-icon`, `.smart-contact-hint`, `--phone` и `--email` модификаторы

**`serve.py`:**
- `format_message()`: `📞 Телефон:` → `📞 Контакт:` с fallback `contact || phone`

### UX
Одно поле принимает телефон или email. При вводе телефона — авто-форматирование и блокировка букв. При вводе email — иконка меняется на конверт, появляется подпись «Email».

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

**Hotfix 2:** `bd4eecd` — переработана цветовая схема тёмной темы: GitHub-dark палитра (`#0D1117`/`#161B22`/`#30363D`), убран яркий синий hero-градиент, добавлены компонентные оверрайды для `.pcard`, `.cta-contact__card`, `.theme-toggle`, `.specs-table__val`, `.footer`.

**Hotfix:** `db55765` — кнопка переключения темы добавлена в хардкодные шапки `index.html`, `catalog.html`, `product.html`, `order.html` (в этих файлах шапка не генерируется через `_tplHeader()`, поэтому кнопка туда не попала при первоначальной реализации).

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

## [2026-04-03] — Итерация 26: Phone widget — код страны внутри поля ввода

**Файлы:** `assets/js/main.js`, `assets/css/components.css`

### Изменения

**`_buildPhoneWidget` (main.js):**
- Кнопка флага теперь показывает **только флаг** — код страны перенесён в само поле ввода
- Поле инициализируется значением `+7 ` по умолчанию
- При смене страны из дропдауна поле получает новый префикс (`+375 `, `+998 ` и т.д.), курсор переводится в конец
- `keydown`: защита префикса от удаления — Backspace и Delete блокируются если курсор в пределах длины префикса
- `input`: восстанавливает префикс если удалён, форматирует локальную часть (цифры после префикса)
- `paste`: вырезает код страны из вставленного текста если он там есть, применяет `prefix + formatLocal()`
- Логика форматирования вынесена в helper `formatLocal(digits, code)`

**`components.css`:**
- Удалено правило `.phone-flag-btn .phone-code` (класс больше не используется в разметке)

### UX
Клиент видит в поле `+7 ` и может набирать сразу с первой цифры номера — ввод с кода (`+7 7...`) или без него обрабатывается корректно.

---

## [2026-04-06] — Итерация 25: Формы → Telegram + phone widget с флагами стран

**Коммит:** `4f6eaef`

### assets/js/main.js

**`initInlineForm()`** — полностью переписана:
- Форма `#inlineRequestForm` на index.html теперь реально отправляет в Telegram через `sendTelegram()`
- Spinner на кнопке во время отправки; `_isThrottled()` защита от спама
- После успешной отправки: `form.reset()` + сброс флага страны обратно на 🇷🇺 +7

**`initCtaContactForm()`** — полностью переписана:
- Форма `.cta-contact__form` («Перезвоните мне») подключена к Telegram
- Сообщение: `'Запрос "Перезвоните мне"'`
- `async/await`, `_isThrottled()`, toast-уведомления об успехе/ошибке

**`initPhoneMask()`** — полностью переписана → `_buildPhoneWidget(input)`:
- Добавлен `PHONE_COUNTRIES` — 8 стран (РФ, КЗ, BY, UZ, KG, AZ, DE, CN)
- Кнопка флага слева от инпута: `🇷🇺 +7` по умолчанию
- Дропдаун со списком стран, плавный hover
- Маска ввода: для кода 7 → `(___) ___-__-__`; для других → цифры с пробелами
- `keydown`: блокируются все нецифровые символы (кроме Backspace, стрелок и т.д.)
- `paste`: очистка от нецифровых символов + применение маски

### assets/css/components.css
- Добавлен блок `.phone-widget` / `.phone-flag-btn` / `.phone-dropdown`
- Тёмная тема: оверрайды для `.phone-flag-btn` и `.phone-dropdown`

---

## [2026-04-06] — Итерация 24: Единый сервер — статика + Telegram proxy на порту 8080

**Коммит:** `8dd1bda`

**Причина:** два отдельных сервера (статика :8080 + proxy :3001) создавали CORS и проблемы с файрволом. Решение — объединить в один процесс.

### serve.py — новый файл (корень проекта)
- `HTTPServer` + `SimpleHTTPRequestHandler` на порту 8080 (настраивается через `SITE_PORT`)
- `do_GET`: отдаёт статические файлы из корня проекта; `/` → `index.html`
- `do_POST` на `/api/notify`: читает `proxy/.env`, форматирует сообщение, шлёт в Telegram
- Нет CORS-проблемы — браузер и API на одном origin
- Нет внешних портов — только один 8080

### assets/js/main.js
- `PROXY_URL`: `http://202.148.53.107/api/notify` → `/api/notify` (относительный путь — работает с любого хоста)

**Проверка:** `POST http://localhost:8080/api/notify` → `{"ok": true}`, message_id: 7; `GET http://localhost:8080/` → `index.html` (200)

---

## [2026-04-06] — Итерация 23: Обход файрвола VPS через nginx

**Коммит:** `581fc90`

**Диагноз:** `ufw inactive`, `iptables` policy ACCEPT — OS не блокирует. Файрвол на уровне панели VPS-провайдера закрывал порт 3001 для внешних подключений. Порт 80 (nginx) открыт.

**Решение:** добавить `location /api/notify` в nginx → `proxy_pass http://127.0.0.1:3001`. Браузер обращается на порт 80, nginx внутри сервера передаёт запрос на proxy.

### /etc/nginx/sites-enabled/default
- Добавлен блок `location /api/notify { proxy_pass http://127.0.0.1:3001; proxy_read_timeout 15s; }`
- `nginx -t && systemctl reload nginx` — конфиг валиден, перезагружен без даунтайма

### assets/js/main.js
- `PROXY_URL`: `http://202.148.53.107:3001/api/notify` → `http://202.148.53.107/api/notify` (порт 80)

**Проверка:** `curl http://202.148.53.107/api/notify` → `{"ok": true}`, message_id: 6, Telegram получил

---

## [2026-04-06] — Итерация 22: Фикс CORS в Telegram proxy

**Коммит:** `92f5522`

### proxy/server.py
- Убран фиксированный `ALLOWED_ORIGIN` — вместо него `_send_cors()` читает `Origin` из заголовка запроса и отражает его обратно (`Access-Control-Allow-Origin: <origin>`)
- Добавлен `Access-Control-Max-Age: 86400` — браузер кэширует preflight на сутки
- `do_OPTIONS` возвращает `204 No Content` с полными CORS-заголовками

**Проверка:**
- `OPTIONS` preflight → `204`, все `Access-Control-Allow-*` заголовки присутствуют
- `POST` с `Origin: http://202.148.53.107:8080` → `{"ok": true}`, message_id: 5, Telegram получил

---

## [2026-04-06] — Итерация 21: Telegram proxy — скрытие токена + товары в уведомлениях

**Коммит:** `27ade61`

### proxy/server.py — новый файл
- HTTP-сервер на `http.server.HTTPServer`, порт `3001` (настраивается через `PROXY_PORT`)
- Единственный эндпоинт: `POST /api/notify`
- Читает токен и chat_id из `proxy/.env` через `load_env()` — токен никогда не уходит во фронтенд
- `format_message(data)` — форматирует сообщение с HTML-разметкой: имя, телефон, комментарий, состав заявки по позициям, итого в рублях
- CORS-заголовки: `ALLOWED_ORIGIN=http://202.148.53.107:8080`, поддержка `OPTIONS` preflight
- Валидация: 400 если нет имени/телефона, 500 если бот не настроен, 502 при сетевой ошибке
- Тест пройден: `{"ok": true}`, сообщение доставлено в @relskomplekt_bot → chat 459417766

### proxy/.env — новый файл (в .gitignore, в git не попадает)
- `BOT_TOKEN`, `CHAT_ID`, `PROXY_PORT=3001`, `ALLOWED_ORIGIN`

### proxy/requirements.txt — новый файл
- `requests>=2.28`

### .gitignore — новый файл
- `proxy/.env` и `*.env` — защита токенов от попадания в репозиторий

### assets/js/main.js
- `sendTelegram(data)` полностью переписана: теперь шлёт `POST` на `http://202.148.53.107:3001/api/notify` вместо прямого вызова Telegram API
- В `handleRequestSubmit`: перед `await sendTelegram(data)` добавлено чтение корзины из `localStorage.getItem('cart')` → `data.items`; товары из заявки теперь включаются в уведомление

### assets/js/catalog.js
- `rowHTML()`: regex `хранения` → `хранени[яе]` — badge «С хранения» теперь корректно матчит оба падежа

---

## [2026-04-05] — Итерация 20: Удаление дублирующей формы с главной страницы

**Коммит:** `022b277`

### index.html
- Удалена секция `<section class="cta-contact">` («Остались вопросы?» / «Перезвоните мне») — располагалась между `</main>` и `<footer>`, дублировала форму обратной связи
- Оставлена основная форма `section--form-cta` («Получите коммерческое предложение») — секция 4 внутри `<main>`, содержит текст с преимуществами и полноценную форму с полями имя/телефон/комментарий
- Переход от блока `contacts-strip` сразу к `<footer>` — без пустых зазоров

---

## [2026-04-05] — Итерация 19: UI-полировка каталога (шрифт, паддинги, плейсхолдер)

**Коммит:** `3911309`

### assets/css/components.css — 4 точечных фикса

**Фикс 1 — Шрифт таблицы крупнее:**
- `.catalog-table`: `font-size: var(--font-size-sm)` → `15px`
- `.catalog-table td`: `padding: 12px 14px` → `16px 14px` (увеличена высота строк)
- Заголовки `thead th` оставлены на `11px`

**Фикс 2 — Название товара жирнее:**
- `.catalog-table td:first-child`: добавлен явный `font-size: 15px`

**Фикс 3 — Поле поиска в сайдбаре:**
- `.search-box`: добавлен `width: 100%; overflow: hidden`
- `.search-box .input`: `width: 100%; box-sizing: border-box; font-size: 14px; padding: 10px 14px 10px 36px`
- `.search-box .input::placeholder`: `color: var(--color-text-muted); opacity: 1` (Firefox-фикс — дефолтный opacity 0.54)

**Фикс 4 — Категории в сайдбаре крупнее:**
- `.cat-tree__cat`: `font-size: var(--font-size-sm)` → `14px`; `padding: 8px` → `9px 10px`
- `.cat-tree__sub`: `font-size: 12px` → `13px`; `padding: 5px` → `6px 10px`

---

## [2026-04-05] — Итерация 18: Сортировка по колонкам Состояние и Цена

**Коммит:** `c0846f8`

### assets/js/catalog.js
- Добавлены переменные уровня модуля: `sortField = 'condition'`, `sortDir = 'asc'`, `CONDITION_WEIGHT = { new:0, storage:1, used:2, unknown:3 }`
- `getCondition(name)` — определяет состояние товара по regex на `item.name` (новы[йе]/ГОСТ → new, хранени[яе] → storage, б/у/старогодн → used, иначе → unknown)
- `sortItems(items)` — копирует и сортирует по `sortField`/`sortDir`; для цены `asc` = дорогой первым, `null`-цены уходят в конец (`-1`)
- `_sortThHtml(field, label, cssClass)` — генерирует `<th>` с кнопкой, проставляет актуальные классы `active`/`sort-asc`/`sort-desc` при каждом перерендере
- `renderCards()`: добавлен вызов `sortItems(state.filtered)` после фильтрации и до `slice` пагинации; заголовки «Состояние» и «Цена» заменены на вывод `_sortThHtml()`
- `bindEvents()`: делегированный обработчик на `dom.grid` для кликов по `.sort-btn` — работает после каждого перерендера таблицы без повторной привязки

### assets/css/components.css
- Добавлен блок `.sort-btn`: `inline-flex`, `font: inherit`, `text-transform: uppercase`, `color: var(--color-text-muted)`, hover/active → `var(--color-cta)`
- `.sort-up`, `.sort-down`: `fill: var(--color-border)` по умолчанию; активная стрелка подсвечивается `var(--color-cta)` через `.sort-btn.active.sort-asc/.sort-desc`

---

## [2026-04-05] — Итерация 17: Двухуровневый аккордеон фильтра категорий

**Коммит:** `891c467`

### catalog.html — статическое дерево категорий
- Заменён динамический `<div id="categoriesList">` (генерировался JS) на статический `<ul class="cat-tree">` с 11 узлами верхнего уровня
- 5 групп с аккордеоном: Рельсы широкой колеи, Рельсы крановые, Рельсы узкоколейные, Шпалы, Крепёж ж/д
- 6 листовых узлов без подкатегорий: Крановый крепёж, DIN 536, Накладки, Прокладки, Подкладки

**Структура данных (верифицировано через node):**
- `Рельсы Р50`, `Рельсы КР 80/100/120/140`, `Рельсы Р8–Р43`, все болты и крепёж — отдельные `category` в JSON
- Только `Рельсы Р65` (subcategory у "Рельсы широкой колеи") и `Рельсы КР 70` (subcategory у "Рельсы крановые") — настоящие subcategory
- Группы используют `data-cats="A|B|C"` → `type: 'multi-category'`; листья — `data-sub-type="category"` или `data-sub-type="subcategory"` соответственно

### catalog.js — новая логика фильтрации
- **Удалено:** `state.categories: new Set()`, `renderCategories()`, `readUrlParams()`, обработчик `categoriesToggle`
- **Добавлено:**
  - `activeFilter = { type: 'all' }` — единый объект состояния фильтра
  - `resetCategoryUI()` — сбрасывает `active`-классы и закрывает `<ul hidden>`
  - `filterItem(item)` — switch по `activeFilter.type`: all / category / multi-category / subcategory
  - `initCategoryFilter()` — биндинг кликов на `.cat-tree__cat` и `.cat-tree__sub`, обработка URL-параметра `?cat=`
- `applyFilters()`: `state.categories.size > 0 &&` → `!filterItem(item)`
- `updateActiveFiltersIndicator()`: `state.categories.size` → `activeFilter.type !== 'all' ? 1 : 0`
- `resetFilters()`: сбрасывает `activeFilter`, вызывает `resetCategoryUI()`

### assets/css/components.css
- Добавлен блок `.cat-tree*`: дерево с hover, active-цветом `var(--color-cta)`, стрелкой с `rotate(90deg)` при открытии

---

## [2026-04-05] — Итерация 16: Фикс ширины таблицы и классов кнопок

**Коммит:** `2a8e8b7`

### assets/css/components.css
- `.catalog-grid:has(.catalog-table) { display: block; }` — когда внутри таблица, grid-режим (3 колонки) сбрасывается и таблица растягивается на всю ширину `.catalog-content`

### assets/js/catalog.js
- Кнопки в `rowHTML` использовали несуществующие классы `btn--sm`/`btn--outline`/`btn--accent` (BEM с двойным дефисом)
- Исправлено: `btn btn-sm btn-primary` (по умолчанию) и `btn btn-sm btn-accent` (товар в заявке) — реальные классы из CSS
- `addToCart()` обновлён: `btn--outline`/`btn--accent` → `btn-primary`/`btn-accent`

---

## [2026-04-03] — Итерация 15: Строчное табличное отображение каталога

**Коммит:** `c4609cc`

### assets/js/catalog.js
- **`cardHTML()` → `rowHTML()`**: генерирует `<tr>` вместо `<article class="pcard">`
  - `<tr>` с `data-href`, `onclick="window.location.href=this.dataset.href"`, `cursor:pointer` — весь ряд кликабелен
  - Колонка «Наименование» — жирный текст
  - Колонка «Подкатегория» — `class="text-muted"`
  - Колонка «Состояние» — badge через regex по `item.name`: `/новый|новые|гост/` → `badge--green`, `/хранения/` → `badge--orange`, `/б\/у|старогодн/` → `badge` (серый)
  - Колонка «Цена» — `toLocaleString('ru-RU') + " ₽/т"` или `<span class="text-muted">По запросу</span>`
  - Колонка кнопки: `btn btn-sm btn-primary`, клик — `e.stopPropagation()` (не триггерит переход на страницу товара)
- **`renderCards()`**: `dom.grid.innerHTML` теперь генерирует `<table class="catalog-table"><thead>...<tbody>...`
- **`addToCart()`**: ищет `tr[data-id]` вместо `.pcard[data-id]`; переключает `btn-primary` ↔ `btn-accent` + `textContent`

### assets/css/components.css
- Добавлен блок `.catalog-table`: `border-collapse: collapse`, заголовки с `var(--color-tint-blue)`, hover строк, `td:first-child` жирный, `max-width: 420px`
- Мобильный брейкпойнт `≤768px`: скрыты колонки «Подкатегория» (2-я) и «Состояние» (3-я)

---

## [2026-03-27] — Итерация 14: Очистка мусорных описаний в catalog.json

**Коммит:** `c636b2b`

### tools/clean_descriptions.py — новый скрипт
- Читает `data/catalog.json`, проверяет `competitor_data.description` на наличие маркеров навигационного мусора (`Покупателю`, `Личный кабинет`, `Заказы`, `В наличии`, `Поиск`, `Каталог`, `КомплектыскреплениЙ`, `Рельсыжелезнодорожные`) или длину >2000 символов
- Зачищенные описания → `null`

### data/catalog.json
- Очищено: 130 / 130 описаний (все содержали мусор или превышали лимит)

---

## [2026-03-27] — Итерация 13: Стили таблицы технических характеристик

**Коммит:** `da8840d`

### assets/css/components.css
- Добавлен класс `.section-title`: `font-size: xl`, `font-weight: 700`, `border-bottom: 2px solid var(--color-primary)`, `margin-bottom: lg`
- Добавлен блок `.specs-table*`: `border-collapse: collapse`, `border: 1px solid var(--color-border)`, `border-radius: md`
  - `.specs-table__key`: фон `var(--color-primary)`, белый текст, `width: 40%`
  - `.specs-table__val`: `background: #fff`, `color: var(--color-text)`
  - Чётные строки — `background: var(--color-surface)` (зебра)
- Добавлены тёмная-тема оверрайды: `.pcard`, `.cta-contact__card`, `.stock-badge--in/out`, `.badge--blue/green/orange`, `.theme-toggle`

### product.html
- Удалены дублирующие inline-стили `.specs-table*` (были в `<style>` в `<head>`)

---

## [2026-03-27] — Итерация 12: Переупорядочивание секций product.html

**Коммит:** `99e95fe`

### product.html — новый порядок секций внутри `<main>`
1. `#productLoading` (спиннер)
2. `#productPage` (хлебные крошки + основной блок товара)
3. `#product-description` (описание от конкурента)
4. `#product-specs` (таблица характеристик)
5. `#product-media` (PDF/фото)
6. `#similarSection` — **перенесён в конец** (был внутри `#productPage`)
7. `.cta-contact` «Остались вопросы?» — за `<main>`

**Причина:** похожие товары показывались слишком рано (до описания и характеристик), что нарушало пользовательский сценарий.

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
