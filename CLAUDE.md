# Рельс-Комплект — инструкции для Claude Code

> Last updated: 2026-04-27
> Главный мастер-документ: [Obsidian → 10-Projects/rels-komplekt/_main.md]
> Обязательное чтение в начале каждой сессии: ЭТОТ ФАЙЛ + `docs/design-system/рельс-комплект/MASTER.md`

---

## О проекте

Сайт оптового B2B поставщика рельсовых материалов (ООО "РКУ", Екатеринбург).

- **Запуск:** 24 марта 2026
- **Сдача MVP:** 20 апреля 2026 ✅
- **Статус:** Delivered → Handover (переезд на боевой домен `rels-komplekt.ru`)
- **Тестовый адрес:** http://202.148.53.107:8080/index.html

---

## Стек (актуальный)

### Frontend
- Чистый HTML5 / CSS3 / Vanilla JavaScript — никаких фреймворков
- Mobile-first, адаптив 768px/1200px

### Backend
- **Flask/WSGI приложение** — `notify_app.py` в корне проекта
- **gunicorn** под systemd: `rels-notify.service`, 2 workers, unix-сокет `/run/rels-notify/app.sock`
- Запускается под выделенным юзером `rels-app`

### Infrastructure
- **nginx** — reverse proxy + статика (sites-enabled/rels-komplekt, listen :8080)
- **Telegram admin bot** — `rels-admin-bot.service`, `python -m bot.main`, python-telegram-bot 21.x async
- **VPS** — Нидерланды, IP 202.148.53.107
- **SQLite** — `data/metrics.db` (аналитика), `data/leads.db` (CRM-заявки)

### Deprecated (НЕ использовать)
- `serve.py` — старый Python HTTP-сервер, отключён ~16 апреля
- `rels-komplekt.service` — systemd-юнит для serve.py, disabled
- `proxy/` — старый Node.js Telegram-прокси, заменён gunicorn'ом

---

## Дизайн

- Основной цвет: `#1A56A0` (синий)
- Акцент: `#E65100` (оранжевый)
- CTA: `#0369A1`
- Шрифт: Inter (Google Fonts)
- Стиль: строгий промышленный B2B
- Ориентир: vsp74.ru
- **Полная design system:** `docs/design-system/рельс-комплект/MASTER.md` — обязательно к прочтению

---

## Структура файлов

```
/root/projects/rels-komplekt/
├── .env                       — Telegram tokens, секреты
├── .well-known/               — acme-challenge для Let's Encrypt
├── CLAUDE.md                  — этот файл
├── DEVLOG.md                  — лог изменений
├── PROJECT_STATUS.md          — текущий статус (если есть)
│
├── notify_app.py              — Flask backend (~41 KB)
├── serve.py                   — DEPRECATED, не запускать
│
├── bot/                       — Telegram admin bot (python -m bot.main)
│   ├── main.py                — entry point
│   ├── handlers/              — обработчики команд
│   ├── utils/ui.py            — паттерн send_screen()/edit_screen()
│   └── ...
│
├── data/
│   ├── catalog.json           — 158 позиций, single source of truth (публичный)
│   ├── catalog.json.bak       — бэкап перед изменениями (закрыт в nginx)
│   ├── metrics.db             — SQLite, аналитика трекера
│   ├── leads.db               — SQLite, CRM-заявки
│   ├── competitor/            — данные vsp74.ru (закрыты в nginx)
│   ├── eshop/                 — закрытые JSON (закрыты в nginx)
│   ├── image_map/             — маппинг изображений (закрыт)
│   └── vsp74_scrape/          — сырые данные скрапинга (закрыт)
│
├── docs/
│   ├── design-system/рельс-комплект/MASTER.md  — design system
│   └── ...                                       — остальная документация
│
├── tools/                     — скрипты парсинга (закрыты в nginx)
│   └── parser/viewer.py       — генератор competitor_report.html
│
├── proxy/                     — DEPRECATED Node.js прокси
│
├── assets/
│   ├── css/style.css, components.css
│   ├── js/main.js, catalog.js, product.js, calculator.js, order.js
│   └── img/                   — изображения, сертификаты
│
└── HTML страницы (9 шт.):
    ├── index.html             — главная
    ├── catalog.html           — каталог с фильтрами
    ├── product.html           — карточка товара (?id=UID)
    ├── calculator.html        — калькулятор тоннажа
    ├── contacts.html          — контакты
    ├── order.html             — корзина / заявка
    ├── privacy.html           — политика конфиденциальности (152-ФЗ)
    ├── about.html             — о компании
    └── rails-reference.html   — справочник по типам рельсов
```

---

## Бизнес-логика

- Цены в рублях за тонну (`price` в catalog.json)
- `price: null` → показывать "Цена по запросу"
- Калькулятор: длина(м) × вес_рельса(кг/м) / 1000 = тоннаж
- Заявки идут в Telegram bot через `/api/notify` и `/api/lead`
- PDF спецификации: `window.print()` + скрытый HTML-блок (НЕ jsPDF)

### Schema `data/catalog.json`

```json
{
  "id": "00011763495",
  "name": "Рельсы Р65 ДТ350, ОТ350 новые",
  "page_name": "relsy-r65-dt350-ot350-novye",
  "category": "Рельсы широкой колеи",
  "subcategory": "Рельсы Р65",
  "price": 144000,
  "unit": "т",
  "in_stock": true,
  "weight_per_unit": 811,
  "competitor_data": {
    "specs": { "ГОСТ": "...", "Длина": "..." },
    "description": "...",
    "has_drawing": true,
    "has_photos": false,
    "images": []
  }
}
```

