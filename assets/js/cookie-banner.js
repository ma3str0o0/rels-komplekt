(function() {
  const STORAGE_KEY = 'cookies_accepted';
  const Y_METRIKA_ID = 32668705;
  const TOP_MAIL_ID = 2690827;

  function loadAnalytics() {
    // Yandex Metrika
    (function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
    m[i].l=1*new Date();
    for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
    k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})
    (window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");
    ym(Y_METRIKA_ID, "init", {clickmap:true, trackLinks:true, accurateTrackBounce:true, webvisor:true});

    // Top@Mail.ru
    var _tmr = window._tmr || (window._tmr = []);
    _tmr.push({id: TOP_MAIL_ID, type: "pageView", start: (new Date()).getTime()});
    (function (d, w, id) {
      if (d.getElementById(id)) return;
      var ts = d.createElement("script"); ts.type = "text/javascript"; ts.async = true; ts.id = id;
      ts.src = "https://top-fwz1.mail.ru/js/code.js";
      var f = function () {var s = d.getElementsByTagName("script")[0]; s.parentNode.insertBefore(ts, s);};
      if (w.opera == "[object Opera]") { d.addEventListener("DOMContentLoaded", f, false); } else { f(); }
    })(document, window, "tmr-code");
  }

  function showBanner() {
    const banner = document.createElement('div');
    banner.id = 'cookie-banner';
    banner.innerHTML = `
      <div class="cookie-banner-content">
        <p>Мы используем cookies для аналитики посещений сайта. Подробнее в <a href="/privacy.html">Политике конфиденциальности</a>.</p>
        <button class="cookie-banner-accept" type="button">Принять</button>
      </div>
    `;
    document.body.appendChild(banner);
    banner.querySelector('.cookie-banner-accept').addEventListener('click', () => {
      try { localStorage.setItem(STORAGE_KEY, 'true'); } catch (e) {}
      banner.remove();
      loadAnalytics();
    });
  }

  let accepted = false;
  try { accepted = localStorage.getItem(STORAGE_KEY) === 'true'; } catch (e) {}

  if (accepted) {
    loadAnalytics();
  } else {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', showBanner);
    } else {
      showBanner();
    }
  }
})();
