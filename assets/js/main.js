/* =============================================================
   Рельс-Комплект — Общий JavaScript
   ============================================================= */

'use strict';

/* ─── EmailJS ─────────────────────────────────────────────────── */
const EMAILJS_SERVICE_ID  = 'service_vc2oz9j';
const EMAILJS_TEMPLATE_ID = 'template_e7f1ke6';
const EMAILJS_PUBLIC_KEY  = 'FZzMmOJ5mTIGrPV3j';

/* ─── Catalog helpers — длина и вес per piece ──────────────────
   Источник правды: catalog.json fields length_m + weight_per_unit.
   До WS-CALC-REFACTOR эти данные дублировались в product.js
   (RAIL_WEIGHT_KG), order.js (та же таблица со stale values),
   calculator.js (RAIL_TYPES). После refactor — единый catalog read. */
const DEFAULT_RAIL_LENGTH_M = 12.5;

function getLengthM(p) {
  if (p && p.length_m != null) return p.length_m;
  console.warn(
    '[catalog-drift] product',
    p && p.id, p && p.name,
    'has no length_m; using fallback', DEFAULT_RAIL_LENGTH_M, 'm'
  );
  return DEFAULT_RAIL_LENGTH_M;
}

function getWeightPerUnit(p) {
  return (p && p.weight_per_unit != null) ? p.weight_per_unit : null;
}

/* ─── Инициализация при загрузке DOM ─────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  // Инициализируем EmailJS если CDN загружен
  if (typeof emailjs !== 'undefined') {
    emailjs.init(EMAILJS_PUBLIC_KEY);
  }
  loadComponents(); // вставляет шапку/футер если есть плейсхолдеры
  initTheme();
  initHeader();
  initMobileMenu();
  initActiveNavLink();
  initRequestModal();
  initFileUpload();
  initInlineForm();
  initCtaContactForm();
  initPhoneMask();
  initSmoothScroll();
});

/* ─── Загрузка общих компонентов (шапка, футер, модал) ───────── */
/* Используется на страницах с плейсхолдерами:
   <div id="header-placeholder"></div>
   <div id="footer-placeholder"></div>
   <div id="modal-placeholder"></div>                            */
function loadComponents() {
  const hp  = document.getElementById('header-placeholder');
  const ctap = document.getElementById('cta-placeholder');
  const fp  = document.getElementById('footer-placeholder');
  const mp  = document.getElementById('modal-placeholder');
  if (hp)   hp.outerHTML   = _tplHeader();
  if (ctap) ctap.outerHTML = _tplCta();
  if (fp)   fp.outerHTML   = _tplFooterOnly();
  if (mp)   mp.outerHTML   = _tplModal();
}

function _tplHeader() {
  // Определяем режим шапки по текущей странице
  const page = window.location.pathname.split('/').pop() || 'index.html';
  const isCatalogMode = page === 'catalog.html' || page === 'product.html';

  // Корзина — только на страницах каталога и товара
  const cartHtml = isCatalogMode ? `
          <a href="order.html" class="cart-btn" id="cartBtn" aria-label="Перейти к заявке" title="Позиции в заявке">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/>
              <path d="M16 10a4 4 0 01-8 0"/>
            </svg>
            <span class="cart-badge hidden" id="cartBadge" aria-live="polite">0</span>
          </a>` : '';

  // Кнопка обратной связи — только НЕ на страницах каталога и товара
  const contactHtml = !isCatalogMode ? `
          <button class="btn btn-primary btn-sm header-contact-btn" data-modal="request" aria-label="Свяжитесь с нами">Свяжитесь с нами</button>` : '';

  return `
  <header class="header" role="banner">
    <div class="container">
      <div class="header__inner">
        <a href="index.html" class="header__logo" aria-label="Рельс-Комплект — на главную">
          <div class="header__logo-icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="2" y1="20" x2="22" y2="20"/><line x1="2" y1="4" x2="22" y2="4"/>
              <line x1="6" y1="4" x2="6" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/><line x1="18" y1="4" x2="18" y2="20"/>
            </svg>
          </div>
          <div class="header__logo-text">
            <span class="header__logo-name">Рельс-Комплект</span>
            <span class="header__logo-sub">Оптовые поставки</span>
          </div>
        </a>
        <nav class="nav" role="navigation" aria-label="Основная навигация">
          <a href="index.html" class="nav__link">Главная</a>
          <a href="catalog.html" class="nav__link">Каталог</a>
          <a href="calculator.html" class="nav__link">Калькулятор</a>
          <a href="about.html" class="nav__link">О компании</a>
          <a href="contacts.html" class="nav__link">Контакты</a>
        </nav>
        <div class="header__actions">
          ${cartHtml}
          <button class="theme-toggle" id="themeToggle" aria-label="Переключить тему" title="Переключить тему">
            <svg class="theme-toggle__icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
          </button>
          ${contactHtml}
          <button class="burger" aria-label="Открыть меню" aria-expanded="false" aria-controls="mobileMenu">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </header>
  <div class="mobile-menu" id="mobileMenu" role="dialog" aria-label="Мобильное меню" aria-modal="true">
    <div class="mobile-menu__header">
      <a href="index.html" class="header__logo" aria-label="Рельс-Комплект">
        <div class="header__logo-icon" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="2" y1="20" x2="22" y2="20"/><line x1="2" y1="4" x2="22" y2="4"/>
            <line x1="6" y1="4" x2="6" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/><line x1="18" y1="4" x2="18" y2="20"/>
          </svg>
        </div>
        <span class="header__logo-name">Рельс-Комплект</span>
      </a>
      <button class="mobile-menu__close" aria-label="Закрыть меню">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>
    <nav class="mobile-menu__nav" role="navigation" aria-label="Мобильная навигация">
      <a href="index.html" class="mobile-menu__link">Главная</a>
      <a href="catalog.html" class="mobile-menu__link">Каталог продукции</a>
      <a href="calculator.html" class="mobile-menu__link">Калькулятор тоннажа</a>
      <a href="about.html" class="mobile-menu__link">О компании</a>
      <a href="contacts.html" class="mobile-menu__link">Контакты</a>
    </nav>
    <div class="mobile-menu__footer">
      <a href="tel:+73433451333" class="mobile-menu__phone">+7 (343) 345-13-33</a>
      <p class="text-sm text-muted">Пн–пт 9:00–18:00</p>
      <button class="btn btn-primary" style="width:100%;margin-top:var(--space-md);" data-modal="request">Свяжитесь с нами</button>
    </div>
  </div>`;
}

