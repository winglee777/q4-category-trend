// 诊断脚本：分别用 1440 / 1280 两档视口，截顶部第一屏，定位"展示不完整"
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const widths = [
    { w: 1440, h: 900,  name: 'diag_1440.png' },
    { w: 1280, h: 800,  name: 'diag_1280.png' },
    { w: 1920, h: 1080, name: 'diag_1920.png' },
  ];

  for (const v of widths) {
    const context = await browser.newContext({
      viewport: { width: v.w, height: v.h },
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    await page.goto('http://localhost:7878/longimage.html', { waitUntil: 'networkidle' });
    await page.waitForFunction(() => document.body.dataset.ready === '1', { timeout: 15000 });
    await page.waitForTimeout(500);

    // 视口截图（不是 fullPage），看真实首屏
    await page.screenshot({ path: v.name, fullPage: false });

    // 同时打印关键宽度信息
    const info = await page.evaluate(() => {
      const c = document.querySelector('.container');
      const t = document.querySelector('.map-table');
      const wrap = document.querySelector('.overall-card > div[style*="overflow"]');
      return {
        bodyW: document.body.clientWidth,
        scrollW: document.body.scrollWidth,
        containerW: c ? c.getBoundingClientRect().width : null,
        tableW: t ? t.scrollWidth : null,
        tableClientW: t ? t.clientWidth : null,
        wrapW: wrap ? wrap.clientWidth : null,
        wrapScrollW: wrap ? wrap.scrollWidth : null,
        hasHorizontalScroll: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      };
    });
    console.log(`viewport ${v.w}px →`, JSON.stringify(info));

    await context.close();
  }

  await browser.close();
  console.log('✅ 截图完成：diag_1280/1440/1920.png');
})();
