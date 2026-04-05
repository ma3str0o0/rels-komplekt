/* =============================================================
   Рельс-Комплект — Каталог
   Загрузка данных, фильтрация, рендер карточек, корзина
   ============================================================= */

'use strict';

/* ─── Константы ──────────────────────────────────────────────── */
const PAGE_SIZE = 24;

/* ─── Активный фильтр категорий ──────────────────────────────── */
// type: 'all' | 'category' | 'multi-category' | 'subcategory'
let activeFilter = { type: 'all' };

/* ─── Состояние сортировки ────────────────────────────────────── */
let sortField = 'condition'; // 'condition' | 'price'
let sortDir   = 'asc';      // 'asc' | 'desc'

// Числовой вес состояния для сортировки (новый → первый)
const CONDITION_WEIGHT = { 'new': 0, 'storage': 1, 'used': 2, 'unknown': 3 };

/* ─── Состояние фильтров ─────────────────────────────────────── */
const state = {
  all:          [],          // все позиции из JSON
  filtered:     [],          // результат после фильтров
  search:       '',
  priceFilter:  'all',       // 'all' | 'priced'
  page:         1,           // текущая страница пагинации
};

/* ─── Ссылки на DOM-элементы ─────────────────────────────────── */
const dom = {};

/* ─── Точка входа ────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  cacheDom();
  await loadCatalog();
  initCategoryFilter();
  applyFilters();
  bindEvents();
  updateCartBadge();
});

/* ─── Кэш DOM ────────────────────────────────────────────────── */
function cacheDom() {
  dom.grid            = document.getElementById('catalogGrid');
  dom.loading         = document.getElementById('catalogLoading');
  dom.emptyState      = document.getElementById('emptyState');
  dom.resultCount     = document.getElementById('resultCount');
  dom.mobileCount     = document.getElementById('mobileResultCount');
  dom.drawerCount     = document.getElementById('drawerResultCount');
  dom.searchInput     = document.getElementById('searchInput');
  dom.resetBtn        = document.getElementById('resetFilters');
  dom.resetBtn2       = document.getElementById('resetFilters2');
  dom.activeFiltersCount = document.getElementById('activeFiltersCount');

  // Мобильный drawer
  dom.sidebar         = document.getElementById('catalogSidebar');
  dom.filterOverlay   = document.getElementById('filterOverlay');
  dom.openFiltersBtn  = document.getElementById('openFiltersBtn');
  dom.closeSidebar    = document.getElementById('closeSidebar');
  dom.applyFilters    = document.getElementById('applyFilters');

  // Пагинация
  dom.pagination      = document.getElementById('catalogPagination');

  // Корзина
  dom.cartBadge       = document.getElementById('cartBadge');
}

/* ─── Загрузка данных ────────────────────────────────────────── */
async function loadCatalog() {
  try {
    const res  = await fetch('data/catalog.json');
    const data = await res.json();
    state.all      = data;
    state.filtered = data;
  } catch (err) {
    console.error('Ошибка загрузки каталога:', err);
    showError();
  }
}

function showError() {
  if (dom.loading) dom.loading.innerHTML = '<p style="color:var(--color-error); padding: var(--space-xl);">Ошибка загрузки данных. Пожалуйста, обновите страницу.</p>';
}

/* ─── Сброс визуального состояния дерева категорий ──────────── */
function resetCategoryUI() {
  document.querySelectorAll('.cat-tree__cat, .cat-tree__sub')
    .forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.cat-tree__subs')
    .forEach(ul => { ul.hidden = true; });
  document.querySelectorAll('.cat-tree__arrow')
    .forEach(a => a.classList.remove('open'));
}

/* ─── Проверка соответствия товара активному фильтру ─────────── */
function filterItem(item) {
  switch (activeFilter.type) {
    case 'all':            return true;
    case 'category':       return item.category === activeFilter.value;
    case 'multi-category': return activeFilter.value.includes(item.category);
    case 'subcategory':    return item.subcategory === activeFilter.value;
    default:               return true;
  }
}

