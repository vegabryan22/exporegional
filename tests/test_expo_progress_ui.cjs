// Run with: node tests/test_expo_progress_ui.cjs
// Exercise the actual browser renderer without an external DOM dependency.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

class Element {
  constructor(tag) { this.tagName = tag; this.children = []; this.dataset = {}; this.open = false; this.textContent = ''; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  addEventListener() {}
  querySelectorAll(tag) {
    return this.children.flatMap(child => [...(child.tagName === tag ? [child] : []), ...child.querySelectorAll(tag)]);
  }
}

function fixture(mobile, includeNames = true) {
  const row = {
    id: 1, title: 'Proyecto', school: 'Colegio', category: 'steam', status: 'pending',
    exposition: 1, english_participants: 1, english: 0, english_expected: 1, english_unassigned: false,
  };
  if (includeNames) row.pending_judges = {
    exposition: [{name: 'Juez de exposición pendiente'}], exposition_unassigned: 1,
    english: [{name: 'Juez de inglés pendiente', completed: 0, expected: 1}],
  };
  const ids = Object.fromEntries([
    'progress-initial', 'progress-search', 'progress-venue', 'progress-category', 'progress-only-pending',
    'progress-export-pdf', 'progress-groups', 'progress-total', 'progress-complete', 'progress-pending',
    'progress-refresh', 'progress-update',
  ].map(id => [id, new Element('div')]));
  ['progress-search', 'progress-venue', 'progress-category'].forEach(id => ids[id].value = '');
  ids['progress-only-pending'].checked = false;
  ids['progress-export-pdf'].href = '/avance.pdf';
  ids['progress-initial'].textContent = JSON.stringify({total: 1, complete: 0,
    categories: [{code: 'steam', name: 'STEAM'}],
    venues: [{id: 'a4', name: 'A4', responsible: 'Responsable', complete: 0, projects: [row]}],
  });
  let onResize;
  const media = {matches: mobile, addEventListener: (event, callback) => { onResize = callback; }};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../app/static/expo-progress.js'), 'utf8'), {
    document: {
      querySelector: () => ({dataset: {url: '/avance.json'}}),
      getElementById: id => ids[id], createElement: tag => new Element(tag),
    },
    window: {matchMedia: () => media, setInterval() {}},
    URLSearchParams, fetch: () => new Promise(() => {}),
  });
  return {root: ids['progress-groups'], resize: mobile => { media.matches = mobile; onResize(); }};
}

const mobile = fixture(true);
const pending = mobile.root.querySelectorAll('details').find(el => el.className === 'progress-judge-details');
assert.ok(pending, 'Mobile must render the pending-judge disclosure');
const pendingCell = mobile.root.querySelectorAll('td').find(el => el.className === 'progress-pending-cell');
assert.equal(pendingCell.children[0], pending, 'Mobile disclosure gets its own full-width cell');
assert.ok(pending.querySelectorAll('p').some(el => el.textContent.includes('Juez de inglés pendiente')));
assert.ok(pending.querySelectorAll('p').some(el => el.textContent.includes('Falta asignar 1')));
pending.open = true;
mobile.resize(false);
assert.equal(mobile.root.querySelectorAll('td').filter(el => el.className === 'progress-pending-cell').length, 0);
assert.equal(mobile.root.querySelectorAll('details').find(el => el.className === 'progress-judge-details').open, true);
mobile.resize(true);
assert.equal(mobile.root.querySelectorAll('details').find(el => el.className === 'progress-judge-details').open, true);
assert.equal(fixture(true, false).root.querySelectorAll('details').filter(el => el.className === 'progress-judge-details').length, 0,
  'Public data must never produce a pending-name disclosure');
console.log('OK: mobile/desktop pending judges, resize state and public-data privacy');
