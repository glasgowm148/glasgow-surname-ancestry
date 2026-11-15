const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
function node() {
  return {value: '', style: {}, children: [], textContent: '', events: {},
    classList: {add() {}, remove() {}, toggle() {}},
    addEventListener(name, fn) {this.events[name] = fn;},
    replaceChildren() {this.children = [];}, append(...children) {this.children.push(...children);},
    setAttribute(name, value) {this[name] = value;}};
}
const elements = {};
for (const id of ['names-data','names-century','names-gender','names-summary','names-pie','names-rows','names-reset','names-leaders','names-count-title']) elements[id] = node();
elements['names-data'].textContent = JSON.stringify([
  ['John',1699,'Male',50],['Mary',1750,'Female',25],['Sarah',null,'Female',5],['A',null,'Unknown',2],
]);
const document = {getElementById: id => elements[id], createElement: node, createElementNS: node, createTextNode: text => text};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../tools/statistics_names.js'), 'utf8'),
  {document, Map, Intl, Math, Object});
assert.equal(elements['names-leaders'].children.length, 4);
assert.equal(elements['names-rows'].children.length, 4);
let first = elements['names-leaders'].children[0].children[0];
assert.equal(first.children[0].textContent, 'John');
assert.equal(first.children[1].textContent, '50');
assert.equal(first.children[2].children[0].style.width, '100%');
first.events.pointerenter();
assert.equal(elements['names-pie'].children[1].children[0].textContent, 'John');
assert(elements['names-pie'].children[1].children[1].textContent.includes('50 people'));
elements['names-gender'].value = 'Female';
elements['names-century'].value = '1800';
elements['names-century'].events.change();
assert.equal(elements['names-leaders'].children.length, 1);
assert.equal(elements['names-rows'].children.length, 1);
assert.equal(elements['names-leaders'].children[0].children[0].children[0].textContent, 'Mary');
elements['names-century'].value = '1500';
elements['names-century'].events.change();
assert.equal(elements['names-leaders'].children.length, 0);
assert.equal(elements['names-rows'].children.length, 0);
assert(elements['names-summary'].textContent.includes('No people'));
elements['names-reset'].events.click();
assert.equal(elements['names-leaders'].children.length, 4);
assert.equal(elements['names-count-title'].textContent, 'View all 4 name counts');
console.log('Name ranking, tooltip, filters, empty state, full counts and reset passed.');
