// Appliquer avant le rendu pour éviter un flash clair au chargement.
(() => {
  let preference;
  try { preference = localStorage.getItem('gaboma-theme'); } catch (_) {}
  const dark = preference === 'dark';
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
})();
