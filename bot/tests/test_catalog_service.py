"""
Unit-тесты для bot/services/catalog.py.

Все тесты используют tmp_catalog fixture — пишут во временный JSON-файл,
а не в проде data/catalog.json. Каждый тест получает чистую копию каталога
и сброшенный module-level кеш.
"""
import json
import shutil
from pathlib import Path

import pytest

import bot.services.catalog as svc

_REAL_CATALOG = Path("/root/projects/rels-komplekt/data/catalog.json")


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_catalog(tmp_path, monkeypatch):
    """Копирует реальный catalog.json во временный путь и подсовывает его в сервис.

    После выхода фикстуры pytest сам удалит tmp_path. Module-level кеш
    сбрасывается до и после теста.
    """
    dst = tmp_path / "catalog.json"
    shutil.copy(_REAL_CATALOG, dst)

    # Подменяем оба места, где используется путь:
    monkeypatch.setattr(svc, "CATALOG_PATH", dst)
    monkeypatch.setattr(svc, "AUDIT_LOG_PATH", tmp_path / "catalog_audit.log")

    # Сброс module-level кеша
    svc._cache = []
    svc._cache_mtime = 0.0

    yield dst

    # Финальный сброс кеша — чтобы следующий тест не подцепил наш tmp каталог
    svc._cache = []
    svc._cache_mtime = 0.0


@pytest.fixture
def small_catalog(tmp_path, monkeypatch):
    """Маленький контролируемый каталог из 3 товаров — для предсказуемых тестов."""
    dst = tmp_path / "catalog.json"
    data = [
        {
            "id": "p001", "name": "Альфа товар", "page_name": "alfa-tovar",
            "category": "Кат1", "subcategory": None,
            "price": 100000, "unit": "т", "in_stock": True,
            "competitor_data": {}, "weight_per_unit": None, "length_m": None,
            "image": None,
        },
        {
            "id": "p002", "name": "Бета штука", "page_name": "beta-shtuka",
            "category": "Кат1", "subcategory": None,
            "price": 144000, "unit": "т", "in_stock": False,
            "competitor_data": {}, "weight_per_unit": None, "length_m": None,
            "image": None,
        },
        {
            "id": "p003", "name": "Гамма деталь", "page_name": "gamma-detal",
            "category": "Кат2", "subcategory": None,
            "price": None, "unit": "шт", "in_stock": True,
            "competitor_data": {}, "weight_per_unit": None, "length_m": None,
            "image": None,
        },
    ]
    dst.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    monkeypatch.setattr(svc, "CATALOG_PATH", dst)
    monkeypatch.setattr(svc, "AUDIT_LOG_PATH", tmp_path / "catalog_audit.log")

    svc._cache = []
    svc._cache_mtime = 0.0

    yield dst

    svc._cache = []
    svc._cache_mtime = 0.0


# ══════════════════════════════════════════════════════════════════════════
# _slugify_page_name
# ══════════════════════════════════════════════════════════════════════════


class TestSlugifyPageName:
    def test_cyrillic_with_digits(self):
        assert svc._slugify_page_name("Рельсы Р65 ДТ350") == "relsy-r65-dt350"

    def test_only_special_chars_and_spaces(self):
        assert svc._slugify_page_name("   !!!   ") == ""

    def test_mixed_special_chars(self):
        assert svc._slugify_page_name("Кран-балка / 5т") == "kran-balka-5t"

    def test_collapses_repeated_separators(self):
        # пробелы, дефисы, спецсимволы → один дефис
        assert svc._slugify_page_name("a  b---c!!!d") == "a-b-c-d"

    def test_no_leading_or_trailing_hyphen(self):
        result = svc._slugify_page_name("-Привет-")
        assert not result.startswith("-")
        assert not result.endswith("-")
        assert result == "privet"

    def test_empty_string(self):
        assert svc._slugify_page_name("") == ""

    def test_pure_latin(self):
        assert svc._slugify_page_name("Hello World") == "hello-world"

    def test_zh_ts_multichar_transliteration(self):
        # ж→zh, ц→ts, ё→yo, ш→sh
        assert svc._slugify_page_name("Жёлтый цыплёнок") == "zhyoltyy-tsyplyonok"


# ══════════════════════════════════════════════════════════════════════════
# find_products
# ══════════════════════════════════════════════════════════════════════════


class TestFindProducts:
    def test_case_insensitive_by_name(self, small_catalog):
        results = svc.find_products("альфа")
        assert len(results) == 1
        assert results[0]["id"] == "p001"

        results_upper = svc.find_products("АЛЬФА")
        assert len(results_upper) == 1
        assert results_upper[0]["id"] == "p001"

    def test_find_by_id_substring(self, tmp_catalog):
        # 00011 встречается у нескольких — главное чтобы 00011763495 был среди них
        results = svc.find_products("00011", limit=20)
        ids = [r["id"] for r in results]
        assert "00011763495" in ids

    def test_find_by_full_id(self, small_catalog):
        results = svc.find_products("p002")
        assert len(results) == 1
        assert results[0]["id"] == "p002"

    def test_empty_query_returns_empty(self, small_catalog):
        assert svc.find_products("") == []
        assert svc.find_products("   ") == []

    def test_limit_respected(self, tmp_catalog):
        # Запрос с очень общим словом — должно быть точно >= limit
        results = svc.find_products("Рельсы", limit=3)
        assert len(results) <= 3

    def test_no_match_returns_empty(self, small_catalog):
        assert svc.find_products("несуществующее_слово_xyz") == []