/* ─── Инициализация дерева категорий ─────────────────────────── */
function initCategoryFilter() {
  // Обработчики кнопок верхнего уровня
  document.querySelectorAll('.cat-tree__cat').forEach(btn => {
    btn.addEventListener('click', () => {
      const isActive = btn.classList.contains('active');
      resetCategoryUI();

      if (isActive || btn.dataset.cat === '') {
        // Сброс на «Все категории»
        activeFilter = { type: 'all' };
        document.querySelector('.cat-tree__cat[data-cat=""]').classList.add('active');
      } else if (btn.dataset.cats) {
        // Мультикатегория (Шпалы, узкоколейные и т.д.)
        const cats = btn.dataset.cats.split('|');
        activeFilter = { type: 'multi-category', value: cats };
        btn.classList.add('active');
        const subs = btn.closest('li').querySelector('.cat-tree__subs');
        if (subs) { subs.hidden = false; btn.querySelector('.cat-tree__arrow')?.classList.add('open'); }
      } else {
        // Обычная одиночная категория
        activeFilter = { type: 'category', value: btn.dataset.cat };
        btn.classList.add('active');
        const subs = btn.closest('li').querySelector('.cat-tree__subs');
        if (subs) { subs.hidden = false; btn.querySelector('.cat-tree__arrow')?.classList.add('open'); }
      }

      state.page = 1;
      applyFilters();
    });
  });

  // Обработчики подкатегорий
  document.querySelectorAll('.cat-tree__sub').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.cat-tree__sub').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      if (btn.dataset.subType === 'category') {
        // Шпалы, Крепёж и т.д.: фильтр по item.category
        activeFilter = { type: 'category', value: btn.dataset.sub };
      } else {
        // Рельсы Р65, КР 70: фильтр по item.subcategory
        activeFilter = { type: 'subcategory', value: btn.dataset.sub };
      }

      state.page = 1;
      applyFilters();
    });
  });

  // Обработка URL-параметра ?cat= при загрузке
  const catParam = new URLSearchParams(location.search).get('cat');
  if (catParam) {
    const decoded = decodeURIComponent(catParam);
    const btn = document.querySelector(`.cat-tree__cat[data-cat="${CSS.escape(decoded)}"]`);
    if (btn) {
      resetCategoryUI();
      btn.classList.add('active');
      activeFilter = { type: 'category', value: decoded };
      const subs = btn.closest('li').querySelector('.cat-tree__subs');
      if (subs) { subs.hidden = false; btn.querySelector('.cat-tree__arrow')?.classList.add('open'); }
    }
  } else {
    // По умолчанию — «Все категории» активна
    document.querySelector('.cat-tree__cat[data-cat=""]')?.classList.add('active');
  }
}

/* ─── Определение состояния товара по названию ───────────────── */
function getCondition(name) {
  if (/новы[йе]|ГОСТ/i.test(name))    return 'new';
  if (/хранени[яе]/i.test(name))       return 'storage';
  if (/б\/у|старогодн/i.test(name))    return 'used';
  return 'unknown';
}

/* ─── Сортировка массива товаров ─────────────────────────────── */
function sortItems(items) {
  return [...items].sort((a, b) => {
    if (sortField === 'condition') {
      const wa = CONDITION_WEIGHT[getCondition(a.name)];
      const wb = CONDITION_WEIGHT[getCondition(b.name)];
      return sortDir === 'asc' ? wa - wb : wb - wa;
    }
    if (sortField === 'price') {
      const pa = a.price ?? -1;
      const pb = b.price ?? -1;
      // asc = дорогой первым (high→low), desc = дешёвый первым
      return sortDir === 'asc' ? pb - pa : pa - pb;
    }
    return 0;
  });
}

/* ─── HTML заголовка с кнопкой сортировки ────────────────────── */
function _sortThHtml(field, label, cssClass) {
  const isActive = sortField === field;
  const cls = ['sort-btn', isActive ? 'active' : '', isActive ? `sort-${sortDir}` : '']
    .filter(Boolean).join(' ');
  return `<th class="${cssClass}">
    <button class="${cls}" data-sort="${field}">
      ${label}
      <span class="sort-icon">
        <svg width="10" height="12" viewBox="0 0 10 12" fill="none">
          <path class="sort-up"   d="M5 1 L9 5 H1Z"/>
          <path class="sort-down" d="M5 11 L9 7 H1Z"/>
        </svg>
      </span>
    </button>
  </th>`;
}

