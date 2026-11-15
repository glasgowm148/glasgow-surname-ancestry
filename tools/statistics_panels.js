/* Progressive charts for the maintained statistics panels; the source lists stay usable. */
(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const palette = ['#267783', '#ad643f', '#8771a2', '#8b852b', '#427f58', '#bb657e', '#5176a9', '#9a7131', '#697b82', '#a65045', '#7473ba', '#588d84'];
  const number = value => value.toLocaleString('en-GB');
  const element = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const svgElement = (tag, attributes, text) => {
    const node = document.createElementNS(NS, tag);
    Object.entries(attributes || {}).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const sum = rows => rows.reduce((total, row) => total + row.count, 0);
  const percentage = (count, total) => (100 * count / total).toFixed(1) + '%';
  const readable = (name, count, total) => name + ': ' + number(count) + ' (' + percentage(count, total) + ')';
  const interactive = (shape, label, tooltip) => {
    shape.setAttribute('tabindex', '0');
    shape.setAttribute('role', 'img');
    shape.setAttribute('aria-label', label);
    shape.append(svgElement('title', {}, label));
    let hovered = false, focused = false;
    const show = () => { tooltip.textContent = label; tooltip.hidden = false; };
    const hide = () => { if (!hovered && !focused) tooltip.hidden = true; };
    shape.addEventListener('pointerenter', () => { hovered = true; show(); });
    shape.addEventListener('pointerleave', () => { hovered = false; hide(); });
    shape.addEventListener('focus', () => { focused = true; show(); });
    shape.addEventListener('blur', () => { focused = false; hide(); });
    shape.addEventListener('click', show);
    return shape;
  };
  function pie(rows, total, heading, tooltip) {
    const ordered = rows.slice().sort((a, b) => b.count - a.count);
    const slices = [], remainder = [];
    ordered.forEach((row, index) => {
      if (index < 10 && row.count / total >= 0.02) slices.push(row);
      else remainder.push(row);
    });
    const omitted = Math.max(0, total - sum(rows));
    const other = sum(remainder) + omitted;
    if (other) slices.push({name: 'Other', count: other});
    const wrapper = element('div', undefined, 'statistics-chart-pie');
    const svg = svgElement('svg', {viewBox: '0 0 340 340', role: 'group', 'aria-label': heading + ' pie chart'});
    let angle = -Math.PI / 2;
    slices.forEach((slice, index) => {
      const next = angle + slice.count / total * 2 * Math.PI;
      const attrs = {fill: palette[index % palette.length], stroke: 'var(--statistics-chart-stroke, #fff)', 'stroke-width': 2};
      let shape;
      if (slices.length === 1) {
        shape = svgElement('circle', {...attrs, cx: 170, cy: 170, r: 150});
      } else {
        const x1 = 170 + 150 * Math.cos(angle), y1 = 170 + 150 * Math.sin(angle);
        const x2 = 170 + 150 * Math.cos(next), y2 = 170 + 150 * Math.sin(next);
        shape = svgElement('path', {...attrs, d: 'M170,170 L' + x1 + ',' + y1 + ' A150,150 0 ' + (next - angle > Math.PI ? 1 : 0) + ',1 ' + x2 + ',' + y2 + ' Z'});
      }
      svg.append(interactive(shape, readable(slice.name, slice.count, total), tooltip));
      const fraction = slice.count / total;
      const radial = fraction < 0.12;
      const fontSize = radial ? 10 : 11;
      // Conservative text width keeps radial names between radii 60 and 150,
      // away from the crowded centre, even before web fonts have loaded.
      const labelFits = slice.name.length * fontSize * 0.6 <= (radial ? 90 : 120);
      if (fraction * 360 >= 6 && labelFits) {
        const middle = (angle + next) / 2;
        const radius = slices.length === 1 ? 0 : radial ? 105 : 100;
        const x = 170 + radius * Math.cos(middle), y = 170 + radius * Math.sin(middle);
        const degrees = middle * 180 / Math.PI;
        const rotation = degrees > 90 && degrees < 270 ? degrees + 180 : degrees;
        const channels = palette[index % palette.length].slice(1).match(/../g).map(hex => {
          const channel = parseInt(hex, 16) / 255;
          return channel <= 0.04045 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
        });
        const luminance = channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
        const label = svgElement('text', {x, y, dy: '.35em', 'text-anchor': 'middle', 'font-size': fontSize, 'font-weight': 650, fill: luminance > 0.179 ? '#151a1d' : '#fff', 'pointer-events': 'none', 'aria-hidden': 'true', class: 'statistics-panel-pie-label' + (radial ? ' is-radial' : '')}, slice.name);
        if (radial) label.setAttribute('transform', 'rotate(' + rotation + ' ' + x + ' ' + y + ')');
        svg.append(label);
      }
      angle = next;
    });
    const legend = element('ul', undefined, 'statistics-chart-legend');
    slices.forEach((slice, index) => {
      const item = element('li');
      const swatch = element('span', undefined, 'statistics-chart-swatch');
      swatch.style.backgroundColor = palette[index % palette.length];
      swatch.setAttribute('aria-hidden', 'true');
      item.append(swatch, document.createTextNode(readable(slice.name, slice.count, total)));
      legend.append(item);
    });
    wrapper.append(svg, legend);
    const note = element('p', 'Shares use ' + number(total) + (omitted ? ' total entries; the linked list shows ' + number(sum(rows)) + '. Other includes the remaining ' + number(omitted) + ' entries and any grouped small categories.' : ' entries across the listed categories; small categories may be grouped as Other.') + ' Hover, tap or focus a slice for its count and share.', 'statistics-chart-note');
    return [wrapper, note];
  }
  function migrations(panel, rows) {
    const script = panel.querySelector('script.statistics-migration-data');
    let source;
    if (script) {
      try {
        source = JSON.parse(script.textContent);
        if (!Array.isArray(source) || !source.every(row => Array.isArray(row) && row.length === 3 && typeof row[0] === 'string' && typeof row[1] === 'string' && Number.isSafeInteger(row[2]) && row[2] > 0)) source = null;
      } catch (_) { source = null; }
    }
    const complete = !!source;
    if (!source) source = rows.map(row => {
      const regions = row.name.split(/\s*→\s*/);
      return regions.length === 2 ? [regions[0], regions[1], row.count] : null;
    }).filter(Boolean);
    const pairs = new Map();
    source.forEach(([origin, destination, count]) => {
      const key = JSON.stringify([origin, destination]);
      const existing = pairs.get(key);
      if (existing) existing.count += count;
      else pairs.set(key, {origin, destination, count});
    });
    return {rows: [...pairs.values()], complete};
  }
  function flows(data, tooltip) {
    const rows = data.rows, total = sum(rows);
    const origins = new Map(), destinations = new Map();
    rows.forEach(row => {
      origins.set(row.origin, (origins.get(row.origin) || 0) + row.count);
      destinations.set(row.destination, (destinations.get(row.destination) || 0) + row.count);
    });
    const count = Math.max(origins.size, destinations.size), gap = 15;
    const height = Math.max(390, count * 34 + 65), available = height - 75;
    const scale = (available - gap * Math.max(0, count - 1)) / total;
    const svg = svgElement('svg', {viewBox: '0 0 900 ' + height, role: 'group', 'aria-label': 'Recorded migrations from birth region to death region', class: 'statistics-flow-svg'});
    svg.append(svgElement('text', {x: 240, y: 22, 'text-anchor': 'end', class: 'statistics-flow-heading'}, 'Birth region'));
    svg.append(svgElement('text', {x: 660, y: 22, class: 'statistics-flow-heading'}, 'Death region'));
    function layout(totals) {
      const nodes = new Map();
      const sorted = [...totals].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
      let y = 45 + (available - total * scale - gap * (sorted.length - 1)) / 2;
      sorted.forEach(([name, value], index) => {
        nodes.set(name, {name, count: value, y, offset: 0, height: value * scale, color: palette[index % palette.length]});
        y += value * scale + gap;
      });
      return nodes;
    }
    const left = layout(origins), right = layout(destinations);
    rows.slice().sort((a, b) => left.get(a.origin).y - left.get(b.origin).y || right.get(a.destination).y - right.get(b.destination).y).forEach(row => {
      const origin = left.get(row.origin), destination = right.get(row.destination);
      const y1 = origin.y + origin.offset, y2 = destination.y + destination.offset, thickness = row.count * scale;
      const path = svgElement('path', {d: 'M260,' + y1 + ' C445,' + y1 + ' 455,' + y2 + ' 640,' + y2 + ' L640,' + (y2 + thickness) + ' C455,' + (y2 + thickness) + ' 445,' + (y1 + thickness) + ' 260,' + (y1 + thickness) + ' Z', fill: origin.color, 'fill-opacity': '.48', class: 'statistics-flow-link'});
      svg.append(interactive(path, readable(row.origin + ' → ' + row.destination, row.count, total), tooltip));
      origin.offset += thickness; destination.offset += thickness;
    });
    [left, right].forEach((nodes, side) => {
      nodes.forEach(node => {
        const rectangle = svgElement('rect', {x: side ? 640 : 246, y: node.y, width: 14, height: node.height, fill: node.color, class: 'statistics-flow-node'});
        svg.append(interactive(rectangle, (side ? 'Death' : 'Birth') + ' region — ' + readable(node.name, node.count, total), tooltip));
        svg.append(svgElement('text', {x: side ? 660 : 236, y: node.y + node.height / 2, dy: '.35em', 'text-anchor': side ? 'start' : 'end', class: 'statistics-flow-label'}, node.name + ' (' + number(node.count) + ')'));
      });
    });
    const note = element('p', number(total) + ' recorded migrations. ' + (data.complete ? 'All recorded broad-region flows are included.' : 'Only the flows in the displayed list are included; other recorded migrations are outside this diagram.') + ' Widths and node heights use the same count scale. Birth and death columns are separate even when a region appears in both. These endpoints do not establish a direct move or travel route. Hover, tap or focus a flow for its count and share.', 'statistics-chart-note');
    return [svg, note];
  }
  document.querySelectorAll('.statistics-panel').forEach(panel => {
    if (panel.dataset.chartEnhanced) return;
    const heading = panel.querySelector('h3'), list = panel.querySelector('ol.statistics-bars');
    if (!heading || !list) return;
    const title = heading.textContent.trim();
    const isFlow = title === 'Most common recorded migrations';
    const isPie = ['Most frequent given names', 'Largest exported family branches', 'Birth centuries'].includes(title);
    if (!isPie && !isFlow) return;
    const rows = [...list.children].map(item => ({
      name: item.querySelector('.statistics-label')?.textContent.trim() || '',
      count: Number((item.querySelector('strong')?.textContent || '').replace(/[^0-9]/g, ''))
    })).filter(row => row.name && Number.isSafeInteger(row.count) && row.count > 0);
    if (!rows.length) return;
    const total = Number(panel.dataset.total) || sum(rows);
    if (!Number.isSafeInteger(total) || total < sum(rows)) return;
    const data = isFlow ? migrations(panel, rows) : null;
    if (isFlow && !data.rows.length) return;
    const chart = element('div', undefined, 'statistics-panel-chart');
    const tooltip = element('p', 'Hover, tap or focus the chart to inspect a count.', 'statistics-chart-tooltip');
    tooltip.setAttribute('role', 'status');
    tooltip.hidden = true;
    const rendered = isFlow ? flows(data, tooltip) : pie(rows, total, title, tooltip);
    chart.append(...rendered, tooltip);
    const controls = element('div', undefined, 'statistics-chart-controls');
    controls.setAttribute('role', 'group');
    controls.setAttribute('aria-label', title + ' chart view');
    const table = element('details', undefined, 'statistics-chart-data');
    const summary = element('summary', 'View linked counts');
    table.append(summary);
    list.before(controls, chart, table);
    table.append(list);
    const buttons = [];
    function select(mode) {
      chart.hidden = mode === 'bars';
      table.open = mode === 'bars';
      summary.hidden = mode === 'bars';
      buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
      panel.dataset.chartView = mode;
    }
    (isFlow ? [['flows', 'Flows'], ['bars', 'Bars']] : [['bars', 'Bars'], ['pie', 'Pie']]).forEach(([mode, label]) => {
      const button = element('button', label);
      button.type = 'button';
      button.dataset.mode = mode;
      button.addEventListener('click', () => select(mode));
      buttons.push(button); controls.append(button);
    });
    select(isFlow ? 'flows' : 'bars');
    panel.dataset.chartEnhanced = 'true';
  });
})();
