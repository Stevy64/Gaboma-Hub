(() => {
  let deferred;
  const status = document.querySelector('[data-pwa-status]');
  const say = text => { if (status) status.textContent = text; };
  const install = document.querySelector('[data-pwa-install]');
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault(); deferred = event;
    if (install) install.hidden = false;
  });
  install?.addEventListener('click', async () => {
    if (!deferred) return;
    await deferred.prompt();
    const result = await deferred.userChoice;
    say(result.outcome === 'accepted' ? 'Installation demandée.' : 'Vous pourrez installer le Hub plus tard.');
    deferred = null; install.hidden = true;
  });
  window.addEventListener('appinstalled', () => {
    say('Gaboma Hub est installé.'); if (install) install.hidden = true;
  });
  if ('serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('/sw.js', {updateViaCache:'none'})
      .catch(() => {}); // Le site connecté reste entièrement utilisable.
  }
})();
