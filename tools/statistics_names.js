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
      pie.style.background = '#e4eadc';
      pie.setAttribute('aria-label', 'No people match these filters');
      return;
    }
    let angle = 0;
    const stops = slices.map(([name, count], i) => {
      const start = angle;
      angle += count / total * 360;
      return colors[i] + ' ' + start + 'deg ' + angle + 'deg';
    });
    pie.style.background = 'conic-gradient(' + stops.join(',') + ')';
    pie.setAttribute('aria-label', 'First-name pie chart. ' + slices.map(
      ([name, count]) => name + ': ' + fmt.format(count) + ' people (' + share(count) + ')').join('; '));
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
