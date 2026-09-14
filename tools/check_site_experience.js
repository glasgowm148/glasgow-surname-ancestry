/* Optional real-browser regressions, using an already-open local site:
 * playwright-cli run-code "$(cat tools/check_site_experience.js)"
 * Run against http://127.0.0.1:8080 (or another local preview origin).
 * This script reads pages only; it does not submit or edit research.
 */
async (page) => {
  const origin = await page.evaluate(() => location.origin);
  if (!/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin)) {
    throw new Error('Open the local site preview before running these checks.');
  }
  const failures = [], errors = [];
  const onError = error => errors.push(error.message);
  page.on('pageerror', onError);
  let checks = 0;
  const check = (condition, message) => { checks++; if (!condition) failures.push(message); };
  const visible = async selector => await page.locator(selector).first().isVisible();
  const visit = async path => { await page.goto(origin + path); await page.waitForLoadState('domcontentloaded'); };
  try {
    for (const width of [1440, 390]) {
      await page.setViewportSize({width, height:900});
      for (const path of ['/', '/resources/']) {
        await visit(path);
        for (const url of ['https://www.wikitree.com/wiki/Space:Glasgow_Name_Study', 'https://groups.io/g/glasgowdnaproject/', 'https://glasgowfamilygenealogy.org/']) {
          check(await visible(`main a[href="${url}"]`), `${width} ${path}: hidden/missing community action ${url}`);
        }
      }
      await visit('/people/glasgow-2223.html');
      check(await visible('.profile-wikitree-actions a[href="https://www.wikitree.com/wiki/Glasgow-2223"]'), `${width}: own WikiTree action unavailable`);
      check(await visible('#person-summary'), `${width}: person summary unavailable`);
      check(await visible('a[href="/changes/"]'), `${width}: Latest research unavailable from person`);
      check(await page.locator('.person-technical-fold[open]').count() === 0, `${width}: technical material expanded by default`);
      await visit('/statistics/');
      check(await page.locator('.statistics-summary > div').count() >= 9, `${width}: missing summary metrics`);
      const panels = page.locator('.statistics-panel');
      check(await panels.count() >= 7, `${width}: missing statistics panels`);
      for (let i=0; i<await panels.count(); i++) check(await panels.nth(i).isVisible(), `${width}: hidden statistics panel ${i}`);
      await visit('/changes/');
      check(await visible('#latest-research .latest-research-entry'), `${width}: research feed unavailable`);
      await visit('/branches/');
      for (const id of ['experience-regions', 'research-studies', 'irish-research-studies']) check(await visible('#' + id), `${width}: missing family section ${id}`);
      check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${width}: family page horizontal overflow`);
      const contrast = await page.locator('.family-study-where').first().evaluate(element => {
        const rgb = value => (value.match(/[\d.]+/g) || []).map(Number);
        const light = values => values.slice(0,3).map(v => { const s=v/255; return s<=0.04045?s/12.92:Math.pow((s+0.055)/1.055,2.4); }).reduce((sum,v,i)=>sum+v*[0.2126,0.7152,0.0722][i],0);
        const foreground = light(rgb(getComputedStyle(element).color));
        let background = [255,255,255];
        for (let node=element; node; node=node.parentElement) {
          const values=rgb(getComputedStyle(node).backgroundColor);
          if (values.length>=3 && (values.length===3 || values[3]===1)) { background=values; break; }
        }
        const back = light(background);
        return (Math.max(foreground,back)+0.05)/(Math.min(foreground,back)+0.05);
      });
      check(contrast >= 4.5, `${width}: family metadata contrast ${contrast.toFixed(2)}:1 below 4.5:1`);
      if (width === 390) {
        await page.locator('#g-nav-toggle').click();
        check(await page.locator('#g-nav-toggle').getAttribute('aria-expanded') === 'true', 'Mobile navigation did not open');
        await page.keyboard.press('Escape');
        check(await page.locator('#g-nav-toggle').getAttribute('aria-expanded') === 'false', 'Escape did not close mobile navigation');
      }
    }
    await visit('/map/?path=1&rootA=Glasgow-951&rootB=Glasgow-822&evidence=explicit&q=Mary%20Glasgow#map');
    await page.waitForURL('**/map/advanced.html?**');
    check(page.url() === origin + '/map/advanced.html?path=1&rootA=Glasgow-951&rootB=Glasgow-822&evidence=explicit&q=Mary%20Glasgow#map', 'Legacy Map query/hash changed');
    await visit('/map/?q=Glasgow&country=ireland&from=1700&to=1900');
    check(await page.evaluate(() => location.pathname) === '/map/', 'Ordinary filters incorrectly redirect to specialist Map');
    const specialist = await page.locator('a[href*="/map/advanced.html"]').first().evaluate(link => {
      const params = new URL(link.href, location.href).searchParams;
      return {q:params.get('q'), year:params.get('year'), regions:params.get('regions')};
    });
    check(specialist.q === 'Glasgow' && specialist.year === '1900' && specialist.regions === 'ireland', 'Specialist Map loses current filters');
    check(errors.length === 0, 'Browser errors: ' + errors.join('; '));
    if (failures.length) throw new Error(failures.join('\n'));
    return {checks, failures:0, widths:[1440,390]};
  } finally {
    page.off('pageerror', onError);
  }
}
