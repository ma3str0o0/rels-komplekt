# DEVLOG — Рельс-Комплект

Журнал изменений на стороне инфраструктуры/проекта. Формат — обратный
хронологический, новые записи сверху. Подробности по сессиям —
в Obsidian (`Backyard Tech/10-Projects/rels-komplekt/sessions/`).

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
