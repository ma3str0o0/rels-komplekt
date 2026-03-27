#!/bin/bash
# Запуск полного пайплайна парсинга vsp74.ru
# Использование: ./run_parser.sh [--skip-scrape] [--from=N]
#   --skip-scrape   пропустить этапы 1-2 (использовать уже скачанные данные)
#   --from=3        начать с этапа N (1-5)

set -e
cd "$(dirname "$0")"

PARSER_DIR="tools/parser"
SKIP_SCRAPE=false
FROM_STAGE=1

for arg in "$@"; do
  case $arg in
    --skip-scrape) SKIP_SCRAPE=true ;;
    --from=*) FROM_STAGE="${arg#*=}" ;;
  esac
done

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Парсер конкурента vsp74.ru             ║"
echo "║   Рельс-Комплект                         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

run_stage() {
  local num=$1
  local name=$2
  local script=$3
  if [ "$num" -lt "$FROM_STAGE" ]; then
    echo "⏭  Этап $num пропущен (--from=$FROM_STAGE)"
    return
  fi
  echo "──────────────────────────────────────────"
  echo "▶  Этап $num: $name"
  echo "──────────────────────────────────────────"
  python3 "$PARSER_DIR/$script"
  echo "✓  Этап $num завершён"
  echo ""
}

if [ "$SKIP_SCRAPE" = true ]; then
  echo "⚡ Режим --skip-scrape: этапы 1-2 пропущены"
  FROM_STAGE=3
fi

run_stage 1 "Сбор каталога конкурента"      "scraper.py"
run_stage 2 "Парсинг карточек товаров"       "scraper_detail.py"
run_stage 3 "Сопоставление с нашим каталогом" "matcher.py"
run_stage 4 "Генерация отчёта"               "report.py"
run_stage 5 "Обогащение catalog.json"        "enrich.py"

echo "══════════════════════════════════════════"
echo "✅ Пайплайн завершён!"
echo ""
echo "Результаты:"
[ -f data/competitor_catalog.json ]  && echo "  📦 data/competitor_catalog.json"
[ -f data/competitor_details.json ]  && echo "  📋 data/competitor_details.json"
[ -f data/catalog_enriched.json ]    && echo "  🔗 data/catalog_enriched.json"
[ -f data/competitor_report.md ]     && echo "  📊 data/competitor_report.md"
[ -f data/catalog.json ]             && echo "  ✅ data/catalog.json (обновлён)"
echo ""