/* CTA и footer разделены: contacts.html использует только footer,
   calculator.html — оба через отдельные плейсхолдеры             */
function _tplCta() {
  return `
  <section class="cta-contact" aria-label="Обратная связь">
    <div class="container">
      <div class="cta-contact__card">
        <h2 class="cta-contact__title">Остались вопросы?</h2>
        <p class="cta-contact__sub">Свяжитесь с нами — ответим в течение часа</p>
        <form class="cta-contact__form" novalidate>
          <div class="cta-contact__fields">
            <input class="input" type="text" name="name" placeholder="Ваше имя" required autocomplete="name">
            <input class="input" type="tel" name="phone" placeholder="+7 (___) ___-__-__" required autocomplete="tel">
          </div>
          <label class="form-consent">
            <input type="checkbox" name="consent_pd" required>
            <span>Я согласен(на) на обработку <a href="privacy.html" target="_blank">персональных данных</a> в соответствии с 152-ФЗ</span>
          </label>
          <button class="btn btn-primary" type="submit">Перезвоните мне</button>
        </form>
      </div>
    </div>
  </section>`;
}

function _tplFooterOnly() {
  return `
  <footer class="footer" role="contentinfo">
    <div class="container">
      <div class="footer__grid">
        <div class="footer__brand">
          <div class="footer__logo">
            <div class="footer__logo-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="2" y1="20" x2="22" y2="20"/><line x1="2" y1="4" x2="22" y2="4"/><line x1="6" y1="4" x2="6" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/><line x1="18" y1="4" x2="18" y2="20"/></svg>
            </div>
            <span class="footer__logo-name">Рельс-Комплект</span>
          </div>
          <p class="footer__desc">Оптовый поставщик рельсовых материалов. 158 позиций: рельсы, шпалы, крепёж. Работаем с 2009 года. Поставки по всей России.</p>
          <div class="footer__contacts">
            <div class="footer__contact-item">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.92v3a2 2 0 01-2.18 2A19.79 19.79 0 019.82 18.9 19.5 19.5 0 013.07 12 19.79 19.79 0 01.12 2.18a2 2 0 012-2h3a2 2 0 012 1.72c.127.96.361 1.9.7 2.81a2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 14.91v2.01z"/></svg>
              <a href="tel:+73433451333" style="color:inherit;cursor:pointer;transition:color var(--transition-fast);" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='inherit'">+7 (343) 345-13-33</a>
            </div>
            <div class="footer__contact-item">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
              <a href="mailto:ooorku@mail.ru" style="color:inherit;cursor:pointer;transition:color var(--transition-fast);" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='inherit'">ooorku@mail.ru</a>
            </div>
            <div class="footer__contact-item">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
              <span>г. Екатеринбург, ул. Радищева, д. 6а, оф. 702б</span>
            </div>
          </div>
        </div>
        <div>
          <div class="footer__col-title">Разделы</div>
          <nav aria-label="Навигация в футере">
            <a href="index.html" class="footer__nav-link">Главная</a>
            <a href="catalog.html" class="footer__nav-link">Каталог продукции</a>
            <a href="calculator.html" class="footer__nav-link">Калькулятор тоннажа</a>
            <a href="about.html" class="footer__nav-link">О компании</a>
            <a href="contacts.html" class="footer__nav-link">Контакты и реквизиты</a>
          </nav>
        </div>
        <div>
          <div class="footer__col-title">Продукция</div>
          <nav aria-label="Категории продукции">
            <a href="catalog.html?cat=%D0%A0%D0%B5%D0%BB%D1%8C%D1%81%D1%8B+%D1%88%D0%B8%D1%80%D0%BE%D0%BA%D0%BE%D0%B9+%D0%BA%D0%BE%D0%BB%D0%B5%D0%B8" class="footer__nav-link">Рельсы широкой колеи</a>
            <a href="catalog.html?cat=%D0%A0%D0%B5%D0%BB%D1%8C%D1%81%D1%8B+%D0%BA%D1%80%D0%B0%D0%BD%D0%BE%D0%B2%D1%8B%D0%B5" class="footer__nav-link">Рельсы крановые</a>
            <a href="catalog.html?cat=%D0%A0%D0%B5%D0%BB%D1%8C%D1%81%D1%8B+%D1%83%D0%B7%D0%BA%D0%BE%D0%BA%D0%BE%D0%BB%D0%B5%D0%B9%D0%BD%D1%8B%D0%B5" class="footer__nav-link">Рельсы узкоколейные</a>
            <a href="catalog.html?cat=%D0%9D%D0%B0%D0%BA%D0%BB%D0%B0%D0%B4%D0%BA%D0%B8+%D1%80%D0%B5%D0%BB%D1%8C%D1%81%D0%BE%D0%B2%D1%8B%D0%B5" class="footer__nav-link">Накладки рельсовые</a>
            <a href="catalog.html?cat=%D0%9A%D1%80%D0%B5%D0%BF%D0%B5%D0%B6+%D0%B6%D0%B5%D0%BB%D0%B5%D0%B7%D0%BD%D0%BE%D0%B4%D0%BE%D1%80%D0%BE%D0%B6%D0%BD%D1%8B%D0%B9" class="footer__nav-link">Крепёж железнодорожный</a>
            <a href="catalog.html?cat=%D0%91%D0%BE%D0%BB%D1%82%D1%8B+%D1%81%D1%82%D1%8B%D0%BA%D0%BE%D0%B2%D1%8B%D0%B5" class="footer__nav-link">Болты стыковые</a>
          </nav>
        </div>
      </div>
      <div class="footer__bottom">
        <p class="footer__copy">&copy; 2009–2026 ООО «Рельс-Комплект». Все права защищены.</p>
        <p class="footer__copy" style="margin-top:4px; font-size:0.85em; opacity:0.8;">
          Информация на сайте не является публичной офертой (ст. 437 ГК РФ).
          <a href="privacy.html" style="color:inherit; text-decoration:underline;">Политика конфиденциальности</a>
        </p>
      </div>
    </div>
  </footer>`;
}

