// Les données, permissions, favoris et paiements sont gérés par Django.
// Ce script améliore uniquement le confort de navigation.
document.addEventListener('DOMContentLoaded', () => {
  document.addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      const search = document.querySelector('input[name="q"]');
      if (search) { event.preventDefault(); search.focus(); search.select(); }
    }
  });
});

// Aperçu des médias avant enregistrement ; toutes les vérifications restent côté Django.
document.querySelectorAll('input[type="file"][name="logo"], input[type="file"][name="banner"]').forEach(input => {
  let localUrl;
  input.addEventListener('change', () => {
    if (localUrl) { URL.revokeObjectURL(localUrl); localUrl = undefined; }
    const field = input.closest('.field');
    if (!field) return;
    let preview = field.querySelector('.upload-preview');
    const file = input.files[0];
    if (!file || !['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      if (preview) preview.remove();
      return;
    }
    if (!preview) {
      preview = document.createElement('img');
      preview.className = 'upload-preview' + (input.name === 'logo' ? ' logo-preview' : '');
      preview.alt = 'Aperçu de votre ' + (input.name === 'logo' ? 'logo' : 'bannière');
      field.append(preview);
    }
    localUrl = URL.createObjectURL(file);
    preview.src = localUrl;
  });
});

// Préférence visuelle seulement ; le catalogue et ses permissions restent côté serveur.
(() => {
  const catalogue = document.querySelector('#app-catalogue');
  const switches = document.querySelectorAll('.layout-choice');
  if (!catalogue) return;
  const applyLayout = mode => {
    if (!['grid', 'list'].includes(mode)) return;
    catalogue.classList.toggle('layout-grid', mode === 'grid');
    catalogue.classList.toggle('layout-list', mode === 'list');
    catalogue.dataset.layout = mode;
    switches.forEach(control => {
      const active = control.dataset.layout === mode;
      control.classList.toggle('selected', active);
      control.setAttribute('aria-pressed', String(active));
    });
    const field = document.querySelector('.search-form input[name="affichage"]');
    if (field) field.value = mode;
  };
  try {
    const explicit = new URL(location.href).searchParams.get('affichage');
    const saved = localStorage.getItem('gaboma-catalogue-layout');
    if (!['grid', 'list'].includes(explicit) && ['grid', 'list'].includes(saved)) applyLayout(saved);
    else localStorage.setItem('gaboma-catalogue-layout', catalogue.dataset.layout);
  } catch (_) { /* Le lien normal reste utilisable si le stockage est désactivé. */ }
  switches.forEach(control => {
    control.addEventListener('keydown', event => {
      if (event.key === ' ') { event.preventDefault(); control.click(); }
    });
    control.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      try { localStorage.setItem('gaboma-catalogue-layout', control.dataset.layout); }
      catch (_) { return; }
      event.preventDefault();
      applyLayout(control.dataset.layout);
      history.replaceState(null, '', control.href);
    });
  });
})();

