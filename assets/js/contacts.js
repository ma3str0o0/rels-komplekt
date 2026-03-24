/* =============================================================
   Рельс-Комплект — Страница контактов (contacts.js)
   Обработка формы быстрого запроса
   ============================================================= */

'use strict';

document.addEventListener('DOMContentLoaded', () => {
  updateCartBadge();
  initContactForm();
});

/* ─── Форма быстрого запроса ─────────────────────────────────── */
function initContactForm() {
  const form = document.getElementById('contactsForm');
  if (!form) return;

  form.addEventListener('submit', e => {
    e.preventDefault();
    if (!validateContactForm()) return;

    // Отправка (заглушка — будет заменена на EmailJS/Telegram)
    sendContactForm({
      name:    form.contactName?.value.trim(),
      phone:   form.contactPhone?.value.trim(),
      message: form.contactMessage?.value.trim(),
    });
  });

  // Сброс ошибок при вводе
  ['contactName', 'contactPhone'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', () => clearError(id));
  });
}

function validateContactForm() {
  let valid = true;

  const name = document.getElementById('contactName');
  if (!name.value.trim()) {
    showError('contactName', 'contactNameError', 'Введите ваше имя');
    valid = false;
  }

  const phone = document.getElementById('contactPhone');
  const phoneVal = phone.value.trim().replace(/\D/g, '');
  if (!phoneVal || phoneVal.length < 10) {
    showError('contactPhone', 'contactPhoneError', 'Введите корректный номер телефона');
    valid = false;
  }

  return valid;
}

function showError(fieldId, errorId, message) {
  const field = document.getElementById(fieldId);
  const err   = document.getElementById(errorId);
  if (field) field.setAttribute('aria-invalid', 'true');
  if (err)   { err.textContent = message; err.hidden = false; }
}

function clearError(fieldId) {
  const field   = document.getElementById(fieldId);
  const errorId = fieldId + 'Error';
  const err     = document.getElementById(errorId);
  if (field) field.removeAttribute('aria-invalid');
  if (err)   err.hidden = true;
}

function sendContactForm(data) {
  // TODO: подключить EmailJS или Telegram Bot API
  console.log('[contacts] Отправка формы:', data);

  // Имитируем отправку
  const btn = document.querySelector('.contacts-form__submit');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Отправка...';
  }

  setTimeout(() => {
    window.RK?.showToast('Спасибо! Мы свяжемся с вами.', 'success');
    document.getElementById('contactsForm').reset();
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Отправить`;
    }
  }, 600);
}

/* ─── Бейдж корзины ──────────────────────────────────────────── */
function updateCartBadge() {
  const badge = document.getElementById('cartBadge');
  if (!badge) return;
  try {
    const count = JSON.parse(localStorage.getItem('cart') || '[]').length;
    badge.textContent = count;
    badge.classList.toggle('hidden', count === 0);
  } catch { /* игнорируем */ }
}
