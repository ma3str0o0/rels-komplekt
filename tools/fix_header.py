#!/usr/bin/env python3
"""
fix_header.py — три фикса хэдера.

Шапка сайта генерируется через loadComponents() из assets/js/main.js,
поэтому фиксы 2 и 3 вносятся в main.js (не в *.html).
Фикс 1 — в assets/css/style.css.

Скрипт также сканирует *.html на наличие хардкодных блоков
и сообщает, если что-то найдено.
"""

import re, os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ─── вспомогательные ────────────────────────────────────────────

def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()

def write(path, text):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)

def patch(path, old, new, label):
    text = read(path)
    if old not in text:
        print(f'  ⚠  [{label}] строка не найдена в {os.path.relpath(path, ROOT)}')
        return False
    write(path, text.replace(old, new, 1))
    print(f'  ✓  [{label}] исправлено в {os.path.relpath(path, ROOT)}')
    return True

# ═══════════════════════════════════════════════════════════════
# ФИКС 1 — align-items в style.css
# ═══════════════════════════════════════════════════════════════

CSS = os.path.join(ROOT, 'assets/css/style.css')

# 1a. .header — добавить display:flex + align-items:center
patch(CSS,
    '''.header {
  position: sticky;
  top: 0;
  z-index: 100;
  height: var(--header-height);
  background-color: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  transition: box-shadow var(--transition-normal);
}''',
    '''.header {
  position: sticky;
  top: 0;
  z-index: 100;
  height: var(--header-height);
  background-color: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  transition: box-shadow var(--transition-normal);
  display: flex;
  align-items: center;
}''',
    'fix1a: .header align-items')

# 1b. .header__phone — flex-end → center  +  переименование в __phones
patch(CSS,
    '''.header__phone {
  display: none;
  flex-direction: column;
  align-items: flex-end;
  line-height: 1.1;
}

@media (min-width: 768px) {
  .header__phone {
    display: flex;
  }
}

.header__phone-number {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-primary);
  cursor: pointer;
  transition: color var(--transition-fast);
}

.header__phone-number:hover {
  color: var(--color-cta);
}

.header__phone-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}''',
    '''.header__phones {
  display: none;
  flex-direction: column;
  align-items: center;
  line-height: 1.1;
}

@media (min-width: 768px) {
  .header__phones {
    display: flex;
  }
}

.header__phone {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-primary);
  cursor: pointer;
  transition: color var(--transition-fast);
  text-decoration: none;
}

.header__phone:hover {
  color: var(--color-cta);
}

.header__schedule {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}''',
    'fix1b: .header__phones align-items + rename')

# ═══════════════════════════════════════════════════════════════
# ФИКС 2 — один телефон в main.js (хэдер, мобильное меню, футер)
# ═══════════════════════════════════════════════════════════════

JS = os.path.join(ROOT, 'assets/js/main.js')

# 2a. Блок телефона в шапке (десктоп)
patch(JS,
    '''          <div class="header__phone">
            <a href="tel:+73432372333" class="header__phone-number">+7 (343) 237-23-33</a>
            <a href="tel:+79676396333" class="header__phone-number">+7 (967) 639-63-33</a>
            <span class="header__phone-label">Пн–пт 9:00–18:00</span>
          </div>''',
    '''          <div class="header__phones">
            <a href="tel:+73433451333" class="header__phone">+7 (343) 345-13-33</a>
            <span class="header__schedule">Пн–пт 9:00–18:00</span>
          </div>''',
    'fix2a: телефон в шапке')

# 2b. Телефоны в мобильном меню
patch(JS,
    '''      <a href="tel:+73432372333" class="mobile-menu__phone">+7 (343) 237-23-33</a>
      <a href="tel:+79676396333" class="mobile-menu__phone">+7 (967) 639-63-33</a>
      <p class="text-sm text-muted">Пн–пт 9:00–18:00</p>''',
    '''      <a href="tel:+73433451333" class="mobile-menu__phone">+7 (343) 345-13-33</a>
      <p class="text-sm text-muted">Пн–пт 9:00–18:00</p>''',
    'fix2b: телефон в мобильном меню')

# 2c. Телефоны в футере (два блока подряд)
patch(JS,
    '''              <a href="tel:+73432372333" style="color:inherit;cursor:pointer;transition:color var(--transition-fast);" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='inherit'">+7 (343) 237-23-33</a>
            </div>
            <div class="footer__contact-item">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.92v3a2 2 0 01-2.18 2A19.79 19.79 0 019.82 18.9 19.5 19.5 0 013.07 12 19.79 19.79 0 01.12 2.18a2 2 0 012-2h3a2 2 0 012 1.72c.127.96.361 1.9.7 2.81a2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 14.91v2.01z"/></svg>
              <a href="tel:+79676396333" style="color:inherit;cursor:pointer;transition:color var(--transition-fast);" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='inherit'">+7 (967) 639-63-33</a>''',
    '''              <a href="tel:+73433451333" style="color:inherit;cursor:pointer;transition:color var(--transition-fast);" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='inherit'">+7 (343) 345-13-33</a>''',
    'fix2c: телефон в футере')

