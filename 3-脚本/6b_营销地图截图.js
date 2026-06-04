// 营销地图单图截图脚本：只截"Q3 时令营销地图"那张卡片，对外宣发用
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1480, height: 900 },
    deviceScaleFactor: 2,  // 2x 高清
  });
  const page = await context.newPage();

  await page.goto('http://localhost:7878/longimage.html?map=1', { waitUntil: 'networkidle' });
  await page.waitForFunction(() => document.body.dataset.ready === '1', { timeout: 15000 });
  await page.waitForTimeout(800);

  // 直接截 overall-card 这一个元素，不留空白
  const card = await page.$('#overall-card');
  if (!card) throw new Error('找不到 #overall-card');

  await card.screenshot({
    path: '../5-交付产物/Q3时令营销地图.png',
    type: 'png',
  });

  console.log('✅ 营销地图已生成：Q3时令营销地图.png');
  await browser.close();
})();
