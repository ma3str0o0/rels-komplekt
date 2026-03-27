/* =============================================================
   Рельс-Комплект — Страница заявки (order.js)
   Читает order_items из localStorage, отрисовывает таблицу,
   позволяет менять кол-во и удалять позиции.
   ============================================================= */

'use strict';

const ORDER_KEY = 'cart';   /* должен совпадать с catalog.js */

/* ─── Точка входа ────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  render();
  updateCartBadge();
});

/* ─── Чтение / запись localStorage ──────────────────────────── */
function getItems() {
  try { return JSON.parse(localStorage.getItem(ORDER_KEY) || '[]'); }
  catch { return []; }
}

function saveItems(items) {
  localStorage.setItem(ORDER_KEY, JSON.stringify(items));
}

/* ─── Главный рендер ─────────────────────────────────────────── */
function render() {
  const items = getItems();
  const wrap  = document.getElementById('orderContent');
  if (!wrap) return;

  if (items.length === 0) {
    wrap.innerHTML = emptyStateHTML();
    wrap.querySelector('#goToCatalog')
        ?.addEventListener('click', () => { window.location.href = 'catalog.html'; });
    return;
  }

  wrap.innerHTML = tableHTML(items);
  bindTableEvents(items);
}

/* ─── HTML таблицы ───────────────────────────────────────────── */
function tableHTML(items) {
  const rows = items.map((item, idx) => rowHTML(item, idx + 1)).join('');

  const { totalQty, totalSum, hasRequest } = calcTotals(items);

  const totalSumText = totalSum > 0
    ? fmtPrice(totalSum) + ' ₽'
    : '—';

  const requestNote = hasRequest
    ? '<span class="order-note">* часть позиций — по запросу</span>'
    : '';

  return `
    <div class="table-wrapper">
      <table class="table order-table" aria-label="Список позиций заявки">
        <thead>
          <tr>
            <th style="width:36px">#</th>
            <th>Наименование</th>
            <th style="width:90px; text-align:center">Кол-во</th>
            <th style="width:60px">Ед.</th>
            <th style="width:130px; text-align:right">Цена/ед., ₽</th>
            <th style="width:140px; text-align:right">Сумма, ₽</th>
            <th style="width:40px"></th>
          </tr>
        </thead>
        <tbody id="orderTableBody">
          ${rows}
        </tbody>
        <tfoot>
          <tr class="order-totals">
            <td colspan="2" class="order-totals__label">Итого</td>
            <td class="order-totals__qty" style="text-align:center" id="totalQty">${fmtNum(totalQty)}</td>
            <td>т</td>
            <td></td>
            <td class="order-totals__sum" style="text-align:right" id="totalSum">${totalSumText}</td>
            <td></td>
          </tr>
        </tfoot>
      </table>
    </div>
    ${requestNote}
    <div class="order-actions">
      <a href="catalog.html" class="btn btn-secondary">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
        Продолжить выбор
      </a>
      <button class="btn btn-accent" id="submitOrderBtn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        Отправить заявку
      </button>
    </div>`;
}

/* ─── HTML одной строки таблицы ──────────────────────────────── */
function rowHTML(item, num) {
  const priceCell = item.price !== null
    ? `<td style="text-align:right">${fmtPrice(item.price)}</td>`
    : `<td style="text-align:right; color:var(--color-text-muted); font-style:italic">По запросу</td>`;

  const sumCell = item.price !== null
    ? `<td class="order-row-sum" style="text-align:right; font-weight:600">${fmtPrice(item.price * item.qty)}</td>`
    : `<td style="text-align:right; color:var(--color-text-muted)">—</td>`;

  return `
    <tr data-id="${escHtml(item.id)}">
      <td class="order-row-num">${num}</td>
      <td class="order-row-name">${escHtml(item.name)}</td>
      <td style="text-align:center">
        <input
          class="input order-qty-input"
          type="number"
          value="${item.qty}"
          min="1"
          max="99999"
          step="1"
          data-id="${escHtml(item.id)}"
          aria-label="Количество для ${escHtml(item.name)}"
          style="width:70px; text-align:center; padding:6px 8px;"
        >
      </td>
      <td>${escHtml(item.unit || 'т')}</td>
      ${priceCell}
      ${sumCell}
      <td>
        <button
          class="btn-icon order-remove-btn"
          data-id="${escHtml(item.id)}"
          aria-label="Удалить ${escHtml(item.name)}"
          title="Удалить из заявки"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>
        </button>
      </td>
    </tr>`;
}

