/* =============================================================
   Рельс-Комплект — Калькулятор тоннажа (calculator.js)
   Wizard из 3 шагов: рельсы → шпалы → результат
   ============================================================= */

'use strict';

/* ─── Утилита экранирования HTML ─────────────────────────────── */
function escHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/* ─── Константы ──────────────────────────────────────────────── */
const CART_KEY      = 'cart';
const RAIL_LENGTH_M = 12.5; // дефолтная мерная длина рельса (fallback если у типа не задано)

/* RAIL_TYPES — fallback-данные, если в catalog.json нет подходящей позиции.
   ИСТОЧНИК ПРАВДЫ — catalog.json: см. resolveRailData() ниже. Калькулятор
   подставляет kgPerM/lengthM/price из catalog для конкретного типа
   (предпочтительно condition='new', availability='in_stock').
   Hardcoded значения нужны только когда позиции в каталоге нет
   (например, временно сняты с продажи целиком). */
const RAIL_TYPES = {
  'Р8':    { kgPerM: 8.0,    label: 'Р8',    lengthM: 6    },
  'Р50':   { kgPerM: 51.67,  label: 'Р50',   lengthM: 12.5 },
  'Р65':   { kgPerM: 64.72,  label: 'Р65',   lengthM: 12.5 },
  'Р75':   { kgPerM: 74.41,  label: 'Р75',   lengthM: 12.5 },
  'КР70':  { kgPerM: 51.67,  label: 'КР70',  lengthM: 12   },
  'КР80':  { kgPerM: 60.00,  label: 'КР80',  lengthM: 12   },
  'КР100': { kgPerM: 87.00,  label: 'КР100', lengthM: 12   },
  'КР120': { kgPerM: 115.67, label: 'КР120', lengthM: 12   },
  'КР140': { kgPerM: 161.02, label: 'КР140', lengthM: 11   },
};

/* Поиск канонических данных рельса в каталоге.
   allowUsed=false → только condition='new'.
   allowUsed=true  → любой condition, берём самый дешёвый вариант.
   Возвращает {kgPerM, lengthM, price, condition} или null. */
