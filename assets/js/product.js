/* =============================================================
   Рельс-Комплект — Страница товара (product.js)
   Читает ?id= из URL, ищет в catalog.json, рендерит страницу
   ============================================================= */

'use strict';

const CART_KEY = 'cart';

/* ─── Точка входа ────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  const id = new URLSearchParams(window.location.search).get('id');
  if (!id) { window.location.replace('catalog.html'); return; }

  const catalog = await loadCatalog();
  const item = catalog.find(i => i.id === id);
  if (!item) { window.location.replace('catalog.html'); return; }

  renderProduct(item, catalog);
  updateCartBadge();
});

/* ─── Загрузка каталога ──────────────────────────────────────── */
async function loadCatalog() {
  try {
    const res = await fetch('data/catalog.json');
    return await res.json();
  } catch (e) {
    console.error('Ошибка загрузки каталога:', e);
    return [];
  }
}

/* ─── Главный рендер ─────────────────────────────────────────── */
function renderProduct(item, catalog) {
  const pageTitle = `${item.name} — Рельс-Комплект`;
  const pageDesc  = `Купить ${item.name} оптом. ${item.price ? fmtPrice(item.price) + ' ₽/т' : 'Цена по запросу'}. Рельс-Комплект.`;

  document.title = pageTitle;

  const metaDesc = document.querySelector('meta[name="description"]');
  if (metaDesc) metaDesc.content = pageDesc;

  // Обновляем OG-теги для корректного превью при шаринге
  const ogTitle = document.querySelector('meta[property="og:title"]');
  const ogDesc  = document.querySelector('meta[property="og:description"]');
  const ogUrl   = document.querySelector('meta[property="og:url"]');
  if (ogTitle) ogTitle.content = pageTitle;
  if (ogDesc)  ogDesc.content  = pageDesc;
  if (ogUrl)   ogUrl.content   = `https://rels-komplekt.ru/product.html?id=${encodeURIComponent(item.id)}`;

  renderBreadcrumbs(item);
  renderBadge(item);
  renderName(item);
  renderSpecs(item);
  renderPricing(item);
  renderActions(item);
  renderSimilar(item, catalog);

  if (typeof _renderCompetitorData === 'function') {
    _renderCompetitorData(item);
  }

  // Показываем страницу, скрываем загрузку
  document.getElementById('productLoading').classList.add('hidden');
  document.getElementById('productPage').classList.remove('hidden');
}

/* ─── Хлебные крошки ─────────────────────────────────────────── */
function renderBreadcrumbs(item) {
  const sep = `<span class="breadcrumbs__sep" aria-hidden="true"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg></span>`;
  document.getElementById('breadcrumbs').innerHTML = `
    <a href="index.html" class="breadcrumbs__item">Главная</a>${sep}
    <a href="catalog.html" class="breadcrumbs__item">Каталог</a>${sep}
    <a href="catalog.html?cat=${encodeURIComponent(item.category)}" class="breadcrumbs__item">${escHtml(item.category)}</a>${sep}
    <span class="breadcrumbs__item active" aria-current="page">${escHtml(item.name)}</span>
  `;
}

/* ─── Бейдж подкатегории ─────────────────────────────────────── */
function renderBadge(item) {
  const text = item.subcategory || item.category;
  document.getElementById('productBadge').innerHTML =
    `<span class="badge badge--blue product-badge">${escHtml(text)}</span>`;
}

/* ─── Название и артикул ─────────────────────────────────────── */
function renderName(item) {
  document.getElementById('productName').textContent = item.name;
  document.getElementById('productUid').textContent = `Артикул: ${item.id}`;
}

/* ─── Определение состояния товара из названия ───────────────── */
function detectCondition(name) {
  const lc = name.toLowerCase();
  if (/нов(ый|ые|ая|ое|ых|ом|ому)/.test(lc)) return 'Новый';
  if (/хранени/.test(lc))                     return 'С хранения';
  if (/б\/у|старогодн/.test(lc))              return 'Б/У';
  return 'Уточнить';
}

