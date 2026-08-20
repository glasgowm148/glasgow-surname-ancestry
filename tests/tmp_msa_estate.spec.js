const { test } = require('@playwright/test');

test('capture remaining estate deposition pages', async ({ page }) => {
  const url = 'https://pve.msa.maryland.gov/pages/viewer.aspx?vURGTEhmw2K2arvRU6JTB55jp41whOKKAWb60Yd4R4u3NJ%2FXxvDGsDOKdf9NZc%2FD41s%2FxaVyQE0YLsOklRdNeQ%3D%3D';
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  for (const number of [2, 3]) {
    await page.locator('#ContentPlaceHolder1_forwardbtntop').click();
    await page.waitForLoadState('domcontentloaded');
    const src = await page.locator('#ContentPlaceHolder1_iframePDF').getAttribute('src');
    console.log(`PAGE${number}=${new URL(src, page.url()).href}`);
  }
});
