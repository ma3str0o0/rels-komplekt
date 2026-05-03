# DEVLOG — Рельс-Комплект

Журнал изменений на стороне инфраструктуры/проекта. Формат — обратный
хронологический, новые записи сверху. Подробности по сессиям —
в Obsidian (`Backyard Tech/10-Projects/rels-komplekt/sessions/`).

---

## [2026-05-03] — WS-INDEX: index.html refactor (формы + footer + cookie-banner)

Параллельный workstream WS-INDEX. Только `index.html`, на одной странице.

### Изменено
- `index.html` — 6 правок:
  - **Чекбокс 152-ФЗ** на `#inlineRequestForm` и `#requestForm`: добавлен `required`,
    обновлён текст. `name="consent"` сохранён (бэкенд `notify_app.py` ожидает это имя —
    переименование в `consent_pd` отвергнуто как противоречащее правилу проекта).
  - **Красные `*`** у обязательных полей (ФИО, телефон/email): заменили
    CSS-pseudo-element `form-label--required::after` на явный `<span class="required-mark">*</span>`.
  - **Поле файла** упрощено: внешний `<label>` и form-hint удалены, placeholder
    переписан как «📎 Прикрепите спецификацию, КП или другой документ». Внутренние
    DOM-узлы сохранены — JS `assets/js/main.js::initFileUpload` зависит от их IDs.
  - **Legal footer** (`<footer class="site-footer-legal">`) добавлен перед `</body>`
    как отдельный блок ниже существующего JS-рендеримого функционального footer'а.
    Реквизиты: ИНН/КПП/ОГРН, юрадрес, дисклеймер ст. 437 ГК РФ, ссылка на privacy.
  - **Cookie-banner интеграция**: подключён `assets/css/cookie-banner.css`,
    `<div id="cookie-banner-root">` после `<body>`, `<script src="assets/js/cookie-banner.js" defer>`
    перед `</body>`. Inline-вставки Y.Metrika и Top@Mail.Ru закомментированы
    HTML-комментариями (для лёгкого rollback).
  - **Schema.org JSON-LD** (Organization) добавлен в `<head>`.

### Решения
- `name="consent"` НЕ переименовывали в `consent_pd` (противоречит исходному промпту,
  но соответствует контракту с `notify_app.py`).
- `novalidate` на формах сохранён — submit блокируется существующим JS `_checkConsent`,
  не нативной валидацией.
- Inline `<style>` в `index.html` для новых классов (`.required-mark`,
  `.file-input-label`, `.site-footer-legal`) — техдолг, унифицировать в отдельном WS.

### Гигиена коммитов
Параллельные WS-A/WS-B оставили staged-изменения в индексе. Первый `git commit`
с `git add index.html` всё равно увлёк их (они уже были staged до сессии).
Откатил через `git reset --soft HEAD~1` + `git restore --staged`, перекоммитил
чисто. Финальный коммит — только `index.html` (131 ins / 42 del).

**Коммит:** `6dc9dbf`
**Бэкап:** `/tmp/ws-index-backup-20260503-172856/index.html`
**Сессия:** `Backyard Tech/10-Projects/rels-komplekt/sessions/2026-05-03-ws-index-form-refactor.md`

---

## [2026-05-02] — Phase 0: secret rotation (PAT + Telegram bot token)

Ротация секретов перед миграцией на новый VPS Beget. Два инцидента:
PAT в plaintext в `.git/config`, Telegram bot token утекал в systemd
journal через `httpx` INFO-логи (`POST .../bot<TOKEN>/getUpdates`).

### Создано
- `/root/.ssh/github_deploy_rels{,.pub}` — отдельный ed25519 deploy key
  для репо `ma3str0o0/rels-komplekt`. Публичный — добавлен в
  GitHub → repo settings → Deploy keys (Allow write access).
  Fingerprint: `SHA256:ZmdZQlRnWWQ2jjnr2VRo7rtfKMvrZi9DeZ/wPlTEbb8`.
  Приватный никогда не покидает VPS.