/* ─── Таблица характеристик ──────────────────────────────────── */
function renderSpecs(item) {
  const condition = detectCondition(item.name);

  const priceCell = item.price !== null
    ? `<strong class="product-specs__price">${fmtPrice(item.price)}&nbsp;₽/${escHtml(item.unit || 'т')}</strong>`
    : `<span class="product-specs__price--request">Цена по запросу</span>`;

  const stockCell = item.in_stock
    ? `<span class="badge badge--green">В наличии</span>`
    : `<span class="badge badge--gray">Под заказ</span>`;

  const rows = [
    ['Цена',           priceCell],
    ['Состояние',      escHtml(condition)],
    ['Ед. измерения',  escHtml(item.unit || 'т')],
    ['Наличие',        stockCell],
  ];

  document.getElementById('productSpecs').innerHTML = rows.map(([label, value]) => `
    <tr class="product-specs__row">
      <td class="product-specs__label">${label}</td>
      <td class="product-specs__value">${value}</td>
    </tr>`
  ).join('');
}

/* ─── Вес 1 шт (рельс 12.5 м), кг — по подкатегории ─────────── */
const RAIL_WEIGHT_KG = {
  'Рельс Р8':    100,   // 8.0 кг/м × 12.5
  'Рельсы Р8':   100,
  'Рельс Р12':   150,   // 12.0 × 12.5
  'Рельсы Р12':  150,
  'Рельс Р15':   188,   // 15.1 × 12.5
  'Рельсы Р15':  188,
  'Рельс Р18':   225,   // 18.0 × 12.5
  'Рельсы Р18':  225,
  'Рельс Р24':   300,   // 24.0 × 12.5
  'Рельсы Р24':  300,
  'Рельсы узкоколейные': 300,
  'Рельс Р33':   413,   // 33.0 × 12.5
  'Рельсы Р33':  413,
  'Рельс Р38':   475,   // 38.0 × 12.5
  'Рельсы Р38':  475,
  'Рельс Р43':   558,   // 44.65 × 12.5
  'Рельсы Р43':  558,
  'Рельс Р50':   646,   // 51.67 × 12.5
  'Рельсы Р50':  646,
  'Рельс Р65':   809,   // 64.72 × 12.5
  'Рельсы Р65':  809,
  'Рельсы КР 70':  576,    // 46.10 кг/м × 12.5 (ГОСТ, данные vsp74)
  'Рельсы КР 80':  748,    // 59.81 кг/м × 12.5
  'Рельсы КР 100': 1039,   // 83.09 кг/м × 12.5
  'Рельсы КР 120': 1418,   // 113.47 кг/м × 12.5
  'Рельсы КР 140': 1771,   // 141.70 кг/м × 12.5
  'Международный стандарт рельс DIN 536': 1250,
};

function getWeightKg(item) {
  // Приоритет 1: данные из catalog.json (актуальные, от ГОСТ через vsp74)
  if (item.weight_per_unit && item.weight_per_unit > 0) {
    return item.weight_per_unit;
  }
  // Приоритет 2: fallback по таблице для позиций без weight_per_unit
  return RAIL_WEIGHT_KG[item.subcategory] || RAIL_WEIGHT_KG[item.category] || null;
}

