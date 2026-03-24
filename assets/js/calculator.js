/* =============================================================
   Рельс-Комплект — Калькулятор тоннажа (calculator.js)
   Wizard из 3 шагов: рельсы → шпалы → результат
   ============================================================= */

'use strict';

/* ─── Константы ──────────────────────────────────────────────── */
const CART_KEY      = 'cart';
const RAIL_LENGTH_M = 12.5; // стандартная длина рельса в метрах

const RAIL_TYPES = {
  'Р50':   { kgPerM: 51.67, label: 'Р50'   },
  'Р65':   { kgPerM: 64.72, label: 'Р65'   },
  'Р75':   { kgPerM: 74.40, label: 'Р75'   },
  'КР70':  { kgPerM: 70.00, label: 'КР70'  },
  'КР80':  { kgPerM: 80.00, label: 'КР80'  },
  'КР100': { kgPerM: 100.00, label: 'КР100' },
  'КР120': { kgPerM: 120.00, label: 'КР120' },
};

/* ─── Состояние калькулятора ─────────────────────────────────── */
let catalog       = [];
let calcResult    = null; // результат последнего расчёта

/* ─── Точка входа ────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  catalog = await loadCatalog();
  bindNavButtons();
  bindResultActions();
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

/* ─── Навигация по шагам ─────────────────────────────────────── */
function bindNavButtons() {
  document.getElementById('step1Next').addEventListener('click', () => {
    if (validateStep1()) goToStep(2);
  });
  document.getElementById('step2Prev').addEventListener('click', () => goToStep(1));
  document.getElementById('step2Next').addEventListener('click', () => {
    calculate();
    goToStep(3);
  });
}

