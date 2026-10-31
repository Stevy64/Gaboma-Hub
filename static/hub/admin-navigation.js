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
 if (sidebar) {
  const railButton = sidebar.querySelector('.console-rail-toggle');
  const desktop = matchMedia('(min-width:1001px)');
  const railKey = 'hub-console-rail';
  sidebar.querySelectorAll('.console-nav-link').forEach((link) => {
   const label = link.querySelector('span:not(.nav-ico):not(.nav-count)');
   if (label && !link.title) link.title = label.textContent.trim();
  });
  function railOn() {
   try { return localStorage.getItem(railKey) === '1'; } catch { return false; }
  }
  function paintRail() {
   const on = railOn() && desktop.matches;
   document.documentElement.classList.toggle('console-rail', on);
   if (!railButton) return;
   railButton.setAttribute('aria-pressed', String(on));
   railButton.setAttribute('aria-label', on ? 'Déplier le menu' : 'Réduire le menu');
  }
  paintRail();
  railButton?.addEventListener('click', () => {
   try { localStorage.setItem(railKey, railOn() ? '0' : '1'); } catch { /* le menu se replie quand même pour cette visite */ }
   paintRail();
  });
  desktop.addEventListener('change', paintRail);
 }

 const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
 document.querySelectorAll('[data-count]').forEach((el) => {
  const target = parseInt((el.getAttribute('data-count') || '').replace(/\s/g, ''), 10);
  if (!Number.isFinite(target) || reduced || target <= 0 || target > 99999) return;
  let t0 = 0;
  const duration = 560;
  const step = (ts) => {
   if (!t0) t0 = ts;
   const p = Math.min(1, (ts - t0) / duration);
   const eased = 1 - Math.pow(1 - p, 3);
   el.textContent = String(Math.round(target * eased));
   if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
 });

 const jumpNav = document.querySelector('#console-form-jump');
 const fieldsets = [...document.querySelectorAll('form fieldset.module')];
 if (jumpNav && fieldsets.length > 1) {
  fieldsets.forEach((fs, idx) => {
   const heading = fs.querySelector('.fieldset-heading, h2, h3');
   if (!heading) return;
   if (!fs.id) fs.id = `console-section-${idx + 1}`;
   const a = document.createElement('a');
   const full = heading.textContent.trim();
   a.href = `#${fs.id}`;
   a.dataset.full = full;
   a.setAttribute('aria-label', full);
   a.textContent = full;
   jumpNav.append(a);
  });
  if (jumpNav.children.length > 1) jumpNav.hidden = false;
  const steps = [...jumpNav.children];
  const narrow = matchMedia('(max-width: 767px)');
  const wizard = document.body.classList.contains('model-application') && document.body.classList.contains('changeform-add');
  const submit = document.querySelector('.submit-row');
  const chipLabel = (full) => (narrow.matches ? full.split('&')[0].trim() : full);
  const fitChips = () => steps.forEach((link) => { link.textContent = chipLabel(link.dataset.full || link.textContent); });
  let bar = null;
  const show = (index, scroll) => {
   const i = Math.max(0, Math.min(steps.length - 1, index));
   const stepped = wizard && narrow.matches;
   fitChips();
   fieldsets.forEach((fs, n) => fs.classList.toggle('is-step-off', stepped && n !== i));
   steps.forEach((link, n) => {
    if (stepped) link.setAttribute('aria-current', n === i ? 'step' : 'false');
    else link.removeAttribute('aria-current');
   });
   if (submit) submit.classList.toggle('is-waiting', stepped && i !== steps.length - 1);
   if (bar) {
    bar.hidden = !stepped;
    const label = bar.querySelector('.console-stepbar-label');
    if (label) label.textContent = `${i + 1} / ${steps.length}`;
    const prev = bar.querySelector('[data-step="prev"]');
    const next = bar.querySelector('[data-step="next"]');
    if (prev) prev.disabled = i === 0;
    if (next) next.hidden = i === steps.length - 1;
    bar.classList.toggle('is-last', i === steps.length - 1);
   }
   if (stepped && scroll) {
    document.querySelector('.console-top')?.scrollIntoView({ block: 'start' });
    steps[i]?.scrollIntoView({ inline: 'center', block: 'nearest' });
   }
  };
  if (wizard) {
   bar = document.createElement('div');
   bar.className = 'console-stepbar';
   bar.hidden = true;
   bar.innerHTML = '<p class="console-stepbar-label"></p><div class="console-stepbar-actions"><button type="button" data-step="prev">Retour</button><button type="button" class="is-next" data-step="next">Continuer</button></div>';
   (submit || jumpNav).before(bar);
   bar.addEventListener('click', (event) => {
    const button = event.target.closest('[data-step]');
    if (!button) return;
    const current = steps.findIndex((link) => link.getAttribute('aria-current') === 'step');
    show((current < 0 ? 0 : current) + (button.dataset.step === 'next' ? 1 : -1), true);
   });
  }
  narrow.addEventListener('change', () => {
   fitChips();
   if (wizard) show(steps.findIndex((link) => link.getAttribute('aria-current') === 'step'));
  });
  jumpNav.addEventListener('click', (event) => {
   const link = event.target.closest('a');
   if (!link || !jumpNav.contains(link)) return;
   const index = steps.indexOf(link);
   if (index < 0) return;
   if (wizard && narrow.matches) {
    event.preventDefault();
    show(index, true);
   }
  });
  fitChips();
  if (wizard) show(fieldsets.findIndex((fs) => fs.querySelector('.errorlist')));
 }

 const loader = document.querySelector('#hub-loader');
 const arm = () => {
  if (progress) { progress.hidden = false; progress.classList.add('is-active'); }
  if (loader) loader.hidden = false;
 };
 const disarm = () => {
  if (progress) { progress.hidden = true; progress.classList.remove('is-active'); }
  if (loader) loader.hidden = true;
 };
 window.addEventListener('pageshow', () => {
  disarm();
  document.querySelectorAll('form[aria-busy="true"]').forEach((form) => form.removeAttribute('aria-busy'));
 });
 document.addEventListener('click', (event) => {
  if (event.defaultPrevented) return;
  const link = event.target.closest('a[href]');
  if (!link || link.target || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
  let url;
  try { url = new URL(link.href, location.origin); } catch { return; }
  if (link.closest('#result_list tbody tr')) return;
  if (url.origin !== location.origin || url.pathname === location.pathname && url.search === location.search) return;
  if (link.getAttribute('href').startsWith('#')) return;
  arm();
 });
 document.addEventListener('submit', (event) => {
  if (event.defaultPrevented) return;
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || form.dataset.submitting) { event.preventDefault(); return; }
  form.dataset.submitting = 'true';
  form.setAttribute('aria-busy', 'true');
  arm();
 });
})();

