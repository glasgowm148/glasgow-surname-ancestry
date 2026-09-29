/* Focused source-library checks using an open local Playwright CLI page. */
async page => {
  const origin = await page.evaluate(() => location.origin);
  if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(origin)) throw Error('Open a local preview first.');
  let checks = 0;
  const errors = [];
  const onError = error => errors.push(error.message);
  const check = (ok, message) => { if (!ok) throw Error(message); checks++; };
  const settled = () => page.waitForFunction(() => document.querySelector('#v3-source-search').getAttribute('aria-busy') !== 'true');
  const rows = page.locator('.v3-source-row');
  const count = page.locator('#v3-source-count');
  const visit = async query => { await page.goto(origin + '/sources/' + (query || '')); await settled(); };
  page.on('pageerror', onError);
  try {
    const data = await (await page.request.get(origin + '/assets/v3/source-index.json')).json();
    await page.setViewportSize({width:1440, height:1000});
    await visit();
    check(!await page.locator('#repair-source-notice').isVisible(), 'Live source index loads without fallback');
    check((await count.textContent()).includes('of ' + data.length.toLocaleString()), 'Full source count loads');
    check(await rows.count() === 24, 'First page has 24 source rows');
    check(await page.locator('.g-crumbs strong').textContent() === 'Sources', 'Breadcrumb identifies sources');
    await page.getByRole('button', {name:'Next →', exact:true}).click(); await settled();
    check((await count.textContent()).startsWith('25–48'), 'Pagination advances range');
    await page.locator('#v3-source-q').fill('Glasgow-951');
    await page.getByRole('button', {name:'Search', exact:true}).click(); await settled();
    check(await rows.count() > 0, 'WikiTree ID search finds sources');
    check(await page.evaluate(() => new URLSearchParams(location.search).get('q')) === 'Glasgow-951', 'Query retained in URL');
    await page.reload(); await settled();
    check(await page.locator('#v3-source-q').inputValue() === 'Glasgow-951', 'Query survives reload');
    await page.getByRole('button', {name:'Clear filters', exact:true}).click(); await settled();
    await page.locator('#v3-source-kind').selectOption('shared'); await settled();
    const shared = data.filter(r => r.members.length > 1).length;
    check((await count.textContent()).includes('of ' + shared.toLocaleString()), 'Shared source filter gives accurate total');
    await page.locator('#v3-source-kind').selectOption('image'); await settled();
    const media = data.filter(r => r.image || r.transcription).length;
    check((await count.textContent()).includes('of ' + media.toLocaleString()), 'Image/text filter handles current availability');
    await page.getByRole('button', {name:'Clear filters', exact:true}).click(); await settled();
    await page.locator('#v3-source-q').fill('zzzz-no-source-match');
    await page.getByRole('button', {name:'Search', exact:true}).click(); await settled();
    check(await rows.count() === 0 && await page.getByRole('heading', {name:'No matching source items.'}).isVisible(), 'Empty search has useful feedback');
    await page.getByRole('button', {name:'Clear this search', exact:true}).click(); await settled();
    check(await rows.count() === 24 && await page.locator('#v3-source-q').inputValue() === '', 'Empty state can clear search');
    await visit('?person=Glasgow-951');
    check((await count.textContent()).includes('selected scope') && await rows.count() > 0, 'Person scope works');
    await page.getByRole('button', {name:'Clear filters', exact:true}).click(); await settled();
    check(await page.evaluate(() => new URLSearchParams(location.search).get('person')) === 'Glasgow-951', 'Clear filters retains scope');
    await visit();
    check(await page.locator('.sources-collection').count() === 5, 'Five research collections retained');
    await page.locator('.sources-collection').first().locator('summary').click();
    check(await page.locator('#opr-births-discovery').isVisible(), 'Collection disclosure opens preserved review');
    const sourceUrl = await rows.first().locator('h3 a').getAttribute('href');
    check((await page.request.get(origin + sourceUrl)).ok(), 'Source reader destination exists');
    await page.locator('.sources-collection').first().locator('summary').click();
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({width, height:width === 1440 ? 1000 : 844});
      await page.evaluate(() => scrollTo(0,0));
      if (width < 600) await page.waitForFunction(() => document.querySelector('.g-rail').getBoundingClientRect().right <= 0);
      check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), width + 'px has no overflow');
      for (const selector of ['#v3-source-q', '#v3-source-kind', '.sources-search-fields button']) {
        const box = await page.locator(selector).boundingBox();
        check(box && box.width > 50 && box.x >= 0 && box.x + box.width <= width, selector + ' fits ' + width);
      }
      if (width !== 320) await page.screenshot({path:'output/playwright/sources-final-' + width + '.png'});
    }
    await page.getByRole('link', {name:'Reviewed collections ↓', exact:true}).click();
    check(await page.locator('#sources-collections-heading').isVisible(), 'Mobile collection jump works');
    const route = '**/assets/v3/source-index-packed.json';
    await page.context().route(route, r => r.fulfill({status:503, body:'Unavailable'}));
    await visit();
    check(await page.locator('#repair-source-notice').isVisible() && await rows.count() === 24, 'Worker error preserves static listing');
    await page.context().unroute(route);
    await page.getByRole('button', {name:'Retry search', exact:true}).click(); await settled();
    check(!await page.locator('#repair-source-notice').isVisible() && await rows.count() === 24, 'Retry restores source search');
    const context = await page.context().browser().newContext({javaScriptEnabled:false});
    try {
      const staticPage = await context.newPage(); await staticPage.goto(origin + '/sources/');
      check(await staticPage.locator('.v3-source-row').count() === 24, 'No-JavaScript listing has 24 usable source links');
      check(await staticPage.getByRole('link', {name:'Complete index ↗'}).getAttribute('href') === '/sources/browse/', 'No-JavaScript full index route retained');
    } finally { await context.close(); }
    check(errors.length === 0, 'No runtime errors: ' + errors.join('; '));
    await page.setViewportSize({width:1440, height:1000}); await visit();
    return {passed:checks, runtimeErrors:errors};
  } finally { page.removeListener('pageerror', onError); }
}
