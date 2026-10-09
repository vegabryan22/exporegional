const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
class Element {
  constructor() { this.value = ''; this.children = []; this.events = {}; this.hidden = false; this.checked = false; }
  append(child) { this.children.push(child); }
  addEventListener(type, handler) { this.events[type] = handler; }
  querySelector(selector) { return selector.includes('judge_ids') ? this.checkbox : this.children.find(child => selector.includes('"' + child.name + '"')); }
}
class Form extends Element { constructor() { super(); this.method = 'post'; } }
const ids = Object.fromEntries([
  'q','school','invitation','response','presence','profile',
].map(key => ['attendance-filter-' + key, new Element()]));
['attendance-filter-count','attendance-empty','attendance-clear-filters','attendance-select-visible','attendance-clear-selection'].forEach(id => { ids[id] = new Element(); });
const button = new Element(), form = new Form(); form.querySelector = () => button;
ids['send-expo-invitations'] = form;
const rows = [
  {search:'José Pérez jose@test',school:'1',schoolName:'Colegio Uno',invitation:'sent',error:'0',response:'yes',presence:'yes',english:'1',englishOnly:'1',spanish:'0'},
  {search:'Ana ana@test',school:'2',schoolName:'Colegio Dos',invitation:'unsent',error:'1',response:'pending',presence:'no',english:'0',englishOnly:'0',spanish:'1'},
  {search:'Luis luis@test',school:'1',schoolName:'Colegio Uno',invitation:'sent',error:'0',response:'no',presence:'no',english:'1',englishOnly:'0',spanish:'1'},
].map(dataset => { const row = new Element(); row.dataset = dataset; row.checkbox = new Element(); return row; });
const docEvents = {}, location = {href:'https://example.test/admin/expo/jueces',search:''};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../app/static/expo-attendance.js'),'utf8'), {
  document: {getElementById:id => ids[id], querySelectorAll:() => rows, createElement:() => new Element(), addEventListener:(event,handler) => { docEvents[event] = handler; }},
  window: {location, history:{replaceState:(state,title,url) => { location.href = String(url); }}},
  URL, URLSearchParams, HTMLFormElement:Form,
});
const setFilter = (key,value) => { const control = ids['attendance-filter-' + key]; control.value = value; control.events.input(); };
const clear = () => ids['attendance-clear-filters'].events.click();
const visible = () => rows.filter(row => !row.hidden);
assert.equal(visible().length,3); assert.equal(button.disabled,true);
assert.equal(ids['attendance-filter-school'].children.length,2, 'School options must be unique');
setFilter('q','JOSE'); assert.equal(visible()[0],rows[0]); assert.equal(visible().length,1);
ids['attendance-select-visible'].events.click(); assert.equal(rows[0].checkbox.checked,true); assert.equal(button.disabled,false);
setFilter('response','pending'); assert.equal(visible().length,0); assert.equal(rows[0].checkbox.checked,false); assert.equal(rows[0].checkbox.disabled,true); assert.equal(button.disabled,true); assert.equal(ids['attendance-empty'].hidden,false);
clear(); setFilter('school','1'); setFilter('presence','no'); assert.deepEqual(visible(),[rows[2]]);
clear(); setFilter('invitation','error'); assert.deepEqual(visible(),[rows[1]]);
clear(); setFilter('invitation','sent'); assert.equal(visible().length,2);
clear(); setFilter('profile','english-only'); assert.deepEqual(visible(),[rows[0]]);
clear(); setFilter('profile','english'); assert.equal(visible().length,2);
clear(); setFilter('profile','spanish'); assert.equal(visible().length,2);
ids['attendance-select-visible'].events.click(); assert.equal(button.textContent,'Enviar invitaciones (2)');
ids['attendance-clear-selection'].events.click(); assert.equal(button.disabled,true);
const responseForm = new Form(); docEvents.submit({target:responseForm});
assert.equal(responseForm.children.find(child => child.name === 'filter_profile').value,'spanish');
assert.ok(location.href.includes('filter_profile=spanish'));
console.log('OK: all operational filters, combined filters, safe visible selection and filter persistence');
