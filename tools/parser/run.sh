#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Шаг 1: Парсинг vsp74.ru..."
python3 scraper.py

echo ""
echo "Шаг 2: Сопоставление с каталогом..."
python3 matcher.py

echo ""
echo "Шаг 3: Генерация отчёта..."
python3 report.py

echo ""
echo "Готово! Результаты:"
echo "  data/competitor_raw.json"
echo "  data/catalog_enriched.json"
echo "  data/competitor_report.md"
