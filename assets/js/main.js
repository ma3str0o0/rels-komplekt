/* =============================================================
   Рельс-Комплект — Общий JavaScript
   ============================================================= */

'use strict';

/* ─── Инициализация при загрузке DOM ─────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  loadComponents(); // вставляет шапку/футер если есть плейсхолдеры
  initTheme();
  initHeader();
  initMobileMenu();
  initActiveNavLink();
  initRequestModal();
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
          <a href="contacts.html" class="nav__link">Контакты</a>
        </nav>
        <div class="header__actions">
          <div class="header__phone">
            <a href="tel:+73432372333" class="header__phone-number">+7 (343) 237-23-33</a>
            <a href="tel:+79676396333" class="header__phone-number">+7 (967) 639-63-33</a>
            <span class="header__phone-label">Пн–пт 9:00–18:00</span>
          </div>
          <a href="order.html" class="cart-btn" id="cartBtn" aria-label="Перейти к заявке" title="Позиции в заявке">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/>
              <path d="M16 10a4 4 0 01-8 0"/>
            </svg>
            <span class="cart-badge hidden" id="cartBadge" aria-live="polite">0</span>
          </a>
          <button class="theme-toggle" id="themeToggle" aria-label="Переключить тему" title="Переключить тему">
            <svg class="theme-toggle__icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
          </button>
          <button class="btn btn-primary btn-sm" data-modal="request" aria-label="Свяжитесь с нами">Свяжитесь с нами</button>
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
      <a href="contacts.html" class="mobile-menu__link">Контакты</a>
    </nav>
    <div class="mobile-menu__footer">
      <a href="tel:+73432372333" class="mobile-menu__phone">+7 (343) 237-23-33</a>
      <a href="tel:+79676396333" class="mobile-menu__phone">+7 (967) 639-63-33</a>
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
              <a href="tel:+73432372333" style="color:inherit;cursor:pointer;transition:color var(--transition-fast);" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='inherit'">+7 (343) 237-23-33</a>
            </div>
            <div class="footer__contact-item">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.92v3a2 2 0 01-2.18 2A19.79 19.79 0 019.82 18.9 19.5 19.5 0 013.07 12 19.79 19.79 0 01.12 2.18a2 2 0 012-2h3a2 2 0 012 1.72c.127.96.361 1.9.7 2.81a2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 14.91v2.01z"/></svg>
              <a href="tel:+79676396333" style="color:inherit;cursor:pointer;transition:color var(--transition-fast);" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='inherit'">+7 (967) 639-63-33</a>
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
          <label class="form-label form-label--required" for="req-phone">Телефон</label>
          <input class="input" type="tel" id="req-phone" name="phone" placeholder="+7 (___) ___-__-__" required autocomplete="tel">
        </div>
        <div class="form-group">
          <label class="form-label" for="req-message">Сообщение</label>
          <textarea class="textarea" id="req-message" name="message" rows="3" placeholder="Чем можем помочь?"></textarea>
        </div>
        <div class="modal__footer">
          <button class="btn btn-primary" type="submit" style="width:100%;">Отправить</button>
          <p class="modal__note">Нажимая кнопку, вы соглашаетесь с обработкой персональных данных</p>
        </div>
      </form>
    </div>
  </div>`;
}

/* ─── Тёмная тема ───────────────────────────────────────────── */
function initTheme() {
  // Применяем тему из localStorage (также применяется inline-скриптом в <head>)
  const saved = localStorage.getItem('theme') || 'light';
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
      if (_isThrottled()) {
        showToast('Подождите немного перед повторной отправкой.', 'error');
        return;
      }
      try {
        await sendTelegram({
          name: nameField.value.trim(),
          phone: phoneField.value.trim(),
          message: 'Запрос "Перезвоните мне"'
        });
        form.reset();
        showToast('Спасибо! Перезвоним вам.', 'success');
      } catch(err) {
        showToast('Ошибка отправки. Позвоните нам напрямую.', 'error');
      }
    });
  });
}