/* ─── HTML пустой заявки ─────────────────────────────────────── */
function emptyStateHTML() {
  return `
    <div class="empty-state">
      <div class="empty-state__icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/>
          <line x1="3" y1="6" x2="21" y2="6"/>
          <path d="M16 10a4 4 0 01-8 0"/>
        </svg>
      </div>
      <h3 class="empty-state__title">Заявка пуста</h3>
      <p class="empty-state__text">Добавьте товары из каталога, чтобы сформировать заявку</p>
      <button class="btn btn-primary" id="goToCatalog">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
        Перейти в каталог
      </button>
    </div>`;
}

/* ─── Привязка событий таблицы ───────────────────────────────── */
function bindTableEvents(items) {
  /* Изменение кол-ва */
  document.querySelectorAll('.order-qty-input').forEach(input => {
    input.addEventListener('change', () => {
      const id  = input.dataset.id;
      let   qty = parseInt(input.value, 10);

      if (isNaN(qty) || qty < 1) { qty = 1; input.value = 1; }
      if (qty > 99999)            { qty = 99999; input.value = 99999; }

      updateQty(id, qty);
    });
  });

  /* Удаление позиции */
  document.querySelectorAll('.order-remove-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      removeItem(btn.dataset.id);
    });
  });

  /* Отправить заявку */
  document.getElementById('submitOrderBtn')?.addEventListener('click', () => {
    window.RK?.openModal(document.getElementById('requestModal'));
  });
}

/* ─── Обновление кол-ва ──────────────────────────────────────── */
function updateQty(id, qty) {
  const items = getItems();
  const item  = items.find(i => i.id === id);
  if (!item) return;

  item.qty = qty;
  saveItems(items);

  /* Обновляем ячейку суммы в строке без полного перерендера */
  const row    = document.querySelector(`tr[data-id="${CSS.escape(id)}"]`);
  const sumTd  = row?.querySelector('.order-row-sum');
  if (sumTd && item.price !== null) {
    sumTd.textContent = fmtPrice(item.price * qty);
  }

  updateTotals(items);
}

/* ─── Удаление позиции ───────────────────────────────────────── */
function removeItem(id) {
  const items    = getItems().filter(i => i.id !== id);
  saveItems(items);

  if (items.length === 0) {
    render(); // перерисовать пустое состояние
    return;
  }

  /* Убираем строку из DOM и обновляем нумерацию */
  const row = document.querySelector(`tr[data-id="${CSS.escape(id)}"]`);
  row?.remove();

  document.querySelectorAll('#orderTableBody tr').forEach((tr, idx) => {
    const numCell = tr.querySelector('.order-row-num');
    if (numCell) numCell.textContent = idx + 1;
  });

  updateTotals(items);
}

/* ─── Пересчёт итоговой строки ───────────────────────────────── */
function updateTotals(items) {
  const { totalQty, totalSum, hasRequest } = calcTotals(items);

  const qtyEl = document.getElementById('totalQty');
  const sumEl = document.getElementById('totalSum');

  if (qtyEl) qtyEl.textContent = fmtNum(totalQty);
  if (sumEl) {
    sumEl.textContent = totalSum > 0
      ? fmtPrice(totalSum) + ' ₽'
      : '—';
  }

  /* Показываем / скрываем примечание о "по запросу" */
  let note = document.querySelector('.order-note');
  if (hasRequest && !note) {
    note = document.createElement('span');
    note.className = 'order-note';
    note.textContent = '* часть позиций — по запросу';
    document.querySelector('.table-wrapper')?.after(note);
  } else if (!hasRequest && note) {
    note.remove();
  }
}

/* ─── Расчёт итогов ──────────────────────────────────────────── */
function calcTotals(items) {
  let totalQty = 0;
  let totalSum = 0;
  let hasRequest = false;

  items.forEach(item => {
    totalQty += Number(item.qty) || 0;
    if (item.price !== null) {
      totalSum += item.price * (Number(item.qty) || 0);
    } else {
      hasRequest = true;
    }
  });

  return { totalQty, totalSum, hasRequest };
}

/* ─── Счётчик в шапке ────────────────────────────────────────── */
function updateCartBadge() {
  const badge = document.getElementById('cartBadge');
  if (!badge) return;
  const count = getItems().length;
  badge.textContent = count;
  badge.classList.toggle('hidden', count === 0);
}

/* ─── Утилиты ────────────────────────────────────────────────── */
function fmtPrice(n) {
  return new Intl.NumberFormat('ru-RU').format(Math.round(n));
}

function fmtNum(n) {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 3 }).format(n);
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
