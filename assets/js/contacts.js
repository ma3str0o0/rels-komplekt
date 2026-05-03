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
    const consent = form.querySelector('[name="consent_pd"]') || form.querySelector('[name="consent"]');
    if (consent && !consent.checked) {
      window.RK?.showToast('Подтвердите согласие на обработку персональных данных', 'error');
      consent.focus();
      return;
    }

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

async function sendContactForm(data) {
  const btn      = document.querySelector('.contacts-form__submit');
  const origHTML = btn?.innerHTML || '';
  if (btn) { btn.disabled = true; btn.textContent = 'Отправка...'; }

  try {
    await fetch('/api/lead', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name:    data.name,
        contact: data.phone,
        message: data.message || '',
        source:  'contacts',
      }),
    });
  } catch (e) {
    console.warn('[contacts] lead error:', e);
  }

  // EmailJS
  try {
    if (typeof emailjs !== 'undefined') {
      await emailjs.send('service_vc2oz9j', 'template_e7f1ke6', {
        subject:      'Новая заявка — Рельс-Комплект',
        from_name:    data.name    || '—',
        from_contact: data.phone   || '—',
        reply_to:     '',
        message:      data.message || '—',
        items_text:   '—',
        source:       'Страница контактов',
      });
    }
  } catch (e) {
    console.warn('[contacts] EmailJS error:', e);
  }

  window.RK?.showToast('Спасибо! Мы свяжемся с вами.', 'success');
  document.getElementById('contactsForm').reset();
  if (btn) { btn.disabled = false; btn.innerHTML = origHTML; }
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
