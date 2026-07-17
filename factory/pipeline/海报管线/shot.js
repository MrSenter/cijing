const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const data = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'data.json'), 'utf-8'));
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1536, height: 1024 },
    deviceScaleFactor: 2,
  });
  const logs = [];
  page.on('console', msg => logs.push(msg.text()));
  await page.addInitScript((d) => { window.__DATA__ = d; }, data);
  const filePath = 'file://' + path.resolve(__dirname, 'poster.html');
  await page.goto(filePath);
  await page.waitForFunction(() => window.__ready === true, { timeout: 5000 });
  await page.waitForTimeout(200);
  const labelCount = await page.evaluate(() => window.__labelCount);
  const issues = await page.evaluate(() => window.__issues);
  await page.screenshot({ path: data.outPath ? path.resolve(data.outPath) : path.resolve(__dirname, '海报A-超市-playwright.png') });
  await browser.close();
  console.log('LOGS:', logs.join(' | '));
  console.log('labelCount=', labelCount, 'issues=', JSON.stringify(issues));
})();