# ═══════════════════════════════════════════════════════════════
# ФИКС 3 — порядок навигации: О компании → предпоследний
#           Главная / Каталог / Калькулятор / О компании / Контакты
# ═══════════════════════════════════════════════════════════════

# 3a. Десктоп nav
patch(JS,
    '''          <a href="index.html" class="nav__link">Главная</a>
          <a href="about.html" class="nav__link">О компании</a>
          <a href="catalog.html" class="nav__link">Каталог</a>
          <a href="calculator.html" class="nav__link">Калькулятор</a>
          <a href="contacts.html" class="nav__link">Контакты</a>''',
    '''          <a href="index.html" class="nav__link">Главная</a>
          <a href="catalog.html" class="nav__link">Каталог</a>
          <a href="calculator.html" class="nav__link">Калькулятор</a>
          <a href="about.html" class="nav__link">О компании</a>
          <a href="contacts.html" class="nav__link">Контакты</a>''',
    'fix3a: порядок nav (десктоп)')

# 3b. Мобильный nav
patch(JS,
    '''      <a href="index.html" class="mobile-menu__link">Главная</a>
      <a href="about.html" class="mobile-menu__link">О компании</a>
      <a href="catalog.html" class="mobile-menu__link">Каталог продукции</a>
      <a href="calculator.html" class="mobile-menu__link">Калькулятор тоннажа</a>
      <a href="contacts.html" class="mobile-menu__link">Контакты</a>''',
    '''      <a href="index.html" class="mobile-menu__link">Главная</a>
      <a href="catalog.html" class="mobile-menu__link">Каталог продукции</a>
      <a href="calculator.html" class="mobile-menu__link">Калькулятор тоннажа</a>
      <a href="about.html" class="mobile-menu__link">О компании</a>
      <a href="contacts.html" class="mobile-menu__link">Контакты</a>''',
    'fix3b: порядок nav (мобильный)')

# 3c. Футер nav
patch(JS,
    '''            <a href="index.html" class="footer__nav-link">Главная</a>
            <a href="about.html" class="footer__nav-link">О компании</a>
            <a href="catalog.html" class="footer__nav-link">Каталог продукции</a>
            <a href="calculator.html" class="footer__nav-link">Калькулятор тоннажа</a>
            <a href="contacts.html" class="footer__nav-link">Контакты и реквизиты</a>''',
    '''            <a href="index.html" class="footer__nav-link">Главная</a>
            <a href="catalog.html" class="footer__nav-link">Каталог продукции</a>
            <a href="calculator.html" class="footer__nav-link">Калькулятор тоннажа</a>
            <a href="about.html" class="footer__nav-link">О компании</a>
            <a href="contacts.html" class="footer__nav-link">Контакты и реквизиты</a>''',
    'fix3c: порядок nav (футер)')

# ═══════════════════════════════════════════════════════════════
# Сканируем HTML на хардкодные хэдеры (для информации)
# ═══════════════════════════════════════════════════════════════

html_files = sorted(glob.glob(os.path.join(ROOT, '*.html')))
hardcoded = []
for f in html_files:
    text = read(f)
    # хэдер считается хардкодным если есть <header без плейсхолдера
    if '<header' in text and 'header-placeholder' not in text:
        hardcoded.append(os.path.relpath(f, ROOT))

print()
print(f'HTML-файлов в корне: {len(html_files)}')
if hardcoded:
    print(f'⚠  Хардкодные хэдеры найдены: {hardcoded}')
else:
    print('✓  Все страницы используют header-placeholder — хардкодных хэдеров нет')

# ═══════════════════════════════════════════════════════════════
# Вывод итоговой nav-строки из main.js для проверки
# ═══════════════════════════════════════════════════════════════

print()
print('── Итоговая десктоп-навигация (из main.js) ──')
js_text = read(JS)
m = re.search(r'<nav class="nav"[^>]*>(.*?)</nav>', js_text, re.S)
if m:
    links = re.findall(r'href="([^"]+)"[^>]*>([^<]+)<', m.group(1))
    for href, label in links:
        print(f'  {label.strip():<20} → {href}')

print()
print('Готово.')