/* ─── Применение фильтров ────────────────────────────────────── */
function applyFilters() {
  const q = state.search.trim().toLowerCase();

  state.filtered = state.all.filter(item => {
    // Поиск по названию
    if (q && !item.name.toLowerCase().includes(q)) return false;

    // Фильтр по категории/подкатегории
    if (!filterItem(item)) return false;

    // Фильтр по наличию цены
    if (state.priceFilter === 'priced' && item.price === null) return false;

    return true;
  });

  state.page = 1;  // при изменении фильтров — всегда на первую страницу
  renderCards();
  updateCounts();
  updateActiveFiltersIndicator();
}

/* ─── Рендер строк таблицы ───────────────────────────────────── */
function renderCards() {
  if (dom.loading) {
    dom.loading.classList.add('hidden');
  }

  if (state.filtered.length === 0) {
    dom.grid.innerHTML = '';
    dom.emptyState.classList.remove('hidden');
    if (dom.pagination) dom.pagination.innerHTML = '';
    return;
  }

  dom.emptyState.classList.add('hidden');

  // Сортировка → пагинация
  const sorted     = sortItems(state.filtered);
  const start      = (state.page - 1) * PAGE_SIZE;
  const pageItems  = sorted.slice(start, start + PAGE_SIZE);

  // Таблица со строками товаров
  dom.grid.innerHTML = `
    <table class="catalog-table">
      <thead>
        <tr>
          <th>Наименование</th>
          <th>Подкатегория</th>
          ${_sortThHtml('condition', 'Состояние', 'col-condition')}
          ${_sortThHtml('price',     'Цена',      'col-price')}
          <th></th>
        </tr>
      </thead>
      <tbody id="catalogBody">
        ${pageItems.map(item => rowHTML(item)).join('')}
      </tbody>
    </table>`;

  // Вешаем обработчики "В заявку" после вставки HTML
  dom.grid.querySelectorAll('[data-action="add-to-cart"]').forEach(btn => {
    btn.addEventListener('click', e => {
      e.preventDefault();
      e.stopPropagation();
      addToCart({
        id:    btn.dataset.id,
        name:  btn.dataset.name,
        price: btn.dataset.price !== '' ? Number(btn.dataset.price) : null,
        unit:  btn.dataset.unit || 'т',
        qty:   1,
      });
    });
  });

  renderPagination();
}

/* ─── Пагинация ──────────────────────────────────────────────── */
function renderPagination() {
  if (!dom.pagination) return;

  const total = Math.ceil(state.filtered.length / PAGE_SIZE);

  // Если всё помещается на одной странице — прячем пагинацию
  if (total <= 1) {
    dom.pagination.innerHTML = '';
    return;
  }

  const cur = state.page;

  // Вычисляем набор номеров страниц для отображения
  // Всегда показываем: первую, последнюю, текущую и ±1 от неё
  const pages = new Set([1, total, cur, cur - 1, cur + 1]);
  const sorted = [...pages]
    .filter(p => p >= 1 && p <= total)
    .sort((a, b) => a - b);

  // Строим HTML кнопок, вставляя «…» на разрывах
  let html = '';

  // Кнопка «Предыдущая»
  html += `<button
    class="pagination__btn"
    data-page="${cur - 1}"
    ${cur === 1 ? 'disabled' : ''}
    aria-label="Предыдущая страница"
  >
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 18 9 12 15 6"/></svg>
    <span class="pagination__label">Предыдущая</span>
  </button>`;

  let prev = 0;
  for (const p of sorted) {
    if (p - prev > 1) {
      // Разрыв — вставляем многоточие
      html += `<span class="pagination__ellipsis" aria-hidden="true">…</span>`;
    }
    html += `<button
      class="pagination__btn${p === cur ? ' active' : ''}"
      data-page="${p}"
      aria-label="Страница ${p}"
      ${p === cur ? 'aria-current="page"' : ''}
    >${p}</button>`;
    prev = p;
  }

  // Кнопка «Следующая»
  html += `<button
    class="pagination__btn"
    data-page="${cur + 1}"
    ${cur === total ? 'disabled' : ''}
    aria-label="Следующая страница"
  >
    <span class="pagination__label">Следующая</span>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="9 18 15 12 9 6"/></svg>
  </button>`;

  dom.pagination.innerHTML = html;

  // Обработчики кликов по кнопкам пагинации
  dom.pagination.querySelectorAll('button[data-page]').forEach(btn => {
    btn.addEventListener('click', () => {
      const p = Number(btn.dataset.page);
      if (p < 1 || p > total || p === state.page) return;
      state.page = p;
      renderCards();
      scrollToGrid();
    });
  });
}

