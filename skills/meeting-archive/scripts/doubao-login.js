#!/usr/bin/env node
// 豆包文档 · 一次性登录（有头 Chrome，扫码后登录态持久化）
//
// 用法:
//   node doubao-login.js [文档URL]
//
// 说明:
//   · 会弹出一个 Chrome 窗口，请用豆包/飞书账号登录（支持"飞书账号一键登录"或抖音扫码）
//   · 登录态写入 ~/.claude/doubao-profile，之后 doubao-fetch.js 直接复用（无需再登录）
//   · 检测到登录成功（页面出现正文）即自动关闭
//
// ⚠️ 用 chrome channel（系统 Chrome）而非 Playwright 自带 chromium —— 后者版本常与本机缓存不匹配。
const path = require('path');
const os = require('os');
const { chromium } = require('playwright');

const PROFILE = path.join(os.homedir(), '.claude', 'doubao-profile');
const URL = process.argv[2] || 'https://www.doubao.com/';

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    channel: 'chrome',
    viewport: { width: 1400, height: 950 },
    locale: 'zh-CN',
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = await ctx.newPage();
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  console.log('🔓 浏览器已打开，请登录豆包 / 飞书账号…（最多等 8 分钟）');

  const deadline = Date.now() + 8 * 60 * 1000;
  while (Date.now() < deadline) {
    let t = '';
    try {
      t = await page.evaluate(() => document.body.innerText || '');
    } catch (e) {
      t = '';
    }
    const onLogin = t.includes('没有权限访问') || t.includes('登录以解锁') || t.includes('扫码登录');
    if (t && !onLogin && t.length > 300) {
      console.log('✅ 登录成功，登录态已保存到 ' + PROFILE);
      console.log('   预览: ' + t.slice(0, 200).replace(/\n+/g, ' ⏎ '));
      break;
    }
    await page.waitForTimeout(4000);
  }
  await ctx.close();
  console.log('提示: 现在可用 doubao-fetch.js 直接抓取文档');
})().catch((e) => {
  console.error('ERROR|' + e.message);
  process.exit(1);
});
