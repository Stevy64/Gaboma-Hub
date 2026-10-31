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
  const loader = document.querySelector('#hub-loader');
  if (!progress && !loader) return;
  const show = () => {
    if (progress) progress.hidden = false;
    if (loader) loader.hidden = false;
  };
  const reset = () => {
    if (progress) progress.hidden = true;
    if (loader) loader.hidden = true;
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
    if (!link || link.closest('[data-legal]') || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.target || link.hasAttribute('download')) return;
    const url = new URL(link.href, location.href);
    if (url.origin !== location.origin || !['http:', 'https:'].includes(url.protocol)) return;
    if (url.pathname === location.pathname && url.search === location.search) return;
    show();
  });
  document.addEventListener('submit', event => {
    if (event.defaultPrevented) return;
    const form = event.target;
    if (form.getAttribute('action')?.includes('/favoris/')) return;
    if (form.dataset.submitting) { event.preventDefault(); return; }
    form.dataset.submitting = 'true'; form.setAttribute('aria-busy', 'true'); show();
    // Après capture du submitter par le navigateur, pour conserver ses éventuels paramètres.
    setTimeout(() => form.querySelectorAll('button[type="submit"]').forEach(button => {
      if (!button.disabled) { button.disabled = true; button.dataset.busyDisabled = 'true'; }
    }), 0);
  });
})();

// Le cœur se met à jour sur place : pas de rechargement de la page.
(() => {
  const sameAction = (form, action) => {
    try { return new URL(form.action, location.href).pathname === action; }
    catch { return false; }
  };
  const paint = (button, liked, pop) => {
    button.classList.toggle('is-favorite', liked);
    button.setAttribute('aria-pressed', liked ? 'true' : 'false');
    if (button.dataset.name) {
      button.setAttribute('aria-label', liked ? `Retirer ${button.dataset.name} des favoris` : `Ajouter ${button.dataset.name} aux favoris`);
    }
    const label = button.querySelector('.favorite-label');
    if (label) label.textContent = liked ? 'Dans mes favoris' : 'Ajouter aux favoris';
    const icon = button.querySelector('.ui-icon');
    if (!icon) return;
    icon.classList.remove('is-pop');
    if (pop && liked) {
      icon.addEventListener('animationend', () => icon.classList.remove('is-pop'), { once: true });
      icon.offsetWidth;
      icon.classList.add('is-pop');
    }
  };
  document.addEventListener('submit', async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.getAttribute('action')?.includes('/favoris/')) return;
    event.preventDefault();
    event.stopPropagation();
    const action = new URL(form.action, location.href).pathname;
    const forms = [...document.querySelectorAll('form')].filter(other => sameAction(other, action));
    if (forms.some(other => other.dataset.pending)) return;
    forms.forEach(other => { other.dataset.pending = 'true'; });
    const buttons = forms.map(other => other.querySelector('button')).filter(Boolean);
    const source = form.querySelector('button');
    const liked = source ? !source.classList.contains('is-favorite') : true;
    buttons.forEach(button => paint(button, liked, button === source));
    try {
      const response = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { 'X-Requested-With': 'fetch', 'Accept': 'application/json' },
        credentials: 'same-origin',
      });
      if (response.redirected || !response.headers.get('content-type')?.includes('json')) {
        location.assign(response.url || form.querySelector('[name=next]')?.value || '/');
        return;
      }
      if (!response.ok) throw new Error('favorite');
      const data = await response.json();
      buttons.forEach(button => {
        if (button.classList.contains('is-favorite') !== !!data.liked) paint(button, !!data.liked, false);
      });
      if (!data.liked && new URLSearchParams(location.search).get('vue') === 'favoris') {
        document.querySelectorAll('#app-catalogue .app-card').forEach(card => {
          if (card.querySelector('form') && sameAction(card.querySelector('form'), action)) card.remove();
        });
        const grid = document.querySelector('#app-catalogue');
        const count = document.querySelector('#applications .count');
        if (count) count.textContent = String(grid ? grid.querySelectorAll('.app-card').length : 0);
        if (grid && !grid.querySelector('.app-card') && !grid.querySelector('.empty-state')) {
          const empty = document.createElement('div');
          empty.className = 'empty-state full-grid';
          const title = document.createElement('h3');
          title.textContent = 'Choisissez vos essentiels.';
          const copy = document.createElement('p');
          copy.textContent = 'Touchez le cœur d’une application pour la retrouver ici.';
          empty.append(title, copy);
          grid.append(empty);
        }
      }
    } catch {
      buttons.forEach(button => paint(button, !liked, false));
    } finally {
      forms.forEach(other => { delete other.dataset.pending; });
    }
  }, true);
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
  document.querySelectorAll('.discovery-banner,.discovery-section,.catalogue-kicker,.creator-banner,.apps-section').forEach(section => observer.observe(section));
})();