/* ─── Скролл к началу сетки ──────────────────────────────────── */
function scrollToGrid() {
  const offset = parseInt(
    getComputedStyle(document.documentElement).getPropertyValue('--header-height') || '72'
  );
  const top = dom.grid.getBoundingClientRect().top + window.scrollY - offset - 16;
  window.scrollTo({ top, behavior: 'smooth' });
}

/* ─── HTML строки таблицы товара ─────────────────────────────── */
function rowHTML(item) {
  const priceHtml = item.price !== null
    ? `${item.price.toLocaleString('ru-RU')}&nbsp;₽/т`
    : `<span class="text-muted">По запросу</span>`;

  // Определяем badge состояния по словам в названии
  const nameLower = item.name.toLowerCase();
  let stateBadge = '';
  if (/новый|новые|гост/.test(nameLower)) {
    stateBadge = `<span class="badge badge--green">Новый</span>`;
  } else if (/хранения/.test(nameLower)) {
    stateBadge = `<span class="badge badge--orange">С хранения</span>`;
  } else if (/б\/у|старогодн/.test(nameLower)) {
    stateBadge = `<span class="badge">Б/У</span>`;
  }

  const inCart = isInCart(item.id);
  const href   = `product.html?id=${encodeURIComponent(item.id)}`;

  return `
    <tr data-href="${href}" data-id="${escapeHtml(item.id)}" style="cursor:pointer" onclick="window.location.href=this.dataset.href">
      <td>${escapeHtml(item.name)}</td>
      <td><span class="text-muted">${escapeHtml(item.subcategory || '')}</span></td>
      <td>${stateBadge}</td>
      <td>${priceHtml}</td>
      <td>
        <button
          class="btn btn-sm ${inCart ? 'btn-accent' : 'btn-primary'}"
          data-action="add-to-cart"
          data-id="${escapeHtml(item.id)}"
          data-name="${escapeHtml(item.name)}"
          data-price="${item.price !== null ? item.price : ''}"
          data-unit="${escapeHtml(item.unit || 'т')}"
          aria-pressed="${inCart}"
        >${inCart ? 'В заявке' : 'В заявку'}</button>
      </td>
    </tr>`;
}

/* ─── Обновление счётчиков ────────────────────────────────────── */
function updateCounts() {
  const n    = state.filtered.length;
  const text = `Найдено: ${n} ${pluralItems(n)}`;

  if (dom.resultCount)   dom.resultCount.textContent  = text;
  if (dom.mobileCount)   dom.mobileCount.textContent  = text;
  if (dom.drawerCount)   dom.drawerCount.textContent   = `(${n})`;
}

/* ─── Индикатор активных фильтров ─────────────────────────────── */
function updateActiveFiltersIndicator() {
  const count = (activeFilter.type !== 'all' ? 1 : 0)
    + (state.search ? 1 : 0)
    + (state.priceFilter !== 'all' ? 1 : 0);

  if (!dom.activeFiltersCount) return;
  dom.activeFiltersCount.textContent = count;
  dom.activeFiltersCount.classList.toggle('hidden', count === 0);
}

