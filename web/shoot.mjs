import puppeteer from 'puppeteer-core';

const [,, out, url, width = '390', height = '844', waitMs = '4000', actions = ''] = process.argv;
const browser = await puppeteer.launch({
  executablePath: '/usr/bin/google-chrome',
  args: ['--no-sandbox', '--disable-gpu', '--hide-scrollbars'],
});
const page = await browser.newPage();
await page.setViewport({ width: Number(width), height: Number(height), deviceScaleFactor: 2 });
await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
await new Promise(r => setTimeout(r, Number(waitMs)));
if (actions) {
  for (const step of actions.split(';;')) {
    const [kind, ...rest] = step.split(':');
    if (kind === 'click') await page.click(rest.join(':'));
    if (kind === 'wait') await new Promise(r => setTimeout(r, Number(rest[0])));
    if (kind === 'scroll') await page.evaluate(y => window.scrollTo({ top: Number(y) }), rest[0]);
  }
}
await page.screenshot({ path: out });
await browser.close();
console.log('saved', out);
