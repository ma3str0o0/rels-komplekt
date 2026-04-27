# Nginx audit — 2026-04-27

Сырой дамп текущего состояния nginx и backend-сервисов на VPS
202.148.53.107 перед подготовкой server-блока для домена
rels-komplekt.ru. Изменений в системе не вносилось.

## Файлы

- `01-nginx-T.txt` — полный `sudo nginx -T`
- `02-snippets.txt` — `/etc/nginx/snippets/` (security-headers, fastcgi-php, snakeoil)
- `03-server-blocks.txt` — sites-available/sites-enabled конфиги (rels-komplekt, backyard, default) + diff
- `04-backend.txt` — systemctl status и unit-файлы для rels-notify, rels-admin-bot, rels-komplekt
- `05-project.txt` — `ls -la` корня проекта + CLAUDE.md
- `06-nginx-logs.txt` — листинг `/var/log/nginx/`

## Маскирование

В `04-backend.txt` Telegram bot token заменён на
`bot<REDACTED_BOT_ID>:<REDACTED_BOT_TOKEN>` (8 вхождений в логах
`rels-admin-bot.service`).
