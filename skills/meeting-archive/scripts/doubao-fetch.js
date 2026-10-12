#!/usr/bin/env node
// 豆包会议文档 → 自动抓取完整逐字稿（拦截内部 API，无需人工导出）
//
// 用法:
//   node doubao-fetch.js <文档URL> [输出目录]
//
// 前提: 已用 doubao-login.js 登录过一次（profile 持久化在 ~/.claude/doubao-profile）
//
// 原理（2026-09-28 逆向确认）:
//   豆包会议文档背后是飞书妙记，正文由两个 API 提供：
//     · my.feishu.cn/minutes/doubao/api/subtitles_v2?size=100000  → paragraphs[]（正文 + 时间戳 + pid）
//     · my.feishu.cn/minutes/doubao/api/speakers                 → paragraph_to_speaker{}（pid → 说话人编号）
//   两者按 pid 关联即得「@说话人 N + 时间戳 + 正文」的完整逐字稿。
//
// ⚠️ 不要试图「滚动抓 innerText」—— 豆包用虚拟滚动，只能拿到当前视口那几百字。
// ⚠️ 不要试图「点下载按钮」—— 浮层是 canvas 渲染，DOM 里点不到。
const path = require('path');
const os = require('os');
const fs = require('fs');
const { chromium } = require('playwright');

const PROFILE = path.join(os.homedir(), '.claude', 'doubao-profile');
const URL = process.argv[2];
const OUTDIR = process.argv[3] || process.cwd();

if (!URL) {
  console.error('用法: node doubao-fetch.js <文档URL> [输出目录]');
  process.exit(1);
}
fs.mkdirSync(OUTDIR, { recursive: true });

const ms2ts = (ms) => {
  const s = Math.floor(Number(ms) / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const p = (n) => String(n).padStart(2, '0');
  return h > 0 ? `${p(h)}:${p(m)}:${p(s % 60)}` : `${p(m)}:${p(s % 60)}`;
};

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    viewport: { width: 1400, height: 1000 },
    locale: 'zh-CN',
  });
  const page = await ctx.newPage();

  let subtitles = null;
  let speakers = null;
  page.on('response', async (res) => {
    try {
      const u = res.url();
      if (!u.includes('/minutes/doubao/api/')) return;
      if (!(res.headers()['content-type'] || '').includes('json')) return;
      const j = await res.json();
      const n = j?.data?.paragraphs?.length || 0;
      if (u.includes('subtitles_v2') && n > (subtitles?.data?.paragraphs?.length || 0)) subtitles = j;
      if (u.includes('/speakers')) speakers = j;
    } catch (e) {
      /* 忽略解析失败 */
    }
  });

  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  for (let i = 0; i < 40 && !subtitles; i++) await page.waitForTimeout(1000);
  await page.waitForTimeout(3000);

  const title = (await page.title()).replace(/\s*-\s*豆包文档$/, '');

  if (!subtitles) {
    console.error('❌ 未捕获到 subtitles API —— 可能未登录（先跑 doubao-login.js）或链接无权限');
    await ctx.close();
    process.exit(2);
  }

  const paras = subtitles.data.paragraphs || [];
  const p2s = speakers?.data?.paragraph_to_speaker || {};
  const lines = paras
    .map((p) => ({
      spk: p2s[p.pid] || '?',
      start: p.start_time,
      text: (p.sentences || [])
        .map((s) => (s.contents || []).map((c) => c.content || '').join(''))
        .join('')
        .replace(/\s+/g, ' ')
        .trim(),
    }))
    .filter((l) => l.text);

  const safe = title.replace(/[\/\\:*?"<>|：]/g, '-').slice(0, 50);
  const dst = path.join(OUTDIR, `逐字稿-${safe}.md`);
  fs.writeFileSync(dst, lines.map((l) => `@说话人 ${l.spk}  ${ms2ts(l.start)}\n${l.text}\n`).join('\n'), 'utf8');

  // 原始 JSON 一并留档（可复算、可重跑）
  fs.writeFileSync(path.join(OUTDIR, `raw-subtitles-${safe}.json`), JSON.stringify(subtitles), 'utf8');
  if (speakers) fs.writeFileSync(path.join(OUTDIR, `raw-speakers-${safe}.json`), JSON.stringify(speakers), 'utf8');

  console.log(`✅ ${title}`);
  console.log(`   段数 ${lines.length} · 说话人 ${[...new Set(lines.map((l) => l.spk))].sort().join(',')}`);
  console.log(`   → ${dst}`);
  await ctx.close();
})().catch((e) => {
  console.error('ERROR|' + e.message);
  process.exit(1);
});