/* ─── Калькулятор / блок "цена по запросу" ──────────────────── */
function renderPricing(item) {
  const el      = document.getElementById('productPricing');
  const KZT     = 5.5; // курс: 1 RUB = 5.5 KZT

  /* Нет цены — только кнопка запроса */
  if (item.price === null) {
    el.innerHTML = `
      <div class="product-price-request">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div>
          <p class="product-price-request__title">Уточните цену у менеджера</p>
          <p class="product-price-request__sub">Стоимость зависит от объёма и условий поставки</p>
        </div>
      </div>`;
    return;
  }

  const weightKg   = getWeightKg(item);
  const initCostRub = weightKg
    ? Math.round((weightKg / 1000) * item.price) // 1 шт → тонны → цена
    : item.price;                                 // 1 тонна если нет веса

  /* Строки ввода: шт + кг (для рельсов) или просто т (для остального) */
  const fieldsHTML = weightKg ? `
    <div class="calc-field">
      <label class="calc-label" for="calcPcs">Кол-во, шт</label>
      <input class="input calc-input" type="number" id="calcPcs" min="1" step="1" value="1">
    </div>
    <span class="calc-eq" aria-hidden="true">=</span>
    <div class="calc-field">
      <label class="calc-label" for="calcKg">Кол-во, кг</label>
      <input class="input calc-input" type="number" id="calcKg" min="0" step="1"
             value="${Math.round(weightKg)}">
    </div>` : `
    <div class="calc-field">
      <label class="calc-label" for="calcTons">Количество, т</label>
      <input class="input calc-input" type="number" id="calcTons" min="0.001" step="0.1" value="1">
    </div>`;

  el.innerHTML = `
    <div class="product-calculator">
      <h3 class="product-calculator__title">Введите данные для расчёта:</h3>
      <div class="calc-fields">${fieldsHTML}</div>
      <div class="calc-result-row">
        <span class="calc-label">Стоимость</span>
        <div class="calc-result">
          <strong id="calcCostVal">${fmtPrice(initCostRub)}</strong>
          <span id="calcCostCurr">₽</span>
        </div>
      </div>
      <div class="currency-toggle" role="group" aria-label="Валюта">
        <label class="currency-opt">
          <input type="radio" name="calcCurr" value="RUB" checked>
          <span>RUB</span>
        </label>
        <label class="currency-opt">
          <input type="radio" name="calcCurr" value="KZT">
          <span>KZT</span>
        </label>
      </div>
    </div>`;

  /* Состояние */
  let costRub  = initCostRub;
  let currency = 'RUB';

  const costVal  = document.getElementById('calcCostVal');
  const costCurr = document.getElementById('calcCostCurr');

  function updateDisplay() {
    const val = currency === 'KZT' ? Math.round(costRub * KZT) : costRub;
    costVal.textContent  = fmtPrice(val);
    costCurr.textContent = currency === 'KZT' ? '₸' : '₽';
  }

  if (weightKg) {
    /* Режим шт ↔ кг */
    const pcsEl = document.getElementById('calcPcs');
    const kgEl  = document.getElementById('calcKg');

    pcsEl.addEventListener('input', () => {
      const pcs = Math.max(1, parseInt(pcsEl.value) || 1);
      pcsEl.value   = pcs;
      const kg      = Math.round(pcs * weightKg);
      kgEl.value    = kg;
      costRub       = Math.round((kg / 1000) * item.price);
      updateDisplay();
    });

    kgEl.addEventListener('input', () => {
      const kg   = Math.max(0, parseFloat(kgEl.value) || 0);
      const pcs  = kg > 0 ? Math.ceil(kg / weightKg) : 0;
      pcsEl.value = pcs;
      costRub     = Math.round((kg / 1000) * item.price);
      updateDisplay();
    });
  } else {
    /* Режим тонн */
    document.getElementById('calcTons').addEventListener('input', e => {
      const tons = Math.max(0, parseFloat(e.target.value) || 0);
      costRub    = Math.round(tons * item.price);
      updateDisplay();
    });
  }

  /* Переключатель валюты */
  el.querySelectorAll('input[name="calcCurr"]').forEach(r => {
    r.addEventListener('change', () => { currency = r.value; updateDisplay(); });
  });
}

/* ─── Кнопки действий ────────────────────────────────────────── */
function renderActions(item) {
  document.getElementById('productActions').innerHTML =
    cartBtnHTML(isInCart(item.id)) + kpBtnHTML();
  bindCartBtn(item);
}

