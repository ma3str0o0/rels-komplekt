#!/usr/bin/env python3
"""
Генератор HTML-отчёта по конкурентному анализу.
Читает data/catalog_enriched.json → создаёт data/competitor_report.html
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
INPUT_FILE = BASE_DIR / "data" / "catalog_enriched.json"
OUTPUT_FILE = BASE_DIR / "data" / "competitor_report.html"


def fmt_price(price):
    if price is None:
        return '<span class="text-muted fst-italic">по запросу</span>'
    return f"{price:,.0f} ₽/т".replace(",", " ")


def fmt_price_plain(price):
    if price is None:
        return "—"
    return f"{price:,.0f}".replace(",", " ")


def badge(val, true_label="✅", false_label="❌"):
    return true_label if val else false_label


def build_report():
    with open(INPUT_FILE, encoding="utf-8") as f:
        items = json.load(f)

    total = len(items)
    has_match = [x for x in items if x.get("competitor")]
    no_match = [x for x in items if not x.get("competitor")]

    we_cheaper = [
        x for x in has_match
        if x.get("price") and x["competitor"].get("price")
        and x["price"] < x["competitor"]["price"]
    ]
    they_cheaper = [
        x for x in has_match
        if x.get("price") and x["competitor"].get("price")
        and x["competitor"]["price"] < x["price"]
    ]

    # Секция "что добавить" — товары где у конкурента есть контент, которого нет у нас
    # У нас нет ни описания, ни таблиц, ни фото в catalog.json — считаем всё отсутствующим
    content_items = []
    for x in has_match:
        c = x["competitor"]
        missing = []
        if c.get("description"):
            missing.append("описание")
        if c.get("has_spec_table"):
            missing.append("таблица хар-к")
        if c.get("has_photos"):
            missing.append("фото")
        if missing:
            content_items.append((len(missing), x, missing))
    content_items.sort(key=lambda t: t[0], reverse=True)

    # ---- Строки таблицы ----
    rows_html = []
    for x in items:
        c = x.get("competitor")
        our_price = x.get("price")

        if c:
            comp_price = c.get("price")
            comp_price_str = fmt_price_plain(comp_price) + " ₽/т" if comp_price else "—"
            diff = None
            diff_html = "—"
            if our_price and comp_price:
                diff = our_price - comp_price
                if diff < 0:
                    # мы дешевле
                    diff_html = f'<span class="diff-cheaper">−{abs(diff):,.0f} ₽</span>'.replace(",", " ")
                elif diff > 0:
                    # они дешевле
                    diff_html = f'<span class="diff-expensive">+{diff:,.0f} ₽</span>'.replace(",", " ")
                else:
                    diff_html = '<span class="text-muted">0</span>'

            url = c.get("url", "")
            link = f'<a href="{url}" target="_blank" class="btn btn-sm btn-outline-secondary py-0">→</a>' if url else "—"
            has_desc = badge(bool(c.get("description")))
            has_specs = badge(c.get("has_spec_table"))
            has_photos = badge(c.get("has_photos"))

            # data-атрибуты для фильтрации
            if our_price and comp_price:
                price_rel = "cheaper" if our_price < comp_price else ("expensive" if our_price > comp_price else "equal")
            else:
                price_rel = "unknown"

            match_flag = "yes"
        else:
            comp_price_str = "—"
            diff_html = "—"
            link = "—"
            has_desc = "—"
            has_specs = "—"
            has_photos = "—"
            price_rel = "unknown"
            match_flag = "no"

        our_price_html = fmt_price(our_price)
        name_escaped = x["name"].replace('"', "&quot;")

        rows_html.append(f"""
        <tr data-match="{match_flag}" data-price-rel="{price_rel}" data-name="{name_escaped}">
          <td>{x["name"]}</td>
          <td class="text-end">{our_price_html}</td>
          <td class="text-end">{comp_price_str}</td>
          <td class="text-end">{diff_html}</td>
          <td class="text-center">{has_desc}</td>
          <td class="text-center">{has_specs}</td>
          <td class="text-center">{has_photos}</td>
          <td class="text-center">{link}</td>
        </tr>""")

    rows_str = "\n".join(rows_html)

    # ---- Секция "что добавить" ----
    todo_rows = []
    for _, x, missing in content_items:
        tags = " ".join(
            f'<span class="badge bg-warning text-dark me-1">{m}</span>' for m in missing
        )
        c = x["competitor"]
        url = c.get("url", "")
        link = f'<a href="{url}" target="_blank">vsp74.ru →</a>' if url else ""
        todo_rows.append(f"""
        <tr>
          <td>{x["name"]}</td>
          <td>{tags}</td>
          <td class="text-center">{len(missing)}</td>
          <td>{link}</td>
        </tr>""")

    todo_str = "\n".join(todo_rows)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Конкурентный анализ — Рельс-Комплект</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {{ font-family: Inter, system-ui, sans-serif; background: #f8f9fa; }}
    .kpi-card {{ border-radius: 12px; border: none; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
    .kpi-value {{ font-size: 2.4rem; font-weight: 700; }}
    .kpi-label {{ font-size: .85rem; color: #666; }}
    .diff-cheaper {{ color: #198754; font-weight: 600; }}
    .diff-expensive {{ color: #dc3545; font-weight: 600; }}
    #main-table th {{ cursor: pointer; user-select: none; white-space: nowrap; }}
    #main-table th:hover {{ background: #e9ecef; }}
    .sort-icon::after {{ content: " ↕"; opacity: .4; font-size: .8em; }}
    .sort-asc::after {{ content: " ↑"; opacity: 1; }}
    .sort-desc::after {{ content: " ↓"; opacity: 1; }}
    .section-header {{ border-left: 4px solid #1A56A0; padding-left: 12px; margin-bottom: 1rem; }}
    #search-input {{ max-width: 300px; }}
    tr.hidden {{ display: none; }}
  </style>
</head>
<body>
<div class="container-fluid py-4 px-4">

  <h1 class="mb-1" style="color:#1A56A0;">Конкурентный анализ</h1>
  <p class="text-muted mb-4">Сравнение с vsp74.ru · {total} позиций в каталоге</p>

  <!-- KPI карточки -->
  <div class="row g-3 mb-5">
    <div class="col-sm-6 col-lg-3">
      <div class="card kpi-card p-3 h-100">
        <div class="kpi-value text-primary">{total}</div>
        <div class="kpi-label">Всего наших товаров</div>
      </div>
    </div>
    <div class="col-sm-6 col-lg-3">
      <div class="card kpi-card p-3 h-100">
        <div class="kpi-value" style="color:#0d6efd;">{len(has_match)}</div>
        <div class="kpi-label">Нашли совпадение у конкурента</div>
      </div>
    </div>
    <div class="col-sm-6 col-lg-3">
      <div class="card kpi-card p-3 h-100">
        <div class="kpi-value text-success">{len(we_cheaper)}</div>
        <div class="kpi-label">Мы дешевле</div>
      </div>
    </div>
    <div class="col-sm-6 col-lg-3">
      <div class="card kpi-card p-3 h-100">
        <div class="kpi-value text-danger">{len(they_cheaper)}</div>
        <div class="kpi-label">Конкурент дешевле</div>
      </div>
    </div>
  </div>

  <!-- Таблица сравнения -->
  <div class="card shadow-sm mb-5">
    <div class="card-body">
      <h4 class="section-header">Сравнение позиций</h4>

      <!-- Фильтры -->
      <div class="d-flex flex-wrap gap-3 align-items-center mb-3">
        <div class="btn-group btn-group-sm" role="group" id="filter-match">
          <input type="radio" class="btn-check" name="match" id="m-all" value="all" checked>
          <label class="btn btn-outline-secondary" for="m-all">Все ({total})</label>
          <input type="radio" class="btn-check" name="match" id="m-yes" value="yes">
          <label class="btn btn-outline-secondary" for="m-yes">С совпадением ({len(has_match)})</label>
          <input type="radio" class="btn-check" name="match" id="m-no" value="no">
          <label class="btn btn-outline-secondary" for="m-no">Без совпадения ({len(no_match)})</label>
        </div>
        <div class="btn-group btn-group-sm" role="group" id="filter-price">
          <input type="radio" class="btn-check" name="price" id="p-all" value="all" checked>
          <label class="btn btn-outline-secondary" for="p-all">Все цены</label>
          <input type="radio" class="btn-check" name="price" id="p-cheaper" value="cheaper">
          <label class="btn btn-outline-success" for="p-cheaper">Мы дешевле</label>
          <input type="radio" class="btn-check" name="price" id="p-expensive" value="expensive">
          <label class="btn btn-outline-danger" for="p-expensive">Конкурент дешевле</label>
        </div>
        <input type="text" id="search-input" class="form-control form-control-sm"
               placeholder="Поиск по названию…">
      </div>

      <div class="table-responsive">
        <table class="table table-hover table-sm align-middle" id="main-table">
          <thead class="table-light">
            <tr>
              <th class="sort-icon" data-col="0">Наш товар</th>
              <th class="sort-icon text-end" data-col="1">Наша цена</th>
              <th class="sort-icon text-end" data-col="2">Цена конкурента</th>
              <th class="sort-icon text-end" data-col="3">Разница</th>
              <th class="text-center">Описание</th>
              <th class="text-center">Хар-ки</th>
              <th class="text-center">Фото</th>
              <th class="text-center">Ссылка</th>
            </tr>
          </thead>
          <tbody>
{rows_str}
          </tbody>
        </table>
      </div>
      <div id="no-results" class="text-center text-muted py-3 d-none">Ничего не найдено</div>
    </div>
  </div>

  <!-- Что добавить на сайт -->
  <div class="card shadow-sm mb-5">
    <div class="card-body">
      <h4 class="section-header">Что добавить на сайт</h4>
      <p class="text-muted small mb-3">
        Товары, по которым у конкурента есть контент, которого нет у нас.
        Сортировка: чем больше недостающего — тем выше.
      </p>
      <div class="table-responsive">
        <table class="table table-sm align-middle">
          <thead class="table-light">
            <tr>
              <th>Наш товар</th>
              <th>Чего не хватает</th>
              <th class="text-center">Кол-во пробелов</th>
              <th>Источник</th>
            </tr>
          </thead>
          <tbody>
{todo_str}
          </tbody>
        </table>
      </div>
    </div>
  </div>

</div><!-- /container -->

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
(function () {{
  // ---- Сортировка ----
  const table = document.getElementById('main-table');
  const tbody = table.querySelector('tbody');
  let sortCol = -1, sortAsc = true;

  function parseVal(td) {{
    const txt = td.textContent.trim().replace(/[^0-9.\\-]/g, '');
    const n = parseFloat(txt);
    return isNaN(n) ? td.textContent.trim().toLowerCase() : n;
  }}

  table.querySelectorAll('th[data-col]').forEach(th => {{
    th.addEventListener('click', () => {{
      const col = parseInt(th.dataset.col);
      if (sortCol === col) sortAsc = !sortAsc;
      else {{ sortCol = col; sortAsc = true; }}

      table.querySelectorAll('th').forEach(h => {{
        h.classList.remove('sort-asc', 'sort-desc');
        if (h.classList.contains('sort-icon')) h.className = h.className;
      }});
      th.classList.add(sortAsc ? 'sort-asc' : 'sort-desc');

      const rows = Array.from(tbody.querySelectorAll('tr'));
      rows.sort((a, b) => {{
        const av = parseVal(a.cells[col]);
        const bv = parseVal(b.cells[col]);
        if (av < bv) return sortAsc ? -1 : 1;
        if (av > bv) return sortAsc ? 1 : -1;
        return 0;
      }});
      rows.forEach(r => tbody.appendChild(r));
      applyFilters();
    }});
  }});

  // ---- Фильтры ----
  function applyFilters() {{
    const matchVal = document.querySelector('input[name="match"]:checked').value;
    const priceVal = document.querySelector('input[name="price"]:checked').value;
    const search = document.getElementById('search-input').value.toLowerCase();

    let visible = 0;
    tbody.querySelectorAll('tr').forEach(row => {{
      const m = row.dataset.match;
      const p = row.dataset.priceRel;
      const name = row.dataset.name.toLowerCase();

      const matchOk = matchVal === 'all' || m === matchVal;
      const priceOk = priceVal === 'all' || p === priceVal;
      const searchOk = !search || name.includes(search);

      if (matchOk && priceOk && searchOk) {{
        row.classList.remove('hidden');
        visible++;
      }} else {{
        row.classList.add('hidden');
      }}
    }});
    document.getElementById('no-results').classList.toggle('d-none', visible > 0);
  }}

  document.querySelectorAll('input[name="match"], input[name="price"]').forEach(el => {{
    el.addEventListener('change', applyFilters);
  }});
  document.getElementById('search-input').addEventListener('input', applyFilters);
}})();
</script>
</body>
</html>"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Отчёт готов: {OUTPUT_FILE.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    build_report()
