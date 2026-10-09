const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
class Element {
  constructor(id, title) {
    this.id = id; this.title = title; this.attributes = {}; this.events = {}; this.classes = new Set();
    this.classList = {
      add: name => this.classes.add(name),
      remove: name => this.classes.delete(name),
      toggle: (name, force) => {
        const on = force === undefined ? !this.classes.has(name) : force;
        if(on) this.classes.add(name); else this.classes.delete(name);
        return on;
      },
    };
  }
  addEventListener(event, handler) { this.events[event] = handler; }
  getAttribute(name) { return this.id; }
  setAttribute(name,value) { this.attributes[name] = value; }
  querySelector() { return {textContent:this.title}; }
  focus() { this.focused = true; }
}
const links = [new Element('1','Primer proyecto'),new Element('2','Segundo proyecto')];
links[0].classList.add('active');
const panels = [new Element('1'),new Element('2')];
const picker = new Element(), label = {}, sidebar = new Element();
sidebar.classList.add('is-mobile-collapsed');
const mobile = {matches:true};
const document = {
  querySelectorAll: selector => selector === '[data-project-target]' ? links : selector === '[data-project-panel]' ? panels : [],
  querySelector: selector => ({
    '[data-public-project-picker]':picker, '[data-public-project-selected]':label,
    '.project-sidebar':sidebar, '[data-project-target].active':links[0],
  })[selector],
};
const template = fs.readFileSync(path.join(__dirname,'../app/templates/public/home_projects.html'),'utf8');
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1];
vm.runInNewContext(script, {document,window:{matchMedia:() => mobile}});
assert.equal(label.textContent,'Primer proyecto');
picker.events.click();
assert.equal(picker.attributes['aria-expanded'],'true');
assert.equal(sidebar.classes.has('is-mobile-collapsed'),false);
links[1].events.click();
assert.equal(label.textContent,'Segundo proyecto');
assert.equal(panels[1].classes.has('active'),true);
assert.equal(panels[0].classes.has('active'),false);
assert.equal(sidebar.classes.has('is-mobile-collapsed'),true);
assert.equal(picker.attributes['aria-expanded'],'false');
assert.equal(picker.focused,true);
mobile.matches = false;
sidebar.classList.remove('is-mobile-collapsed');
links[0].events.click();
assert.equal(sidebar.classes.has('is-mobile-collapsed'),false, 'Desktop selector remains open');
assert.equal(label.textContent,'Primer proyecto');
console.log('OK: mobile project selection, collapse, focus and unchanged desktop selection');
