document.addEventListener('submit', (event) => {
  const form = event.target;
  if (!form.matches('.flow-action')) return;
  if (form.getAttribute('aria-busy') === 'true') { event.preventDefault(); return; }
  form.setAttribute('aria-busy', 'true');
  const button = event.submitter;
  if (button) { button.setAttribute('aria-disabled', 'true'); button.classList.add('flow-working'); }
  const status = document.createElement('p');
  status.setAttribute('role', 'status');
  status.textContent = 'Traitement en cours…';
  form.append(status);
});
window.addEventListener('pageshow', () => {
  document.querySelectorAll('.flow-action[aria-busy]').forEach(form => {
    form.removeAttribute('aria-busy');
    form.querySelectorAll('[role="status"]').forEach(item => item.remove());
    form.querySelectorAll('.flow-working').forEach(button => { button.classList.remove('flow-working'); button.removeAttribute('aria-disabled'); });
  });
});