function _tplModal() {
  return `
  <div class="modal-overlay" id="requestModal" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
    <div class="modal">
      <div class="modal__header">
        <h2 class="modal__title" id="modalTitle">Свяжитесь с нами</h2>
        <button class="modal__close" aria-label="Закрыть окно">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <form class="modal__body" id="requestForm" novalidate>
        <div class="form-group">
          <label class="form-label form-label--required" for="req-name">Ваше имя</label>
          <input class="input" type="text" id="req-name" name="name" placeholder="Иванов Иван" required autocomplete="name">
        </div>
        <div class="form-group">
          <label class="form-label form-label--required" for="req-contact">Телефон или email</label>
          <div class="smart-contact-wrap" id="req-contact-wrap">
            <span class="smart-contact-icon" id="req-contact-icon" aria-hidden="true">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 01-2.18 2A19.79 19.79 0 019.82 18.9 19.5 19.5 0 013.07 12 19.79 19.79 0 01.12 2.18a2 2 0 012-2h3a2 2 0 012 1.72c.127.96.361 1.9.7 2.81a2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 14.91z"/></svg>
            </span>
            <input
              class="input smart-contact-input"
              type="text"
              id="req-contact"
              name="contact"
              placeholder="Телефон или email"
              required
              autocomplete="off"
              aria-label="Телефон или email"
            >
            <span class="smart-contact-hint" id="req-contact-hint"></span>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label" for="req-message">Сообщение</label>
          <textarea class="textarea" id="req-message" name="message" rows="3" placeholder="Чем можем помочь?"></textarea>
        </div>
        <div class="modal__footer">
          <label class="form-consent">
            <input type="checkbox" name="consent_pd" required>
            <span>Я согласен(на) на обработку <a href="privacy.html" target="_blank">персональных данных</a> в соответствии с 152-ФЗ</span>
          </label>
          <button class="btn btn-primary" type="submit" style="width:100%;">Получить КП</button>
        </div>
      </form>
    </div>
  </div>`;
}

/* ─── Тёмная тема ───────────────────────────────────────────── */
function initTheme() {
  // Применяем тему из localStorage, иначе — системная тема устройства
  const systemDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const saved = localStorage.getItem('theme') || (systemDark ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', saved);
  _updateThemeIcon(saved);

  const btn = document.getElementById('themeToggle');
  if (!btn) return;

  btn.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    const next    = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    _updateThemeIcon(next);
  });
}

function _updateThemeIcon(theme) {
  const icon = document.querySelector('#themeToggle .theme-toggle__icon');
  if (!icon) return;
  if (theme === 'dark') {
    // Солнце — нажать чтобы вернуть светлую тему
    icon.innerHTML = `
      <circle cx="12" cy="12" r="5"/>
      <line x1="12" y1="1" x2="12" y2="3"/>
      <line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/>
      <line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>`;
  } else {
    // Луна — нажать чтобы включить тёмную тему
    icon.innerHTML = `<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>`;
  }
}