(() => {
  const jumps = document.querySelector('.section-jumps');
  if (!jumps || !('IntersectionObserver' in window)) return;
  const links = [...jumps.querySelectorAll('a[href^="#"]')];
  const sections = links.map(link => document.querySelector(link.getAttribute('href'))).filter(Boolean);
  if (!sections.length) return;
  const mark = (id) => links.forEach(link => {
    if (link.getAttribute('href') === '#' + id) link.setAttribute('aria-current', 'true');
    else link.removeAttribute('aria-current');
  });
  const spy = new IntersectionObserver(entries => {
    const visible = entries.filter(entry => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (visible) mark(visible.target.id);
  }, { rootMargin: '-20% 0px -55% 0px', threshold: [0.15, 0.4] });
  sections.forEach(section => spy.observe(section));
  links.forEach(link => link.addEventListener('click', () => mark(link.getAttribute('href').slice(1))));
})();

// Feuilles basses : filtres du catalogue et aperçu d'une application.
(() => {
  const sheet = document.querySelector('#hub-sheet');
  if (!sheet) return;
  const card = sheet.querySelector('.hub-sheet-card');
  const body = document.querySelector('#hub-sheet-body');
  const actions = document.querySelector('#hub-sheet-actions');
  const kicker = document.querySelector('#hub-sheet-kicker');
  const title = document.querySelector('#hub-sheet-title');
  if (!card || !body || !actions) return;
  let restore = null;
  let closing = false;
  const finish = () => {
    if (!closing) return;
    closing = false;
    sheet.hidden = true;
    sheet.classList.remove('is-closing');
    if (restore) { restore(); restore = null; }
    body.replaceChildren();
    actions.replaceChildren();
    document.body.classList.remove('hub-sheet-open');
  };
  const close = () => {
    if (sheet.hidden || closing) return;
    closing = true;
    sheet.classList.add('is-closing');
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) { finish(); return; }
    const timer = setTimeout(finish, 420);
    card.addEventListener('animationend', (event) => {
      if (event.target !== card) return;
      clearTimeout(timer);
      finish();
    });
  };
  const openSheet = ({ kickerText, titleText, node, actionNodes, restoreNode }) => {
    if (!sheet.hidden) { closing = true; finish(); }
    restore = restoreNode || null;
    kicker.textContent = kickerText;
    title.textContent = titleText;
    body.replaceChildren(node);
    actions.replaceChildren(...(actionNodes || []));
    sheet.hidden = false;
    document.body.classList.add('hub-sheet-open');
    sheet.querySelector('.hub-sheet-x').focus();
  };
  document.addEventListener('click', (event) => {
    const legal = event.target.closest('[data-legal]');
    if (legal) {
      event.preventDefault();
      event.stopPropagation();
      const source = document.querySelector(legal.dataset.legal === 'faq' ? '#hub-legal-faq' : '#hub-legal-terms');
      if (!source) { location.href = legal.href; return; }
      const node = source.cloneNode(true);
      node.hidden = false;
      openSheet({
        kickerText: 'Gaboma Hub',
        titleText: legal.dataset.legal === 'faq' ? 'Questions fréquentes' : 'Conditions générales d’utilisation',
        node,
      });
      return;
    }
    const install = event.target.closest('[data-install-hub]');
    if (!install) return;
    event.preventDefault();
    const agent = navigator.userAgent || '';
    const platform = /android/i.test(agent) ? 'android' : /iphone|ipad|ipod/i.test(agent) ? 'ios' : 'desktop';
    const native = platform === 'android' ? install.dataset.android : platform === 'ios' ? install.dataset.ios : '';
    if (!native && window.hubInstallPrompt) {
      const prompt = window.hubInstallPrompt;
      window.hubInstallPrompt = null;
      prompt.prompt();
      return;
    }
    const node = document.createElement('div');
    node.className = 'install-sheet';
    const text = document.createElement('p');
    if (native) {
      text.textContent = platform === 'android'
        ? 'L’application Android de Gaboma Hub est disponible. Vous pouvez l’installer sur ce téléphone.'
        : 'L’application Apple de Gaboma Hub est disponible. Vous pouvez la télécharger sur cet appareil.';
      const link = document.createElement('a');
      link.className = 'hub-sheet-go';
      link.href = native;
      link.textContent = platform === 'android' ? 'Télécharger l’application Android' : 'Télécharger l’application Apple';
      node.append(text, link);
    } else if (platform === 'ios') {
      text.textContent = 'Sur iPhone, ouvrez le menu Partager du navigateur, puis choisissez « Sur l’écran d’accueil ».';
      node.append(text);
    } else {
      text.textContent = 'Aucune application native n’est proposée pour cet appareil. Utilisez le menu du navigateur, puis « Installer l’application » ou « Ajouter à l’écran d’accueil ».';
      node.append(text);
    }
    openSheet({ kickerText: 'Installation', titleText: 'Installer Gaboma Hub', node });
  }, true);

  const panel = document.querySelector('.filter-panel');
  const options = panel?.querySelector('.filter-options');
  panel?.querySelector('summary')?.addEventListener('click', (event) => {
    if (!options) return;
    event.preventDefault();
    const form = panel.closest('form');
    if (form && !form.id) form.id = 'catalogue-form';
    if (form) options.querySelectorAll('input, select, textarea, button').forEach((field) => field.setAttribute('form', form.id));
    openSheet({
      kickerText: 'Catalogue', titleText: 'Filtres', node: options,
      restoreNode: () => panel.append(options),
    });
  });
  const linkButton = (className, href, label, external) => {
    const link = document.createElement('a');
    link.className = className;
    link.href = href;
    link.textContent = label;
    if (external) { link.target = '_blank'; link.rel = 'noopener noreferrer'; }
    return link;
  };
  document.addEventListener('click', (event) => {
    const preview = event.target.closest('[data-app-preview]');
    if (!preview || event.target.closest('.compact-favorite')) return;
    event.preventDefault();
    event.stopPropagation();
    const node = document.createElement('div');
    node.className = 'app-preview';
    const hero = document.createElement('div');
    hero.className = 'app-preview-hero';
    if (preview.dataset.cover) {
      const image = document.createElement('img');
      image.alt = '';
      image.src = preview.dataset.cover;
      hero.append(image);
    }
    const copy = document.createElement('p');
    copy.className = 'app-preview-copy';
    copy.textContent = preview.dataset.description || '';
    const rating = document.createElement('p');
    rating.className = 'app-preview-rating';
    rating.textContent = preview.dataset.rating || '';
    node.append(hero, copy, rating);
    const buttons = [linkButton('hub-sheet-go', preview.dataset.detail, 'Voir les détails')];
    if (preview.dataset.open) buttons.push(linkButton('hub-sheet-next', preview.dataset.open, 'Ouvrir l’app', true));
    else {
      const wait = document.createElement('span');
      wait.className = 'hub-sheet-next';
      wait.textContent = 'Lien à venir';
      buttons.push(wait);
    }
    openSheet({ kickerText: preview.dataset.category || 'Application', titleText: preview.dataset.name || 'Application', node, actionNodes: buttons });
  }, true);
  sheet.querySelectorAll('[data-hub-sheet-close]').forEach((button) => button.addEventListener('click', close));
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && !sheet.hidden) close(); });
  let startY = 0;
  let dragging = false;
  card.addEventListener('pointerdown', (event) => {
    if (event.button !== 0 || !event.target.closest('.hub-sheet-grab')) return;
    dragging = true;
    startY = event.clientY;
    card.style.transition = 'none';
  });
  card.addEventListener('pointermove', (event) => {
    if (!dragging) return;
    card.style.transform = `translateY(${Math.max(0, event.clientY - startY)}px)`;
  });
  const endDrag = (event) => {
    if (!dragging) return;
    dragging = false;
    const distance = Math.max(0, event.clientY - startY);
    card.style.transition = '';
    card.style.transform = '';
    if (distance > 90) close();
  };
  card.addEventListener('pointerup', endDrag);
  card.addEventListener('pointercancel', endDrag);
})();

