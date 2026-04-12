#!/usr/bin/env python3
"""
Генератор страницы rails-reference.html.
Все стили таблиц — инлайн hex-значения, без CSS-переменных.
"""

import os

# ── Данные ──────────────────────────────────────────────────────────────────

CATEGORIES = [
    ("ДТ370ИК",  "Термоупрочнённый, износостойкий, повышенная прямолинейность"),
    ("ОТ370ИК",  "Объёмно-термоупрочнённый, износостойкий"),
    ("ДТ350ВС",  "Термоупрочнённый, высокая стойкость к хрупкому разрушению"),
    ("ДТ350СС",  "Термоупрочнённый, стойкий к хрупкому разрушению"),
    ("ОТ350СС",  "Объёмно-термоупрочнённый, стойкий к хрупкому разрушению"),
    ("ДТ350НН",  "Термоупрочнённый, необработанные концы"),
    ("ОТ350НН",  "Объёмно-термоупрочнённый, необработанные концы"),
    ("ДТ350",    "Дифференцированно термоупрочнённый"),
    ("ОТ350",    "Объёмно-термоупрочнённый"),
    ("НТ320ВС",  "Нетермоупрочнённый, высокая стойкость к хрупкому разрушению"),
    ("НТ320",    "Нетермоупрочнённый, повышенная твёрдость"),
    ("НТ300",    "Нетермоупрочнённый, нормальная твёрдость"),
    ("НТ260",    "Нетермоупрочнённый, пониженная твёрдость"),
]

TOLERANCES = [
    ("Высота рельса",         "±1,0",       "±1,0",       "±1,0"),
    ("Ширина головки",        "±1,0",       "±1,0",       "±1,0"),
    ("Ширина подошвы",        "+3,0/−1,0",  "+3,0/−1,0",  "+3,0/−1,0"),
    ("Толщина шейки",         "+1,0/−0,5",  "+1,0/−0,5",  "+1,0/−0,5"),
    ("Симметричность подошвы","2,0",         "2,0",         "2,0"),
    ("Перпендикулярность торцов","1,0",      "1,0",         "1,0"),
]

WEIGHTS = [
    ("Р50",    "51,67 кг/м",  "Широкая колея",  "blue"),
    ("Р65",    "64,88 кг/м",  "Широкая колея",  "blue"),
    ("Р75",    "74,40 кг/м",  "Широкая колея",  "blue"),
    ("КР 70",  "46,10 кг/м",  "Крановый",       "orange"),
    ("КР 80",  "59,81 кг/м",  "Крановый",       "orange"),
    ("КР 100", "83,09 кг/м",  "Крановый",       "orange"),
    ("КР 120", "113,47 кг/м", "Крановый",       "orange"),
    ("КР 140", "141,70 кг/м", "Крановый",       "orange"),
    ("Р33",    "33,48 кг/м",  "Узкоколейный",   "gray"),
    ("Р24",    "24,90 кг/м",  "Узкоколейный",   "gray"),
    ("Р18",    "17,91 кг/м",  "Узкоколейный",   "gray"),
]

# ── Инлайн-стили таблиц (CSS-переменные с hex-fallback) ─────────────────────

S_WRAP  = 'style="border:1px solid var(--color-border, #E2E8F0);border-radius:8px;overflow:hidden;overflow-x:auto;"'
S_TABLE = 'style="width:100%;border-collapse:collapse;font-size:13.5px;"'

S_TH = (
    'style="background:#0A2463;color:#fff;font-weight:600;font-size:12px;'
    'text-transform:uppercase;letter-spacing:.04em;padding:10px 16px;'
    'text-align:left;white-space:nowrap;"'
)

def td_style(idx, first=False):
    """Возвращает инлайн-стиль для <td> с чередованием строк."""
    bg = "var(--color-surface, #F8FAFC)" if idx % 2 == 0 else "var(--color-bg, #ffffff)"
    fw = "font-weight:600;" if first else ""
    return (
        f'style="background:{bg};padding:10px 16px;color:var(--color-text, #020617);'
        f'border-bottom:1px solid var(--color-border, #E2E8F0);{fw}"'
    )


# ── Построители секций ───────────────────────────────────────────────────────