/* ─── Липкая шапка ──────────────────────────────────────────── */
function initHeader() {
  const header = document.querySelector('.header');
  if (!header) return;

  const onScroll = () => {
    header.classList.toggle('scrolled', window.scrollY > 10);
  };

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll(); // вызов при инициализации на случай если страница уже прокручена
}

/* ─── Мобильное меню ────────────────────────────────────────── */
function initMobileMenu() {
  const burgerBtn  = document.querySelector('.burger');
  const mobileMenu = document.querySelector('.mobile-menu');
  const closeBtn   = document.querySelector('.mobile-menu__close');

  if (!burgerBtn || !mobileMenu) return;

  const openMenu = () => {
    mobileMenu.classList.add('open');
    document.body.style.overflow = 'hidden';
    burgerBtn.setAttribute('aria-expanded', 'true');
  };

  const closeMenu = () => {
    mobileMenu.classList.remove('open');
    document.body.style.overflow = '';
    burgerBtn.setAttribute('aria-expanded', 'false');
  };

  burgerBtn.addEventListener('click', openMenu);
  closeBtn?.addEventListener('click', closeMenu);

  // Закрытие по клику на пункт меню
  mobileMenu.querySelectorAll('.mobile-menu__link').forEach(link => {
    link.addEventListener('click', closeMenu);
  });

  // Закрытие по Escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && mobileMenu.classList.contains('open')) {
      closeMenu();
    }
  });
}

/* ─── Подсветка активной ссылки навигации ───────────────────── */
function initActiveNavLink() {
  const currentPath = window.location.pathname.split('/').pop() || 'index.html';

  document.querySelectorAll('.nav__link, .mobile-menu__link').forEach(link => {
    const href = link.getAttribute('href');
    if (href && (href === currentPath || href.startsWith(currentPath.split('.')[0]))) {
      link.classList.add('active');
    }
  });
}

/* ─── Модальное окно заявки ─────────────────────────────────── */
function initRequestModal() {
  const overlay = document.querySelector('#requestModal');
  if (!overlay) return;

  const modal    = overlay.querySelector('.modal');
  const closeBtn = overlay.querySelector('.modal__close');
  const form     = overlay.querySelector('#requestForm');

  // Открытие
  document.querySelectorAll('[data-modal="request"]').forEach(trigger => {
    trigger.addEventListener('click', () => openModal(overlay));
  });

  // Закрытие по кнопке
  closeBtn?.addEventListener('click', () => closeModal(overlay));

  // Закрытие по клику на оверлей (не на само модальное окно)
  overlay.addEventListener('click', e => {
    if (e.target === overlay) closeModal(overlay);
  });

  // Закрытие по Escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && overlay.classList.contains('open')) {
      closeModal(overlay);
    }
  });

  // Отправка формы
  form?.addEventListener('submit', handleRequestSubmit);
}

function openModal(overlay) {
  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';
  // Фокус на первое поле
  setTimeout(() => {
    overlay.querySelector('input, select, textarea')?.focus();
  }, 100);
}

function closeModal(overlay) {
  overlay.classList.remove('open');
  document.body.style.overflow = '';
}

/* ─── Форма "Перезвоните мне" (секция cta-contact) ──────────── */
function initCtaContactForm() {
  document.querySelectorAll('.cta-contact__form').forEach(form => {
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const nameField  = form.querySelector('[name="name"]');
      const phoneField = form.querySelector('[name="phone"]');
      if (!nameField?.value.trim())  { nameField?.focus();  return; }
      if (!phoneField?.value.trim() || !isValidPhone(phoneField.value)) {
        phoneField?.focus();
        return;
      }
      if (!_checkConsent(form)) return;
      if (_isThrottled()) {
        showToast('Подождите немного перед повторной отправкой.', 'error');
        return;
      }
      try {
        await sendTelegram({
          name: nameField.value.trim(),
          phone: phoneField.value.trim(),
          message: 'Запрос "Перезвоните мне"'
        }, 'callback');
        form.reset();
        showToast('Спасибо! Перезвоним вам.', 'success');
        if (window.rkTrack) window.rkTrack('form_submit', { extra: { form: 'callback_form' } });
      } catch(err) {
        showToast('Ошибка отправки. Позвоните нам напрямую.', 'error');
      }
    });
  });
}

