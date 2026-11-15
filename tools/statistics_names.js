/* First-name distribution: public aggregate rows emitted by the page builder. */
(() => {
  'use strict';
  const data = document.getElementById('names-data');
  if (!data) return;
  const rows = JSON.parse(data.textContent);
  const century = document.getElementById('names-century');
  const gender = document.getElementById('names-gender');
  const summary = document.getElementById('names-summary');
  const pie = document.getElementById('names-pie');
  const body = document.getElementById('names-rows');
  const colors = ['#375840','#6b7340','#b17a43','#607f94','#957085','#8eaa7b',
    '#c8a44e','#637c72','#b96854','#7984a4','#a99678','#447b78','#c1c6b5'];
  const fmt = new Intl.NumberFormat('en-GB');
  const ns = 'http://www.w3.org/2000/svg';
  function svgElement(tag, attributes = {}) {
    const node = document.createElementNS(ns, tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }
  function point(radius, angle) {
    const radians = (angle - 90) * Math.PI / 180;
    return [200 + radius * Math.cos(radians), 200 + radius * Math.sin(radians)];
  }
  function slicePath(start, end) {
    // Two arcs per edge also handle a single name occupying the whole circle.
    const middle = (start + end) / 2;
    return 'M ' + point(178, start).join(' ') +
      ' A 178 178 0 0 1 ' + point(178, middle).join(' ') +
      ' A 178 178 0 0 1 ' + point(178, end).join(' ') +
      ' L ' + point(106, end).join(' ') +
      ' A 106 106 0 0 0 ' + point(106, middle).join(' ') +
      ' A 106 106 0 0 0 ' + point(106, start).join(' ') + ' Z';
  }
  function render() {
    const counts = new Map();
    let omitted = 0;
    for (const [name, year, sex, count] of rows) {
      if (gender.value && sex !== gender.value) continue;
      if (century.value && year === null) { omitted += count; continue; }
      if (century.value && year >= Number(century.value)) continue;
      counts.set(name, (counts.get(name) || 0) + count);
    }
    const names = [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    const total = names.reduce((sum, item) => sum + item[1], 0);
    const slices = names.slice(0, 12);
    if (names.length > 12) slices.push(['Other names', names.slice(12).reduce((sum, item) => sum + item[1], 0)]);
    const share = count => (100 * count / total).toFixed(1) + '%';
    summary.textContent = total
      ? fmt.format(total) + ' people · ' + fmt.format(names.length) + ' first names'
      : 'No people match these filters.';
    summary.textContent += ' · ' + (century.value ? 'Born before ' + century.value : 'All birth years') +
      ' · ' + (gender.value || 'All genders') + ' · Surname at birth: Glasgow';
    if (century.value) summary.textContent += ' · ' + fmt.format(omitted) + ' excluded without a single birth year.';
    pie.replaceChildren();
    body.replaceChildren();
    if (!total) {
      const empty = document.createElement('p');
      empty.className = 'statistics-name-empty';
      empty.textContent = 'No matching people';
      pie.append(empty);
      return;
    }
    const chart = svgElement('svg', {viewBox: '0 0 400 400', role: 'group',
      'aria-label': 'First-name pie chart. Focus or tap a slice for its name, count and percentage.'});
    const centerCount = svgElement('text', {x: 200, y: 197, class: 'statistics-pie-total', 'aria-hidden': 'true'});
    centerCount.textContent = fmt.format(total);
    const centerLabel = svgElement('text', {x: 200, y: 225, class: 'statistics-pie-label', 'aria-hidden': 'true'});
    centerLabel.textContent = 'people';
    const tooltip = document.createElement('div');
    tooltip.id = 'names-tooltip';
    tooltip.className = 'statistics-pie-tooltip';
    tooltip.setAttribute('role', 'tooltip');
    tooltip.hidden = true;
    const tipName = document.createElement('strong');
    const tipDetail = document.createElement('span');
    tooltip.append(tipName, tipDetail);
    const tableRows = [];
    const paths = [];
    function clear() {
      tooltip.hidden = true;
      centerCount.textContent = fmt.format(total);
      centerLabel.textContent = 'people';
      paths.forEach(path => path.classList.remove('is-active'));
      tableRows.forEach(row => row.classList.remove('is-highlighted'));
    }
    function show(index) {
      clear();
      const [name, count] = slices[index];
      paths[index].classList.add('is-active');
      // The Other names slice represents every table row beyond the first 12.
      tableRows.forEach((row, i) => row.classList.toggle('is-highlighted', index === 12 ? i >= 12 : i === index));
      centerCount.textContent = share(count);
      centerLabel.textContent = 'of people';
      tipName.textContent = name;
      tipDetail.textContent = fmt.format(count) + ' people · ' + share(count);
      tooltip.hidden = false;
    }
    let angle = 0;
    slices.forEach(([name, count], i) => {
      const start = angle;
      angle += count / total * 360;
      const path = svgElement('path', {d: slicePath(start, angle), fill: colors[i],
        class: 'statistics-pie-slice', tabindex: '0', role: 'button',
        'aria-label': name + ': ' + fmt.format(count) + ' people (' + share(count) + ')',
        'aria-describedby': 'names-tooltip'});
      const title = svgElement('title');
      title.textContent = name + ' — ' + fmt.format(count) + ' people (' + share(count) + ')';
      path.append(title);
      path.addEventListener('pointerenter', () => show(i));
      path.addEventListener('pointerleave', () => {
        if (document.activeElement === path) show(i);
        else clear();
      });
      path.addEventListener('focus', () => show(i));
      path.addEventListener('blur', clear);
      path.addEventListener('click', () => show(i));
      path.addEventListener('keydown', event => {
        if (event.key === 'Escape') { clear(); event.preventDefault(); }
        if (event.key === 'Enter' || event.key === ' ') { show(i); event.preventDefault(); }
        if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
          event.preventDefault();
          paths[(i + (event.key === 'ArrowRight' ? 1 : paths.length - 1)) % paths.length].focus();
        }
      });
      paths.push(path);
      chart.append(path);
    });
    let labelAngle = 0;
    slices.forEach(([name, count], i) => {
      const span = count / total * 360;
      const middle = labelAngle + span / 2;
      labelAngle += span;
      // Reserve enough arc length for the full name; smaller slices keep tooltips.
      if (span < 12 || 142 * span * Math.PI / 180 < name.length * 6.3 + 10) return;
      const [x, y] = point(142, middle);
      const label = svgElement('text', {x, y, class: 'statistics-pie-slice-label',
        transform: 'rotate(' + (middle > 90 && middle < 270 ? middle + 180 : middle) + ' ' + x + ' ' + y + ')',
        'aria-hidden': 'true'});
      const rgb = colors[i].slice(1).match(/../g).map(value => {
        const channel = parseInt(value, 16) / 255;
        return channel <= 0.04045 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
      });
      const luminance = rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722;
      label.setAttribute('fill', luminance > 0.24 ? '#20301c' : '#ffffff');
      label.textContent = name;
      chart.append(label);
    });
    chart.append(centerCount, centerLabel);
    pie.append(chart, tooltip);
    names.forEach(([name, count], i) => {
      const tr = document.createElement('tr');
      const label = document.createElement('th');
      label.scope = 'row';
      const swatch = document.createElement('span');
      swatch.className = 'statistics-name-swatch';
      swatch.style.backgroundColor = colors[Math.min(i, 12)];
      swatch.setAttribute('aria-hidden', 'true');
      label.append(swatch, document.createTextNode(name));
      const number = document.createElement('td');
      number.textContent = fmt.format(count);
      const percent = document.createElement('td');
      percent.textContent = share(count);
      tr.append(label, number, percent);
      tr.addEventListener('pointerenter', () => show(Math.min(i, 12)));
      tr.addEventListener('pointerleave', () => {
        const focused = paths.indexOf(document.activeElement);
        if (focused >= 0) show(focused);
        else clear();
      });
      tableRows.push(tr);
      body.append(tr);
    });
  }
  document.getElementById('names-reset').addEventListener('click', () => {
    century.value = '';
    gender.value = '';
    render();
  });
  century.addEventListener('change', render);
  gender.addEventListener('change', render);
  render();
})();