function resolveRailData(railType, allowUsed = false) {
  // Регекс с unicode-aware boundary через lookbehind/lookahead (JS \b
   // не работает с кириллицей). «КР80» матчит «кр80», «кр 80» — но НЕ
  // «кр800» и НЕ «р8» внутри «кр80».
  const m = /^([а-яёa-z]+)(\d+)$/i.exec(railType);
  let typeRe;
  if (m) {
    const letters = m[1].replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    typeRe = new RegExp(`(?<![а-яёa-z])${letters}\\s*${m[2]}(?![а-яёa-z0-9])`, 'i');
  } else {
    const esc = railType.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    typeRe = new RegExp(`(?<![а-яёa-z0-9])${esc}(?![а-яёa-z0-9])`, 'i');
  }
  // Кандидаты: имя или подкатегория содержит тип, не «снят с продажи»,
  // не накладка/подкладка (anchored на "Рельс" в начале имени).
  const cands = catalog.filter(it => {
    if (it.availability === 'not_for_sale') return false;
    const name = (it.name || '').toLowerCase();
    const sub  = (it.subcategory || '').toLowerCase();
    if (!name.startsWith('рельс')) return false;          // только сами рельсы
    return typeRe.test(name) || typeRe.test(sub);
  });
  if (cands.length === 0) return null;

  /* Если б/у НЕ разрешены — оставляем только новые. */
  let pool = allowUsed ? cands : cands.filter(c => c.condition === 'new');
  if (pool.length === 0) return null;

  /* Среди pool — берём в наличии с заполненными вес+длина. */
  const ready = pool.filter(c => c.availability === 'in_stock' &&
                                 c.weight_per_unit && c.length_m);
  let picked;
  if (ready.length > 0) {
    // С ценой → берём с минимальной ценой (выгоднее клиенту).
    // Без цены → берём первый просто чтобы иметь вес/длину.
    const priced = ready.filter(c => c.price !== null);
    picked = priced.length
      ? priced.reduce((a, b) => (a.price <= b.price ? a : b))
      : ready[0];
  } else {
    // Fallback: хоть какая-то запись с весом/длиной.
    picked = pool.find(c => c.weight_per_unit && c.length_m);
    if (!picked) return null;
  }

  return {
    kgPerM:    picked.weight_per_unit / picked.length_m,
    lengthM:   picked.length_m,
    price:     picked.price,
    condition: picked.condition,
  };
}

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
  const allowUsed    = !!document.getElementById('allowUsed')?.checked;
  // Источник правды: catalog.json. Если позиции нет — fallback на канонические
  // значения из RAIL_TYPES (Р75 в каталоге пока нет, КР140 редкий и т.д.).
  const fallback     = RAIL_TYPES[railTypeVal];
  const resolved     = resolveRailData(railTypeVal, allowUsed);
  const kgPerM       = resolved?.kgPerM   ?? fallback.kgPerM;
  const railLengthM  = resolved?.lengthM  ?? fallback.lengthM ?? RAIL_LENGTH_M;
  const railPrice    = resolved?.price    ?? null;
  const railCondition= resolved?.condition ?? null;

  const railCount    = Math.ceil(trackLenM / railLengthM) * threads;
  const weightT      = railCount * railLengthM * kgPerM / 1000;

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
    railLabel:    fallback.label,
    kgPerM,
    railLengthM,
    trackLenM,
    threads,
    railCount,
    weightT,
    railPrice,        // null если не найдена в каталоге
    railCondition,    // 'new'|'storage'|'restored'|'used'|null — для UI
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
  if (window.rkTrack) {
    window.rkTrack('calculator_use', {
      extra: { rail_type: railTypeVal, total_tons: Math.round(calcResult.weightT * 100) / 100 },
    });
  }
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
        <div class="calc-result__card-label">Рельсов (${r.railLengthM}&nbsp;м)</div>
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
    name:     `Рельс ${r.railLabel} (${r.kgPerM.toFixed(2)}\u00a0кг/м)${(({'new':' — новые','storage':' — с хранения','restored':' — восстановленные','used':' — б/у'})[r.railCondition]||'')}`,
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
      <td>${escHtml(row.name)}</td>
      <td>${escHtml(row.qty)}</td>
      <td>${escHtml(row.unit)}</td>
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
  document.getElementById('btnSendTelegram').addEventListener('click', openTgModal);
  document.getElementById('btnSendEmail').addEventListener('click', openEmailModal);
  document.getElementById('btnReset').addEventListener('click', handleReset);

  /* Управление модальным окном Telegram */
  document.getElementById('tgModalClose').addEventListener('click', closeTgModal);
  document.getElementById('tgModalCancel').addEventListener('click', closeTgModal);
  document.getElementById('tgModal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeTgModal();
  });
  document.getElementById('tgModalForm').addEventListener('submit', handleSendTelegram);

  /* Управление модальным окном email */
  document.getElementById('emailModalClose').addEventListener('click', closeEmailModal);
  document.getElementById('emailModalCancel').addEventListener('click', closeEmailModal);
  document.getElementById('emailModal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeEmailModal();
  });
  document.getElementById('emailModalForm').addEventListener('submit', handleSendEmail);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { closeTgModal(); closeEmailModal(); }
  });
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

/* ─── Telegram-модальное окно ────────────────────────────────── */
function openTgModal() {
  if (!calcResult) return;
  document.getElementById('tgModal').classList.add('open');
  requestAnimationFrame(() => document.getElementById('tgContact').focus());
}

function closeTgModal() {
  document.getElementById('tgModal').classList.remove('open');
  document.getElementById('tgModalForm').reset();
  document.getElementById('tgContactError').hidden = true;
  document.getElementById('tgContact').removeAttribute('aria-invalid');
  setTgSubmitLoading(false);
}

