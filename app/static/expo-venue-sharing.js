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