/* ─── Привязка событий ───────────────────────────────────────── */
function bindEvents() {

  // Сортировка по колонкам — делегирование, т.к. таблица перегенерируется
  dom.grid.addEventListener('click', e => {
    const btn = e.target.closest('.sort-btn');
    if (!btn) return;
    const field = btn.dataset.sort;
    if (sortField === field) {
      sortDir = sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      sortField = field;
      sortDir   = 'asc';
    }
    state.page = 1;
    renderCards();
  });

  // Поиск в реальном времени
  dom.searchInput?.addEventListener('input', e => {
    state.search = e.target.value;
    applyFilters();
  });

  // Радио-кнопки "Наличие цены"
  document.querySelectorAll('input[name="priceFilter"]').forEach(radio => {
    radio.addEventListener('change', e => {
      state.priceFilter = e.target.value;
      applyFilters();
    });
  });

  // Сброс фильтров
  [dom.resetBtn, dom.resetBtn2].forEach(btn => {
    btn?.addEventListener('click', resetFilters);
  });

  // Мобильный drawer: открытие
  dom.openFiltersBtn?.addEventListener('click', openDrawer);

  // Мобильный drawer: закрытие
  dom.closeSidebar?.addEventListener('click', closeDrawer);
  dom.filterOverlay?.addEventListener('click', closeDrawer);
  dom.applyFilters?.addEventListener('click', closeDrawer);

  // Закрытие по Escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && dom.sidebar?.classList.contains('open')) {
      closeDrawer();
    }
  });
}

/* ─── Сброс фильтров ─────────────────────────────────────────── */
function resetFilters() {
  state.search      = '';
  state.priceFilter = 'all';
  activeFilter      = { type: 'all' };

  // Сброс UI
  if (dom.searchInput) dom.searchInput.value = '';
  document.querySelectorAll('input[name="priceFilter"]')
    .forEach(r => { r.checked = r.value === 'all'; });
  resetCategoryUI();
  document.querySelector('.cat-tree__cat[data-cat=""]')?.classList.add('active');

  applyFilters();
}

/* ─── Мобильный drawer ───────────────────────────────────────── */
function openDrawer() {
  dom.sidebar?.classList.add('open');
  dom.filterOverlay?.classList.add('open');
  document.body.style.overflow = 'hidden';
  dom.openFiltersBtn?.setAttribute('aria-expanded', 'true');
}

function closeDrawer() {
  dom.sidebar?.classList.remove('open');
  dom.filterOverlay?.classList.remove('open');
  document.body.style.overflow = '';
  dom.openFiltersBtn?.setAttribute('aria-expanded', 'false');
}

/* ─── Корзина (localStorage) ─────────────────────────────────── */
const CART_KEY = 'cart';

function getCart() {
  try { return JSON.parse(localStorage.getItem(CART_KEY) || '[]'); }
  catch { return []; }
}

function isInCart(id) {
  return getCart().some(item => item.id === id);
}

function addToCart(item) {
  const cart = getCart();
  // Ищем строку таблицы по data-id
  const row = dom.grid.querySelector(`tr[data-id="${item.id}"]`);
  const btn = row?.querySelector('[data-action="add-to-cart"]');

  if (isInCart(item.id)) {
    // Товар уже в корзине — убираем (toggle)
    const updated = cart.filter(i => i.id !== item.id);
    localStorage.setItem(CART_KEY, JSON.stringify(updated));

    if (btn) {
      btn.classList.remove('btn-accent');
      btn.classList.add('btn-primary');
      btn.setAttribute('aria-pressed', 'false');
      btn.textContent = 'В заявку';
    }

    updateCartBadge();
    window.RK?.showToast(`«${item.name}» убран из заявки`, 'info');
    return;
  }

  // Товара нет — добавляем
  cart.push({ id: item.id, name: item.name, price: item.price, unit: item.unit, qty: 1 });
  localStorage.setItem(CART_KEY, JSON.stringify(cart));

  if (btn) {
    btn.classList.remove('btn-primary');
    btn.classList.add('btn-accent');
    btn.setAttribute('aria-pressed', 'true');
    btn.textContent = 'В заявке';
  }

  updateCartBadge();
  window.RK?.showToast(`«${item.name}» добавлен в заявку`, 'success');
}

function updateCartBadge() {
  const count = getCart().length;
  if (!dom.cartBadge) return;
  dom.cartBadge.textContent = count;
  dom.cartBadge.classList.toggle('hidden', count === 0);
}

/* ─── Утилиты ────────────────────────────────────────────────── */
function formatPrice(price) {
  return new Intl.NumberFormat('ru-RU').format(price);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function pluralItems(n) {
  const mod10  = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return 'позиция';
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return 'позиции';
  return 'позиций';
}
