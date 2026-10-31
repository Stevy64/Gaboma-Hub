(() => {
  window.hubInstallPrompt = null;
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    window.hubInstallPrompt = event;
  });
  window.addEventListener('appinstalled', () => { window.hubInstallPrompt = null; });
  if ('serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('/sw.js', {updateViaCache: 'none'}).catch(() => {});
  }
})();