- `/root/.ssh/config` — Host github.com → IdentityFile github_deploy_rels,
  IdentitiesOnly yes (изоляция от других ключей в /root/.ssh/).

### Изменено
- `.git/config` — git remote переключён с HTTPS+PAT на
  `git@github.com:ma3str0o0/rels-komplekt.git`. PAT удалён из конфига.
- `.env` — `TELEGRAM_BOT_TOKEN` заменён на новый (старый отозван
  через BotFather → Revoke current token).
- `bot/main.py` — добавлен `logging.getLogger("httpx").setLevel(WARNING)`
  сразу после `logging.basicConfig()`. Убирает INFO-логи httpx, в которых
  светится полный URL с токеном.

### Внешние действия (вручную, не в репо)
- GitHub → settings/tokens → старый PAT (`ghp_MJEx...`) Revoked.
- BotFather → @relskomplekt_bot → API Token → Revoke current token,
  получен новый, подставлен в .env.

### Не изменялось
- nginx, gunicorn (rels-notify), сертификаты, cron-задачи
- catalog.json, HTML-страницы, assets, notify_app.py
- остальные ключи в /root/.ssh/ (id_ed25519, rels_komplekt_rf)
- backyard-tech.ru

### Проверено
- `ssh -T git@github.com` → "Hi ma3str0o0/rels-komplekt! You've successfully
  authenticated" — deploy key опознан как принадлежащий именно репо.
- `git fetch origin` через SSH работает без credentials.
- `grep -c "ghp_" .git/config` → 0 (PAT действительно удалён).
- `systemctl is-active rels-admin-bot` → active после рестарта.
- В journalctl за последнюю минуту: 0 совпадений regex
  `bot[0-9]+:[A-Za-z0-9_-]+/(getUpdates|sendMessage)` — токен в логах
  больше не светится.
- Application started в логах, scheduler запустил все три job
  (watchdog, daily_digest, cleanup_metrics).
- Ручной тест: `/start` боту в Telegram → отвечает.

### Бэкапы
- `/tmp/rels-03a-backup-20260502-145149/` — `.env`, `bot/main.py`,
  `.git/config` (со старым PAT, оставлен временно — после полной
  валидации миграции 03b бэкап удалить).

### Косметика (не блокер)
- При `systemctl restart rels-admin-bot` старый процесс выдал
  `RuntimeError: Event loop is closed` в asyncio shutdown
  (python-telegram-bot 21.x quirk на SIGTERM). Новый процесс встал
  корректно. Если будет надоедать — отдельный issue про graceful
  shutdown, не сегодня.

### Дальше
- Промпт 03b — настройка нового VPS Beget (85.198.102.212),
  миграция приложения и DNS-cutover.

---

## [2026-05-02] — Pre-cutover preparation

Закрытие пяти подготовительных задач из промпта 02 (велись с 27 апреля,
финализированы 2 мая).

### Создано
- `/etc/nginx/snippets/rels-redirects.conf` — базовый набор
  301-редиректов с URL Уралсофта (системные страницы +
  топ-категории `/store/*` с фильтром `?cat=` под точные
  значения category из catalog.json + `/uploadedFiles/` и
  `/img/k1_4/` → 410 Gone + catch-all `/store/*`)
- `/root/migration-backup/rels-komplekt.ru/` — wget-бэкап старого
  сайта (217 HTML, 537 картинок, 57М, страховка перед cutover;
  вне репо)
- `deploy/nginx/rels-redirects.conf` — версионированная копия
  snippet'а в репо

### Изменено
- `sitemap.xml` — все URL под https://rels-komplekt.ru/, lastmod=2026-04-27,
  index → `/` (без `/index.html`), убран product.html (динамический)
- `robots.txt` — добавлены `Disallow` для api/data/docs/tools/proxy/bot/.well-known/
- 9 HTML-страниц — добавлены счётчики:
  - Яндекс.Метрика 32668705 в `<head>`
  - Top@Mail.Ru 2690827 перед `</body>`
- 8 HTML-страниц (без product.html) — добавлен `<link rel="canonical">`
- `/etc/nginx/sites-available/rels-komplekt.ru` — раскомментирован include
  для rels-redirects.conf
