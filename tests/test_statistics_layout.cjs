const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const listeners = {};
const location = {hash: ''};
const nav = {setAttribute(key, value) { this[key] = value; }};
const keys = ['names', 'time', 'places', 'journeys'];
const anchors = ['first-names', 'birth-centuries', 'regions', 'migration'];
const panes = keys.map(key => ({dataset: {statisticsPane: key}, setAttribute(key, value) {this[key] = value;}}));
const tabs = keys.map((key, i) => ({
  dataset: {statisticsView: key}, hash: '#' + anchors[i], events: {},
  closest() {return nav;}, setAttribute(key, value) {this[key] = value;},
  addEventListener(key, action) {this.events[key] = action;}, focus() {this.focused = true;},
}));
const nodes = {};
anchors.forEach((id, i) => {nodes[id] = {
  closest() {return panes[i];}, parentElement: panes[i],
  scrollIntoView() {this.scrolled = true;},
};});
const comparison = {tagName: 'DETAILS', open: false, parentElement: panes[0]};
nodes['given-names'] = {closest() {return panes[0];}, parentElement: comparison, scrollIntoView() {}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../tools/statistics_layout.js'), 'utf8'), {
  document: {querySelectorAll: selector => selector.includes('data-statistics-view') ? tabs : selector.includes('data-statistics-pane') ? panes : [],
    getElementById: id => nodes[id]},
  location, history: {pushState(_, __, hash) {location.hash = hash;}},
  addEventListener: (name, action) => {listeners[name] = action;},
  requestAnimationFrame: action => action(),
});
const visible = () => panes.filter(pane => !pane.hidden).map(pane => pane.dataset.statisticsPane);
assert.deepEqual(visible(), ['names']);
tabs[3].events.click({preventDefault() {}});
assert.deepEqual(visible(), ['journeys']);
assert.equal(location.hash, '#migration');
assert.equal(tabs[3]['aria-selected'], 'true');
tabs[3].events.keydown({key: 'ArrowRight', preventDefault() {}});
assert.deepEqual(visible(), ['names']);
assert.equal(tabs[0].focused, true);
location.hash = '#birth-centuries';
listeners.hashchange();
assert.deepEqual(visible(), ['time']);
assert.equal(nodes['birth-centuries'].scrolled, true);
location.hash = '#given-names';
listeners.hashchange();
assert.equal(comparison.open, true);
assert.deepEqual(visible(), ['names']);
location.hash = '#migration';
listeners.popstate();
assert.deepEqual(visible(), ['journeys']);
location.hash = '';
listeners.popstate();
assert.deepEqual(visible(), ['names']);
console.log('Statistics views: clicks, keyboard, anchors, nested details and browser history passed.');