// Le répertoire charge la suite au fil du scroll, sans recharger la page.
(() => {
  const grid = document.querySelector('#app-catalogue');
  const sentinel = document.querySelector('.catalogue-sentinel');
  if (!grid || !sentinel || !('IntersectionObserver' in window)) return;
  const spinner = sentinel.querySelector('.hub-loader-mark');
  const more = sentinel.querySelector('.catalogue-more');
  let next = sentinel.dataset.next;
  let busy = false;
  let streak = 0;
  const take = async (manual) => {
    if (!next || busy) return;
    busy = true;
    let loaded = false;
    if (manual) streak = 0;
    if (spinner) spinner.hidden = false;
    if (more) more.hidden = true;
    try {
      const response = await fetch(next, { headers: { 'X-Requested-With': 'fetch' } });
      if (!response.ok) throw new Error('catalogue');
      const box = document.createElement('div');
      box.innerHTML = await response.text();
      box.querySelectorAll('.app-card').forEach((item) => grid.append(item));
      next = box.querySelector('.catalogue-meta')?.dataset.next || '';
      if (!next) { sentinel.remove(); observer.disconnect(); }
      loaded = true;
    } catch {
      if (more) { more.hidden = false; more.textContent = 'Réessayer'; }
    } finally {
      busy = false;
      if (spinner) spinner.hidden = true;
    }
    if (!loaded || !next || !sentinel.isConnected) return;
    streak += 1;
    const room = sentinel.getBoundingClientRect().top < window.innerHeight + 280;
    // Quatre lots d'affilée, puis un geste : le navigateur ne monte pas des milliers de fiches seul.
    if (streak >= 4) {
      streak = 0;
      if (more) { more.hidden = false; more.textContent = 'Continuer le répertoire'; }
      return;
    }
    if (room) take(false);
  };
  if (more) more.addEventListener('click', (event) => { event.preventDefault(); take(true); });
  const observer = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) take();
  }, { rootMargin: '280px' });
  observer.observe(sentinel);
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

