(() => {
  const keys = ['q','school','invitation','response','presence','profile'];
  const controls = Object.fromEntries(keys.map(key => [key, document.getElementById('attendance-filter-' + key)]));
  const rows = Array.from(document.querySelectorAll('[data-attendance-row]'));
  const sendForm = document.getElementById('send-expo-invitations');
  const sendButton = sendForm.querySelector('button[type="submit"]');
  const normalize = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const schools = new Map(rows.map(row => [row.dataset.school, row.dataset.schoolName]));
  Array.from(schools).sort((a,b) => a[1].localeCompare(b[1], 'es')).forEach(([id,name]) => {
    const option = document.createElement('option'); option.value = id; option.textContent = name; controls.school.append(option);
  });
  const params = new URLSearchParams(window.location.search);
  keys.forEach(key => { controls[key].value = params.get('filter_' + key) || ''; });

  function updateSelection() {
    const visible = rows.filter(row => !row.hidden);
    const selected = visible.filter(row => row.querySelector('input[name="judge_ids"]').checked).length;
    document.getElementById('attendance-filter-count').textContent = `${visible.length} de ${rows.length} jueces · ${selected} seleccionados`;
    document.getElementById('attendance-empty').hidden = visible.length !== 0;
    sendButton.disabled = selected === 0;
    sendButton.textContent = `Enviar invitaciones (${selected})`;
  }

  function applyFilters() {
    rows.forEach(row => {
      const d = row.dataset, f = controls;
      const invitationMatch = !f.invitation.value || (f.invitation.value === 'error' ? d.error === '1' : d.invitation === f.invitation.value);
      const profileMatch = !f.profile.value || (f.profile.value === 'english-only' ? d.englishOnly === '1' : f.profile.value === 'english' ? d.english === '1' : d.spanish === '1');
      row.hidden = !(normalize(d.search).includes(normalize(f.q.value.trim())) &&
        (!f.school.value || d.school === f.school.value) && invitationMatch && profileMatch &&
        (!f.response.value || d.response === f.response.value) && (!f.presence.value || d.presence === f.presence.value));
      const checkbox = row.querySelector('input[name="judge_ids"]');
      if(row.hidden) checkbox.checked = false;
      checkbox.disabled = row.hidden;
    });
    const url = new URL(window.location.href);
    keys.forEach(key => {
      if(controls[key].value) url.searchParams.set('filter_' + key,controls[key].value);
      else url.searchParams.delete('filter_' + key);
    });
    window.history.replaceState(null,'',url);
    updateSelection();
  }
  Object.values(controls).forEach(control => control.addEventListener('input',applyFilters));
  rows.forEach(row => row.querySelector('input[name="judge_ids"]').addEventListener('change',updateSelection));
  document.getElementById('attendance-clear-filters').addEventListener('click',() => { keys.forEach(key => { controls[key].value = ''; }); applyFilters(); });
  document.getElementById('attendance-select-visible').addEventListener('click',() => { rows.filter(row => !row.hidden).forEach(row => { row.querySelector('input[name="judge_ids"]').checked = true; }); updateSelection(); });
  document.getElementById('attendance-clear-selection').addEventListener('click',() => { rows.forEach(row => { row.querySelector('input[name="judge_ids"]').checked = false; }); updateSelection(); });
  // Preserve operational filters after recording a response/arrival or sending mail.
  document.addEventListener('submit',event => {
    if(!(event.target instanceof HTMLFormElement) || event.target.method.toLowerCase() !== 'post') return;
    keys.forEach(key => {
      let input = event.target.querySelector(`input[name="filter_${key}"]`);
      if(!input) { input = document.createElement('input'); input.type = 'hidden'; input.name = 'filter_' + key; event.target.append(input); }
      input.value = controls[key].value;
    });
  });
  applyFilters();
})();