function setTgSubmitLoading(loading) {
  const btn = document.getElementById('tgModalSubmit');
  btn.disabled = loading;
  btn.innerHTML = loading
    ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="animation:spin .8s linear infinite"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.18-4.61"/></svg> Отправка...`
    : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Отправить`;
}

async function handleSendTelegram(e) {
  e.preventDefault();

  /* novalidate на форме отключает нативную проверку required — проверяем согласие явно */
  const consent = e.target.querySelector('[name="consent"]');
  if (consent && !consent.checked) {
    window.RK?.showToast('Подтвердите согласие на обработку персональных данных', 'error');
    consent.focus();
    return;
  }

  const contact = document.getElementById('tgContact').value.trim();
  const errEl   = document.getElementById('tgContactError');

  /* Валидация: username (@...) или телефон (цифры/+/пробелы/скобки/дефис) */
  const isUsername = /^@\w{3,}$/.test(contact);
  const isPhone    = /^[\d\s\+\(\)\-]{7,}$/.test(contact);
  if (!contact || (!isUsername && !isPhone)) {
    errEl.textContent = 'Введите @username или номер телефона';
    errEl.hidden = false;
    document.getElementById('tgContact').setAttribute('aria-invalid', 'true');
    return;
  }
  errEl.hidden = true;
  document.getElementById('tgContact').removeAttribute('aria-invalid');

  setTgSubmitLoading(true);

  /* ─── Отправка через /api/lead ────────────────────────────── */
  const r = calcResult;
  const railQty = r.weightT < 10 ? r.weightT.toFixed(2) : Math.round(r.weightT);

  const items = [];
  items.push({
    name:  `Рельс ${r.railLabel}`,
    qty:   parseFloat(r.weightT.toFixed(3)),
    unit:  'т',
    price: r.railPrice,
  });
  if (r.sleeperType !== 'none' && r.sleeperCount > 0) {
    items.push({ name: r.sleeperLabel, qty: r.sleeperCount, unit: 'шт', price: null });
  }
  if (r.fastenType !== 'none' && r.fastenQty > 0) {
    items.push({ name: r.fastenLabel, qty: r.fastenQty, unit: r.fastenUnit, price: null });
  }

  try {
    const res = await fetch('/api/lead', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name:    'Расчёт из калькулятора',
        contact: contact,
        source:  'calculator',
        message: `Путь: ${r.trackLenM} м, ${r.threads} нит., рельс ${r.railLabel} (${r.kgPerM} кг/м)`,
        items,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    closeTgModal();
    window.RK?.showToast('Запрос принят. Менеджер свяжется с вами.', 'success');
    if (window.rkTrack) window.rkTrack('form_submit', { extra: { form: 'calculator_tg' } });
  } catch (err) {
    console.error('[calc] Ошибка отправки:', err);
    window.RK?.showToast('Ошибка отправки. Позвоните нам напрямую.', 'error');
  } finally {
    setTgSubmitLoading(false);
  }
}

/* ─── Email-модальное окно ───────────────────────────────────── */
function openEmailModal() {
  if (!calcResult) return;
  const overlay = document.getElementById('emailModal');
  overlay.classList.add('open');
  // Фокус на первое поле
  requestAnimationFrame(() => document.getElementById('emailTo').focus());
}

function closeEmailModal() {
  const overlay = document.getElementById('emailModal');
  overlay.classList.remove('open');
  // Сбрасываем форму и ошибки
  document.getElementById('emailModalForm').reset();
  document.getElementById('emailToError').hidden = true;
  document.getElementById('emailTo').removeAttribute('aria-invalid');
  setEmailSubmitLoading(false);
}

function setEmailSubmitLoading(loading) {
  const btn = document.getElementById('emailModalSubmit');
  btn.disabled = loading;
  btn.innerHTML = loading
    ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="animation:spin .8s linear infinite"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.18-4.61"/></svg> Отправка...`
    : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Отправить`;
}

async function handleSendEmail(e) {
  e.preventDefault();

  /* novalidate на форме отключает нативную проверку required — проверяем согласие явно */
  const consent = e.target.querySelector('[name="consent"]');
  if (consent && !consent.checked) {
    window.RK?.showToast('Подтвердите согласие на обработку персональных данных', 'error');
    consent.focus();
    return;
  }

  const emailTo = document.getElementById('emailTo').value.trim();
  const errEl   = document.getElementById('emailToError');

  /* Валидация email */
  if (!emailTo || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailTo)) {
    errEl.textContent = 'Введите корректный email';
    errEl.hidden = false;
    document.getElementById('emailTo').setAttribute('aria-invalid', 'true');
    return;
  }
  errEl.hidden = true;
  document.getElementById('emailTo').removeAttribute('aria-invalid');

  const name    = document.getElementById('emailName').value.trim();
  const comment = document.getElementById('emailComment').value.trim();
  const r       = calcResult;

  /* Формируем данные для шаблона */
  const railQty = r.weightT < 10 ? r.weightT.toFixed(2) : Math.round(r.weightT);
  const templateParams = {
    to_email:     emailTo,
    sender_name:  name || 'Клиент',
    comment:      comment || '—',
    spec_date:    new Date().toLocaleDateString('ru-RU'),
    rail_type:    r.railLabel,
    track_length: `${r.trackLenM} м`,
    threads:      String(r.threads),
    rail_qty:     `${railQty} т`,
    rail_count:   `${r.railCount} шт`,
    sleeper_info: r.sleeperType !== 'none' && r.sleeperCount > 0
      ? `${r.sleeperLabel} — ${r.sleeperCount} шт`
      : 'Без шпал',
    fasten_info:  r.fastenType !== 'none' && r.fastenQty > 0
      ? `${r.fastenLabel} — ${r.fastenQty} ${r.fastenUnit}`
      : 'Без скреплений',
    total_price:  r.railPrice !== null
      ? `${fmtPrice((r.weightT * r.railPrice) + r.sleeperCost)} ₽`
      : 'По запросу',
  };

  setEmailSubmitLoading(true);

  /* ─── Отправка через EmailJS ──────────────────────────────── */
  try {
    await emailjs.send(
      EMAILJS_SERVICE_ID,
      EMAILJS_TEMPLATE_ID,
      templateParams,
      EMAILJS_PUBLIC_KEY
    );
    closeEmailModal();
    window.RK?.showToast(`Спецификация отправлена на ${emailTo}`, 'success');
  } catch (err) {
    console.error('EmailJS error:', err);
    setEmailSubmitLoading(false);
    window.RK?.showToast('Ошибка отправки. Попробуйте позже.', 'error');
  }
}

function handleDownloadPdf() {
  if (!calcResult) return;

  const r   = calcResult;
  const now = new Date();
  const dateStr = now.toLocaleDateString('ru-RU');
  const specNo  = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0'),
  ].join('') + '-' + [
    String(now.getHours()).padStart(2, '0'),
    String(now.getMinutes()).padStart(2, '0'),
  ].join('');

  /* --- Строки таблицы --- */
  const railQty   = r.weightT < 10 ? r.weightT.toFixed(2) : Math.round(r.weightT);
  const railTotal = r.railPrice !== null
    ? `${fmtPrice(r.weightT * r.railPrice)}&thinsp;₽`
    : '<em>По запросу</em>';
  const railPriceStr = r.railPrice !== null
    ? `${fmtPrice(r.railPrice)}&thinsp;₽/т`
    : '—';

  let tableRows = `
      <tr>
        <td>Рельс ${r.railLabel} (${r.kgPerM}&thinsp;кг/м)</td>
        <td class="ps-num">${railQty}</td>
        <td>т</td>
        <td class="ps-num">${railPriceStr}</td>
        <td class="ps-num">${railTotal}</td>
      </tr>`;

  if (r.sleeperType !== 'none' && r.sleeperCount > 0) {
    tableRows += `
      <tr>
        <td>${r.sleeperLabel}</td>
        <td class="ps-num">${r.sleeperCount.toLocaleString('ru-RU')}</td>
        <td>шт</td>
        <td class="ps-num">${fmtPrice(r.sleeperPrice)}&thinsp;₽/шт</td>
        <td class="ps-num">${fmtPrice(r.sleeperCost)}&thinsp;₽</td>
      </tr>`;
  }

  if (r.fastenType !== 'none' && r.fastenQty > 0) {
    tableRows += `
      <tr>
        <td>${r.fastenLabel}</td>
        <td class="ps-num">${r.fastenQty.toLocaleString('ru-RU')}</td>
        <td>${r.fastenUnit}</td>
        <td class="ps-num">—</td>
        <td class="ps-num"><em>По запросу</em></td>
      </tr>`;
  }

  /* --- Итог --- */
  let totalVal = 0;
  if (r.railPrice !== null) totalVal += r.weightT * r.railPrice;
  totalVal += r.sleeperCost;
  const hasPriceOnRequest = r.railPrice === null ||
    (r.fastenType !== 'none' && r.fastenQty > 0);
  const totalLabel = hasPriceOnRequest
    ? 'Итого (без позиций по запросу)'
    : 'Итого';

  /* --- Карточки --- */
  const weightFormatted = r.weightT < 10
    ? r.weightT.toFixed(2)
    : Math.round(r.weightT).toLocaleString('ru-RU');

  let summaryCards = `
      <div class="ps-card">
        <div class="ps-card-val">${weightFormatted}&thinsp;т</div>
        <div class="ps-card-lbl">Тоннаж рельсов</div>
      </div>
      <div class="ps-card">
        <div class="ps-card-val">${r.railCount.toLocaleString('ru-RU')}&thinsp;шт</div>
        <div class="ps-card-lbl">Рельсов (${r.railLengthM}&thinsp;м)</div>
      </div>`;
  if (r.sleeperCount > 0) {
    summaryCards += `
      <div class="ps-card">
        <div class="ps-card-val">${r.sleeperCount.toLocaleString('ru-RU')}&thinsp;шт</div>
        <div class="ps-card-lbl">Шпал (шаг ${r.spacingMm}&thinsp;мм)</div>
      </div>`;
  }

  /* --- Логотип SVG (рельс + две шпалы) --- */
  const logoSvg = `<svg width="44" height="44" viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <rect width="44" height="44" rx="6" fill="rgba(255,255,255,0.15)"/>
    <rect x="10" y="8" width="5" height="28" rx="2" fill="white"/>
    <rect x="29" y="8" width="5" height="28" rx="2" fill="white"/>
    <rect x="10" y="14" width="24" height="4" rx="1" fill="white"/>
    <rect x="10" y="26" width="24" height="4" rx="1" fill="white"/>
  </svg>`;

  /* --- Полный HTML спецификации --- */
  const specHtml = `
<div id="rkPrintSpec">
  <style>
    /* Скрываем страницу, показываем только спецификацию при печати */
    @media print {
      body * { visibility: hidden; }
      #rkPrintSpec, #rkPrintSpec * { visibility: visible; }
      #rkPrintSpec {
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        display: block !important;
      }
      @page { size: A4 portrait; margin: 10mm 12mm; }
    }

    #rkPrintSpec {
      display: none;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 10pt;
      color: #111;
      background: #fff;
    }

    /* Шапка */
    #rkPrintSpec .ps-header {
      background: #1A56A0;
      color: #fff;
      padding: 14px 20px;
      display: flex;
      align-items: center;
      gap: 16px;
    }
    #rkPrintSpec .ps-header-logo { flex-shrink: 0; }
    #rkPrintSpec .ps-header-name {
      font-size: 18pt;
      font-weight: 700;
      letter-spacing: 0.02em;
      line-height: 1.1;
    }
    #rkPrintSpec .ps-header-sub {
      font-size: 9pt;
      opacity: 0.85;
      margin-top: 2px;
    }
    #rkPrintSpec .ps-header-contacts {
      margin-left: auto;
      text-align: right;
      font-size: 9pt;
      line-height: 1.6;
      opacity: 0.9;
    }

    /* Блок заголовка спецификации */
    #rkPrintSpec .ps-title-block {
      padding: 14px 20px 10px;
      border-bottom: 1px solid #d0d8e8;
    }
    #rkPrintSpec .ps-spec-no {
      font-size: 14pt;
      font-weight: 700;
      color: #1A56A0;
      margin-bottom: 6px;
    }
    #rkPrintSpec .ps-meta {
      font-size: 9pt;
      color: #444;
      line-height: 1.7;
    }

    /* Карточки итогов */
    #rkPrintSpec .ps-cards {
      display: flex;
      gap: 10px;
      padding: 12px 20px;
      border-bottom: 1px solid #d0d8e8;
    }
    #rkPrintSpec .ps-card {
      flex: 1;
      background: #EBF2FB;
      border-radius: 6px;
      padding: 10px 14px;
      text-align: center;
    }
    #rkPrintSpec .ps-card-val {
      font-size: 15pt;
      font-weight: 700;
      color: #1A56A0;
      line-height: 1.1;
    }
    #rkPrintSpec .ps-card-lbl {
      font-size: 8pt;
      color: #555;
      margin-top: 3px;
    }

    /* Таблица */
    #rkPrintSpec .ps-table-wrap { padding: 12px 20px 0; }
    #rkPrintSpec table {
      width: 100%;
      border-collapse: collapse;
      font-size: 10pt;
    }
    #rkPrintSpec thead th {
      background: #E8F0F8;
      color: #1A56A0;
      font-weight: 700;
      padding: 7px 8px;
      border: 1px solid #c5d5e8;
      text-align: left;
      font-size: 9pt;
    }
    #rkPrintSpec tbody td {
      padding: 6px 8px;
      border: 1px solid #dde6f0;
      vertical-align: middle;
    }
    #rkPrintSpec tbody tr:nth-child(even) td { background: #F5F8FC; }
    #rkPrintSpec .ps-num { text-align: right; white-space: nowrap; }
    #rkPrintSpec tfoot td {
      padding: 8px;
      border: 1px solid #c5d5e8;
      font-weight: 700;
      border-top: 2px solid #1A56A0;
    }
    #rkPrintSpec tfoot .ps-num { text-align: right; }

    /* Сноска */
    #rkPrintSpec .ps-note {
      padding: 8px 20px 0;
      font-size: 8pt;
      color: #666;
      font-style: italic;
    }

    /* Футер */
    #rkPrintSpec .ps-footer {
      margin-top: 14px;
      padding: 12px 20px;
      border-top: 2px solid #1A56A0;
      font-size: 9pt;
      color: #333;
      line-height: 1.7;
    }
    #rkPrintSpec .ps-footer-title {
      font-weight: 700;
      color: #1A56A0;
      margin-bottom: 4px;
    }
  </style>

  <!-- Шапка -->
  <div class="ps-header">
    <div class="ps-header-logo">${logoSvg}</div>
    <div>
      <div class="ps-header-name">РЕЛЬС-КОМПЛЕКТ</div>
      <div class="ps-header-sub">Оптовые поставки рельсовых материалов</div>
    </div>
    <div class="ps-header-contacts">
      +7 (343) 237-23-33 · +7 (967) 639-63-33<br>
      ooorku@mail.ru · rels-komplekt.ru
    </div>
  </div>

  <!-- Заголовок спецификации -->
  <div class="ps-title-block">
    <div class="ps-spec-no">СПЕЦИФИКАЦИЯ № ${specNo}</div>
    <div class="ps-meta">
      Дата:&nbsp;${dateStr}&nbsp;&nbsp;·&nbsp;&nbsp;
      Длина пути:&nbsp;${r.trackLenM}&nbsp;м&nbsp;&nbsp;·&nbsp;&nbsp;
      Нитей:&nbsp;${r.threads}&nbsp;&nbsp;·&nbsp;&nbsp;
      Рельс:&nbsp;${r.railLabel} (${r.kgPerM}&nbsp;кг/м)
    </div>
  </div>

  <!-- Карточки итогов -->
  <div class="ps-cards">${summaryCards}</div>

  <!-- Таблица -->
  <div class="ps-table-wrap">
    <table>
      <thead>
        <tr>
          <th style="width:40%">Наименование</th>
          <th class="ps-num" style="width:12%">Количество</th>
          <th style="width:6%">Ед.</th>
          <th class="ps-num" style="width:20%">Цена</th>
          <th class="ps-num" style="width:22%">Сумма</th>
        </tr>
      </thead>
      <tbody>${tableRows}</tbody>
      <tfoot>
        <tr>
          <td colspan="4">${totalLabel}</td>
          <td class="ps-num">${fmtPrice(totalVal)}&thinsp;₽</td>
        </tr>
      </tfoot>
    </table>
  </div>

  <!-- Сноска -->
  <div class="ps-note">
    * Цены ориентировочные. Точная стоимость уточняется у менеджера.
    Расчёт выполнен автоматически на основе введённых параметров.
  </div>

  <!-- Футер -->
  <div class="ps-footer">
    <div class="ps-footer-title">Для оформления заказа свяжитесь с нами:</div>
    Тел.: +7 (343) 237-23-33 · +7 (967) 639-63-33&nbsp;&nbsp;·&nbsp;&nbsp;
    E-mail: ooorku@mail.ru&nbsp;&nbsp;·&nbsp;&nbsp;
    Сайт: rels-komplekt.ru
  </div>
</div>`;

  /* Вставляем и печатаем */
  document.body.insertAdjacentHTML('beforeend', specHtml);
  window.print();

  /* Удаляем после закрытия диалога печати */
  window.addEventListener('afterprint', function cleanup() {
    document.getElementById('rkPrintSpec')?.remove();
    window.removeEventListener('afterprint', cleanup);
  });
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