/* ─── File upload UX ────────────────────────────────────────── */
function initFileUpload() {
  const input       = document.getElementById('il-file');
  const drop        = document.getElementById('il-file-drop');
  const placeholder = document.getElementById('il-file-placeholder');
  const selected    = document.getElementById('il-file-selected');
  const nameEl      = document.getElementById('il-file-name');
  const clearBtn    = document.getElementById('il-file-clear');
  const errorEl     = document.getElementById('il-file-error');
  if (!input) return;

  const MAX_SIZE = 10 * 1024 * 1024; // 10 МБ
  const ALLOWED  = ['.pdf','.doc','.docx','.xls','.xlsx','.jpg','.jpeg','.png'];

  function showFile(file) {
    if (!file) return;
    if (file.size > MAX_SIZE) {
      errorEl.textContent = 'Файл слишком большой (максимум 10 МБ)';
      errorEl.classList.remove('hidden');
      input.value = '';
      return;
    }
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED.includes(ext)) {
      errorEl.textContent = 'Формат не поддерживается. Допустимо: PDF, Word, Excel, JPG, PNG';
      errorEl.classList.remove('hidden');
      input.value = '';
      return;
    }
    errorEl.classList.add('hidden');
    nameEl.textContent = file.name;
    placeholder.classList.add('hidden');
    selected.classList.remove('hidden');
  }

  function clearFile() {
    input.value = '';
    placeholder.classList.remove('hidden');
    selected.classList.add('hidden');
    nameEl.textContent = '';
    errorEl.classList.add('hidden');
  }

  input.addEventListener('change', () => { if (input.files[0]) showFile(input.files[0]); });
  clearBtn?.addEventListener('click', (e) => { e.stopPropagation(); clearFile(); });

  // Drag & drop
  drop.addEventListener('dragover',  (e) => { e.preventDefault(); drop.classList.add('drag-over'); });
  drop.addEventListener('dragleave', ()  => drop.classList.remove('drag-over'));
  drop.addEventListener('drop', (e) => {
    e.preventDefault();
    drop.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) { input.files = e.dataTransfer.files; showFile(file); }
  });
}

/* ─── Инлайн-форма на главной странице ──────────────────────── */
function initInlineForm() {
  const form = document.querySelector('#inlineRequestForm');
  if (!form) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const btn     = form.querySelector('[type="submit"]');
    const name    = form.querySelector('[name="name"]')?.value.trim();
    const contact = form.querySelector('[name="contact"]')?.value.trim();
    const message = form.querySelector('[name="message"]')?.value.trim();

    if (!name)    { form.querySelector('[name="name"]').focus(); return; }
    if (!contact || !isValidContact(contact)) {
      form.querySelector('[name="contact"]').focus();
      return;
    }
    if (!_checkConsent(form)) return;
    if (_isThrottled()) { showToast('Подождите немного перед повторной отправкой.', 'error'); return; }

    btn.disabled = true;
    const origText = btn.textContent;
    btn.innerHTML = '<span class="spinner" style="width:18px;height:18px;margin:0 auto;"></span>';

    const isEmail  = contact.includes('@');
    const fileInput = document.getElementById('il-file');
    const file      = fileInput?.files?.[0];

    // Формируем запрос: multipart если есть файл, иначе JSON
    let fetchOptions;
    if (file) {
      const fd = new FormData();
      fd.append('name',    name);
      fd.append('contact', contact);
      fd.append('message', message || '');
      fd.append('file', file, file.name);
      fetchOptions = { method: 'POST', body: fd };
    } else {
      fetchOptions = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, contact, message: message || '', source: 'order' }),
      };
    }

    const fetchUrl = file ? '/api/notify' : '/api/lead';
    try {
      const res = await fetch(fetchUrl, fetchOptions);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      showToast('Спасибо! Мы свяжемся с вами.', 'success');
      if (window.rkTrack) window.rkTrack('form_submit', { extra: { form: 'order_form' } });
      // Дублируем в EmailJS (fire-and-forget, не блокирует UX)
      sendEmailJS(_buildEmailJSParams(
        { name, contact, message: message || '' },
        'Главная страница'
      )).catch(err => console.warn('EmailJS (inline):', err));
      form.reset();
      // Сбрасываем file upload UI
      document.getElementById('il-file-placeholder')?.classList.remove('hidden');
      document.getElementById('il-file-selected')?.classList.add('hidden');
      if (document.getElementById('il-file-name')) document.getElementById('il-file-name').textContent = '';
      document.querySelectorAll('#inlineRequestForm .smart-contact-wrap').forEach(w => {
        w.dataset.type = '';
        const hint = w.querySelector('.smart-contact-hint');
        if (hint) hint.textContent = '';
      });
    } catch(err) {
      console.error('Ошибка отправки:', err);
      showToast('Ошибка отправки. Позвоните нам напрямую.', 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = origText;
    }
  });
}

/* ─── Проверка чекбокса согласия на обработку ПДн ───────────── */
function _checkConsent(form) {
  const cb = form.querySelector('[name="consent_pd"]') || form.querySelector('[name="consent"]');
  if (cb && !cb.checked) {
    showToast('Подтвердите согласие на обработку персональных данных', 'error');
    cb.focus();
    return false;
  }
  return true;
}

/* ─── Rate limiting: не чаще одного запроса в 30 секунд ─────── */
const _submitThrottle = { lastAt: 0, limit: 30_000 };

function _isThrottled() {
  const now = Date.now();
  if (now - _submitThrottle.lastAt < _submitThrottle.limit) return true;
  _submitThrottle.lastAt = now;
  return false;
}