// La barre basse se retire pendant la descente, puis revient en remontant ou après une pause.
(() => {
  const nav = document.querySelector('.mobile-nav');
  if (!nav) return;
  let last = window.scrollY;
  let queued = false;
  let idle = 0;
  const update = () => {
    const y = Math.max(0, window.scrollY);
    const delta = y - last;
    const nearTop = y < 48;
    const nearBottom = window.innerHeight + y > document.documentElement.scrollHeight - 80;
    const focused = nav.contains(document.activeElement);
    if (nearTop || nearBottom || focused || delta < -10) nav.classList.remove('is-away');
    else if (delta > 12 && y > 72) nav.classList.add('is-away');
    last = y;
    queued = false;
    clearTimeout(idle);
    if (nav.classList.contains('is-away')) idle = setTimeout(() => nav.classList.remove('is-away'), 700);
  };
  window.addEventListener('scroll', () => {
    if (!queued) { queued = true; requestAnimationFrame(update); }
  }, { passive: true });
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

// La note est le nombre d'étoiles allumées, de la première jusqu'à celle choisie.
(() => {
  document.querySelectorAll('.rating-picker').forEach(picker => {
    const labels = [...picker.querySelectorAll('label')].filter(label => label.querySelector('input'));
    if (!labels.length) return;
    const paint = (value) => labels.forEach(label => {
      label.classList.toggle('is-on', Number(label.querySelector('input').value) <= value);
    });
    const current = () => {
      const checked = picker.querySelector('input:checked');
      return checked ? Number(checked.value) : 0;
    };
    picker.addEventListener('pointerover', event => {
      const label = event.target.closest('label');
      if (!label || !picker.contains(label)) return;
      const input = label.querySelector('input');
      if (input) paint(Number(input.value));
    });
    picker.addEventListener('pointerleave', () => paint(current()));
    picker.addEventListener('focusin', event => {
      const input = event.target.closest('input');
      if (input && picker.contains(input)) paint(Number(input.value));
    });
    picker.addEventListener('focusout', event => {
      if (!picker.contains(event.relatedTarget)) paint(current());
    });
    picker.addEventListener('change', () => paint(current()));
    paint(current());
  });
})();

(() => {
  const hero = document.querySelector('[data-hero-carousel]');
  if (!hero) return;
  const slides = [...hero.querySelectorAll('.hero-slide')];
  if (slides.length < 2) return;
  const dots = [...hero.querySelectorAll('[data-hero-dot]')];
  let index = 0;
  let timer = 0;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const show = (next) => {
    index = (next + slides.length) % slides.length;
    slides.forEach((slide, i) => slide.classList.toggle('is-active', i === index));
    dots.forEach((dot, i) => dot.setAttribute('aria-current', i === index ? 'true' : 'false'));
  };
  const arm = () => {
    clearInterval(timer);
    if (reduced) return;
    timer = setInterval(() => show(index + 1), 5500);
  };
  hero.querySelector('[data-hero-prev]')?.addEventListener('click', () => { show(index - 1); arm(); });
  hero.querySelector('[data-hero-next]')?.addEventListener('click', () => { show(index + 1); arm(); });
  dots.forEach((dot) => dot.addEventListener('click', () => { show(Number(dot.dataset.heroDot)); arm(); }));
  arm();
})();
