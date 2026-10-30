(() => {
  const button = document.querySelector('.theme-toggle');
  if (!button) return;
  const system = matchMedia('(prefers-color-scheme: dark)');
  let explicit = false;
  try { explicit = ['light', 'dark'].includes(localStorage.getItem('gaboma-theme')); } catch (_) {}
  function apply(theme) {
    const dark = theme === 'dark';
    document.documentElement.dataset.theme = theme;
    button.setAttribute('aria-pressed', String(dark));
    button.title = dark ? 'Passer en mode jour' : 'Passer en mode nuit';
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#101827' : '#f7f8fa');
  }
  apply(document.documentElement.dataset.theme || 'light');
  button.hidden = false;
  button.addEventListener('click', () => {
    const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    explicit = true;
    try { localStorage.setItem('gaboma-theme', theme); } catch (_) {}
    apply(theme);
  });

  window.addEventListener('pageshow', () => {
    try {
      const saved = localStorage.getItem('gaboma-theme');
      explicit = ['light', 'dark'].includes(saved);
      apply(explicit ? saved : 'light');
    } catch (_) {}
  });
  window.addEventListener('storage', event => {
    if (event.key !== 'gaboma-theme' && event.key !== null) return;
    explicit = ['light', 'dark'].includes(event.newValue);
    apply(explicit ? event.newValue : 'light');
  });
})();
