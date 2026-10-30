(() => {
 const toggle = document.querySelector('.console-menu-toggle');
 const sidebar = document.querySelector('#console-sidebar');
 const scrim = document.querySelector('.console-menu-scrim');
 const progress = document.querySelector('.console-progress');
 if (sidebar && toggle && scrim) {
  const close = sidebar.querySelector('.console-menu-close');
  const mobile = matchMedia('(max-width:1000px)');
  const nav = sidebar.querySelector('nav');
  function sync() { sidebar.inert = mobile.matches && !document.body.classList.contains('console-menu-open'); }
  mobile.addEventListener('change', () => {
   document.body.classList.remove('console-menu-open');
   scrim.hidden = true;
   toggle.setAttribute('aria-expanded', 'false');
   sync();
  });
  sync();
  function setOpen(open) {
   document.body.classList.toggle('console-menu-open', open);
   toggle.setAttribute('aria-expanded', String(open));
   scrim.hidden = !open;
   sync();
   if (open) close.focus();
   else toggle.focus();
  }
  toggle.addEventListener('click', () => setOpen(!document.body.classList.contains('console-menu-open')));
  close.addEventListener('click', () => setOpen(false));
  scrim.addEventListener('click', () => setOpen(false));
  document.addEventListener('keydown', (event) => {
   if (!document.body.classList.contains('console-menu-open')) return;
   if (event.key === 'Escape') setOpen(false);
   if (event.key !== 'Tab') return;
   const nodes = [...sidebar.querySelectorAll('a,button')];
   const first = nodes[0];
   const last = nodes[nodes.length - 1];
   if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
   else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  const path = location.pathname.endsWith('/') ? location.pathname : location.pathname + '/';
  let best = null;
  sidebar.querySelectorAll('a[href]').forEach((link) => {
   let href = '';
   try { href = new URL(link.getAttribute('href'), location.origin).pathname; } catch { return; }
   if (!href.endsWith('/')) href += '/';
   const same = path === href;
   const nested = href !== '/admin/' && path.startsWith(href);
   if ((same || nested) && (!best || href.length > best.length)) best = { link, length: href.length };
   link.addEventListener('pointerenter', () => {
    if (link.dataset.prefetched || link.origin !== location.origin) return;
    const hint = document.createElement('link');
    hint.rel = 'prefetch';
    hint.href = link.href;
    document.head.appendChild(hint);
    link.dataset.prefetched = '1';
   }, { once: true });
  });
  if (best) {
   best.link.setAttribute('aria-current', 'page');
   best.link.scrollIntoView({ block: 'nearest' });
  }
  if (nav) {
   const key = 'hub-console-nav-scroll';
   try {
    const saved = Number(sessionStorage.getItem(key) || 0);
    if (saved) nav.scrollTop = saved;
    nav.addEventListener('scroll', () => sessionStorage.setItem(key, String(nav.scrollTop)), { passive: true });
   } catch { /* navigation reste utilisable sans mémoire de défilement */ }
  }
 }
 if (!progress) return;
 window.addEventListener('pageshow', () => { progress.hidden = true; progress.classList.remove('is-active'); });
 document.addEventListener('click', (event) => {
  const link = event.target.closest('a[href]');
  if (!link || link.target || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
  let url;
  try { url = new URL(link.href, location.origin); } catch { return; }
  if (url.origin !== location.origin || url.pathname === location.pathname && url.search === location.search) return;
  if (link.getAttribute('href').startsWith('#')) return;
  progress.hidden = false;
  progress.classList.add('is-active');
 });
})();
