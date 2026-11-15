/* Lightweight DOM contract tests; no browser or external dependencies. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Element {
  constructor(tagName) {
    this.tagName = tagName;
    this.children = [];
    this.dataset = {};
    this.attributes = {};
    this.style = {};
    this.listeners = {};
    this._text = '';
    this.hidden = false;
  }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  set textContent(value) { this._text = String(value); this.children = []; }
  append(...children) {
    children.forEach(child => {
      if (child.parentNode) child.parentNode.children = child.parentNode.children.filter(node => node !== child);
      child.parentNode = this;
      this.children.push(child);
    });
  }
  before(...nodes) {
    const parent = this.parentNode;
    parent.children.splice(parent.children.indexOf(this), 0, ...nodes);
    nodes.forEach(node => { node.parentNode = parent; });
  }
  setAttribute(name, value) {
    this.attributes[name] = String(value);
    if (name === 'class') this.className = String(value);
    if (name.startsWith('data-')) this.dataset[name.slice(5).replace(/-([a-z])/g, (_, character) => character.toUpperCase())] = String(value);
  }
  getAttribute(name) { return this.attributes[name] ?? null; }
  addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
  querySelector(selector) {
    const matches = node => {
      if (selector === 'h3' || selector === 'strong') return node.tagName === selector;
      const [tag, className] = selector.split('.');
      return (!tag || node.tagName === tag) && hasClass(node, className);
    };
    return descend(this).find(matches) || null;
  }
}
function descend(node) { return node.children.flatMap(child => [child, ...descend(child)]); }
function hasClass(node, name) { return (node.className || '').split(/\s+/).includes(name); }
function fire(node, type, fields = {}) {
  const event = {type, target: node, key: undefined, defaultPrevented: false, stopped: false,
    preventDefault() { this.defaultPrevented = true; }, stopPropagation() { this.stopped = true; }, ...fields};
  let current = node;
  do {
    (current.listeners[type] || []).forEach(callback => callback(event));
    if (event.stopped || !['click', 'keydown'].includes(type)) break;
    current = current.parentNode;
  } while (current);
  return event;
}
function el(tag, text, className) {
  const node = new Element(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.setAttribute('class', className);
  return node;
}
const fixture = [
  ['Ireland', 'United States', 7], ['Ireland', 'United States', 3],
  ['Ireland', 'Scotland', 4], ['Scotland', 'Ireland', 3],
  ['England', 'Ireland', 2], ['England', 'United States', 6],
  ['France', 'Canada', 5], ['France', 'United States', 1]
];
const panel = el('section', undefined, 'statistics-panel');
const list = el('ol', undefined, 'statistics-bars');
const item = el('li');
item.append(el('span', 'Ireland → United States', 'statistics-label'), el('strong', '10'));
list.append(item);
const source = el('script', JSON.stringify(fixture), 'statistics-migration-data');
panel.append(el('h3', 'Most common recorded migrations'), list, source);
const document = {
  querySelectorAll: () => [panel],
  createElement: tag => new Element(tag),
  createElementNS: (_, tag) => new Element(tag),
  createTextNode: value => el('#text', value)
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../tools/statistics_panels.js'), 'utf8'), {document});
const all = () => descend(panel);
const one = className => all().find(node => hasClass(node, className));
const svg = one('statistics-flow-svg'), stage = one('statistics-flow-stage');
const status = one('statistics-flow-status'), clear = one('statistics-flow-clear');
const tooltip = one('statistics-chart-tooltip');
const links = all().filter(node => hasClass(node, 'statistics-flow-link'));
const nodes = all().filter(node => hasClass(node, 'statistics-flow-node'));
const labels = all().filter(node => hasClass(node, 'statistics-flow-label'));
const country = (region, side = 'birth', label = false) => (label ? labels : nodes).find(node => node.dataset.flowRegion === region && node.dataset.flowSide === side);
const route = (origin, destination) => links.find(node => node.dataset.flowOrigin === origin && node.dataset.flowDestination === destination);
const pressed = node => node.getAttribute('aria-pressed') === 'true';

assert.equal(panel.dataset.chartView, 'flows');
assert.equal(links.length, 7, 'Repeated origin/destination pairs aggregate exactly');
assert.equal(links.reduce((total, node) => total + Number(node.dataset.flowCount), 0), 31);
assert.equal(route('Ireland', 'United States').dataset.flowCount, '10');
assert.equal(country('Ireland').getAttribute('fill'), country('Ireland', 'death').getAttribute('fill'));
assert.equal(country('Scotland').getAttribute('fill'), country('Scotland', 'death').getAttribute('fill'));
assert(nodes.concat(labels, links).every(node => node.getAttribute('role') === 'button' && node.getAttribute('tabindex') === '0'));
assert.equal(clear.disabled, true);
assert.equal(tooltip.hidden, true);

// Count scale, exact offsets and one-unit underlap are invariant.
const beforeGeometry = links.concat(nodes).map(node => JSON.stringify(node.attributes));
const leftHeight = nodes.filter(node => node.dataset.flowSide === 'birth').reduce((sum, node) => sum + Number(node.getAttribute('height')), 0);
const rightHeight = nodes.filter(node => node.dataset.flowSide === 'death').reduce((sum, node) => sum + Number(node.getAttribute('height')), 0);
assert(Math.abs(leftHeight - rightHeight) < 1e-10);
const scale = leftHeight / 31;
links.forEach(link => {
  const coordinates = link.getAttribute('d').match(/-?\d+(?:\.\d+)?(?:e[+-]?\d+)?/gi).map(Number);
  assert.deepEqual([coordinates[0], coordinates[6], coordinates[8], coordinates[14]], [259, 641, 641, 259]);
  assert(Math.abs(coordinates[15] - coordinates[1] - Number(link.dataset.flowCount) * scale) < 1e-10);
  assert(Math.abs(coordinates[9] - coordinates[7] - Number(link.dataset.flowCount) * scale) < 1e-10);
});
assert.equal(246 + 14 - 259, 1);
assert.equal(641 - 640, 1);
assert(svg.children.indexOf(links[links.length - 1]) < svg.children.indexOf(nodes[0]), 'Opaque nodes draw after ribbons');
nodes.forEach(node => {
  const name = node.dataset.flowRegion, side = node.dataset.flowSide;
  const segments = links.filter(link => link.dataset[side === 'birth' ? 'flowOrigin' : 'flowDestination'] === name).map(link => {
    const c = link.getAttribute('d').match(/-?\d+(?:\.\d+)?(?:e[+-]?\d+)?/gi).map(Number);
    return side === 'birth' ? [c[1], c[15]] : [c[7], c[9]];
  }).sort((a, b) => a[0] - b[0]);
  assert(Math.abs(segments[0][0] - Number(node.getAttribute('y'))) < 1e-10);
  segments.slice(1).forEach((segment, index) => assert(Math.abs(segment[0] - segments[index][1]) < 1e-10));
  assert(Math.abs(segments[segments.length - 1][1] - Number(node.getAttribute('y')) - Number(node.getAttribute('height'))) < 1e-10);
});

// Region preview highlights every incoming and outgoing route, on both sides.
fire(country('Ireland'), 'pointerenter');
assert(hasClass(svg, 'has-selection'));
links.forEach(link => assert.equal(hasClass(link, 'is-connected'), link.dataset.flowOrigin === 'Ireland' || link.dataset.flowDestination === 'Ireland'));
nodes.concat(labels).filter(node => node.dataset.flowRegion === 'Ireland').forEach(node => assert(hasClass(node, 'is-selected')));
assert(hasClass(country('France'), 'is-muted'));
assert(hasClass(country('Canada', 'death'), 'is-muted'));
assert(status.textContent.includes('Ireland: 19 recorded migrations across 4 routes.'));
assert.equal(tooltip.hidden, false);
assert(tooltip.textContent.includes('Ireland: 14 (45.2%)'));
fire(country('Ireland'), 'pointerleave');
assert(!hasClass(svg, 'has-selection'));

// Pin country, retain selection through pointerleave, and toggle off via opposite label.
fire(country('Ireland'), 'click');
assert.equal(clear.disabled, false);
nodes.concat(labels).filter(node => node.dataset.flowRegion === 'Ireland').forEach(node => assert(pressed(node)));
fire(country('Ireland'), 'pointerleave');
assert(hasClass(svg, 'has-selection'));
fire(country('Ireland', 'death', true), 'click');
assert(!hasClass(svg, 'has-selection'));
assert(nodes.concat(labels, links).every(node => !pressed(node)));

// Label keyboard interaction and focus preview work independently of pointer.
fire(country('Ireland', 'death', true), 'focus');
assert(hasClass(route('Scotland', 'Ireland'), 'is-connected'));
assert.equal(fire(country('Ireland', 'death', true), 'keydown', {key: ' '}).defaultPrevented, true);
assert(pressed(country('Ireland')));
fire(country('Ireland', 'death', true), 'blur');
assert(hasClass(svg, 'has-selection'));
fire(clear, 'click');
assert(!hasClass(svg, 'has-selection'));

// A route previews/pins one pair; hovering elsewhere cannot replace a pin.
const irelandUS = route('Ireland', 'United States');
fire(irelandUS, 'pointerenter');
assert.equal(links.filter(node => hasClass(node, 'is-connected')).length, 1);
assert(hasClass(country('Ireland'), 'is-connected'));
assert(hasClass(country('Ireland', 'death'), 'is-muted'));
fire(irelandUS, 'keydown', {key: 'Enter'});
assert(pressed(irelandUS));
fire(irelandUS, 'pointerleave');
fire(country('France'), 'pointerenter');
assert(hasClass(irelandUS, 'is-selected'));
assert.equal(links.filter(node => hasClass(node, 'is-connected')).length, 1);
fire(country('France'), 'pointerleave');
fire(irelandUS, 'keydown', {key: 'Escape'});
assert(!hasClass(svg, 'has-selection'));
assert.equal(clear.disabled, true);

// Route click toggles; blank SVG and Escape clear both pin and focus preview.
fire(irelandUS, 'click'); assert(pressed(irelandUS));
fire(irelandUS, 'click'); assert(!pressed(irelandUS));
fire(country('Ireland', 'birth', true), 'click'); assert(pressed(country('Ireland')));
fire(svg, 'click'); assert(!hasClass(svg, 'has-selection'));
fire(irelandUS, 'focus'); assert(hasClass(irelandUS, 'is-connected'));
fire(stage, 'keydown', {key: 'Escape'}); assert(!hasClass(svg, 'has-selection'));
fire(irelandUS, 'blur');

// No interaction mutates the geometry, counts, source list or source data.
links.concat(nodes).forEach((node, index) => {
  const before = JSON.parse(beforeGeometry[index]);
  for (const attribute of ['d', 'x', 'y', 'width', 'height', 'data-flow-count', 'fill']) {
    assert.equal(node.getAttribute(attribute), before[attribute] ?? null);
  }
});
const counts = all().find(node => node.tagName === 'button' && node.dataset.mode === 'counts');
fire(counts, 'click');
assert.equal(list.parentNode.className, 'statistics-chart-data');
assert.equal(list.parentNode.open, true);
assert.equal(source.textContent, JSON.stringify(fixture));
console.log('Sankey contracts passed: all-country incident selection, both-side labels, focus, keyboard pin/toggle, route pin, clear/Escape/blank reset, exact counts, stable colours, conserved geometry and one-unit joins.');
