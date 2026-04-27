# DEVLOG — Рельс-Комплект

Журнал изменений на стороне инфраструктуры/проекта. Формат — обратный
хронологический, новые записи сверху. Подробности по сессиям —
в Obsidian (`Backyard Tech/10-Projects/rels-komplekt/sessions/`).

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
