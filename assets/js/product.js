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

  // Обработчики лайтбокса
  document.getElementById('lightboxClose')?.addEventListener('click', closeLightbox);
  document.getElementById('lightboxBackdrop')?.addEventListener('click', closeLightbox);
});

/* ─── Загрузка каталога ──────────────────────────────────────── */
async function loadCatalog() {
  try {
    const res = await fetch('data/catalog.json?v=' + (window._catalogVersion || Date.now()));
    return await res.json();
  } catch (e) {
    console.error('Ошибка загрузки каталога:', e);
    return [];
  }
}

/* ─── Главный рендер ─────────────────────────────────────────── */
function renderProduct(item, catalog) {
  const pageTitle = `${item.name} — Рельс-Комплект`;
  const pageDesc  = `Купить ${item.name} оптом. ${item.price ? fmtPrice(item.price) + ' ₽/' + (item.unit || 'т') : 'Цена по запросу'}. Рельс-Комплект.`;

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

  renderBackButton(item);
  renderBreadcrumbs(item);
  renderBadge(item);
  renderName(item);
  renderProductImage(item);
  renderPriceDisplay(item);
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

/* ─── Кнопка «Назад» с именем категории ─────────────────────── */
function renderBackButton(item) {
  const wrap = document.getElementById('backBtnWrap');
  if (!wrap) return;

  // Определяем метку кнопки из сохранённого состояния каталога
  let label = 'Каталог';
  try {
    const saved = sessionStorage.getItem('rk_catalog_state');
    if (saved) {
      const s = JSON.parse(saved);
      const f = s.filter;
      if (f) {
        if (f.type === 'category' || f.type === 'subcategory') {
          label = f.value || 'Каталог';
        } else if (f.type === 'multi-category' && Array.isArray(f.value) && f.value.length) {
          label = f.value[0];
        }
      }
    }
  } catch(e) { /* sessionStorage недоступен */ }

  wrap.innerHTML = `
    <a href="catalog.html" class="product-back-btn" aria-label="Вернуться: ${escHtml(label)}">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 18 9 12 15 6"/></svg>
      <span>${escHtml(label)}</span>
    </a>`;
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

/* ─── Фото товара ────────────────────────────────────────────── */
function renderProductImage(item) {
  const wrap = document.getElementById('productImageWrap');
  if (!wrap) return;
  if (!item.image) return; // SVG-заглушка из HTML остаётся

  // Сохраняем HTML заглушки до замены содержимого
  const placeholderHtml = wrap.querySelector('.product-image__placeholder')?.outerHTML
    || '<div class="product-image__placeholder"><span class="product-image__label">Фото отсутствует</span></div>';

  const btn = document.createElement('button');
  btn.className = 'product-photo-btn';
  btn.type = 'button';
  btn.setAttribute('aria-label', `Увеличить фото: ${item.name}`);

  const img = document.createElement('img');
  img.className = 'product-photo';
  img.src = item.image;
  img.alt = item.name;
  img.loading = 'lazy';
  img.addEventListener('error', () => {
    btn.replaceWith(document.createRange().createContextualFragment(placeholderHtml));
  });

  const zoom = document.createElement('span');
  zoom.className = 'product-photo-zoom';
  zoom.setAttribute('aria-hidden', 'true');
  zoom.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>`;

  btn.appendChild(img);
  btn.appendChild(zoom);
  btn.addEventListener('click', () => openLightbox(item.image, item.name));

  wrap.innerHTML = '';
  wrap.appendChild(btn);
}

/* ─── Лайтбокс ───────────────────────────────────────────────── */
function openLightbox(src, alt) {
  const lb  = document.getElementById('imgLightbox');
  const img = document.getElementById('lightboxImg');
  if (!lb || !img) return;
  img.src = src;
  img.alt = alt || '';
  lb.hidden = false;
  document.body.style.overflow = 'hidden';
  document.addEventListener('keydown', _onLightboxKey);
}

function closeLightbox() {
  const lb = document.getElementById('imgLightbox');
  if (!lb) return;
  lb.hidden = true;
  document.body.style.overflow = '';
  document.removeEventListener('keydown', _onLightboxKey);
  const img = document.getElementById('lightboxImg');
  if (img) img.src = '';
}

function _onLightboxKey(e) {
  if (e.key === 'Escape') closeLightbox();
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

/* ─── Цена крупно в buy-box ──────────────────────────────────── */
function renderPriceDisplay(item) {
  const el = document.getElementById('productPriceDisplay');
  if (!el) return;
  if (item.price === null) {
    el.innerHTML = `<span style="font-size:1rem;font-weight:500;color:#64748B">Цена по запросу</span>`;
  } else {
    el.innerHTML = `${fmtPrice(item.price)} <span style="font-size:1rem;font-weight:400;color:#64748B">₽/${escHtml(item.unit || 'т')}</span>`;
  }
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

  const stockCell = item.in_stock
    ? `<span class="badge badge--green">В наличии</span>`
    : `<span class="badge badge--gray">Под заказ</span>`;

  const rows = [
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
  const el  = document.getElementById('productPricing');
  const KZT = 5.5; // курс: 1 RUB = 5.5 KZT

  if (!el) return;

  /* Нет цены — заглушка */
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

  /* Режим «По штукам» — для unit='шт' (Р8, Р12, Р15, DIN 536) */
  if (item.unit === 'шт') {
    return renderPricingPerPiece(el, item, KZT);
  }

  const weightPerUnit = getWeightKg(item);               // кг на рельс 12.5 м (из каталога или таблицы ГОСТ)
  const hasWeight     = weightPerUnit && weightPerUnit > 0;
  const wpm           = hasWeight ? weightPerUnit / 12.5 : null; // кг/м
  const pricePerMeter = hasWeight ? (wpm / 1000) * item.price : null; // ₽/м

  /* Начальные значения */
  const initMeters   = 12.5;
  const initWeightKg = hasWeight ? Math.round(initMeters * wpm) : 0;
  const initCost     = hasWeight
    ? Math.round(initMeters * pricePerMeter)
    : item.price;

  /* HTML секций */
  const tabsHTML = hasWeight ? `
    <div class="calc-tabs" id="calcTabs">
      <button class="calc-tab active" data-tab="meters">По метражу</button>
      <button class="calc-tab" data-tab="weight">По весу</button>
    </div>` : '';

  const metersPanel = hasWeight ? `
    <div id="calcMetersPanel">
      <div class="calc-row">
        <label>Метраж, м</label>
        <input class="input calc-input" type="number" id="calcMeters" min="1" step="0.5" value="${initMeters}">
      </div>
      <div class="calc-hint" id="calcMetersHint">≈ ${initWeightKg} кг</div>
    </div>` : '';

  const weightPanel = hasWeight ? `
    <div id="calcWeightPanel" class="hidden">
      <div class="calc-row">
        <label>Вес, кг</label>
        <input class="input calc-input" type="number" id="calcWeightKg" min="1" step="10" value="${initWeightKg}">
      </div>
      <div class="calc-hint" id="calcWeightHint">≈ ${initMeters} м</div>
    </div>` : '';

  const tonsPanel = !hasWeight ? `
    <div id="calcTonsPanel">
      <div class="calc-row">
        <label>Количество, т</label>
        <input class="input calc-input" type="number" id="calcTons" min="0.1" step="0.1" value="1">
      </div>
    </div>` : '';

  el.innerHTML = `
    <div class="product-calc-inline">
      ${tabsHTML}
      ${metersPanel}
      ${weightPanel}
      ${tonsPanel}
      <div class="calc-total">
        <span class="calc-total-label">Стоимость</span>
        <div class="calc-total-right">
          <strong class="calc-total-value" id="calcResult">${fmtPrice(initCost)}</strong>
          <span id="calcCurr">₽</span>
          <div class="currency-toggle">
            <label class="currency-opt"><input type="radio" name="cr" value="RUB" checked><span>RUB</span></label>
            <label class="currency-opt"><input type="radio" name="cr" value="KZT"><span>KZT</span></label>
          </div>
        </div>
      </div>
    </div>`;

  /* Состояние */
  let costRub  = initCost;
  let currency = 'RUB';

  function updateDisplay() {
    const val = currency === 'KZT' ? Math.round(costRub * KZT) : costRub;
    document.getElementById('calcResult').textContent = fmtPrice(val);
    document.getElementById('calcCurr').textContent   = currency === 'KZT' ? '₸' : '₽';
  }

  /* Переключение вкладок */
  el.querySelectorAll('.calc-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      el.querySelectorAll('.calc-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const isMeters = tab.dataset.tab === 'meters';
      document.getElementById('calcMetersPanel')?.classList.toggle('hidden', !isMeters);
      document.getElementById('calcWeightPanel')?.classList.toggle('hidden', isMeters);
    });
  });

  /* Вкладка «По метражу» */
  if (hasWeight) {
    document.getElementById('calcMeters')?.addEventListener('input', e => {
      const m  = Math.max(0, parseFloat(e.target.value) || 0);
      const kg = Math.round(m * wpm);
      document.getElementById('calcMetersHint').textContent = `≈ ${kg} кг`;
      costRub = Math.round(m * pricePerMeter);
      updateDisplay();
    });

    /* Вкладка «По весу» */
    document.getElementById('calcWeightKg')?.addEventListener('input', e => {
      const kg = Math.max(0, parseFloat(e.target.value) || 0);
      const m  = Math.round((kg / wpm) * 10) / 10;
      document.getElementById('calcWeightHint').textContent = `≈ ${m} м`;
      costRub = Math.round((kg / 1000) * item.price);
      updateDisplay();
    });
  }

  /* Режим «По тоннам» (fallback без веса) */
  document.getElementById('calcTons')?.addEventListener('input', e => {
    const t = Math.max(0, parseFloat(e.target.value) || 0);
    costRub = Math.round(t * item.price);
    updateDisplay();
  });

  /* Переключатель валюты */
  el.querySelectorAll('input[name="cr"]').forEach(r => {
    r.addEventListener('change', () => { currency = r.value; updateDisplay(); });
  });
}

/* ─── Калькулятор для unit='шт' (поштучно или по весу) ───────── */
// Используется для рельсов с пословной ценой: Р8/Р12/Р15 и DIN 536 (А45-А150).
// Если weight_per_unit задан — показывает 2 вкладки «По штукам» / «По весу».
// Если нет — только «По штукам». Цена = qty × item.price.
function renderPricingPerPiece(el, item, KZT) {
  const lengthM   = item.length_m || null;        // м на штуку
  const weightKg  = item.weight_per_unit || null; // кг на штуку
  const hasWeight = !!(weightKg && weightKg > 0);
  const initQty   = 1;
  const initKg    = hasWeight ? Math.round(weightKg * initQty) : 0;
  const initCost  = item.price * initQty;

  function fmtNum(n) { return String(n).replace(/\.?0+$/, '') || '0'; }
  function hintForQty(qty) {
    const parts = [];
    if (lengthM)  parts.push(`${fmtNum((lengthM * qty).toFixed(1))} м`);
    if (weightKg) parts.push(`${Math.round(weightKg * qty)} кг`);
    return parts.length ? `≈ ${parts.join(', ')}` : '';
  }
  function hintForWeight(kg) {
    if (!hasWeight) return '';
    const qty = kg / weightKg;
    const parts = [`${fmtNum(qty.toFixed(2))} шт`];
    if (lengthM) parts.push(`${fmtNum((lengthM * qty).toFixed(1))} м`);
    return `≈ ${parts.join(', ')}`;
  }

  const tabsHTML = hasWeight ? `
    <div class="calc-tabs" id="calcTabs">
      <button class="calc-tab active" data-tab="pieces">По штукам</button>
      <button class="calc-tab" data-tab="weight">По весу</button>
    </div>` : '';

  const piecesPanel = `
    <div id="calcPiecesPanel">
      <div class="calc-row">
        <label>Количество, шт</label>
        <input class="input calc-input" type="number" id="calcQty" min="1" step="1" value="${initQty}">
      </div>
      ${(lengthM || weightKg) ? `<div class="calc-hint" id="calcQtyHint">${hintForQty(initQty)}</div>` : ''}
    </div>`;

  const weightPanel = hasWeight ? `
    <div id="calcWeightPanel" class="hidden">
      <div class="calc-row">
        <label>Вес, кг</label>
        <input class="input calc-input" type="number" id="calcWeightKg" min="1" step="10" value="${initKg}">
      </div>
      <div class="calc-hint" id="calcWeightHint">${hintForWeight(initKg)}</div>
    </div>` : '';

  el.innerHTML = `
    <div class="product-calc-inline">
      ${tabsHTML}
      ${piecesPanel}
      ${weightPanel}
      <div class="calc-total">
        <span class="calc-total-label">Стоимость</span>
        <div class="calc-total-right">
          <strong class="calc-total-value" id="calcResult">${fmtPrice(initCost)}</strong>
          <span id="calcCurr">₽</span>
          <div class="currency-toggle">
            <label class="currency-opt"><input type="radio" name="cr" value="RUB" checked><span>RUB</span></label>
            <label class="currency-opt"><input type="radio" name="cr" value="KZT"><span>KZT</span></label>
          </div>
        </div>
      </div>
    </div>`;

  let costRub  = initCost;
  let currency = 'RUB';

  function updateDisplay() {
    const val = currency === 'KZT' ? Math.round(costRub * KZT) : costRub;
    document.getElementById('calcResult').textContent = fmtPrice(val);
    document.getElementById('calcCurr').textContent   = currency === 'KZT' ? '₸' : '₽';
  }

  /* Переключение вкладок */
  el.querySelectorAll('.calc-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      el.querySelectorAll('.calc-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const isPieces = tab.dataset.tab === 'pieces';
      document.getElementById('calcPiecesPanel')?.classList.toggle('hidden', !isPieces);
      document.getElementById('calcWeightPanel')?.classList.toggle('hidden', isPieces);
    });
  });

  /* Вкладка «По штукам» */
  document.getElementById('calcQty').addEventListener('input', e => {
    const qty = Math.max(0, parseInt(e.target.value) || 0);
    costRub = qty * item.price;
    const hintEl = document.getElementById('calcQtyHint');
    if (hintEl) hintEl.textContent = hintForQty(qty);
    updateDisplay();
  });

  /* Вкладка «По весу» */
  if (hasWeight) {
    document.getElementById('calcWeightKg').addEventListener('input', e => {
      const kg = Math.max(0, parseFloat(e.target.value) || 0);
      const qty = kg / weightKg;
      costRub = Math.round(qty * item.price);
      document.getElementById('calcWeightHint').textContent = hintForWeight(kg);
      updateDisplay();
    });
  }

  /* Переключатель валюты */
  el.querySelectorAll('input[name="cr"]').forEach(r => {
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

  // 1. Таблица технических характеристик (specs)
  if (cd.specs && Object.keys(cd.specs).length > 0) {
    const sec  = document.getElementById('product-specs');
    const wrap = document.getElementById('enrichedSpecsWrap');
    if (sec && wrap) {
      wrap.innerHTML = `<table class="specs-table specs-table--compact"><tbody>` +
        Object.entries(cd.specs).map(([k, v]) => `<tr>
          <th class="specs-table__key">${escHtml(k)}</th>
          <td class="specs-table__val">${escHtml(String(v))}</td>
        </tr>`).join('') +
        `</tbody></table>`;
      sec.classList.remove('hidden');
    }
  }

  // 3. ГОСТ номер — добавляем строку со ссылками на docs.cntd.ru
  if (cd.gost) {
    const specsTable = document.getElementById('productSpecs');
    if (specsTable) {
      const linksHtml = cd.gost
        .split(/[,;]/)
        .map(g => g.trim())
        .filter(g => g.length > 3)
        .map(g => `<a href="https://docs.cntd.ru/search?text=${encodeURIComponent(g)}"
              target="_blank" rel="noopener noreferrer"
              class="gost-link">${escHtml(g)}</a>`)
        .join(', ');
      const tr = document.createElement('tr');
      tr.className = 'product-specs__row';
      tr.innerHTML = `<td class="product-specs__label">ГОСТ</td>
                      <td class="product-specs__value" id="productGost">${linksHtml}</td>`;
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
