/* Восстановление темы до первой отрисовки — предотвращает мигание */
(function(){
  var t=localStorage.getItem("theme");
  if(!t){t=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}
  document.documentElement.setAttribute("data-theme",t);
})();