(() => {
 const sheet = document.querySelector('#console-sheet');
 if (!sheet) return;
 const card = sheet.querySelector('.console-sheet-card');
 const kicker = document.querySelector('#console-sheet-kicker');
 const title = document.querySelector('#console-sheet-title');
 const body = document.querySelector('#console-sheet-body');
 const actions = document.querySelector('#console-sheet-actions');
 let restore = null;
 let lastFocus = null;
 let closing = false;

 let epoch = 0;
 function finishClose() {
  if (!closing) return;
  closing = false;
  epoch += 1;
  sheet.hidden = true;
  sheet.classList.remove('is-closing');
  card.style.transform = '';
  if (restore) { restore(); restore = null; }
  body.replaceChildren();
  actions.replaceChildren();
  document.body.classList.remove('console-sheet-open');
  if (lastFocus && document.contains(lastFocus)) lastFocus.focus();
 }

 function closeSheet() {
  if (sheet.hidden || closing) return;
  closing = true;
  sheet.classList.add('is-closing');
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { finishClose(); return; }
  const timer = setTimeout(finishClose, 420);
  card.addEventListener('animationend', (event) => {
   if (event.target !== card) return;
   clearTimeout(timer);
   finishClose();
  });
 }

 function openSheet({ kickerText, titleText, node, action, secondaryAction }) {
  if (!sheet.hidden) {
   closing = true;
   finishClose();
  }
  lastFocus = document.activeElement;
  kicker.textContent = kickerText || 'Détail';
  title.textContent = titleText || '—';
  let avatar = sheet.querySelector('.console-sheet-avatar');
  if (!avatar) {
   avatar = document.createElement('div');
   avatar.className = 'console-sheet-avatar';
   avatar.setAttribute('aria-hidden', 'true');
   sheet.querySelector('.console-sheet-head').prepend(avatar);
  }
  avatar.textContent = (titleText || '?').trim().charAt(0).toUpperCase() || '?';
  body.replaceChildren(node || '');
  actions.replaceChildren();
  if (secondaryAction) {
   const sec = document.createElement('a');
   sec.className = 'console-sheet-go is-secondary';
   sec.href = secondaryAction.href;
   sec.textContent = secondaryAction.label;
   actions.append(sec);
  }
  if (action) {
   const link = document.createElement('a');
   link.className = 'console-sheet-go';
   link.href = action.href;
   link.textContent = action.label;
   actions.append(link);
  }
  sheet.hidden = false;
  document.body.classList.add('console-sheet-open');
  sheet.querySelector('.console-sheet-x').focus();
 }

 document.addEventListener('click', (event) => {
  const link = event.target.closest('a.add-related');
  if (!link || link.closest('#console-sheet')) return;
  const href = link.getAttribute('href') || '';
  let endpoint = '';
  let titleText = 'Ajouter';
  let kickerText = 'Ajout rapide';
  if (href.includes('/hub/category/add/')) {
   endpoint = '/admin/hub/application/rapide/categorie/';
   titleText = 'Nouvelle catégorie';
   kickerText = 'Catégorie';
  } else if (href.includes('/auth/user/add/')) {
   endpoint = '/admin/hub/application/rapide/deposant/';
   titleText = 'Nouveau déposant';
   kickerText = 'Déposant';
  } else return;
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();
  openQuick(link, endpoint, kickerText, titleText);
 }, true);

 function showFieldErrors(form, errors) {
  form.querySelectorAll('.errorlist').forEach((node) => node.remove());
  Object.entries(errors || {}).forEach(([name, messages]) => {
   const list = document.createElement('ul');
   list.className = 'errorlist';
   (Array.isArray(messages) ? messages : [messages]).forEach((message) => {
    const item = document.createElement('li');
    item.textContent = typeof message === 'string' ? message : (message.message || '');
    list.append(item);
   });
   const field = form.querySelector(`[name="${name}"]`);
   (field ? field.closest('p') || field : form).before(list);
  });
 }

 async function openQuick(link, endpoint, kickerText, titleText) {
  const hold = document.createElement('p');
  hold.className = 'console-related-status';
  hold.textContent = 'Chargement…';
  openSheet({ kickerText, titleText, node: hold });
  const stamp = epoch;
  let response;
  try {
   response = await fetch(endpoint, { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } });
  } catch {
   if (stamp !== epoch) return;
   hold.textContent = 'Le formulaire n’a pas pu s’ouvrir. Réessayez.';
   return;
  }
  if (stamp !== epoch) return;
  if (!response.ok) {
   hold.textContent = 'Ce formulaire n’est pas disponible.';
   return;
  }
  const html = await response.text();
  if (stamp !== epoch) return;
  const form = new DOMParser().parseFromString(html, 'text/html').querySelector('form');
  if (!form) {
   hold.textContent = 'Formulaire introuvable.';
   return;
  }
  openSheet({ kickerText, titleText, node: form });
  const save = document.createElement('button');
  save.type = 'button';
  save.className = 'console-sheet-go';
  save.textContent = 'Enregistrer';
  actions.append(save);
  save.addEventListener('click', async () => {
   save.disabled = true;
   let payload;
   try {
    const posted = await fetch(endpoint, {
     method: 'POST',
     body: new FormData(form),
     credentials: 'same-origin',
     headers: { 'X-Requested-With': 'fetch' },
    });
    payload = await posted.json();
   } catch {
    save.disabled = false;
    showFieldErrors(form, { __all__: ['L’enregistrement n’a pas abouti. Réessayez.'] });
    return;
   }
   if (!payload.ok) {
    showFieldErrors(form, payload.errors || {});
    save.disabled = false;
    return;
   }
   const select = link.closest('.related-widget-wrapper')?.querySelector('select');
   if (select) {
    const value = String(payload.value);
    let option = [...select.options].find((item) => item.value === value);
    if (!option) {
     option = new Option(payload.label, value);
     select.add(option);
    }
    select.value = value;
    select.dispatchEvent(new Event('change', { bubbles: true }));
   }
   closeSheet();
  });
 }

 sheet.querySelectorAll('[data-sheet-close]').forEach((button) => button.addEventListener('click', closeSheet));
 document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && !sheet.hidden) closeSheet(); });

 let startY = 0;
 let dragging = false;
 card.addEventListener('pointerdown', (event) => {
  if (event.button !== 0 || !event.target.closest('.console-sheet-grab')) return;
  dragging = true;
  startY = event.clientY;
  card.style.transition = 'none';
 });
 card.addEventListener('pointermove', (event) => {
  if (!dragging) return;
  card.style.transform = `translateY(${Math.max(0, event.clientY - startY)}px)`;
 });
 function endDrag(event) {
  if (!dragging) return;
  dragging = false;
  const distance = Math.max(0, event.clientY - startY);
  card.style.transition = '';
  card.style.transform = '';
  if (distance > 90) closeSheet();
 }
 card.addEventListener('pointerup', endDrag);
 card.addEventListener('pointercancel', endDrag);

 const filter = document.querySelector('#changelist-filter');
 if (filter) {
  const anchor = document.createElement('div');
  anchor.id = 'console-filter-anchor';
  filter.before(anchor);
  const launch = document.createElement('button');
  launch.type = 'button';
  launch.className = 'console-filter-launch';
  const activeCount = filter.querySelectorAll('li.selected').length - filter.querySelectorAll('details').length;
  launch.textContent = activeCount > 0 ? `Filtres (${activeCount})` : 'Affiner & filtrer';
  const actionsBar = document.querySelector('#changelist-form .actions');
  const searchBar = document.querySelector('#changelist-search .console-search-bar');
  if (searchBar) searchBar.append(launch);
  else if (actionsBar) actionsBar.prepend(launch);
  else (document.querySelector('#toolbar') || document.querySelector('.console-top'))?.after(launch);
  launch.addEventListener('click', () => {
   filter.classList.add('is-in-sheet');
   restore = () => { filter.classList.remove('is-in-sheet'); anchor.after(filter); };
   openSheet({ kickerText: 'Affiner la liste', titleText: 'Filtres', node: filter });
  });
 }

 document.querySelectorAll('#result_list tbody tr').forEach((row) => {
  const link = row.querySelector('th a, td a');
  if (!link) return;
  const titleText = link.textContent.trim();
  if (titleText && !link.dataset.initial) {
   link.dataset.initial = titleText.charAt(0).toUpperCase();
  }
  const headers = [...document.querySelectorAll('#result_list thead th')];
  [...row.children].forEach((cell, index) => {
   const label = headers[index]?.innerText.trim();
   if (label) cell.dataset.label = label;
  });
  row.classList.add('console-row');
  row.tabIndex = 0;
  const extraLink = [...row.querySelectorAll('td a')].find((a) => a !== link);
  const show = () => {
   const list = document.createElement('div');
   list.className = 'console-sheet-fields';
   [...row.children].forEach((cell) => {
    if (cell.querySelector('input[type="checkbox"]')) return;
    if (extraLink && cell.contains(extraLink)) return;
    const label = cell.dataset.label;
    const input = cell.querySelector('input:not([type="hidden"]), select, textarea');
    const value = input ? (input.value || input.options?.[input.selectedIndex]?.text || '').trim() : cell.innerText.trim();
    if (!label || !value || (cell.contains(link) && value === titleText)) return;
    const item = document.createElement('div');
    item.className = 'console-sheet-field';
    const term = document.createElement('em');
    term.textContent = label;
    const detail = document.createElement('strong');
    detail.textContent = value;
    item.append(term, detail);
    list.append(item);
   });
   openSheet({
    kickerText: document.querySelector('#console-sidebar a[aria-current="page"]')?.textContent.trim() || 'Liste',
    titleText,
    node: list,
    action: { href: link.href, label: 'Ouvrir la fiche' },
    secondaryAction: extraLink ? { href: extraLink.href, label: extraLink.textContent.replace('→', '').trim() } : null,
   });
  };
  row.addEventListener('click', (event) => {
   if (event.target.closest('button, input, label, select')) return;
   const clicked = event.target.closest('a');
   if (clicked && clicked !== link) return;
   event.preventDefault();
   show();
  }, true);
  row.addEventListener('keydown', (event) => {
   if (event.target !== row || (event.key !== 'Enter' && event.key !== ' ')) return;
   event.preventDefault();
   show();
  });
 });

 document.querySelectorAll('.flow-grid > .flow-card').forEach((card) => {
  const link = card.querySelector('a.flow-button');
  if (!link) return;
  card.classList.add('console-row');
  card.tabIndex = 0;
  const show = () => {
   const list = document.createElement('div');
   list.className = 'console-sheet-fields';
   const cat = card.querySelector('.flow-card-heading span')?.textContent.trim();
   const status = card.querySelector('.console-pill, .flow-badge')?.textContent.trim();
   if (cat) {
    const item = document.createElement('div');
    item.className = 'console-sheet-field';
    const em = document.createElement('em');
    em.textContent = 'Catégorie';
    const st = document.createElement('strong');
    st.textContent = cat;
    item.append(em, st);
    list.append(item);
   }
   if (status) {
    const item = document.createElement('div');
    item.className = 'console-sheet-field';
    const em = document.createElement('em');
    em.textContent = 'Statut';
    const st = document.createElement('strong');
    st.textContent = status;
    item.append(em, st);
    list.append(item);
   }
   card.querySelectorAll('.flow-meta').forEach((node) => {
    const item = document.createElement('div');
    item.className = 'console-sheet-field';
    const em = document.createElement('em');
    em.textContent = node.dataset.label || 'Suivi';
    const detail = document.createElement('strong');
    detail.textContent = node.textContent.trim();
    item.append(em, detail);
    list.append(item);
   });
   openSheet({
    kickerText: 'Dossier de soumission',
    titleText: card.querySelector('h2')?.textContent.trim() || 'Dossier',
    node: list,
    action: { href: link.href, label: 'Examiner le dossier' },
   });
  };
  card.addEventListener('click', (event) => {
   if (event.target.closest('a, button, input, label, select')) return;
   show();
  });
  card.addEventListener('keydown', (event) => {
   if (event.target !== card || (event.key !== 'Enter' && event.key !== ' ')) return;
   event.preventDefault();
   show();
  });
 });

 const flow = document.querySelector('.flow-options');
 flow?.querySelector('summary')?.addEventListener('click', (event) => {
  event.preventDefault();
  const controls = flow.querySelector('.flow-controls');
  const form = flow.closest('form');
  if (!controls || !form) return;
  if (!form.id) form.id = 'console-flow-form';
  controls.querySelectorAll('input, select, textarea, button').forEach((field) => field.setAttribute('form', form.id));
  restore = () => flow.append(controls);
  openSheet({ kickerText: 'Suivi', titleText: 'Filtres et affichage', node: controls });
 });

 const bulk = document.getElementById('flow-bulk');
 const pageBox = document.getElementById('flow-select-page');
 const acrossInput = document.getElementById('flow-select-across');
 const acrossButton = document.getElementById('flow-across');
 pageBox?.addEventListener('change', () => {
  document.querySelectorAll('.flow-select').forEach((box) => { box.checked = pageBox.checked; });
  if (!pageBox.checked && acrossInput) acrossInput.value = '0';
  acrossButton?.classList.remove('is-on');
  acrossButton?.setAttribute('aria-pressed', 'false');
 });
 acrossButton?.addEventListener('click', () => {
  if (!acrossInput) return;
  const on = acrossInput.value !== '1';
  acrossInput.value = on ? '1' : '0';
  acrossButton.classList.toggle('is-on', on);
  acrossButton.setAttribute('aria-pressed', on ? 'true' : 'false');
 });
 bulk?.addEventListener('submit', (event) => {
  if (acrossInput?.value !== '1') return;
  const total = acrossInput.dataset.total || '';
  const label = bulk.querySelector('#flow-action')?.selectedOptions?.[0]?.textContent?.trim() || 'Cette action';
  if (!window.confirm(`${label} sur les ${total} dossiers de ce filtre ?`)) event.preventDefault();
 });

 const account = document.querySelector('.console-account');
 account?.querySelector('summary')?.addEventListener('click', (event) => {
  const menu = account.querySelector('.console-account-menu');
  if (!menu) return;
  event.preventDefault();
  openSheet({ kickerText: 'Session', titleText: 'Mon compte', node: menu.cloneNode(true) });
 });
})();
