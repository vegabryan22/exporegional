const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
class Element {
  constructor() { this.value=''; this.hidden=false; this.events={}; this.classes=new Set(); this.classList={toggle:(name,on) => { if(on) this.classes.add(name); else this.classes.delete(name); }}; }
  addEventListener(event,handler) { this.events[event]=handler; }
  querySelector() { return this.select || this.count; }
  querySelectorAll() { return this.rows; }
}
const rows = [
  {search:'Árbol CTP Águila',school:'a',category:'steam',value:'a4'},
  {search:'Zeta CTP Águila',school:'a',category:'emprendimiento',value:''},
  {search:'Proyecto CTP Zeta',school:'z',category:'steam',value:'a5'},
].map(data => { const row=new Element(); row.dataset=data; row.select=new Element(); row.select.value=data.value; row.select.disabled=false; return row; });
const groups = [rows.slice(0,2),rows.slice(2)].map(groupRows => {const group=new Element(); group.rows=groupRows; group.count=new Element(); return group;});
const ids = Object.fromEntries(['venue-search','venue-school-filter','venue-location-filter','venue-category-filter','venue-visible-count','venue-empty-filter','venue-dirty-count','venue-clear-filters'].map(id=>[id,new Element()]));
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../app/static/expo-venue-editor.js'),'utf8'),{
  document:{querySelectorAll:selector=>selector==='[data-venue-project]' ? rows : groups,getElementById:id=>ids[id]},
});
function filter(id,value) { ids[id].value=value; ids[id].events.input(); }
assert.equal(groups[0].count.textContent,'2 proyectos · 1 ubicados');
filter('venue-search','ARBOL');
assert.equal(rows[0].hidden,false); assert.equal(rows[1].hidden,true); assert.equal(groups[1].hidden,true);
assert.equal(rows[1].select.disabled,false,'Hidden locations must stay in the submitted form');
ids['venue-clear-filters'].events.click();
filter('venue-location-filter','unassigned');
assert.equal(rows[1].hidden,false); assert.equal(rows[0].hidden,true);
rows[1].select.value='a4'; rows[1].select.events.change();
assert.equal(ids['venue-dirty-count'].textContent,'1 cambio(s) sin guardar');
assert.equal(rows[1].classes.has('venue-project-changed'),true);
assert.equal(rows[1].hidden,false,'Editing a filtered row must not abruptly hide it');
ids['venue-clear-filters'].events.click();
filter('venue-school-filter','a'); filter('venue-category-filter','steam');
assert.equal(ids['venue-visible-count'].textContent,'1 de 3 proyectos · 1 colegios');
rows[1].select.value=''; rows[1].select.events.change();
assert.equal(ids['venue-dirty-count'].textContent,'Sin cambios pendientes');
filter('venue-search','No existe');
assert.equal(ids['venue-empty-filter'].hidden,false);
assert.ok(rows.every(row=>!row.select.disabled));
console.log('OK: venue filters, school counts, dirty tracking and preservation of filtered locations');
