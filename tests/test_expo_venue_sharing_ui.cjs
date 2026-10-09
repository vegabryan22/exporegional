const assert = require('node:assert/strict');
const {whatsappNumber} = require('../app/static/expo-venue-sharing.js');
assert.equal(whatsappNumber('8888 8888'),'50688888888');
assert.equal(whatsappNumber('+506 8888-8888'),'50688888888');
assert.equal(whatsappNumber('00506 8888 8888'),'50688888888');
assert.equal(whatsappNumber('+502 5555 5555'),'50255555555');
assert.equal(whatsappNumber(''),null);
assert.equal(whatsappNumber('123'),null);
assert.equal(whatsappNumber('8888<script>'),null);
assert.equal(whatsappNumber('+1234567890123456'),null);
// Exercise the actual submit handler: invalid input must not open WhatsApp.
const fs = require('node:fs'), vm = require('node:vm');
const listeners = {}, phoneListeners = {}, windows = [];
const phone = {value:'123',setCustomValidity(message){this.message=message;},reportValidity(){this.reported=true;},addEventListener(type,fn){phoneListeners[type]=fn;}};
const form = {dataset:{message:'Hola Carlos, consulta tu recinto: https://event.test/r/short'},querySelector(){return phone;},addEventListener(type,fn){listeners[type]=fn;}};
vm.runInNewContext(fs.readFileSync('app/static/expo-venue-sharing.js','utf8'),{document:{querySelectorAll(){return [form];}},window:{open(...args){windows.push(args);}},URL});
listeners.submit({preventDefault(){}});
assert.equal(windows.length,0); assert.equal(phone.reported,true);
phone.value='8888 8888'; phoneListeners.input();
assert.equal(phone.message,'');
listeners.submit({preventDefault(){}});
assert.equal(windows.length,1);
assert.ok(windows[0][0].startsWith('https://wa.me/50688888888?text='));
assert.equal(new URL(windows[0][0]).searchParams.get('text'),form.dataset.message);
assert.equal(windows[0][2],'noopener,noreferrer');
console.log('OK: destination phone, country codes, validation and prepared WhatsApp message');
const storage = new Map([['venue-manager-return',JSON.stringify({scroll:350,phones:{'venue-phone-one':'8888 8888'}})]]);
let saveHandler;
const modal = {scrollTop:0,querySelectorAll(selector){return selector.startsWith('form') ? [{querySelector(){return {value:'access_enable'};},addEventListener(type,handler){saveHandler=handler;}}] : [{id:'venue-phone-one',value:phone.value}];}};
vm.runInNewContext(fs.readFileSync('app/static/expo-venue-sharing.js','utf8'),{
  document:{getElementById(id){return id==='manage-venues' ? modal : phone;},querySelectorAll(){return [];}},
  window:{location:{hash:'#manage-venues'}},
  sessionStorage:{getItem(key){return storage.get(key);},removeItem(key){storage.delete(key);},setItem(key,value){storage.set(key,value);}},URL
});
assert.equal(modal.scrollTop,350);
assert.equal(phone.value,'8888 8888');
assert.equal(storage.has('venue-manager-return'),false);
modal.scrollTop=450; saveHandler();
assert.equal(JSON.parse(storage.get('venue-manager-return')).scroll,450);
assert.equal(JSON.parse(storage.get('venue-manager-return')).phones['venue-phone-one'],'8888 8888');
console.log('OK: venue manager restores scroll and phone inputs after enabling access');
