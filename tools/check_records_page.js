/* Focused browser check; run with Playwright CLI on a local site preview. */
async page => {
  const origin = await page.evaluate(() => location.origin);
  const param = key => page.evaluate(key => new URLSearchParams(location.search).get(key), key);
  if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(origin)) throw Error('Open a local preview first.');
  let checks = 0;
  const errors = [];
  const onError = error => errors.push(error.message);
  page.on('pageerror', onError);
  const check = (condition, label) => { if (!condition) throw Error(label); checks++; };
  const count = page.locator('#record-count');
  const rows = page.locator('.record-result');
  const settled = () => page.waitForFunction(() => !document.querySelector('#record-count').textContent.includes('Loading'));
  const visit = async query => { await page.goto(origin + '/records/' + (query || '')); await settled(); };
  const total = async expected => check((await count.textContent()).includes('of ' + expected.toLocaleString() + ' record'), 'Expected ' + expected + ' results');
  try {
    const data = await (await page.request.get(origin + '/data/records-index.json')).json();
    await page.setViewportSize({width:1440, height:1000});
    await visit();
    await total(data.length);
    check(await rows.count() === 50, 'First page contains 50 rows');
    await page.getByRole('button', {name:'Next', exact:true}).click();
    check((await count.textContent()).startsWith('51–100'), 'Next page advances range');
    check(await param('page') === '2', 'Page is retained in URL');
    await page.locator('#record-query').fill('Glasgow-951');
    check(await rows.count() > 0 && await rows.locator('.record-person a[href="/people/glasgow-951.html"]').count() > 0, 'WikiTree ID search finds its person');
    check(!await param('page'), 'Search resets page');
    await page.reload(); await settled();
    check(await page.locator('#record-query').inputValue() === 'Glasgow-951', 'Query survives reload');
    await page.getByRole('button', {name:'Clear filters'}).click();
    await page.locator('#r-record-citation').selectOption('explicit');
    await total(data.filter(r => r.supporting_source_status === 'explicit').length);
    check(await rows.locator('.evidence-explicit').count() === await rows.count(), 'Citation filter applies to every result');
    await page.getByRole('button', {name:'Clear filters'}).click();
    await page.locator('#record-region').selectOption('Ireland');
    await page.locator('#record-category').selectOption('Marriages');
    await page.locator('#record-from').fill('1800');
    await page.locator('#record-to').fill('1900');
    await total(data.filter(r => r.region === 'Ireland' && r.record_category.includes('Marriages') && r.filter_year >= 1800 && r.filter_year <= 1900).length);
    await page.locator('#record-from').fill('2000');
    check((await count.textContent()).includes('Start year'), 'Reversed years get useful feedback');
    await page.getByRole('button', {name:'Clear filters'}).click();
    await page.locator('#record-sort').selectOption('date-desc');
    const newest = Math.max(...data.filter(r => r.filter_year != null).map(r => Number(r.filter_year)));
    check((await rows.first().locator('.record-date').textContent()).includes(String(newest)), 'Newest sort starts with latest dated record');
    await page.getByRole('button', {name:'Clear filters'}).click();
    check(await page.locator('#record-sort').inputValue() === 'date-asc', 'Reset restores default sort');
    await page.locator('#record-query').fill('zzzz-no-such-record');
    check(await rows.count() === 0 && (await count.textContent()).includes('No record'), 'Empty search is explicit');
    await visit('?person=Glasgow-951');
    await total(data.filter(r => r.catalogue_id === 'glasgow-951').length);
    check(await page.locator('#records-scope').isVisible(), 'Person scope is visible');
    await page.getByRole('button', {name:'Clear filters'}).click();
    check(await param('person') === 'Glasgow-951', 'Clear filters retains person scope');
    await visit('?place=Lisnagaver');
    await total(data.filter(r => (r.record_location || '').toLowerCase().includes('lisnagaver')).length);
    await visit('?branch=larne-kilwaughter');
    check(await rows.count() > 0 && await page.locator('#records-scope').isVisible(), 'Family links open scoped records');
    await visit();
    await rows.first().locator('summary').click();
    check(await rows.first().locator('details').getAttribute('open') !== null, 'Record details expand');
    const target = await rows.first().locator('.record-person a').getAttribute('href');
    check((await page.request.get(origin + target)).ok(), 'Result opens a real person page');
    await rows.first().locator('summary').click();
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({width, height:width === 1440 ? 1000 : 844});
      await page.evaluate(() => scrollTo(0,0));
      if(width < 600) await page.waitForFunction(() => document.querySelector('.g-rail').getBoundingClientRect().right <= 0);
      check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), width + 'px has no horizontal overflow');
      for (const selector of ['#record-query', '#record-region', '#record-category', '#record-from', '#record-to', '#record-quality', '#r-record-citation']) {
        const box = await page.locator(selector).boundingBox();
        check(box && box.width >= 50 && box.x >= 0 && box.x + box.width <= width, selector + ' fits at ' + width);
      }
      if (width !== 320) await page.screenshot({path:'output/playwright/records-final-' + width + '.png'});
    }
    const route = '**/data/records-index.json';
    await page.route(route, r => r.fulfill({status:503, body:'Unavailable'}));
    await visit();
    check((await count.textContent()).includes('unavailable') && await page.getByRole('button', {name:'Retry', exact:true}).isVisible(), 'Failed request offers retry');
    await page.unroute(route);
    await page.getByRole('button', {name:'Retry', exact:true}).click();
    await settled(); await total(data.length);
    check(errors.length === 0, 'No browser runtime errors: ' + errors.join('; '));
    await page.setViewportSize({width:1440, height:1000});
    await visit();
    return {passed:checks, runtimeErrors:errors};
  } finally {
    page.removeListener('pageerror', onError);
  }
}
