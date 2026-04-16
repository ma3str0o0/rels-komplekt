/**
 * Трекер аналитики Рельс-Комплект
 * Отправляет события на /api/track через sendBeacon/fetch
 */
(function () {
  'use strict';

  if (/bot|crawl|spider|headless|phantom/i.test(navigator.userAgent)) return;

  var ENDPOINT = '/api/track';

  function track(event, data) {
    var payload = Object.assign({
      event:    event,
      page:     location.pathname,
      referrer: document.referrer || null,
    }, data || {});

    var body = JSON.stringify(payload);

    if (navigator.sendBeacon) {
      navigator.sendBeacon(ENDPOINT, new Blob([body], { type: 'application/json' }));
    } else {
      fetch(ENDPOINT, {
        method:    'POST',
        headers:   { 'Content-Type': 'application/json' },
        body:      body,
        keepalive: true,
      }).catch(function () {});
    }
  }

  window.rkTrack = track;

  // page_view
  track('page_view');

  // product_view — страница карточки товара
  (function () {
    var params    = new URLSearchParams(location.search);
    var productId = params.get('id');
    if (location.pathname.indexOf('product.html') !== -1 && productId) {
      track('product_view', { product_id: productId });
    }
  })();

  // phone_click
  document.addEventListener('click', function (e) {
    var link = e.target.closest('a[href^="tel:"]');
    if (link) track('phone_click', { extra: { phone: link.getAttribute('href') } });
  });

  // email_click
  document.addEventListener('click', function (e) {
    var link = e.target.closest('a[href^="mailto:"]');
    if (link) track('email_click');
  });

})();
