/* Run with Playwright CLI against an open preview or the published site. */
async page => {
  const origin = new URL(page.url()).origin;
  const errors = [], failures = [];
  let checks = 0;
  const onError = error => errors.push(error.message);
  const check = (value, message) => { checks++; if (!value) failures.push(message); };
  const visit = route => page.goto(origin + route);
  page.on('pageerror', onError);
  try {
    for (const width of [1440, 390]) {
      await page.setViewportSize({width, height:900});
      await visit('/records/?person=Glasgow-951');
      await page.waitForFunction(() => document.querySelector('#record-count').textContent.includes('of 6 record'));
      await page.getByLabel('People included').selectOption('family');
      await page.waitForFunction(() => document.querySelector('#record-count').textContent.includes('of 37 record'));
      check((await page.locator('.record-result').count()) === 37, width + ': family results update without reload');
      await page.getByLabel('People included').selectOption('person');
      await page.waitForFunction(() => document.querySelector('#record-count').textContent.includes('of 6 record'));
      check((await page.locator('.record-result').count()) === 6, width + ': person scope restores');
      await page.screenshot({path:'output/playwright/site-fixes-20261002/records-' + width + '.png'});
      await visit('/records/?country=scotland');
      const records = await (await page.request.get(origin + '/data/records-index.json')).json();
      const expected = records.filter(r => ['Scotland','Scotland / England'].includes(r.region)).length;
      await page.waitForFunction(n => document.querySelector('#record-count').textContent.includes('of ' + n.toLocaleString() + ' record'), expected);
      check(expected > 0, width + ': inherited Scottish filter applied');
      await page.getByRole('combobox', {name:'Region', exact:true}).selectOption('Ireland');
      await page.waitForFunction(() => document.querySelector('#record-count').textContent === 'No record matches those filters.');
      check(await page.locator('.record-result').count() === 0, width + ': conflicting filters do not override scope');

      await visit('/');
      await page.locator('[data-g-search]').first().click();
      const input = page.getByRole('combobox', {name:'Search people, places, records and pages'});
      await input.fill('Glasgow');
      await page.waitForFunction(() => [...document.querySelectorAll('.g-result-group')].some(e => e.textContent.startsWith('People ·')));
      const groups = await page.locator('.g-result-group').allTextContents();
      check(groups.some(s => s.startsWith('People ·')) && groups.some(s => s.startsWith('Records ·')), width + ': All includes people and records');
      await page.getByRole('tab', {name:'Pages',exact:true}).click();
      await input.fill('latest findings');
      await page.waitForFunction(() => document.querySelectorAll('#g-search-results a[href="/latest-findings/"]').length === 1);
      check(await page.locator('#g-search-results a').count() === 1, width + ': Latest findings searchable once');
      await input.fill('free-space library');
      await page.waitForFunction(() => document.querySelectorAll('#g-search-results a[href="/free-space/"]').length === 1);
      check(await page.locator('#g-search-results a').count() === 1, width + ': old library alias deduplicated');
      await page.keyboard.press('Escape');
      check(!await page.locator('#g-search-dialog').isVisible(), width + ': keyboard closes search');
    }
    await visit('/catalogue/index.html?missingProfile=1');
    await page.waitForURL(url => url.pathname === '/catalogue/' || url.pathname === '/catalogue');
    check(new URL(page.url()).searchParams.get('missingProfile') === '1', 'Catalogue redirect preserves query and destination');
    await visit('/people/research-material/glasgow-951-d73f1b5ef1a0f47b/index.html');
    check(new URL(page.url()).pathname.startsWith('/people/research-material/'), 'Research reader stays on its own page');
    for (const type of ['births','deaths']) {
      const response = await page.request.get(origin + '/data/scotlandspeople-opr-' + type + '-to-1700.json');
      check(response.ok(), 'Reviewed ' + type + ' download exists');
      await visit('/branches/scottish-families/#opr-' + type + '-to-1700');
      check(await page.locator('#opr-' + type + '-to-1700').count() === 1, 'Reviewed ' + type + ' anchor exists');
    }
    await visit('/sources/s-948d67e0bace40ea/');
    check(!(await page.locator('.static-source-evidence').innerText()).includes('research assessment — 1081'), 'False source date removed from static reader');
    await visit('/about/');
    check((await page.locator('table').first().innerText()).includes('27 September 2026'), 'About compilation date agrees with catalogue');
    await visit('/people/glasgow-3080.html');
    check(await page.getByText('Source located: parish index; original image uninspected.', {exact:true}).isVisible(), 'Reviewed OPR source note visible by default');
    check(errors.length === 0, 'No runtime errors: ' + errors.join('; '));
    if (failures.length) throw Error(failures.join('\n'));
    return {checks, failures:0, widths:[1440,390], origin};
  } finally { page.off('pageerror', onError); }
}