// Carrousels : défilement natif, tactile, clavier et boutons, sans bibliothèque.
document.querySelectorAll('.app-rail').forEach(rail => {
  const section = rail.closest('.discovery-section');
  const controls = section.querySelector('[data-carousel-controls]');
  const buttons = [...controls.querySelectorAll('button')];
  controls.hidden = false;
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const move = direction => rail.scrollBy({left: direction * (rail.classList.contains('showcase-track') ? rail.clientWidth + 16 : rail.clientWidth * .8), behavior: reduced() ? 'auto' : 'smooth'});
  const update = () => {
    const max = rail.scrollWidth - rail.clientWidth;
    buttons[0].disabled = rail.scrollLeft < 3;
    buttons[1].disabled = rail.scrollLeft >= max - 3;
    controls.hidden = max < 3;
    const counter = section.querySelector('[data-slide-counter]');
    if (counter) counter.textContent = (Math.round(rail.scrollLeft / (rail.clientWidth + 16)) + 1) + ' / ' + rail.children.length;
  };
  buttons.forEach(button => button.addEventListener('click', () => move(Number(button.dataset.direction))));
  rail.addEventListener('keydown', event => {
    if (event.target !== rail || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    event.preventDefault(); move(event.key === 'ArrowLeft' ? -1 : 1);
  });
  let frame;
  rail.addEventListener('scroll', () => {
    if (frame) return;
    frame = requestAnimationFrame(() => { update(); frame = null; });
  }, {passive:true});
  if ('ResizeObserver' in window) new ResizeObserver(update).observe(rail);
  else window.addEventListener('resize', update);
  update();
});

// Montrer/masquer un mot de passe sans modifier les champs envoyés à Django.
document.querySelectorAll('.hub-form input[type="password"]').forEach(input => {
  const wrap = document.createElement('span'); wrap.className = 'password-wrap';
  input.before(wrap); wrap.append(input);
  const button = document.createElement('button'); button.type = 'button';
  button.className = 'password-toggle'; button.setAttribute('aria-pressed', 'false');
  button.setAttribute('aria-label', 'Afficher le mot de passe');
  button.setAttribute('aria-controls', input.id);
  button.innerHTML = '<svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>';
  button.addEventListener('click', () => {
    const visible = input.type === 'password'; input.type = visible ? 'text' : 'password';
    button.setAttribute('aria-pressed', String(visible));
    button.setAttribute('aria-label', visible ? 'Masquer le mot de passe' : 'Afficher le mot de passe');
  });
  wrap.append(button);
});
document.querySelectorAll('.hub-form textarea[maxlength]').forEach(input => {
  const counter = document.createElement('small'); counter.className = 'field-counter';
  counter.id = input.id + '-counter';
  input.setAttribute('aria-describedby', [input.getAttribute('aria-describedby'), counter.id].filter(Boolean).join(' '));
  input.after(counter);
  const update = () => {
    counter.textContent = input.value.length + ' / ' + input.maxLength;
    counter.classList.toggle('near-limit', input.value.length > input.maxLength * .9);
  };
  input.addEventListener('input', update); update();
});

// Indicateurs réels de navigation et d'envoi : aucune attente artificielle.
(() => {
  const progress = document.querySelector('#navigation-progress');
  if (!progress) return;
  let timer;
  const show = () => { clearTimeout(timer); timer = setTimeout(() => { progress.hidden = false; }, 120); };
  const reset = () => {
    clearTimeout(timer); progress.hidden = true;
    document.querySelectorAll('form[aria-busy="true"]').forEach(form => {
      form.removeAttribute('aria-busy'); delete form.dataset.submitting;
      form.querySelectorAll('button[data-busy-disabled]').forEach(button => {
        button.disabled = false; delete button.dataset.busyDisabled;
      });
    });
  };
  window.addEventListener('pageshow', reset);
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.target || link.hasAttribute('download')) return;
    const url = new URL(link.href, location.href);
    if (url.origin !== location.origin || !['http:', 'https:'].includes(url.protocol)) return;
    if (url.pathname === location.pathname && url.search === location.search) return;
    show();
  });
  document.addEventListener('submit', event => {
    if (event.defaultPrevented) return;
    const form = event.target;
    if (form.dataset.submitting) { event.preventDefault(); return; }
    form.dataset.submitting = 'true'; form.setAttribute('aria-busy', 'true'); show();
    // Après capture du submitter par le navigateur, pour conserver ses éventuels paramètres.
    setTimeout(() => form.querySelectorAll('button[type="submit"]').forEach(button => {
      if (!button.disabled) { button.disabled = true; button.dataset.busyDisabled = 'true'; }
    }), 0);
  });
})();
// Apparitions uniques : le contenu reste visible sans JavaScript.
(() => {
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (motion.matches || !('IntersectionObserver' in window)) return;
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      if (!motion.matches) entry.target.classList.add('section-arrived');
      observer.unobserve(entry.target);
    });
  }, {threshold: 0.08});
  document.querySelectorAll('.discovery-banner,.discovery-section,.catalogue-kicker,.creator-banner').forEach(section => observer.observe(section));
})();

// En-tête toujours visible : seuils distincts pour éviter les oscillations.
(() => {
  const header = document.querySelector('.header');
  if (!header) return;
  let queued = false;
  const update = () => {
    const y = Math.max(0, window.scrollY);
    if (y > 96) header.classList.add('is-compact');
    else if (y < 24) header.classList.remove('is-compact');
    queued = false;
  };
  window.addEventListener('scroll', () => {
    if (!queued) { queued = true; requestAnimationFrame(update); }
  }, {passive: true});
  window.addEventListener('pageshow', update);
  update();
})();