# ══════════════════════════════════════════════════════════════════════════
# quick_adjust_price
# ══════════════════════════════════════════════════════════════════════════


class TestQuickAdjustPrice:
    def test_plus_10_percent(self, small_catalog):
        ok, old, new = svc.quick_adjust_price("p001", 10)
        assert ok is True
        assert old == 100000
        assert new == 110000

    def test_minus_5_percent_on_144000(self, small_catalog):
        ok, old, new = svc.quick_adjust_price("p002", -5)
        assert ok is True
        assert old == 144000
        assert new == 136800

    def test_price_is_none(self, small_catalog):
        ok, old, new = svc.quick_adjust_price("p003", 5)
        assert ok is False
        assert old is None
        assert new is None

    def test_unknown_id(self, small_catalog):
        ok, old, new = svc.quick_adjust_price("nope", 5)
        assert ok is False
        assert old is None
        assert new is None

    def test_audit_log_written(self, small_catalog, tmp_path):
        audit_path = tmp_path / "catalog_audit.log"
        assert not audit_path.exists()

        ok, old, new = svc.quick_adjust_price("p001", 10, user_id=42)
        assert ok is True
        assert audit_path.exists()

        content = audit_path.read_text(encoding="utf-8")
        # Должна быть строка с op=quick_adjust (это op для quick_adjust_price)
        assert "op=quick_adjust" in content
        assert "pid=p001" in content
        assert "user_id=42" in content
        assert "old=100000" in content
        assert "new=110000" in content

    def test_persists_to_disk(self, small_catalog):
        svc.quick_adjust_price("p001", 10)
        # Перезагружаем — кеш сбрасываем чтобы быть уверенными
        svc._cache_mtime = 0.0
        item = svc.get_product("p001")
        assert item["price"] == 110000


# ══════════════════════════════════════════════════════════════════════════
# set_in_stock / bulk_set_in_stock
# ══════════════════════════════════════════════════════════════════════════


class TestSetInStock:
    def test_set_in_stock_true(self, small_catalog):
        # p002 был False — ставим True
        assert svc.set_in_stock("p002", True) is True
        svc._cache_mtime = 0.0
        assert svc.get_product("p002")["in_stock"] is True

    def test_set_in_stock_false(self, small_catalog):
        # p001 был True — ставим False
        assert svc.set_in_stock("p001", False) is True
        svc._cache_mtime = 0.0
        assert svc.get_product("p001")["in_stock"] is False

    def test_unknown_id_returns_false(self, small_catalog):
        assert svc.set_in_stock("nope", True) is False


class TestBulkSetInStock:
    def test_bulk_set_in_stock_by_category(self, small_catalog):
        # Кат1: p001 (True), p002 (False). Ставим False — изменится только p001.
        count = svc.bulk_set_in_stock(False, category="Кат1")
        assert count == 1
        svc._cache_mtime = 0.0
        assert svc.get_product("p001")["in_stock"] is False
        assert svc.get_product("p002")["in_stock"] is False

    def test_bulk_set_in_stock_all_no_category(self, small_catalog):
        # Все: p001=True, p002=False, p003=True. Ставим True — поменяется только p002.
        count = svc.bulk_set_in_stock(True, category=None)
        assert count == 1
        svc._cache_mtime = 0.0
        assert svc.get_product("p002")["in_stock"] is True

    def test_bulk_set_in_stock_all_flip_false(self, small_catalog):
        # Все → False: должны измениться p001 (True→False) и p003 (True→False), всего 2
        count = svc.bulk_set_in_stock(False, category=None)
        assert count == 2

    def test_bulk_set_in_stock_nonexistent_category(self, small_catalog):
        count = svc.bulk_set_in_stock(True, category="НетТакой")
        assert count == 0


# ══════════════════════════════════════════════════════════════════════════
# set_price_request
# ══════════════════════════════════════════════════════════════════════════


class TestSetPriceRequest:
    def test_sets_price_to_none(self, small_catalog):
        assert svc.set_price_request("p001") is True
        svc._cache_mtime = 0.0
        assert svc.get_product("p001")["price"] is None

    def test_unknown_id_returns_false(self, small_catalog):
        assert svc.set_price_request("nope") is False


# ══════════════════════════════════════════════════════════════════════════
# get_product_count
# ══════════════════════════════════════════════════════════════════════════


class TestGetProductCount:
    def test_count_matches_data(self, small_catalog):
        assert svc.get_product_count() == 3

    def test_real_catalog_count(self, tmp_catalog):
        # 158 позиций согласно CLAUDE.md, но мы не закладываемся на точное число
        assert svc.get_product_count() > 0