`weight_per_unit` добавлено 7 апреля 2026. `competitor_data` есть у 130/158 позиций (специфики от vsp74.ru).

---

## API endpoints (production)

Все эндпоинты обслуживаются gunicorn'ом (`notify_app.py`) через nginx proxy_pass на unix-сокет.

| Endpoint | Назначение | Rate limit | Burst |
|---|---|---|---|
| `POST /api/notify` | Заявки с форм (Telegram уведомление) | 10 req/min | 3 |
| `POST /api/track` | Трекер аналитики (события на страницах) | 120 req/min | 20 |
| `POST /api/lead` | CRM-заявки (запись в leads.db + уведомление в бот) | 3 req/min | 2 |

При rate limit nginx возвращает 429.

---

## Systemd-сервисы

```bash
# API (gunicorn)
sudo systemctl status rels-notify.service
sudo journalctl -u rels-notify.service -f

# Telegram admin bot
sudo systemctl status rels-admin-bot.service
sudo journalctl -u rels-admin-bot.service -f

# nginx
sudo systemctl status nginx
sudo nginx -t   # проверка конфига перед reload
sudo systemctl reload nginx
```

Файлы юнитов: `/etc/systemd/system/rels-{notify,admin-bot}.service`.

После правок: `sudo systemctl daemon-reload && sudo systemctl restart <service>`.

---

## nginx — текущая структура

| Файл sites-enabled | listen | server_name | Назначение |
|---|---|---|---|
| `default` | 80 default_server | `_` | catch-all на :80, отдаёт сайт по IP. Битый proxy на :3001 — техдолг. |
| `rels-komplekt` | 8080 | `_` | основной сайт + API. **НЕ симлинк** (рассинхрон с available — техдолг). |
| `backyard` | 80, 443 | `backyard-tech.ru` | соседний проект через Cloudflare |

**Включённые snippets:**
- `/etc/nginx/snippets/security-headers.conf` — HSTS, X-Frame, nosniff, Referrer-Policy

**Webroot:** `/root/projects/rels-komplekt/`
**Webroot для acme:** `/root/projects/rels-komplekt/.well-known/`

---

## Правила работы (ОБЯЗАТЕЛЬНЫ)

### Перед началом работы
1. Прочитать ЭТОТ файл (`CLAUDE.md`) и `docs/design-system/рельс-комплект/MASTER.md`
2. Проверить `pwd` — должно быть `/root/projects/rels-komplekt/`
3. Проверить `git status` — рабочая ветка чистая
4. Проверить активные сервисы перед изменениями: `systemctl is-active rels-notify rels-admin-bot nginx`

### Защитный паттерн для deploy-промптов
> С 27 апреля 2026 — обязательно для всех инфра-меняющих сессий.

Любой промпт, изменяющий nginx / systemd / production-конфиги:
1. Начинается с **read-only audit-фазы** — собрать состояние, не менять
2. Содержит явную инструкцию: **"Если X уже существует — остановись и спроси"**
3. Бэкап файлов ДО изменений: `sudo cp -a /etc/nginx /root/nginx-backup-$(date +%Y%m%d-%H%M%S)`
4. `nginx -t` ВСЕГДА перед `systemctl reload`
5. Функциональная проверка после изменений (curl, проверка backyard-tech не сломан)

### В конце сессии
1. `git add -A && git status` (показать что коммитим)
2. `git commit -m "..." && git push`
3. Залогировать в Obsidian: `Backyard Tech/10-Projects/rels-komplekt/sessions/YYYY-MM-DD.md`

### Логирование сессий — ОБЯЗАТЕЛЬНО
> С 27 апреля 2026. Раньше нарушалось — привело к провалу памяти (8-26 апреля без логов, при том что велась активная работа: gunicorn-миграция, бот, новые страницы).

Каждая существенная сессия (новый функционал, фикс, инфра-изменение, миграция) логируется в `Backyard Tech/10-Projects/rels-komplekt/sessions/YYYY-MM-DD.md` по шаблону `_template.md`. Минимум — секции "Выполнено", "Коммиты", "Технический долг".

---

## Известные технические долги

См. полный список в [Obsidian → sessions/2026-04-27#tech-debt]. Топ-5:

1. **`sites-enabled/rels-komplekt` — НЕ симлинк** (рассинхрон с available). Синхронизировать после cutover.
2. **`default` nginx-блок** — проксит битую ссылку `127.0.0.1:3001`. Заменить на gunicorn-сокет или удалить.
3. **`serve.py` + `rels-komplekt.service`** — deprecated, удалить.
4. **`proxy/` директория** — старый Node.js прокси, удалить.
5. **`deploy/nginx/` в репо** — создать и заверсионировать актуальные конфиги.

---

## Текущие активные workstreams

1. **Переезд на боевой домен `rels-komplekt.ru`** (handover, в работе с 27 апреля)
2. (опционально) Очистка `competitor_data.description` от nav-мусора
3. (опционально) Реальные фотографии товаров со скрапингом

---

## Комментарии в коде

На русском языке. Краткие, по делу. Без стаффа типа "// initialize variable".

---

*Связанные документы:*
- *Obsidian master:* `Backyard Tech/10-Projects/rels-komplekt/_main.md`
- *Devlog:* `Backyard Tech/10-Projects/rels-komplekt/devlog.md`
- *Retrospective:* `Backyard Tech/10-Projects/rels-komplekt/retro-2026-04-19.md`
- *Шаблон сессий:* `Backyard Tech/10-Projects/rels-komplekt/sessions/_template.md`
