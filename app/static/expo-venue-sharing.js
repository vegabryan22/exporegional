(() => {
  function whatsappNumber(value) {
    const raw = String(value).trim();
    if (!/^[+\d\s().-]+$/.test(raw)) return null;
    let digits = raw.replace(/\D/g, '');
    if (digits.startsWith('00')) digits = digits.slice(2);
    if (digits.length === 8 && !raw.startsWith('+') && !raw.startsWith('00')) digits = '506' + digits;
    return /^[1-9]\d{7,14}$/.test(digits) ? digits : null;
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {whatsappNumber};
  if (typeof document === 'undefined') return;
  const manager = document.getElementById ? document.getElementById('manage-venues') : null;
  if (manager) {
    try {
      const saved = JSON.parse(sessionStorage.getItem('venue-manager-return') || 'null');
      sessionStorage.removeItem('venue-manager-return');
      if (saved && window.location.hash === '#manage-venues') {
        manager.scrollTop = saved.scroll || 0;
        Object.entries(saved.phones || {}).forEach(([id, value]) => {
          const input = document.getElementById(id);
          if (input) input.value = value;
        });
      }
    } catch (_) { /* Storage may be disabled; the modal still reopens via its hash. */ }
    manager.querySelectorAll('form[method="post"]').forEach(form => {
      form.addEventListener('submit', () => {
        const action = form.querySelector('input[name="action"]');
        if (!action || !action.value.startsWith('access_')) return;
        const phones = {};
        manager.querySelectorAll('input[type="tel"]').forEach(input => { phones[input.id] = input.value; });
        try { sessionStorage.setItem('venue-manager-return', JSON.stringify({scroll:manager.scrollTop,phones})); } catch (_) {}
      });
    });
  }
  document.querySelectorAll('[data-venue-whatsapp]').forEach(form => {
    const phone = form.querySelector('input[type="tel"]');
    phone.addEventListener('input', () => phone.setCustomValidity(''));
    form.addEventListener('submit', event => {
      event.preventDefault();
      const number = whatsappNumber(phone.value);
      if (!number) {
        phone.setCustomValidity('Indica 8 dígitos para Costa Rica o un número con código de país (hasta 15 dígitos).');
        phone.reportValidity(); return;
      }
      phone.setCustomValidity('');
      const target = new URL('https://wa.me/' + number);
      target.searchParams.set('text', form.dataset.message);
      window.open(target.href, '_blank', 'noopener,noreferrer');
    });
  });
})();
