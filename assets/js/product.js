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

/* ─── Мини-калькулятор / блок "цена по запросу" ─────────────── */
function renderPricing(item) {
  const el = document.getElementById('productPricing');

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

  el.innerHTML = `
    <div class="product-calculator">
      <h3 class="product-calculator__title">Расчёт стоимости</h3>
      <div class="product-calculator__row">
        <label class="form-label" for="calcQty">Количество (тонн)</label>
        <input class="input product-calculator__input" type="number" id="calcQty"
               min="1" step="1" value="1" placeholder="Введите количество">
      </div>
      <div class="product-calculator__result">
        Ориентировочная стоимость:
        <strong id="calcTotal">${fmtPrice(item.price)}&nbsp;₽</strong>
      </div>
    </div>`;

  document.getElementById('calcQty').addEventListener('input', e => {
    const qty = Math.max(1, parseFloat(e.target.value) || 1);
    document.getElementById('calcTotal').innerHTML = `${fmtPrice(item.price * qty)}&nbsp;₽`;
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