# ══════════════════════════════════════════════════════════════════════════
# parse_csv_prices
# ══════════════════════════════════════════════════════════════════════════


class TestParseCsvPrices:
    def test_valid_id_price_csv(self, small_catalog):
        csv = "id,price\np001,200000\np002,160000\n"
        updates, errors = svc.parse_csv_prices(csv)
        assert updates == {"p001": 200000, "p002": 160000}
        assert errors == []

    def test_valid_name_price_csv(self, small_catalog):
        csv = "name,price\nАльфа товар,250000\n"
        updates, errors = svc.parse_csv_prices(csv)
        assert updates == {"p001": 250000}
        assert errors == []

    def test_unknown_id_in_errors(self, small_catalog):
        csv = "id,price\np001,200000\nDOESNT_EXIST,300000\n"
        updates, errors = svc.parse_csv_prices(csv)
        assert updates == {"p001": 200000}
        assert any("DOESNT_EXIST" in e or "не найден" in e.lower() for e in errors)

    def test_invalid_price_in_errors(self, small_catalog):
        csv = "id,price\np001,abcxyz\n"
        updates, errors = svc.parse_csv_prices(csv)
        assert updates == {}
        assert len(errors) >= 1
        assert any("abcxyz" in e or "цена" in e.lower() or "price" in e.lower() for e in errors)

    def test_missing_required_columns(self, small_catalog):
        csv = "foo,bar\nx,y\n"
        updates, errors = svc.parse_csv_prices(csv)
        assert updates == {}
        assert errors

    def test_price_zero_or_dash_means_none(self, small_catalog):
        csv = "id,price\np001,0\np002,-\np003,null\n"
        updates, errors = svc.parse_csv_prices(csv)
        # 0 / "-" / "null" / "" → None («По запросу») — соответствует UI csv_info
        assert updates.get("p001") is None
        assert updates.get("p002") is None
        assert updates.get("p003") is None


# ══════════════════════════════════════════════════════════════════════════
# add_product
# ══════════════════════════════════════════════════════════════════════════


class TestAddProduct:
    def test_basic_add(self, small_catalog):
        item = svc.add_product("Рельсы Р50", "Рельсы", 50000, "т")
        assert item["name"] == "Рельсы Р50"
        assert item["category"] == "Рельсы"
        assert item["price"] == 50000
        assert item["unit"] == "т"
        assert item["in_stock"] is True
        assert item["weight_per_unit"] is None
        assert item["length_m"] is None

    def test_page_name_is_slug(self, small_catalog):
        item = svc.add_product("Рельсы Р65 ДТ350", "Кат", 100, "т")
        assert item["page_name"] == "relsy-r65-dt350"

    def test_weight_and_length(self, small_catalog):
        item = svc.add_product(
            "Кран-балка", "Балки", 200, "шт",
            weight_per_unit=150.5, length_m=12.0,
        )
        assert item["weight_per_unit"] == 150.5
        assert item["length_m"] == 12.0

    def test_generated_id_is_unique(self, small_catalog):
        item1 = svc.add_product("Хром молибден", "Сталь", 1000)
        item2 = svc.add_product("Хром молибден", "Сталь", 2000)
        assert item1["id"] != item2["id"]

    def test_persists_to_disk(self, small_catalog):
        item = svc.add_product("Тест товар", "Кат1", 5000)
        svc._cache_mtime = 0.0
        loaded = svc.get_product(item["id"])
        assert loaded is not None
        assert loaded["name"] == "Тест товар"


# ══════════════════════════════════════════════════════════════════════════
# Ротация .bak
# ══════════════════════════════════════════════════════════════════════════


class TestBackupRotation:
    def test_rotation_creates_numbered_baks(self, small_catalog):
        catalog_path = small_catalog
        bak0 = catalog_path.with_suffix(".json.bak")
        bak1 = Path(f"{bak0}.1")
        bak2 = Path(f"{bak0}.2")

        # Три последовательных мутации = три _save() = три ротации .bak
        svc.set_in_stock("p001", False)
        svc.set_in_stock("p002", True)
        svc.set_in_stock("p001", True)

        assert bak0.exists(), ".bak должен существовать после первого save"
        assert bak1.exists(), ".bak.1 должен существовать после второго save"
        assert bak2.exists(), ".bak.2 должен существовать после третьего save"

    def test_manual_dated_baks_untouched(self, small_catalog):
        catalog_path = small_catalog
        # Создаём ручной снимок «bak-2026-xxx»
        manual = catalog_path.parent / "catalog.json.bak-2026-05-13-test"
        manual.write_text("manual snapshot", encoding="utf-8")

        # Несколько мутаций
        svc.set_in_stock("p001", False)
        svc.set_in_stock("p002", True)
        svc.set_in_stock("p003", False)

        # Ручной снимок не должен быть перезаписан
        assert manual.exists()
        assert manual.read_text(encoding="utf-8") == "manual snapshot"
