# Рельс-Комплект — инструкции для Claude Code

## О проекте
Сайт оптового B2B поставщика рельсовых материалов. Дедлайн: 20 апреля 2026.

## Стек
- Чистый HTML5 / CSS3 / Vanilla JavaScript — никаких фреймворков
- Полностью статический сайт, без бэкенда
- Mobile-first

## Дизайн
- Основной цвет: #1A56A0 (синий)
- Акцент: #E65100 (оранжевый)
- Шрифт: Inter (Google Fonts)
- Стиль: строгий промышленный B2B
- Ориентир: vsp74.ru
- Design system: `docs/design-system/рельс-комплект/MASTER.md`

## Структура файлов
```
*.html              — страницы в корне
assets/css/         — style.css, components.css
assets/js/          — main.js, catalog.js, product.js, ...
assets/img/certs/   — сертификаты
data/catalog.json   — 158 позиций (публичный)
docs/               — документация разработки (DEVLOG, PROJECT_STATUS, design-system)
tools/              — скрипты парсинга (не для продакшна)
proxy/              — серверный прокси (секреты в .env)
serve.py            — единый HTTP-сервер (статика + /api/notify)
```

## Бизнес-логика
- Цены в рублях за тонну
- price: null → показывать "Цена по запросу"
- Калькулятор: длина(м) × вес_рельса(кг/м) / 1000 = тоннаж
- Заявки: EmailJS + Telegram Bot API
- PDF спецификации: jsPDF через CDN

## Комментарии в коде — на русском языке
