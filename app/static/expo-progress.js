(() => {
  const script = document.querySelector('script[data-url]');
  let data = JSON.parse(document.getElementById('progress-initial').textContent);
  const search = document.getElementById('progress-search'), venue = document.getElementById('progress-venue'), category = document.getElementById('progress-category'), pending = document.getElementById('progress-only-pending');
  const labels = {complete:'Completo',pending:'En proceso',not_started:'Sin evaluar',review:'Requiere revisión'};
  const normalize = value => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  function element(tag, text, className) {const el = document.createElement(tag); if(text !== undefined) el.textContent = text; if(className) el.className = className; return el;}
  function badge(text, state) {return element('span', text, 'progress-badge ' + state);}
  function render() {
    const exportLink = document.getElementById('progress-export-pdf');
    const params = new URLSearchParams({q:search.value,venue:venue.value,category:category.value,pending:pending.checked ? '1' : '0'});
    exportLink.href = exportLink.href.split('?')[0] + '?' + params.toString();
    const root = document.getElementById('progress-groups');
    const open = new Map(Array.from(root.querySelectorAll('details')).map(el => [el.dataset.id,el.open]));
    root.replaceChildren();
    document.getElementById('progress-total').textContent = data.total;
    document.getElementById('progress-complete').textContent = data.complete;
    document.getElementById('progress-pending').textContent = data.total - data.complete;
    let visible = 0;
    data.venues.forEach(group => {
      if(venue.value && venue.value !== group.id) return;
      const rows = group.projects.filter(row => (!category.value || row.category === category.value) && (!pending.checked || row.status !== 'complete') && normalize(row.title + ' ' + row.school).includes(normalize(search.value)));
      if(!rows.length) return;
      visible += rows.length;
      const details = element('details',undefined,'progress-recinto'); details.dataset.id = group.id; details.open = open.has(group.id) ? open.get(group.id) : true;
      const summary = element('summary',group.name); summary.append(element('small',`${group.complete}/${group.projects.length} proyectos completos · ${rows.length} visibles`)); details.append(summary);
      const wrap = element('div',undefined,'table-wrap'), table = element('table'), head = element('thead'), heading = element('tr');
      ['Proyecto','Colegio','Exposición','Inglés','Estado'].forEach(text => heading.append(element('th',text))); head.append(heading); table.append(head);
      const body = element('tbody');
      rows.forEach(row => {
        const tr = element('tr'), title = element('td'); title.append(element('strong',row.title),element('br'),element('small',data.categories.find(c => c.code === row.category)?.name || row.category)); tr.append(title,element('td',row.school));
        if(row.pending_judges) {
          const judges = row.pending_judges, panel = element('details',undefined,'progress-judge-details');
          panel.dataset.id = 'judges-' + row.id;
          panel.open = open.get(panel.dataset.id) || false;
          panel.append(element('summary',`Jueces pendientes (${judges.exposition.length + judges.english.length})`));
          const exposition = element('div',undefined,'progress-judge-section'); exposition.append(element('strong','Exposición'));
          judges.exposition.forEach(judge => exposition.append(element('p',judge.name + ' · Pendiente')));
          if(!judges.exposition.length) exposition.append(element('p','Sin jueces asignados pendientes.'));
          if(judges.exposition_unassigned) exposition.append(element('p',`Falta asignar ${judges.exposition_unassigned} juez(es) para completar la cobertura.`, 'progress-english-note'));
          panel.append(exposition);
          if(row.english_participants) {
            const englishSection = element('div',undefined,'progress-judge-section'); englishSection.append(element('strong','Inglés'));
            judges.english.forEach(judge => englishSection.append(element('p',`${judge.name} · ${judge.completed}/${judge.expected} estudiantes evaluados · faltan ${judge.expected - judge.completed}`)));
            if(row.english_unassigned) englishSection.append(element('p','Sin juez de inglés asignado.','progress-english-note'));
            else if(!judges.english.length) englishSection.append(element('p','Evaluaciones de inglés completas.'));
            panel.append(englishSection);
          }
          title.append(panel);
        }
        const expo = element('td'); expo.append(badge(`${row.exposition}/3`,row.exposition === 3 ? 'complete' : row.exposition > 3 ? 'review' : 'pending')); tr.append(expo);
        const english = element('td');
        if(!row.english_participants) english.textContent = 'No participa';
        else {english.append(badge(`${row.english}/${row.english_expected}`, !row.english_unassigned && row.english === row.english_expected ? 'complete' : 'pending')); if(row.english_unassigned) english.append(element('small','Sin juez de inglés asignado','progress-english-note'));}
        const state = element('td'); state.append(badge(labels[row.status],row.status)); tr.append(english,state);
        Array.from(tr.children).forEach((cell,index) => {cell.dataset.label = ['Proyecto','Colegio','Exposición','Inglés','Estado'][index];});
        body.append(tr);
      });
      table.append(body); wrap.append(table); details.append(wrap); root.append(details);
    });
    if(!visible) root.append(element('p',data.total ? 'No hay proyectos que coincidan con los filtros.' : 'Todavía no hay proyectos aprobados para evaluar.','progress-empty'));
  }
  let busy = false;
  async function refresh() {
    if(busy) return; busy = true;
    try {const response = await fetch(script.dataset.url,{cache:'no-store'}); if(!response.ok) throw new Error(); data = await response.json();
      const selected = venue.value; venue.replaceChildren(new Option('Todos','')); data.venues.forEach(v => venue.add(new Option(v.name,v.id))); venue.value = selected;
      render(); document.getElementById('progress-update').textContent = 'Última actualización: ' + new Date(data.updated_at).toLocaleTimeString('es-CR',{timeZone:'America/Costa_Rica'}) + ' · Actualización automática cada 30 segundos.';
    } catch(error) {document.getElementById('progress-update').textContent = 'No se pudo actualizar. Se conserva el último avance disponible.';} finally {busy = false;}
  }
  [search,venue,category,pending].forEach(el => el.addEventListener('input',render));
  document.getElementById('progress-refresh').addEventListener('click',refresh);
  render(); refresh(); window.setInterval(() => {if(!document.hidden) refresh();},30000);
})();