- `deploy/nginx/rels-komplekt.ru.conf` и `deploy/nginx/README.md` —
  актуализированы под новый snippet

### Не изменялось
- backyard-tech.ru, default-блок, :8080-блок rels-komplekt
- gunicorn / Telegram bot / SQLite
- assets/, notify_app.py, bot/, serve.py
- secrets / .env

### Проверено
- `nginx -t` проходит, `reload` без ошибок
- Все 14 curl-проверок редиректов прошли:
  `/feedback{,/}` → 301 на /contacts.html
  `/store/relsy{,/}` → 301 с правильным URL-encoded ?cat=
  `/store/krepezh-zhd/` (Е, не Ё — реальное название) → 301
  `/store/random-unknown/` → 301 catch-all на /catalog.html
  `/uploadedFiles/test.png` → 410, `/img/k1_4/foo.jpg` → 410
  `/produkciya{,/}`, `/privacy-policy`, `/sitemap/` → 301
- backyard-tech.ru не сломан (301 на https)
- :8080-блок работает (200 + gunicorn проксирование живо)
- HTML-парсер OK для всех 9 страниц
- Через nginx (Host: rels-komplekt.ru) Метрика/Top@Mail/canonical
  виден в ответе
- В HTML/JS/JSON НЕТ хардкода `202.148.53.107`, `localhost:8080`, `:8080`
- В коммите нет .db, .env, __pycache__, бэкапов, секретов

### Что осталось до cutover
- Полная карта редиректов из админки Уралсофта (44 редиректа от заказчика)
- Доступ заказчика в nic.ru
- Подтверждение по Яндекс.Почте для домена

### В момент cutover
- Смена NS в nic.ru → собственные
- A-запись на 202.148.53.107
- `certbot --nginx -d rels-komplekt.ru -d www.rels-komplekt.ru`
- Опубликовать sitemap в Яндекс.Вебмастер (старый аккаунт
  с ID Метрики 32668705)

---

## [2026-04-27] — Подготовка nginx под боевой домен

### Создано
- `/etc/nginx/sites-available/rels-komplekt.ru` — server-блок для
  публичного домена (HTTP only, до SSL)
- `/etc/nginx/sites-enabled/rels-komplekt.ru` — симлинк
- `/etc/nginx/conf.d/rels-rate-limits.conf` — общие rate-limit
  зоны (api_notify, api_track, api_lead)
- `deploy/nginx/` в репо — версионирование конфигов
- `.well-known/acme-challenge/` директория (была отсутствующей)

### Изменено
- `/etc/nginx/sites-enabled/rels-komplekt` — удалены 3 строки
  limit_req_zone из шапки (теперь грузятся из conf.d)

### Не изменялось
- backyard-tech.ru
- default-блок
- gunicorn / Telegram bot / SQLite
- любые HTML/JS/CSS файлы проекта

### Проверено
- `nginx -t` проходит
- backyard-tech.ru работает (301 на https)
- Тестовый доступ :8080 не сломан
- API-эндпоинты на :8080 проксируются через gunicorn
- Новый домен отвечает 200 локально через Host-заголовок
- Acme-challenge доступен по новому конфигу (тест-файл вернулся)
- Блокировки путей (/.env, /CLAUDE.md, /data/competitor/) → 403

### Что осталось до cutover
- Промпт 02: карта 301-редиректов с URL Уралсофта
- Установка Метрика 32668705 + Top@Mail.ru 2690827 на новые
  страницы (about.html, rails-reference.html)
- Обновление sitemap.xml под боевой домен
- Wget-бэкап старого сайта Уралсофта

### Что в момент cutover
- Смена NS в nic.ru на собственные
- A-запись на 202.148.53.107
- `certbot --nginx -d rels-komplekt.ru -d www.rels-komplekt.ru`
- Опубликовать sitemap в Яндекс.Вебмастер

### Бэкап
- `/root/nginx-backup-20260427-194442/` — полный снимок /etc/nginx до
  изменений.