function goToStep(n) {
  [1, 2, 3].forEach(i => {
    const panel = document.getElementById(`wizardStep${i}`);
    if (panel) panel.hidden = (i !== n);
  });
  updateProgressBar(n);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updateProgressBar(activeStep) {
  [1, 2, 3].forEach(i => {
    const stepEl      = document.getElementById(`progressStep${i}`);
    const connectorEl = document.getElementById(`connector${i}`);

    stepEl.classList.remove('wizard__step--active', 'wizard__step--done');
    stepEl.removeAttribute('aria-current');

    if (i < activeStep) {
      stepEl.classList.add('wizard__step--done');
    } else if (i === activeStep) {
      stepEl.classList.add('wizard__step--active');
      stepEl.setAttribute('aria-current', 'step');
    }

    if (connectorEl) {
      connectorEl.classList.toggle('wizard__connector--done', i < activeStep);
    }
  });
}

/* ─── Валидация шага 1 ───────────────────────────────────────── */
function validateStep1() {
  let valid = true;

  const railType = document.getElementById('railType');
  const railErr  = document.getElementById('railTypeError');
  if (!railType.value) {
    railErr.textContent = 'Выберите тип рельса';
    railErr.hidden = false;
    railType.setAttribute('aria-invalid', 'true');
    valid = false;
  } else {
    railErr.hidden = true;
    railType.removeAttribute('aria-invalid');
  }

  const trackLength = document.getElementById('trackLength');
  const lenErr      = document.getElementById('trackLengthError');
  const len = parseFloat(trackLength.value);
  if (!trackLength.value || isNaN(len) || len < 1) {
    lenErr.textContent = 'Введите длину пути (минимум 1 м)';
    lenErr.hidden = false;
    trackLength.setAttribute('aria-invalid', 'true');
    valid = false;
  } else {
    lenErr.hidden = true;
    trackLength.removeAttribute('aria-invalid');
  }

  return valid;
}

/* ─── Основной расчёт ────────────────────────────────────────── */
function calculate() {
  /* --- Шаг 1: параметры рельсов --- */
  const railTypeVal  = document.getElementById('railType').value;
  const trackLenM    = parseFloat(document.getElementById('trackLength').value);
  const threads      = parseInt(
    document.querySelector('input[name="threadCount"]:checked').value
  );
  const railData     = RAIL_TYPES[railTypeVal];

  const railCount    = Math.ceil(trackLenM / RAIL_LENGTH_M) * threads;
  const weightT      = railCount * RAIL_LENGTH_M * railData.kgPerM / 1000;

  // Ищем минимальную цену по subcategory из catalog.json
  const railPrice    = findRailPrice(railTypeVal);

  /* --- Шаг 2: шпалы и скрепления --- */
  const sleeperSel   = document.getElementById('sleeperType');
  const sleeperOpt   = sleeperSel.options[sleeperSel.selectedIndex];
  const sleeperType  = sleeperSel.value;
  const sleeperPrice = parseFloat(sleeperOpt.getAttribute('data-price'));

  const spacingSel   = document.getElementById('sleeperSpacing');
  const perMeter     = parseFloat(spacingSel.value);

  const fastenType   = document.getElementById('fastenType').value;

  let sleeperCount = 0;
  let sleeperCost  = 0;
  if (sleeperType !== 'none') {
    sleeperCount = Math.ceil(trackLenM * perMeter);
    sleeperCost  = sleeperCount * sleeperPrice;
  }

  /* --- Скрепления (ориентировочно) --- */
  const fastenInfo = getFastenInfo(fastenType, railCount, threads);

  /* --- Сохраняем результат --- */
  calcResult = {
    railTypeVal,
    railLabel:    railData.label,
    kgPerM:       railData.kgPerM,
    trackLenM,
    threads,
    railCount,
    weightT,
    railPrice,     // null если не найдена
    sleeperType,
    sleeperLabel:  sleeperOpt.text,
    sleeperCount,
    sleeperPrice,
    sleeperCost,
    fastenType,
    fastenLabel:   fastenInfo.label,
    fastenQty:     fastenInfo.qty,
    fastenUnit:    fastenInfo.unit,
    spacingMm:     Math.round(1000 / perMeter),
  };

  renderResult(calcResult);
}

/* ─── Поиск цены рельса в каталоге ──────────────────────────── */
function findRailPrice(railType) {
  const matches = catalog.filter(item => {
    if (item.price === null) return false;
    const name = (item.name || '').toLowerCase();
    const sub  = (item.subcategory || '').toLowerCase();
    const key  = railType.toLowerCase();
    return name.includes(key) || sub.includes(key);
  });
  if (matches.length === 0) return null;
  return Math.min(...matches.map(i => i.price));
}

/* ─── Данные по скреплениям ──────────────────────────────────── */
function getFastenInfo(type, railCount, threads) {
  if (type === 'none') return { label: 'Не требуется', qty: 0, unit: '' };
  // ~4 костыля / 4 клеммы на стык рельса с каждой стороны
  const qty = type === 'kostyl'
    ? railCount * 8
    : railCount * 4;
  const label = type === 'kostyl' ? 'Костыльное скрепление' : 'Клеммное скрепление';
  const unit  = 'шт';
  return { label, qty, unit };
}

/* ─── Рендер результата ──────────────────────────────────────── */
function renderResult(r) {
  renderSummaryCards(r);
  renderTable(r);
}

function renderSummaryCards(r) {
  const weightFormatted = r.weightT < 10
    ? r.weightT.toFixed(2)
    : Math.round(r.weightT).toLocaleString('ru-RU');

  const railCostHtml = r.railPrice !== null
    ? `<strong>${fmtPrice(r.weightT * r.railPrice)}&nbsp;₽</strong>`
    : `<strong>По запросу</strong>`;

  document.getElementById('calcSummaryCards').innerHTML = `
    <div class="calc-result__cards">
      <div class="calc-result__card">
        <div class="calc-result__card-value">${weightFormatted}&nbsp;т</div>
        <div class="calc-result__card-label">Тоннаж рельсов</div>
      </div>
      <div class="calc-result__card">
        <div class="calc-result__card-value">${r.railCount.toLocaleString('ru-RU')}&nbsp;шт</div>
        <div class="calc-result__card-label">Рельсов (${RAIL_LENGTH_M}&nbsp;м)</div>
      </div>
      ${r.sleeperCount > 0 ? `
      <div class="calc-result__card">
        <div class="calc-result__card-value">${r.sleeperCount.toLocaleString('ru-RU')}&nbsp;шт</div>
        <div class="calc-result__card-label">Шпал (шаг ${r.spacingMm}&nbsp;мм)</div>
      </div>` : ''}
    </div>`;
}

function renderTable(r) {
  const rows  = [];
  let   total = 0;
  let   hasPriceOnRequest = false;

  /* --- Рельсы --- */
  const railCostPerT = r.railPrice;
  const railTotal    = railCostPerT !== null ? r.weightT * railCostPerT : null;
  if (railTotal !== null) total += railTotal;
  else hasPriceOnRequest = true;

  rows.push({
    name:     `Рельс ${r.railLabel} (${r.kgPerM}&nbsp;кг/м)`,
    qty:      r.weightT < 10 ? r.weightT.toFixed(2) : Math.round(r.weightT),
    unit:     'т',
    priceStr: railCostPerT !== null ? `${fmtPrice(railCostPerT)}&nbsp;₽/т` : '—',
    totalStr: railTotal   !== null ? `${fmtPrice(railTotal)}&nbsp;₽`     : '<em>По запросу</em>',
  });

  /* --- Шпалы --- */
  if (r.sleeperType !== 'none' && r.sleeperCount > 0) {
    total += r.sleeperCost;
    rows.push({
      name:     r.sleeperLabel,
      qty:      r.sleeperCount.toLocaleString('ru-RU'),
      unit:     'шт',
      priceStr: `${fmtPrice(r.sleeperPrice)}&nbsp;₽/шт`,
      totalStr: `${fmtPrice(r.sleeperCost)}&nbsp;₽`,
    });
  }

  /* --- Скрепления --- */
  if (r.fastenType !== 'none' && r.fastenQty > 0) {
    rows.push({
      name:     r.fastenLabel,
      qty:      r.fastenQty.toLocaleString('ru-RU'),
      unit:     r.fastenUnit,
      priceStr: '—',
      totalStr: '<em>По запросу</em>',
    });
    hasPriceOnRequest = true;
  }

  /* --- Таблица --- */
  document.getElementById('calcTableBody').innerHTML = rows.map(row => `
    <tr>
      <td>${row.name}</td>
      <td>${row.qty}</td>
      <td>${row.unit}</td>
      <td>${row.priceStr}</td>
      <td>${row.totalStr}</td>
    </tr>`).join('');

  /* --- Итог --- */
  const totalLabel = hasPriceOnRequest
    ? 'Итого (без позиций по запросу)'
    : 'Итого';
  document.getElementById('calcTableFoot').innerHTML = `
    <tr class="calc-result__total-row">
      <td colspan="4"><strong>${totalLabel}</strong></td>
      <td><strong>${fmtPrice(total)}&nbsp;₽</strong></td>
    </tr>`;

  /* --- Сноска --- */
  const noteEl = document.getElementById('calcPriceNote');
  noteEl.classList.toggle('hidden', !hasPriceOnRequest);
}

/* ─── Кнопки результата ──────────────────────────────────────── */
function bindResultActions() {
  document.getElementById('btnAddToCart').addEventListener('click', handleAddToCart);
  document.getElementById('btnDownloadPdf').addEventListener('click', handleDownloadPdf);
  document.getElementById('btnReset').addEventListener('click', handleReset);
}

function handleAddToCart() {
  if (!calcResult) return;

  const cart = getCart();

  // Рельсы
  const railId = `rail-${calcResult.railTypeVal}`;
  removeFromCart(cart, railId);
  cart.push({
    id:    railId,
    name:  `Рельс ${calcResult.railLabel} — ${calcResult.weightT < 10 ? calcResult.weightT.toFixed(2) : Math.round(calcResult.weightT)} т`,
    price: calcResult.railPrice,
    unit:  'т',
    qty:   calcResult.weightT < 10
      ? parseFloat(calcResult.weightT.toFixed(2))
      : Math.round(calcResult.weightT),
  });

  // Шпалы
  if (calcResult.sleeperType !== 'none' && calcResult.sleeperCount > 0) {
    const sleeperId = `sleeper-${calcResult.sleeperType}`;
    removeFromCart(cart, sleeperId);
    cart.push({
      id:    sleeperId,
      name:  calcResult.sleeperLabel,
      price: calcResult.sleeperPrice,
      unit:  'шт',
      qty:   calcResult.sleeperCount,
    });
  }

  // Скрепления
  if (calcResult.fastenType !== 'none' && calcResult.fastenQty > 0) {
    const fastenId = `fasten-${calcResult.fastenType}`;
    removeFromCart(cart, fastenId);
    cart.push({
      id:    fastenId,
      name:  calcResult.fastenLabel,
      price: null,
      unit:  calcResult.fastenUnit,
      qty:   calcResult.fastenQty,
    });
  }

  saveCart(cart);
  updateCartBadge();
  window.location.href = 'order.html';
}

function handleDownloadPdf() {
  if (!calcResult) return;

  const { jsPDF } = window.jspdf;
  if (!jsPDF) {
    window.RK?.showToast('Библиотека PDF не загружена', 'error');
    return;
  }

  const doc  = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const now  = new Date();
  const date = now.toLocaleDateString('ru-RU');
  let   y    = 20;

  /* --- Заголовок --- */
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(16);
  doc.text('Specifikaciya Rels-Komplekt', 20, y);
  y += 8;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  doc.text(`Data: ${date}`, 20, y);
  y += 5;
  doc.text(`Put: ${calcResult.trackLenM} m, ${calcResult.threads} nit(i), rel's ${calcResult.railLabel}`, 20, y);
  y += 10;

  /* --- Шапка таблицы --- */
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  const colX = [20, 100, 125, 150, 175];
  const headers = ['Naimenovanie', 'Kol-vo', 'Ed.', 'Cena', 'Summa'];
  headers.forEach((h, i) => doc.text(h, colX[i], y));
  y += 2;
  doc.setLineWidth(0.3);
  doc.line(20, y, 190, y);
  y += 5;

  /* --- Строки таблицы --- */
  doc.setFont('helvetica', 'normal');

  const railQty = calcResult.weightT < 10
    ? calcResult.weightT.toFixed(2)
    : String(Math.round(calcResult.weightT));

  const tableRows = [
    [
      `Rels ${calcResult.railLabel} (${calcResult.kgPerM} kg/m)`,
      railQty,
      't',
      calcResult.railPrice !== null ? `${fmtPricePlain(calcResult.railPrice)} r/t` : '-',
      calcResult.railPrice !== null
        ? `${fmtPricePlain(calcResult.weightT * calcResult.railPrice)} r`
        : 'Po zaprosu',
    ],
  ];

  if (calcResult.sleeperType !== 'none' && calcResult.sleeperCount > 0) {
    tableRows.push([
      calcResult.sleeperLabel,
      String(calcResult.sleeperCount),
      'sht',
      `${fmtPricePlain(calcResult.sleeperPrice)} r`,
      `${fmtPricePlain(calcResult.sleeperCost)} r`,
    ]);
  }

  if (calcResult.fastenType !== 'none' && calcResult.fastenQty > 0) {
    tableRows.push([
      calcResult.fastenLabel,
      String(calcResult.fastenQty),
      calcResult.fastenUnit,
      '-',
      'Po zaprosu',
    ]);
  }

  tableRows.forEach(row => {
    // Перенос длинного текста в первом столбце
    const lines = doc.splitTextToSize(row[0], 75);
    doc.text(lines, colX[0], y);
    doc.text(row[1], colX[1], y);
    doc.text(row[2], colX[2], y);
    doc.text(row[3], colX[3], y);
    doc.text(row[4], colX[4], y);
    y += lines.length > 1 ? lines.length * 5 + 2 : 7;
  });

  doc.line(20, y, 190, y);
  y += 5;

  /* --- Итог --- */
  let totalVal = 0;
  if (calcResult.railPrice !== null) totalVal += calcResult.weightT * calcResult.railPrice;
  totalVal += calcResult.sleeperCost;

  doc.setFont('helvetica', 'bold');
  doc.text('Itogo:', colX[3], y);
  doc.text(`${fmtPricePlain(totalVal)} r`, colX[4], y);
  y += 10;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.text('* Ceny orientirovochnye. Tochhnaya stoimost\' utochnyaetsya u menedzhera.', 20, y);

  doc.save(`specifikaciya-rels-komplekt-${date.replace(/\./g, '-')}.pdf`);
}

function handleReset() {
  calcResult = null;
  // Сбрасываем поля шага 1
  document.getElementById('railType').value     = '';
  document.getElementById('trackLength').value  = '';
  document.querySelector('input[name="threadCount"][value="2"]').checked = true;
  // Сбрасываем поля шага 2
  document.getElementById('sleeperType').selectedIndex    = 0;
  document.getElementById('sleeperSpacing').selectedIndex = 0;
  document.getElementById('fastenType').selectedIndex     = 0;
  // Очищаем результат
  document.getElementById('calcSummaryCards').innerHTML = '';
  document.getElementById('calcTableBody').innerHTML    = '';
  document.getElementById('calcTableFoot').innerHTML    = '';
  document.getElementById('calcPriceNote').classList.add('hidden');
  // Возвращаемся к шагу 1
  goToStep(1);
}

/* ─── Корзина ────────────────────────────────────────────────── */
function getCart() {
  try { return JSON.parse(localStorage.getItem(CART_KEY) || '[]'); }
  catch { return []; }
}

function saveCart(cart) {
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
}

function removeFromCart(cart, id) {
  const idx = cart.findIndex(i => i.id === id);
  if (idx !== -1) cart.splice(idx, 1);
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

// Для PDF — без спецсимволов
function fmtPricePlain(n) {
  return Math.round(n).toLocaleString('ru-RU');
}
