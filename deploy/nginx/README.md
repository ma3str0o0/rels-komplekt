# Nginx-конфигурация для VPS

Версионированные копии production-конфигов.
Source of truth — VPS 202.148.53.107, эти файлы — для версионирования.

## Файлы

- `rels-komplekt-internal.conf` — внутренний server-блок на :8080
  (sites-enabled/rels-komplekt). Обслуживает текущий тестовый
  доступ http://202.148.53.107:8080.

- `rels-komplekt.ru.conf` — публичный server-блок для домена
  rels-komplekt.ru. HTTP only до cutover; SSL добавляется через
  certbot --nginx после смены A-записи в nic.ru.

- `rels-rate-limits.conf` — общие rate-limit zones, грузятся
  из /etc/nginx/conf.d/. Используются обоими server-блоками.

- `rels-redirects.conf` — 301-редиректы со старых URL Уралсофта.
  Базовый набор покрывает топ-категории + системные страницы
  (/feedback, /produkciya, /privacy-policy, /sitemap, /store/*).
  /uploadedFiles/* и /img/k1_4/* возвращают 410 Gone. Полная
  карта (44 редиректа из админки Уралсофта) добавляется
  отдельным промптом. Подключается через include внутри
  rels-komplekt.ru.conf.

## Как обновить конфиг на сервере

```
sudo cp deploy/nginx/rels-komplekt.ru.conf \
        /etc/nginx/sites-available/rels-komplekt.ru
sudo cp deploy/nginx/rels-rate-limits.conf \
        /etc/nginx/conf.d/rels-rate-limits.conf
sudo cp deploy/nginx/rels-redirects.conf \
        /etc/nginx/snippets/rels-redirects.conf
sudo nginx -t && sudo systemctl reload nginx
```

## Бэкапы

Перед каждым изменением nginx — полный бэкап в:
`/root/nginx-backup-YYYYMMDD-HHMMSS/`

## Технический долг

- sites-enabled/rels-komplekt — НЕ симлинк, рассинхрон с available.
  После cutover — синхронизировать и сделать симлинком.
- default блок проксит битую ссылку 127.0.0.1:3001 — переписать
  или удалить.