def build_categories_table():
    rows = []
    for i, (code, desc) in enumerate(CATEGORIES):
        last = " border-bottom:none;" if i == len(CATEGORIES) - 1 else ""
        bg = "var(--color-surface, #F8FAFC)" if i % 2 == 0 else "var(--color-bg, #ffffff)"
        td0 = (
            f'style="background:{bg};'
            f'padding:10px 16px;color:var(--color-text, #020617);font-weight:600;'
            f'border-bottom:1px solid var(--color-border, #E2E8F0){last};"'
        )
        td1 = (
            f'style="background:{bg};'
            f'padding:10px 16px;color:var(--color-text, #020617);'
            f'border-bottom:1px solid var(--color-border, #E2E8F0){last};"'
        )
        rows.append(f'        <tr class="trow"><td {td0}>{code}</td><td {td1}>{desc}</td></tr>')
    return "\n".join(rows)


def build_tolerances_table():
    thead = (
        f'      <thead>\n'
        f'        <tr>\n'
        f'          <th {S_TH}>Параметр</th>\n'
        f'          <th {S_TH}>Р50</th>\n'
        f'          <th {S_TH}>Р65 / Р65К</th>\n'
        f'          <th {S_TH}>Р75</th>\n'
        f'        </tr>\n'
        f'      </thead>'
    )
    rows = []
    for i, (param, r50, r65, r75) in enumerate(TOLERANCES):
        last = " border-bottom:none;" if i == len(TOLERANCES) - 1 else ""
        bg = "var(--color-surface, #F8FAFC)" if i % 2 == 0 else "var(--color-bg, #ffffff)"
        def cell(val, bold=False):
            fw = "font-weight:600;" if bold else ""
            return (
                f'<td style="background:{bg};padding:10px 16px;color:var(--color-text, #020617);'
                f'border-bottom:1px solid var(--color-border, #E2E8F0){last};{fw}">{val}</td>'
            )
        rows.append(
            f'        <tr class="trow">'
            f'{cell(param, bold=True)}{cell(r50)}{cell(r65)}{cell(r75)}'
            f'</tr>'
        )
    return thead + "\n      <tbody>\n" + "\n".join(rows) + "\n      </tbody>"


def build_weight_cards():
    badge_colors = {
        "blue":   "background:#DBEAFE;color:#1D4ED8;",
        "orange": "background:#FFEDD5;color:#C2410C;",
        "gray":   "background:#F1F5F9;color:#475569;",
    }
    cards = []
    for name, weight, label, color in WEIGHTS:
        bc = badge_colors[color]
        cards.append(
            f'          <div class="pcard" role="listitem">\n'
            f'            <div class="pcard__top">\n'
            f'              <span class="pcard__badge" style="display:inline-block;'
            f'padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;{bc}">'
            f'{label}</span>\n'
            f'            </div>\n'
            f'            <strong class="pcard__name">{name}</strong>\n'
            f'            <p>{weight}</p>\n'
            f'          </div>'
        )
    return "\n".join(cards)


# ── Главный шаблон HTML ──────────────────────────────────────────────────────