function cartBtnHTML(inCart) {
  if (inCart) {
    return `<button class="btn btn-lg btn-accent product-cart-btn product-cart-btn--added" id="productCartBtn" aria-pressed="true">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>
      В заявке
    </button>`;
  }
  return `<button class="btn btn-lg btn-primary product-cart-btn" id="productCartBtn" aria-pressed="false">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
    Добавить в заявку
  </button>`;
}

function kpBtnHTML() {
  return `<button class="btn btn-lg btn-secondary" id="productKpBtn" data-modal="request">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
    </svg>
    Запросить КП
  </button>`;
}

function bindCartBtn(item) {
  document.getElementById('productCartBtn').addEventListener('click', () => {
    toggleCart(item);
  });
}

/* ─── Toggle корзины ─────────────────────────────────────────── */
function toggleCart(item) {
  const btn = document.getElementById('productCartBtn');
  if (isInCart(item.id)) {
    saveCart(getCart().filter(i => i.id !== item.id));
    btn.outerHTML = cartBtnHTML(false);
    bindCartBtn(item);
    window.RK?.showToast('Товар убран из заявки', 'info');
  } else {
    const cart = getCart();
    cart.push({ id: item.id, name: item.name, price: item.price, unit: item.unit || 'т', qty: 1 });
    saveCart(cart);
    btn.outerHTML = cartBtnHTML(true);
    bindCartBtn(item);
    window.RK?.showToast(`«${item.name}» добавлен в заявку`, 'success');
  }
  updateCartBadge();
}

/* ─── Похожие товары ─────────────────────────────────────────── */
function renderSimilar(item, catalog) {
  const similar = catalog
    .filter(i => i.id !== item.id && i.subcategory === item.subcategory)
    .slice(0, 3);

  const section = document.getElementById('similarSection');
  if (similar.length === 0) { section.classList.add('hidden'); return; }

  document.getElementById('similarGrid').innerHTML = similar.map(s => {
    const priceHtml = s.price !== null
      ? `<span class="pcard__price">${fmtPrice(s.price)}&nbsp;₽/${escHtml(s.unit)}</span>`
      : `<span class="pcard__price pcard__price--request">Цена по запросу</span>`;
    const badgeHtml = s.subcategory
      ? `<span class="badge badge--blue pcard__badge">${escHtml(s.subcategory)}</span>`
      : `<span class="badge badge--gray pcard__badge">${escHtml(s.category)}</span>`;
    return `
      <article class="pcard" role="listitem">
        <div class="pcard__top">${badgeHtml}</div>
        <h3 class="pcard__name">${escHtml(s.name)}</h3>
        <div class="pcard__price-row">${priceHtml}</div>
        <div class="pcard__actions">
          <a href="product.html?id=${encodeURIComponent(s.id)}" class="btn btn-primary btn-sm pcard__btn-detail" style="width:100%;">Подробнее</a>
        </div>
      </article>`;
  }).join('');
}

/* ─── Корзина (localStorage) ─────────────────────────────────── */
function getCart() {
  try { return JSON.parse(localStorage.getItem(CART_KEY) || '[]'); }
  catch { return []; }
}

function saveCart(cart) {
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
}

function isInCart(id) {
  return getCart().some(i => i.id === id);
}

function updateCartBadge() {
  const badge = document.getElementById('cartBadge');
  if (!badge) return;
  const count = getCart().length;
  badge.textContent = count;
  badge.classList.toggle('hidden', count === 0);
}

