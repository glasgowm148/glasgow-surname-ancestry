/* Progressive charts for the maintained statistics panels; the source lists stay usable. */
(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const palette = ['#426f58', '#b78049', '#58889b', '#8b7397', '#8e9c62', '#bd766d', '#c2a04a', '#527c7b', '#a66a43', '#7e8da9', '#9e967e', '#6b8c64', '#d3d6c9'];
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
  function horizontalBars(rows, title, tooltip) {
    const shown = rows.slice(0, 10);
    const width = 480, rowHeight = 32, height = shown.length * rowHeight + 16;
    const maximum = Math.max(...rows.map(row => row.count));
    const svg = svgElement('svg', {viewBox: '0 0 ' + width + ' ' + height, role: 'group', 'aria-label': title + ' bar chart', class: 'statistics-horizontal-svg'});
    shown.forEach((row, index) => {
      const y = 8 + index * rowHeight;
      const name = row.name.length > 24 ? row.name.slice(0, 23).trimEnd() + '…' : row.name;
      const label = svgElement('text', {x: 178, y: y + 15, 'text-anchor': 'end', class: 'statistics-horizontal-label'}, name);
      label.append(svgElement('title', {}, row.name));
      svg.append(label);
      svg.append(svgElement('rect', {x: 190, y, width: 230, height: 20, rx: 3, class: 'statistics-horizontal-track', 'aria-hidden': 'true'}));
      const bar = svgElement('rect', {x: 190, y, width: row.count / maximum * 230, height: 20, rx: 3, fill: palette[0], class: 'statistics-horizontal-bar'});
      svg.append(interactive(bar, row.name + ': ' + number(row.count), tooltip));
      svg.append(svgElement('text', {x: 470, y: y + 15, 'text-anchor': 'end', class: 'statistics-horizontal-count'}, number(row.count)));
    });
    const subset = shown.length < rows.length ? 'The leading ' + shown.length + ' categories are shown; select Counts for all ' + rows.length + '. ' : '';
    return [svg, element('p', subset + 'Counts match the linked source list. Each bar uses the same scale; categories may overlap where a person has several documented associations.', 'statistics-chart-note')];
  }
  function columns(rows, total, title, tooltip) {
    const numbered = rows.map(row => [Number((row.name.match(/^\d+/) || [])[0]), row]);
    if (numbered.every(([century]) => Number.isInteger(century))) {
      const first = Math.min(...numbered.map(([century]) => century));
      const last = Math.max(...numbered.map(([century]) => century));
      if (last - first <= 30) {
        const known = new Map(numbered);
        const ordinal = value => value + ([11, 12, 13].includes(value % 100) ? 'th' : ({1: 'st', 2: 'nd', 3: 'rd'}[value % 10] || 'th'));
        rows = Array.from({length: last - first + 1}, (_, index) => {
          const century = first + index;
          return known.get(century) || {name: ordinal(century) + ' century', count: 0};
        });
      }
    }
    const svg = svgElement('svg', {viewBox: '0 0 580 310', role: 'group', 'aria-label': title + ' column chart', class: 'statistics-columns-svg'});
    const maximum = Math.max(...rows.map(row => row.count)), baseline = 257, plotHeight = 205;
    [...new Set([0, Math.round(maximum / 2), maximum])].forEach(value => {
      const y = baseline - value / maximum * plotHeight;
      svg.append(svgElement('line', {x1: 45, x2: 570, y1: y, y2: y, stroke: '#ccd8d5', class: 'statistics-chart-gridline', 'aria-hidden': 'true'}));
      svg.append(svgElement('text', {x: 37, y, dy: '.35em', 'text-anchor': 'end', 'font-size': 10, class: 'statistics-chart-axis'}, number(value)));
    });
    const step = 525 / rows.length, barWidth = Math.min(42, step * 0.64);
    rows.forEach((row, index) => {
      const x = 45 + step * (index + 0.5), barHeight = row.count / maximum * plotHeight;
      const bar = svgElement('rect', {x: x - barWidth / 2, y: baseline - barHeight, width: barWidth, height: barHeight, rx: 3, fill: palette[0], class: 'statistics-column'});
      svg.append(interactive(bar, readable(row.name, row.count, total), tooltip));
      svg.append(svgElement('text', {x, y: baseline - barHeight - 8, 'text-anchor': 'middle', 'font-size': 11, class: 'statistics-column-count'}, number(row.count)));
      const label = svgElement('text', {x, y: baseline + 24, 'text-anchor': 'middle', 'font-size': 11, class: 'statistics-column-label'}, row.name.replace(/\s+century$/i, ''));
      label.append(svgElement('title', {}, row.name));
      svg.append(label);
    });
    svg.append(svgElement('text', {x: 305, y: 304, 'text-anchor': 'middle', 'font-size': 10, class: 'statistics-chart-axis'}, 'Birth century'));
    return [svg, element('p', number(total) + ' people have a usable birth year. Columns show recorded century counts, including zero for empty intervening centuries; estimated birth years remain estimates.', 'statistics-chart-note')];
  }
  document.querySelectorAll('.statistics-panel').forEach(panel => {
    if (panel.dataset.chartEnhanced) return;
    const heading = panel.querySelector('h3'), list = panel.querySelector('ol.statistics-bars');
    if (!heading || !list) return;
    const title = heading.textContent.trim();
    const isFlow = title === 'Most common recorded migrations';
    const isCentury = title === 'Birth centuries';
    const isPie = ['Most frequent given names', 'Largest exported family branches'].includes(title);
    const isOverlap = ['People by region', 'Most frequent mapped places', 'Surnames joined by marriage to Glasgow'].includes(title);
    if (!isPie && !isFlow && !isCentury && !isOverlap) return;
    const rows = [...list.children].map(item => ({
      name: item.querySelector('.statistics-label')?.textContent.trim() || '',
      count: Number((item.querySelector('strong')?.textContent || '').replace(/[^0-9]/g, ''))
    })).filter(row => row.name && Number.isSafeInteger(row.count) && row.count > 0);
    if (!rows.length) return;
    const total = Number(panel.dataset.total) || sum(rows);
    if (!Number.isSafeInteger(total) || total < sum(rows)) return;
    const data = isFlow ? migrations(panel, rows) : null;
    if (isFlow && !data.rows.length) return;
    const modes = isFlow ? [['flows', 'Flows']] : isCentury ? [['columns', 'Columns'], ['pie', 'Pie']] : isPie ? [['pie', 'Pie'], ['bars', 'Bars']] : [['bars', 'Bars']];
    const chart = element('div', undefined, 'statistics-panel-chart');
    const tooltip = element('p', 'Hover, tap or focus the chart to inspect a count.', 'statistics-chart-tooltip');
    tooltip.setAttribute('role', 'status');
    tooltip.hidden = true;
    const views = [];
    modes.forEach(([mode]) => {
      const view = element('div', undefined, 'statistics-chart-view');
      view.dataset.mode = mode;
      const rendered = mode === 'flows' ? flows(data, tooltip) : mode === 'columns' ? columns(rows, total, title, tooltip) : mode === 'bars' ? horizontalBars(rows, title, tooltip) : pie(rows, total, title, tooltip);
      const method = element('details', undefined, 'statistics-chart-method');
      method.append(element('summary', 'Chart details'), rendered[1]);
      view.append(rendered[0], method);
      chart.append(view);
      views.push(view);
    });
    chart.append(tooltip);
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
      chart.hidden = mode === 'counts';
      tooltip.hidden = true;
      views.forEach(view => { view.hidden = view.dataset.mode !== mode; });
      table.open = mode === 'counts';
      summary.hidden = mode === 'counts';
      buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
      panel.dataset.chartView = mode;
    }
    [...modes, ['counts', 'Counts']].forEach(([mode, label]) => {
      const button = element('button', label);
      button.type = 'button';
      button.dataset.mode = mode;
      button.addEventListener('click', () => select(mode));
      buttons.push(button); controls.append(button);
    });
    select(modes[0][0]);
    panel.dataset.chartEnhanced = 'true';
  });
})();