// Sélecteurs accessibles : le select Django reste la source du formulaire.
(() => {
  let closeCurrent;
  document.querySelectorAll('.search-form select, .hub-form select').forEach((select, index) => {
    if (select.multiple || select.size > 1) return;
    const labels = [...select.labels];
    const labelText = labels.map(label => { const copy = label.cloneNode(true); copy.querySelectorAll('select,svg').forEach(node=>node.remove()); return copy.textContent.trim(); }).join(' ');
    const wrapper = document.createElement('div'); wrapper.className = 'hub-select';
    const parentLabel = select.closest('label');
    if (parentLabel) parentLabel.after(wrapper); else select.before(wrapper);
    wrapper.append(select);
    const trigger = document.createElement('button'); trigger.type = 'button';
    trigger.className = 'hub-select-trigger'; trigger.id = (select.id || 'hub-select-' + index) + '-trigger';
    trigger.setAttribute('role', 'combobox'); trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false'); trigger.setAttribute('aria-required', String(select.required));
    labels.forEach((label, i) => { if (!label.id) label.id = trigger.id + '-label-' + i; label.htmlFor = trigger.id; });
    trigger.setAttribute('aria-label', labelText || 'Choisir une option');
    if (select.getAttribute('aria-describedby')) trigger.setAttribute('aria-describedby', select.getAttribute('aria-describedby'));
    const text = document.createElement('span'); trigger.append(text);
    const menu = document.createElement('div'); menu.id = trigger.id + '-options';
    menu.className = 'hub-select-menu'; menu.hidden = true; menu.setAttribute('role', 'listbox');
    menu.setAttribute('aria-label', labelText || 'Options');
    trigger.setAttribute('aria-controls', menu.id);
    const options = [...select.options]; let active = Math.max(0, select.selectedIndex); let buffer = '', typedAt = 0;
    const rows = options.map((option, i) => {
      const row = document.createElement('div'); row.className = 'hub-select-option'; row.tabIndex = -1; row.id = menu.id + '-' + i;
      row.setAttribute('role', 'option'); row.setAttribute('aria-disabled', String(option.disabled)); row.textContent = option.text;
      row.addEventListener('click', () => choose(i)); menu.append(row); return row;
    });
    function sync() {
      text.textContent = select.selectedOptions[0]?.text || 'Choisir'; trigger.disabled = select.disabled;
      rows.forEach((row, i) => row.setAttribute('aria-selected', String(i === select.selectedIndex)));
      trigger.setAttribute('aria-invalid', select.getAttribute('aria-invalid') || 'false');
    }
    function highlight(i) {
      active = i; rows.forEach((row, j) => row.classList.toggle('is-focused', j === i));
      trigger.setAttribute('aria-activedescendant', rows[i]?.id || '');
      rows[i]?.scrollIntoView({block:'nearest'});
    }
    function close() { menu.hidden = true; trigger.setAttribute('aria-expanded', 'false'); trigger.removeAttribute('aria-activedescendant'); }
    function open() {
      if (closeCurrent) closeCurrent(); closeCurrent = close;
      menu.hidden = false; trigger.setAttribute('aria-expanded', 'true'); highlight(Math.max(0, select.selectedIndex));
    }
    function choose(i) {
      if (options[i].disabled) return;
      select.selectedIndex = i; select.dispatchEvent(new Event('input', {bubbles:true}));
      select.dispatchEvent(new Event('change', {bubbles:true})); sync(); close(); trigger.focus();
    }
    trigger.addEventListener('click', () => menu.hidden ? open() : close());
    trigger.addEventListener('keydown', event => {
      if (event.key === 'Tab') { close(); return; }
      if (event.key === 'Escape') { event.preventDefault(); close(); return; }
      if (['Enter', ' '].includes(event.key)) { event.preventDefault(); menu.hidden ? open() : choose(active); return; }
      if (['ArrowDown','ArrowUp','Home','End'].includes(event.key)) {
        event.preventDefault(); if (menu.hidden) { open(); return; }
        const enabled = options.map((o,i)=>o.disabled ? -1 : i).filter(i=>i>=0);
        const at = enabled.indexOf(active);
        const next = event.key === 'Home' ? enabled[0] : event.key === 'End' ? enabled.at(-1) : enabled[Math.max(0,Math.min(enabled.length-1,at+(event.key==='ArrowDown'?1:-1)))];
        if (next !== undefined) highlight(next); return;
      }
      if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
        event.preventDefault(); const now = Date.now(); buffer = now-typedAt>700 ? event.key : buffer+event.key; typedAt = now;
        if (menu.hidden) open(); const found = options.findIndex(o=>!o.disabled && o.text.toLocaleLowerCase().startsWith(buffer.toLocaleLowerCase()));
        if (found >= 0) highlight(found);
      }
    });
    wrapper.addEventListener('focusout', event => { if (!wrapper.contains(event.relatedTarget)) close(); });
    document.addEventListener('click', event => { if (!wrapper.contains(event.target)) close(); });
    select.addEventListener('change', sync);
    select.addEventListener('invalid', event => { event.preventDefault(); trigger.setAttribute('aria-invalid','true'); trigger.focus(); });
    select.form?.addEventListener('reset', () => setTimeout(() => { sync(); close(); },0));
    if (parentLabel) {
      const caption = document.createElement('span'); caption.className = 'hub-select-caption'; caption.textContent = labelText; wrapper.append(caption);
    }
    wrapper.append(trigger,menu); select.classList.add('hub-select-native'); select.tabIndex = -1; select.setAttribute('aria-hidden','true'); sync();
  });
})();