/* ─── Утилиты ────────────────────────────────────────────────── */
function fmtPrice(n) {
  return new Intl.NumberFormat('ru-RU').format(Math.round(n));
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/* ─── Обогащённый контент (competitor_data) ─────────────────── */
function _renderCompetitorData(item) {
  const cd = item.competitor_data;
  if (!cd) return;

  // 1. Описание — разбиваем на абзацы, экранируем
  const descText    = cd.description || '';
  const descSection = document.getElementById('product-description');
  const descEl      = document.getElementById('product-description-text');
  if (descText && descEl) {
    const paras = descText.split(/\n\n+/).filter(p => p.trim().length > 20);
    descEl.innerHTML = (paras.length > 0 ? paras : [descText])
      .map(p => `<p>${escHtml(p.trim())}</p>`).join('');
    if (descSection) descSection.style.display = '';
  }

  // 2. Таблица технических характеристик (specs)
  if (cd.specs && Object.keys(cd.specs).length > 0) {
    const sec   = document.getElementById('product-specs');
    const tbody = document.getElementById('product-specs-tbody');
    if (sec && tbody) {
      tbody.innerHTML = Object.entries(cd.specs)
        .map(([k, v]) => `<tr>
          <th class="specs-table__key">${escHtml(k)}</th>
          <td class="specs-table__val">${escHtml(String(v))}</td>
        </tr>`).join('');
      sec.style.display = '';
    }
  }

  // 3. ГОСТ-таблицы (gost_tables)
  const gostWrap = document.getElementById('product-gost-tables');
  if (cd.gost_tables && cd.gost_tables.length > 0 && gostWrap) {
    gostWrap.innerHTML = cd.gost_tables.map((tbl, idx) => {
      const headerRow = tbl.headers?.length
        ? `<tr>${tbl.headers.map(h => `<th>${escHtml(h)}</th>`).join('')}</tr>`
        : '';
      const bodyRows = (tbl.rows || []).map(row =>
        `<tr>${row.map(cell => `<td>${escHtml(String(cell))}</td>`).join('')}</tr>`
      ).join('');
      return `<div class="gost-table-wrap">
        <h4 class="gost-table__title">Таблица ${idx + 1}</h4>
        <div class="table-scroll">
          <table class="specs-table">${headerRow}${bodyRows}</table>
        </div>
      </div>`;
    }).join('');
    gostWrap.classList.remove('hidden');
  }

  // 4. ГОСТ номер — добавляем строку в карточку характеристик
  if (cd.gost) {
    const specsTable = document.getElementById('productSpecs');
    if (specsTable) {
      const tr = document.createElement('tr');
      tr.className = 'product-specs__row';
      tr.innerHTML = `<td class="product-specs__label">ГОСТ</td>
                      <td class="product-specs__value" id="productGost">${escHtml(cd.gost)}</td>`;
      specsTable.appendChild(tr);
    }
  }

  // 5. Плейсхолдеры медиа (чертёж / фото)
  if (cd.has_drawing || cd.has_photos) {
    const sec  = document.getElementById('product-media');
    const grid = document.getElementById('product-media-grid');
    if (sec && grid) {
      const items = [];
      if (cd.has_photos) {
        items.push(`<div class="media-placeholder">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/>
            <polyline points="21 15 16 10 5 21"/>
          </svg>
          <p class="media-placeholder__text">Фотографии доступны — обратитесь к менеджеру</p>
          <a href="contacts.html" class="btn btn-secondary btn-sm">Запросить фото</a>
        </div>`);
      }
      if (cd.has_drawing) {
        items.push(`<div class="media-placeholder">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          <p class="media-placeholder__text">Чертёж доступен — обратитесь к менеджеру</p>
          <a href="contacts.html" class="btn btn-secondary btn-sm">Запросить чертёж</a>
        </div>`);
      }
      grid.innerHTML = items.join('');
      sec.style.display = '';
    }
  }

  // 6. Галерея изображений — только http/https URL
  if (cd.images && cd.images.length > 0) {
    const gallery = document.getElementById('product-gallery');
    if (gallery) {
      const imgs = cd.images
        .filter(src => { try { const u = new URL(src); return u.protocol === 'https:' || u.protocol === 'http:'; } catch { return false; } })
        .slice(0, 6)
        .map(src => {
          const img = document.createElement('img');
          img.src = src; img.alt = item.name;
          img.className = 'product-gallery__img'; img.loading = 'lazy';
          return img.outerHTML;
        }).join('');
      gallery.innerHTML = imgs;
    }
  }
}