/* ─── Инлайн-форма на главной странице ──────────────────────── */
function initInlineForm() {
  const form = document.querySelector('#inlineRequestForm');
  if (!form) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = form.querySelector('[type="submit"]');
    const name    = form.querySelector('[name="name"]')?.value.trim();
    const phone   = form.querySelector('[name="phone"]')?.value.trim();
    const message = form.querySelector('[name="message"]')?.value.trim();

    if (!name)  { form.querySelector('[name="name"]').focus();  return; }
    if (!phone || !isValidPhone(phone)) {
      form.querySelector('[name="phone"]').focus();
      return;
    }

    if (_isThrottled()) {
      showToast('Подождите немного перед повторной отправкой.', 'error');
      return;
    }

    btn.disabled = true;
    const origText = btn.textContent;
    btn.innerHTML = '<span class="spinner" style="width:18px;height:18px;margin:0 auto;"></span>';

    try {
      await sendTelegram({ name, phone, message: message || '' });
      showToast('Спасибо! Мы свяжемся с вами.', 'success');
      form.reset();
      // Сбрасываем флаг страны обратно на +7
      const flagBtn = form.querySelector('.phone-flag-btn');
      if (flagBtn) {
        flagBtn.innerHTML = '<span class="phone-flag">🇷🇺</span><span class="phone-code">+7</span>';
        flagBtn.dataset.code = '7';
      }
      const phoneInput = form.querySelector('[name="phone"]');
      if (phoneInput) phoneInput.placeholder = '(___) ___-__-__';
    } catch(err) {
      console.error('Ошибка отправки:', err);
      showToast('Ошибка отправки. Позвоните нам напрямую.', 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = origText;
    }
  });
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
    await sendTelegram(data);
    showToast('Спасибо! Мы свяжемся с вами.', 'success');
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

/* ─── Отправка в Telegram через proxy ────────────────────────── */
async function sendTelegram(data) {
  const PROXY_URL = '/api/notify'; // относительный путь — работает с любого хоста и порта
  const res = await fetch(PROXY_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
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
}

function _buildPhoneWidget(input) {
  const parent = input.parentElement;
  if (!parent || parent.classList.contains('phone-widget')) return;

  // Создаём обёртку
  const wrapper = document.createElement('div');
  wrapper.className = 'phone-widget';

  // Кнопка флага
  const flagBtn = document.createElement('button');
  flagBtn.type = 'button';
  flagBtn.className = 'phone-flag-btn';
  flagBtn.dataset.code = '7';
  flagBtn.innerHTML = '<span class="phone-flag">🇷🇺</span><span class="phone-code">+7</span>';

  // Дропдаун
  const dropdown = document.createElement('ul');
  dropdown.className = 'phone-dropdown';

  PHONE_COUNTRIES.forEach(c => {
    const li = document.createElement('li');
    li.innerHTML = `<span>${c.flag}</span><span style="flex:1">${c.name}</span><span style="color:var(--color-text-muted)">+${c.code}</span>`;
    li.addEventListener('click', () => {
      flagBtn.innerHTML = `<span class="phone-flag">${c.flag}</span><span class="phone-code">+${c.code}</span>`;
      flagBtn.dataset.code = c.code;
      input.placeholder = c.mask.replace(/#/g, '_');
      input.value = '';
      input.focus();
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

  // Только цифры — блокируем нецифровые символы
  input.addEventListener('keydown', e => {
    const allowed = ['Backspace','Delete','Tab','ArrowLeft','ArrowRight','Home','End'];
    if (allowed.includes(e.key)) return;
    if (!/^\d$/.test(e.key)) e.preventDefault();
  });

  // Авто-форматирование при вводе
  input.addEventListener('input', () => {
    const code = flagBtn.dataset.code;
    let digits = input.value.replace(/\D/g, '');

    if (code === '7') {
      // Убираем ведущую 7 или 8 если введена
      if (digits.startsWith('8') || digits.startsWith('7')) digits = digits.slice(1);
      digits = digits.slice(0, 10);
      let fmt = '';
      if (digits.length > 0) fmt = '(' + digits.slice(0, 3);
      if (digits.length > 3) fmt += ') ' + digits.slice(3, 6);
      if (digits.length > 6) fmt += '-' + digits.slice(6, 8);
      if (digits.length > 8) fmt += '-' + digits.slice(8, 10);
      input.value = fmt;
    } else {
      // Остальные страны: цифры с пробелами каждые 3
      digits = digits.slice(0, 12);
      input.value = digits.replace(/(\d{3})(?=\d)/g, '$1 ').trim();
    }
  });

  // Вставка из буфера — только цифры
  input.addEventListener('paste', e => {
    e.preventDefault();
    const pasted = (e.clipboardData || window.clipboardData).getData('text');
    input.value = pasted.replace(/\D/g, '');
    input.dispatchEvent(new Event('input'));
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
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;

  const icon = type === 'success'
    ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
    : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';

  toast.innerHTML = `${icon}<span>${message}</span>`;
  container.appendChild(toast);

  // Автоматическое удаление
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