/* ─── Отправка заявки ───────────────────────────────────────── */
async function handleRequestSubmit(e) {
  e.preventDefault();
  const form    = e.target;
  const btn     = form.querySelector('[type="submit"]');
  const overlay = form.closest('.modal-overlay');

  if (_isThrottled()) {
    showToast('Подождите немного перед повторной отправкой.', 'error');
    return;
  }

  if (!validateForm(form)) return;
  if (!_checkConsent(form)) return;

  // Состояние загрузки
  btn.disabled = true;
  const origText = btn.textContent;
  btn.innerHTML = '<span class="spinner" style="width:18px;height:18px;margin:0 auto;"></span>';

  const data = Object.fromEntries(new FormData(form));

  try {
    // Добавляем товары из корзины в данные заявки
    try {
      data.items = JSON.parse(localStorage.getItem('cart') || '[]');
    } catch(e) {
      data.items = [];
    }
    // Определяем тип умного поля
    if (data.contact) {
      const isEmail = data.contact.includes('@');
      data.phone = isEmail ? '' : data.contact;
      data.email = isEmail ? data.contact : '';
    }
    await sendTelegram(data, 'modal');
    showToast('Спасибо! Мы свяжемся с вами.', 'success');
    if (window.rkTrack) window.rkTrack('form_submit', { extra: { form: 'request_form' } });
    // Дублируем в EmailJS (fire-and-forget)
    sendEmailJS(_buildEmailJSParams(data, 'Форма заявки')).catch(err => console.warn('EmailJS (modal):', err));
    form.reset();
    if (overlay) closeModal(overlay);
  } catch (err) {
    console.error('Ошибка отправки:', err);
    showToast('Ошибка отправки. Позвоните нам напрямую.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = origText;
  }
}

/* ─── EmailJS: отправка уведомления о заявке ─────────────────── */
function _buildEmailJSParams(data, source) {
  const items = Array.isArray(data.items) ? data.items : [];
  let itemsText = '—';
  if (items.length) {
    itemsText = items.map((it, i) => {
      const price = it.price
        ? `${Number(it.price).toLocaleString('ru-RU')} ₽/${it.unit || 'т'}`
        : 'По запросу';
      return `${i + 1}. ${it.name} — ${it.qty} ${it.unit || 'т'} × ${price}`;
    }).join('\n');
  }
  const contact = data.contact || data.phone || data.email || '—';
  const isEmail = contact.includes('@');
  return {
    subject:      'Новая заявка — Рельс-Комплект',
    from_name:    data.name    || '—',
    from_contact: contact,
    reply_to:     isEmail ? contact : '',
    message:      data.message || '—',
    items_text:   itemsText,
    source:       source || 'Сайт',
  };
}

async function sendEmailJS(params) {
  if (typeof emailjs === 'undefined') return;
  return emailjs.send(EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, params);
}

/* ─── Отправка заявки через /api/lead ────────────────────────── */
async function sendTelegram(data, source) {
  const res = await fetch('/api/lead', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name:    data.name    || '',
      contact: data.contact || data.phone || '',
      message: data.message || '',
      source:  source       || 'site',
      items:   data.items   || [],
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
}

function formatTelegramMessage(data) {
  const lines = [
    '<b>📋 Новая заявка — Рельс-Комплект</b>',
    '',
    `👤 Имя: ${data.name || '—'}`,
    `🏢 Компания: ${data.company || '—'}`,
    `📞 Телефон: ${data.phone || '—'}`,
    `📧 Email: ${data.email || '—'}`,
  ];

  if (data.product) lines.push(`🔩 Товар: ${data.product}`);
  if (data.message) lines.push(`💬 Комментарий: ${data.message}`);

  return lines.join('\n');
}

/* ─── Валидация формы ───────────────────────────────────────── */
function validateForm(form) {
  let valid = true;

  // Очищаем прошлые ошибки
  form.querySelectorAll('.input--error').forEach(el => el.classList.remove('input--error'));
  form.querySelectorAll('.form-error').forEach(el => el.remove());

  form.querySelectorAll('[required]').forEach(field => {
    const value = field.value.trim();
    if (!value) {
      markFieldError(field, 'Обязательное поле');
      valid = false;
    } else if (field.name === 'contact' && !isValidContact(value)) {
      markFieldError(field, 'Введите телефон или email');
      valid = false;
    } else if (field.type === 'tel' && !isValidPhone(value)) {
      markFieldError(field, 'Введите корректный номер телефона');
      valid = false;
    } else if (field.type === 'email' && !isValidEmail(value)) {
      markFieldError(field, 'Введите корректный email');
      valid = false;
    }
  });

  return valid;
}

function markFieldError(field, message) {
  field.classList.add('input--error');
  const error = document.createElement('span');
  error.className = 'form-error';
  error.textContent = message;
  field.parentNode.appendChild(error);
}

function isValidPhone(value) {
  return /^[\+]?[0-9\s\-\(\)]{10,}$/.test(value);
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

/* ─── Страны для дропдауна ──────────────────────────────────── */
const PHONE_COUNTRIES = [
  { flag: '🇷🇺', name: 'Россия',      code: '7',   mask: '(###) ###-##-##' },
  { flag: '🇰🇿', name: 'Казахстан',   code: '7',   mask: '(###) ###-##-##' },
  { flag: '🇧🇾', name: 'Беларусь',    code: '375', mask: '(##) ###-##-##'  },
  { flag: '🇺🇿', name: 'Узбекистан',  code: '998', mask: '(##) ###-##-##'  },
  { flag: '🇰🇬', name: 'Кыргызстан',  code: '996', mask: '(###) ##-##-##'  },
  { flag: '🇦🇿', name: 'Азербайджан', code: '994', mask: '(##) ###-##-##'  },
  { flag: '🇩🇪', name: 'Германия',    code: '49',  mask: '### ###-####'    },
  { flag: '🇨🇳', name: 'Китай',       code: '86',  mask: '### ####-####'   },
];

/* ─── Телефонный виджет с флагом страны ─────────────────────── */
function initPhoneMask() {
  document.querySelectorAll('input[type="tel"]').forEach(input => {
    _buildPhoneWidget(input);
  });
  initSmartContactFields();
}

/* ─── Умное поле: телефон или email ─────────────────────────── */
function initSmartContactFields() {
  document.querySelectorAll('.smart-contact-input').forEach(input => {
    const wrap = input.closest('.smart-contact-wrap');
    const icon = wrap?.querySelector('.smart-contact-icon');
    const hint = wrap?.querySelector('.smart-contact-hint');

    const PHONE_SVG = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 01-2.18 2A19.79 19.79 0 019.82 18.9 19.5 19.5 0 013.07 12 19.79 19.79 0 01.12 2.18a2 2 0 012-2h3a2 2 0 012 1.72c.127.96.361 1.9.7 2.81a2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 14.91z"/></svg>`;
    const EMAIL_SVG = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>`;

    function detectType(val) {
      if (!val) return 'empty';
      if (val.includes('@')) return 'email';
      const digits = val.replace(/\D/g, '');
      if (digits.length > 2) return 'phone';
      return 'empty';
    }

    function formatPhone(val) {
      let digits = val.replace(/\D/g, '');
      if (digits.startsWith('8') || digits.startsWith('7')) digits = digits.slice(1);
      digits = digits.slice(0, 10);
      let fmt = '';
      if (digits.length > 0) fmt = '+7 (' + digits.slice(0, 3);
      if (digits.length > 3) fmt += ') ' + digits.slice(3, 6);
      if (digits.length > 6) fmt += '-' + digits.slice(6, 8);
      if (digits.length > 8) fmt += '-' + digits.slice(8, 10);
      return fmt;
    }

    function update(val) {
      const type = detectType(val);
      if (type === 'phone') {
        if (icon) icon.innerHTML = PHONE_SVG;
        if (hint) { hint.textContent = 'Телефон'; hint.className = 'smart-contact-hint smart-contact-hint--phone'; }
        if (wrap)  wrap.dataset.type = 'phone';
      } else if (type === 'email') {
        if (icon) icon.innerHTML = EMAIL_SVG;
        if (hint) { hint.textContent = 'Email'; hint.className = 'smart-contact-hint smart-contact-hint--email'; }
        if (wrap)  wrap.dataset.type = 'email';
      } else {
        if (icon) icon.innerHTML = PHONE_SVG;
        if (hint) { hint.textContent = ''; hint.className = 'smart-contact-hint'; }
        if (wrap)  wrap.dataset.type = '';
      }
    }

    input.addEventListener('keydown', e => {
      const type = detectType(input.value);
      // Если похоже на телефон — блокируем не-цифры (кроме + в начале)
      if (type === 'phone') {
        const allowed = ['Backspace','Delete','Tab','ArrowLeft','ArrowRight','Home','End','Enter'];
        if (allowed.includes(e.key)) return;
        if (e.key === '+' && input.selectionStart === 0) return;
        if (!/^\d$/.test(e.key)) e.preventDefault();
      }
    });

    input.addEventListener('input', () => {
      const raw = input.value;
      const type = detectType(raw);
      // Автоформатирование только для телефона
      if (type === 'phone') {
        const pos = input.selectionStart;
        const formatted = formatPhone(raw);
        input.value = formatted;
        const diff = formatted.length - raw.length;
        input.setSelectionRange(pos + diff, pos + diff);
      }
      update(input.value);
    });

    input.addEventListener('paste', e => {
      e.preventDefault();
      const pasted = (e.clipboardData || window.clipboardData).getData('text');
      input.value = pasted;
      input.dispatchEvent(new Event('input'));
    });

    input.addEventListener('blur', () => {
      if (wrap?.dataset.type === 'phone') {
        input.value = formatPhone(input.value);
      }
    });
  });
}

/* ─── Валидация умного поля ──────────────────────────────────── */
function isValidContact(val) {
  if (!val) return false;
  if (val.includes('@')) return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
  const digits = val.replace(/\D/g, '');
  return digits.length >= 10;
}

function _buildPhoneWidget(input) {
  const parent = input.parentElement;
  if (!parent || parent.classList.contains('phone-widget')) return;

  // Создаём обёртку
  const wrapper = document.createElement('div');
  wrapper.className = 'phone-widget';

  // Кнопка флага — только флаг, код отображается в самом поле ввода
  const flagBtn = document.createElement('button');
  flagBtn.type = 'button';
  flagBtn.className = 'phone-flag-btn';
  flagBtn.dataset.code = '7';
  flagBtn.innerHTML = '<span class="phone-flag">🇷🇺</span>';

  // Дропдаун
  const dropdown = document.createElement('ul');
  dropdown.className = 'phone-dropdown';

  // Возвращает текущий префикс: "+7 ", "+375 " и т.д.
  function getPrefix() {
    return '+' + flagBtn.dataset.code + ' ';
  }

  // Форматирование локальных цифр (без кода страны)
  function formatLocal(digits, code) {
    if (code === '7') {
      if (digits.startsWith('8') || digits.startsWith('7')) digits = digits.slice(1);
      digits = digits.slice(0, 10);
      let fmt = '';
      if (digits.length > 0) fmt = '(' + digits.slice(0, 3);
      if (digits.length > 3) fmt += ') ' + digits.slice(3, 6);
      if (digits.length > 6) fmt += '-' + digits.slice(6, 8);
      if (digits.length > 8) fmt += '-' + digits.slice(8, 10);
      return fmt;
    }
    digits = digits.slice(0, 12);
    return digits.replace(/(\d{3})(?=\d)/g, '$1 ').trim();
  }

  // Устанавливаем префикс по умолчанию в поле ввода
  input.value = '+7 ';
  input.placeholder = '';

  PHONE_COUNTRIES.forEach(c => {
    const li = document.createElement('li');
    li.innerHTML = `<span>${c.flag}</span><span style="flex:1">${c.name}</span><span style="color:var(--color-text-muted)">+${c.code}</span>`;
    li.addEventListener('click', () => {
      flagBtn.innerHTML = `<span class="phone-flag">${c.flag}</span>`;
      flagBtn.dataset.code = c.code;
      input.value = '+' + c.code + ' ';
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
      dropdown.style.display = 'none';
    });
    dropdown.appendChild(li);
  });

  // Переставляем в DOM
  parent.insertBefore(wrapper, input);
  wrapper.appendChild(flagBtn);
  wrapper.appendChild(dropdown);
  wrapper.appendChild(input);

  // Открытие/закрытие дропдауна
  flagBtn.addEventListener('click', e => {
    e.stopPropagation();
    dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
  });
  document.addEventListener('click', () => { dropdown.style.display = 'none'; });

  // Защита префикса от удаления
  input.addEventListener('keydown', e => {
    const prefix = getPrefix();
    const nav = ['Tab', 'ArrowLeft', 'ArrowRight', 'Home', 'End'];
    if (nav.includes(e.key)) return;
    if (!/^\d$/.test(e.key) && e.key !== 'Backspace' && e.key !== 'Delete') {
      e.preventDefault();
      return;
    }
    if (e.key === 'Backspace' && input.selectionStart <= prefix.length && input.selectionEnd <= prefix.length) {
      e.preventDefault();
    }
    if (e.key === 'Delete' && input.selectionStart < prefix.length && input.selectionEnd <= prefix.length) {
      e.preventDefault();
    }
  });

  // Авто-форматирование: восстанавливаем префикс и форматируем локальную часть
  input.addEventListener('input', () => {
    const prefix = getPrefix();
    const code = flagBtn.dataset.code;
    const val = input.value;

    // Если пользователь стёр весь префикс — восстанавливаем
    if (!val.startsWith('+')) {
      input.value = prefix;
      return;
    }

    // Извлекаем то, что пользователь ввёл после префикса
    const afterPrefix = val.length > prefix.length ? val.slice(prefix.length) : '';
    const digits = afterPrefix.replace(/\D/g, '');
    input.value = prefix + formatLocal(digits, code);
  });

  // Вставка из буфера — очищаем, убираем код страны если есть, форматируем
  input.addEventListener('paste', e => {
    e.preventDefault();
    const prefix = getPrefix();
    const code = flagBtn.dataset.code;
    const pasted = (e.clipboardData || window.clipboardData).getData('text');
    let digits = pasted.replace(/\D/g, '');
    if (digits.startsWith(code)) digits = digits.slice(code.length);
    input.value = prefix + formatLocal(digits, code);
  });
}

/* ─── Плавный скролл к якорям ───────────────────────────────── */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', e => {
      const id = link.getAttribute('href');
      const target = document.querySelector(id);
      if (!target) return;
      e.preventDefault();
      const offset = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--header-height') || '72');
      const top = target.getBoundingClientRect().top + window.scrollY - offset - 16;
      window.scrollTo({ top, behavior: 'smooth' });
    });
  });
}

/* ─── Уведомления (Toast) ───────────────────────────────────── */
function showToast(message, type = 'success') {
  const MAX_TOASTS = 3;

  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  // Если тостов уже MAX_TOASTS — убираем самый старый немедленно
  const existing = container.querySelectorAll('.toast');
  if (existing.length >= MAX_TOASTS) {
    existing[0].remove();
  }

  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;

  const icon = type === 'success'
    ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
    : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';

  toast.innerHTML = `${icon}<span>${message}</span>`;
  container.appendChild(toast);

  // Автоматическое скрытие через 4 секунды
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    toast.style.transition = 'opacity 300ms, transform 300ms';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/* ─── Форматирование цены ───────────────────────────────────── */
function formatPrice(price) {
  if (price === null || price === undefined) return 'Цена по запросу';
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0,
  }).format(price);
}

/* ─── Экспорт утилит для других модулей ─────────────────────── */
window.RK = {
  openModal,
  closeModal,
  showToast,
  formatPrice,
  validateForm,
  loadComponents,
};
