(() => {
  const rows = Array.from(document.querySelectorAll('[data-venue-project]'));
  const groups = Array.from(document.querySelectorAll('[data-venue-school]'));
  const search = document.getElementById('venue-search'), school = document.getElementById('venue-school-filter');
  const venue = document.getElementById('venue-location-filter'), category = document.getElementById('venue-category-filter');
  const normalize = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const initial = new Map(rows.map(row => [row, row.querySelector('[data-venue-select]').value]));
  function groupCounts() {
    groups.forEach(group => {
      const visible = Array.from(group.querySelectorAll('[data-venue-project]')).filter(row => !row.hidden);
      group.hidden = visible.length === 0;
      const assigned = visible.filter(row => row.querySelector('[data-venue-select]').value).length;
      group.querySelector('[data-venue-group-count]').textContent = `${visible.length} proyectos · ${assigned} ubicados`;
    });
  }
  function filter() {
    rows.forEach(row => {
      const location = row.querySelector('[data-venue-select]').value;
      row.hidden = !(normalize(row.dataset.search).includes(normalize(search.value.trim())) &&
        (!school.value || row.dataset.school === school.value) && (!category.value || row.dataset.category === category.value) &&
        (!venue.value || (venue.value === 'unassigned' ? !location : location === venue.value)));
    });
    groupCounts();
    const visible = rows.filter(row => !row.hidden).length;
    document.getElementById('venue-visible-count').textContent = `${visible} de ${rows.length} proyectos · ${groups.filter(group => !group.hidden).length} colegios`;
    document.getElementById('venue-empty-filter').hidden = visible !== 0;
  }
  function dirtyCount() {
    let dirty = 0;
    rows.forEach(row => {
      const changed = row.querySelector('[data-venue-select]').value !== initial.get(row);
      row.classList.toggle('venue-project-changed',changed);
      if(changed) dirty++;
    });
    document.getElementById('venue-dirty-count').textContent = dirty ? `${dirty} cambio(s) sin guardar` : 'Sin cambios pendientes';
    groupCounts();
  }
  [search,school,venue,category].forEach(control => control.addEventListener('input',filter));
  rows.forEach(row => row.querySelector('[data-venue-select]').addEventListener('change',dirtyCount));
  document.getElementById('venue-clear-filters').addEventListener('click',() => { [search,school,venue,category].forEach(control => {control.value = '';}); filter(); });
  // Filtered rows stay enabled: the complete location map must be submitted.
  filter();
})();
