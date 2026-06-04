// 长图截图脚本：生成 Q3 品类趋势洞察长图（不含排行榜）
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1480, height: 900 },
    deviceScaleFactor: 2,  // 2x 高清
  });
  const page = await context.newPage();

  await page.goto('http://localhost:7878/longimage.html', { waitUntil: 'networkidle' });

  // 等待 body 标记 ready，确保 OVERALL 和 INSIGHTS 都渲染完
  await page.waitForFunction(() => document.body.dataset.ready === '1', { timeout: 15000 });
  await page.waitForTimeout(800); // 字体&样式收尾

  await page.screenshot({
    path: '../5-交付产物/Q3品类趋势_长图.png',
    fullPage: true,
    type: 'png',
  });

  console.log('✅ 长图已生成：Q3品类趋势洞察_长图.png');
  await browser.close();
})();