def build_html():
    cat_rows  = build_categories_table()
    tol_body  = build_tolerances_table()
    wgt_cards = build_weight_cards()

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <script>(function(){{var t=localStorage.getItem("theme");if(t)document.documentElement.setAttribute("data-theme",t);}})();</script>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' https://cdnjs.cloudflare.com 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https://api.telegram.org; frame-src https://yandex.ru https://maps.yandex.ru; base-uri 'self'; form-action 'self'">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="Справочник по типам рельсов: категории по ГОСТ 51685-2022, допускаемые отклонения размеров, погонный вес. Рельс-Комплект.">
  <title>Справочник по типам рельсов — Рельс-Комплект</title>

  <!-- Open Graph -->
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Рельс-Комплект">
  <meta property="og:title" content="Справочник по типам рельсов — Рельс-Комплект">
  <meta property="og:description" content="Справочник по типам рельсов: категории по ГОСТ 51685-2022, допускаемые отклонения размеров, погонный вес.">
  <meta property="og:url" content="https://rels-komplekt.ru/rails-reference.html">

  <link rel="stylesheet" href="assets/css/style.css">
  <link rel="stylesheet" href="assets/css/components.css">
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%230369A1'/><text y='22' x='6' font-size='20' fill='white' font-family='sans-serif' font-weight='bold'>Р</text></svg>">

  <!-- Hover-эффект для строк таблицы (hover нельзя задать инлайн) -->
  <style>
    .trow:hover td {{ background: #EFF6FF !important; }}

    /* ── Dark theme overrides ── */
    [data-theme="dark"] body {{
      background: #0D1117;
      color: #E6EDF3;
    }}
    [data-theme="dark"] .trow td {{
      background: #161B22 !important;
      color: #E6EDF3 !important;
      border-bottom-color: #30363D !important;
    }}
    [data-theme="dark"] .trow:nth-child(even) td {{
      background: #1C2128 !important;
    }}
    [data-theme="dark"] .trow:hover td {{
      background: rgba(47, 129, 247, 0.08) !important;
    }}
    [data-theme="dark"] div[style*="border:1px solid"] {{
      border-color: #30363D !important;
    }}
    [data-theme="dark"] .pcard {{
      background: #161B22;
      border-color: #30363D;
    }}
    [data-theme="dark"] .pcard__name,
    [data-theme="dark"] .pcard p {{
      color: #E6EDF3;
    }}
    [data-theme="dark"] .cta-section {{
      background: #161B22;
      border-color: #30363D;
    }}
  </style>
</head>
<body>

  <!-- ═══════════════════════════════════════════════════════════
       ШАПКА
  ═══════════════════════════════════════════════════════════ -->
  <div id="header-placeholder"></div>

  <!-- ═══════════════════════════════════════════════════════════
       ГЛАВНЫЙ КОНТЕНТ
  ═══════════════════════════════════════════════════════════ -->
  <main id="main-content">

    <!-- ── Герой ──────────────────────────────────────────────── -->
    <section class="hero hero--sm">
      <div class="container">
        <h1 class="hero__title">Справочник по типам рельсов</h1>
        <p class="hero__sub">Технические характеристики, категории и вес по ГОСТ 51685-2022</p>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════════════
         1. КАТЕГОРИИ РЕЛЬСОВ ПО ГОСТ 51685-2022
    ══════════════════════════════════════════════════════════ -->
    <section class="section">
      <div class="container">

        <h2 class="section-title">Категории рельсов по ГОСТ 51685-2022</h2>

        <div {S_WRAP}>
          <table {S_TABLE} aria-label="Категории рельсов по ГОСТ 51685-2022">
            <tbody>
{cat_rows}
            </tbody>
          </table>
        </div>

      </div>
    </section>

    <!-- ══════════════════════════════════════════════════════════
         2. ДОПУСКАЕМЫЕ ОТКЛОНЕНИЯ РАЗМЕРОВ
    ══════════════════════════════════════════════════════════ -->
    <section class="section section--muted">
      <div class="container">

        <h2 class="section-title">Допускаемые отклонения размеров, мм</h2>

        <div {S_WRAP}>
          <table {S_TABLE} aria-label="Допускаемые отклонения размеров">
{tol_body}
          </table>
        </div>

      </div>
    </section>

    <!-- ══════════════════════════════════════════════════════════
         3. ПОГОННЫЙ ВЕС РЕЛЬСОВ
    ══════════════════════════════════════════════════════════ -->
    <section class="section">
      <div class="container">

        <h2 class="section-title">Погонный вес рельсов, кг/м</h2>

        <div class="grid grid--3" role="list" aria-label="Погонный вес рельсов">
{wgt_cards}
        </div>

      </div>
    </section>

    <!-- ══════════════════════════════════════════════════════════
         CTA
    ══════════════════════════════════════════════════════════ -->
    <section class="cta-section">
      <div class="container" style="text-align:center; padding-block: 48px;">
        <h2 class="section-title">Нужна помощь с выбором?</h2>
        <p>Наши специалисты помогут подобрать рельс под ваши условия эксплуатации</p>
        <a href="contacts.html" class="btn btn-primary" style="margin-top:16px;">Связаться с нами</a>
      </div>
    </section>

  </main>

  <!-- ═══════════════════════════════════════════════════════════
       ФУТЕР
  ═══════════════════════════════════════════════════════════ -->
  <div id="footer-placeholder"></div>

  <!-- Скрипты -->
  <script src="assets/js/main.js"></script>
</body>
</html>
"""


# ── Точка входа ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "rails-reference.html")
    out = os.path.normpath(out)

    html = build_html()
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✓ Сгенерирован {out} ({len(html):,} символов)")
