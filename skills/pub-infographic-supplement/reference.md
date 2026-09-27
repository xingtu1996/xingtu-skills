# pub-infographic-supplement · reference.md

> 主入口见 `SKILL.md`。本文件承载：五类信息图 HTML 模板骨架（含引子图）、完整双同步插入脚本、素材标注用语库、家族配色速查、md2wechat 支路细节。

## 一、家族配色速查

> 色值 SSoT 在工作区根 `DESIGN.md` §一（三原色）/ §四（信息图）。本表是信息图侧投影，冲突以 `DESIGN.md` 为准（§八 变更纪律）。

| 用途 | 色值 | 备注 |
|---|---|---|
| 底色 | `#FFFFFF` | **纯白**，与纯白封面 / 榜单图 / 阅读页同族（DESIGN.md §一） |
| 主文本 | `#1A1A1A` | 纯黑，标题 / 正文 / 结论横条底 |
| 强调 | `#d71a1b` | 行途红，重点数字 / 警示 / 空位框 / 卡片顶部层级线 |
| 次文本 | `#7A8087` | 灰阶，副标题 / 说明 |
| 弱文本 | `#A8ADB3` | 浅灰，来源标注 / 版权行 |
| 分隔线 | `#E6E8EA` | 中性浅灰，卡片边 / 分节线 |
| 卡片底 | `#FFFFFF` | 纯白；**与页面同色，层次不靠底色差**——`border:1px solid #E6E8EA` 勾边，需强调层级时加 `border-top:4px solid #d71a1b`（FDE-03 实测） |

**禁用**：纸白 `#F7F5F2`（偏灰，09-16 弃用）、米灰 `#E5E1DA` 与暖米 `#F0EDE7`（纸白家族衍生色，随之退场，改中性浅灰）、旧炭黑 `#1F2225`（黑一律纯黑 `#1A1A1A`）、橙红 `#F2644F`（PUB-045 OpenDesign 旧色板，DESIGN.md 定强调色为行途红 `#d71a1b`）；渐变、阴影堆叠、彩色图标、圆角超过 8px、emoji。

**视口**：`body { width: 1080px }` → fig_fit `--width 1080` 出图 2160 宽（@2x）。

## 二、五类信息图模板骨架（2.1~2.4 正文配图 · 2.5 引子图专用）

> ### ⚠️ 模板里的 `<img src="_assets/...">` 有渲染前置条件（AGENT-03 引子图首案，2026-09-16）
>
> **机理**：`_assets/` 相对路径按 **HTML 文件所在目录**解析；`fig_fit.py` 用 Chrome headless 打开 `file://` URL，**跨目录不共享 `_assets/`**。HTML 所在目录下没有真实的 `_assets/` 时，渲染**静默出破图占位符**——fig_fit 退出码照样 0，不报错不警告，只有逐张 Read 才能看见。
>
> **首案实录**：引子图 `00-引子图-三家生态位.html` 放在 `04_配图/`、引用 `_assets/app-*.png`；但 logo 此前是 `cp` 进 `03_封面/_assets/` 的（做封面时放的）。渲染前还错误假设过「_assets 在 04_配图/ 下 ✅」——凭记忆不查凭证，白渲一张三 logo 全破的图。
>
> **修复三步（照跑）**：
>
> ```bash
> cd ${WORKSPACE}   # 工作区根
> P="outputs/发布包_YYYY-MM/<包名>"
> # ① 动手前先 ls 实测 assets 实际落点（别凭记忆）
> ls "$P/03_封面/_assets/" "$P/04_配图/_assets/" 2>/dev/null
> # ② 复制到位并再验证
> mkdir -p "$P/04_配图/_assets"
> cp "$P/03_封面/_assets/"*.png "$P/04_配图/_assets/"
> ls "$P/04_配图/_assets/"
> # ③ 重渲 + 逐张 Read 眼见，logo 全加载才进 Step 6（底色按 DESIGN.md §四现行 = 纯白）
> python3 tools/fig_fit.py "$P/04_配图/0X-图名.html" --width 1080 --bg "#FFFFFF"
> ```
>
> **防呆原则**：引子图/配图凡引 logo，`_assets/` 必须复制进 HTML 所在目录（原地 `ls` 确认文件到位才算数，B-009 同源：查凭证不查记忆）。
>
> 以下模板均按「HTML 与 `_assets/` 同目录」这一前提书写 `<img src>`。

### 2.1 三栏对比（Three-Column Compare）

**用途**：三个工具 / 方案 / 生态位并列对比。
**关键结构**：三列 grid，每列 logo + 一句定位 + 3~4 条要点 + 底句总结。

```html
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;background:#FFFFFF;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB",Arial,sans-serif;-webkit-font-smoothing:antialiased;padding:44px 52px 38px}
h1{font-size:34px;font-weight:800;color:#1A1A1A;margin-bottom:8px;letter-spacing:-0.5px}
.sub{font-size:16px;color:#7A8087;margin-bottom:32px;line-height:1.6}
.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin-bottom:28px}
.col{background:#FFFFFF;border:1px solid #E6E8EA;border-top:4px solid #1A1A1A;border-radius:6px;padding:24px 20px}
.col.hi{border-top-color:#d71a1b}
.col-logo{height:44px;display:flex;align-items:center;margin-bottom:14px}
.col-logo img{height:36px;width:auto}
.col-title{font-size:20px;font-weight:700;color:#1A1A1A;margin-bottom:6px}
.col-tag{display:inline-block;font-size:12px;color:#d71a1b;border:1px solid #d71a1b;padding:2px 8px;border-radius:3px;margin-bottom:14px}
.col-list{list-style:none;font-size:14px;color:#333;line-height:1.75}
.col-list li{padding-left:14px;position:relative;margin-bottom:6px}
.col-list li:before{content:"";position:absolute;left:0;top:9px;width:5px;height:5px;background:#1A1A1A;border-radius:50%}
.bottom{background:#1A1A1A;color:#FFFFFF;padding:18px 24px;font-size:17px;font-weight:600;text-align:center;border-radius:4px;margin-bottom:20px}
.bottom .accent{color:#ff6b6b}
.source{font-size:13px;color:#A8ADB3;border-top:1px solid #E6E8EA;padding-top:12px;line-height:1.6}
</style></head><body>

<h1>三个工具里的<span style="color:#d71a1b">真实会话</span></h1>
<div class="sub">同一个我在三个工具里干完全不同的活——这是我最直观的感受。</div>

<div class="grid">
  <div class="col">
    <div class="col-logo"><img src="_assets/app-doubao.png" alt="豆包工作"></div>
    <div class="col-title">豆包工作</div>
    <div class="col-tag">内容活</div>
    <ul class="col-list">
      <li>写稿、改标题</li>
      <li>拉素材、做归纳</li>
      <li>快速试思路</li>
    </ul>
  </div>
  <div class="col">
    <div class="col-logo"><img src="_assets/app-workbuddy.png" alt="WorkBuddy"></div>
    <div class="col-title">WorkBuddy</div>
    <div class="col-tag">流水线</div>
    <ul class="col-list">
      <li>跑定时任务</li>
      <li>看数据、拉报表</li>
      <li>盯发布链路</li>
    </ul>
  </div>
  <div class="col">
    <div class="col-logo"><img src="_assets/app-claudecode.png" alt="Claude Code"></div>
    <div class="col-title">Claude Code</div>
    <div class="col-tag">造工具</div>
    <ul class="col-list">
      <li>写 skill、改工具</li>
      <li>调工程细节</li>
      <li>做长期资产</li>
    </ul>
  </div>
</div>

<div class="bottom">生态决定八成体验，<span class="accent">协作工具选哪家，Agent 就用哪家</span></div>

<div class="source">素材出处：正文第 5 节 · 引文来自作者本地三个工具的会话记录（已脱敏）</div>

</body></html>
```

### 2.2 数字卡（Number Card）

**用途**：提效数据 / 榜单数字 / 关键指标。
**关键结构**：大字号数字（72~96px 红或黑）+ 小字说明 + 「该问 vs 不该问」对比 + 来源标注。

```html
<style>
/* 共用 head 样式省略，见 2.1 */
.numbers{display:grid;grid-template-columns:1fr 1fr 1fr;gap:24px;margin-bottom:32px}
.num-card{background:#fff;border:1px solid #E6E8EA;border-radius:6px;padding:28px 20px;text-align:center}
.num-big{font-size:80px;font-weight:800;color:#d71a1b;line-height:1;letter-spacing:-2px;margin-bottom:10px}
.num-big.black{color:#1A1A1A}
.num-unit{font-size:16px;color:#7A8087;margin-bottom:14px}
.num-desc{font-size:14px;color:#333;line-height:1.6}
.qa{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}
.qa-col{padding:20px;border-radius:4px}
.qa-col.good{background:#fff;border-left:4px solid #d71a1b}
.qa-col.bad{background:#F5F6F7;border-left:4px solid #A8ADB3}
.qa-title{font-size:15px;font-weight:700;margin-bottom:10px}
.qa-col.good .qa-title{color:#d71a1b}
.qa-col.bad .qa-title{color:#7A8087}
.qa-list{list-style:none;font-size:14px;color:#333;line-height:1.85}
</style>

<h1>老板视角：上 AI 之前，先想清楚<span style="color:#d71a1b">这三件事</span></h1>
<div class="sub">不是「哪个产品功能多」，是「我的公司到底要解决什么」。</div>

<div class="numbers">
  <div class="num-card">
    <div class="num-big">9</div>
    <div class="num-unit">个业务部门</div>
    <div class="num-desc">某大厂内部 AI 落地<br>覆盖范围</div>
  </div>
  <div class="num-card">
    <div class="num-big">4.5<span style="font-size:36px">×</span></div>
    <div class="num-unit">提效倍数</div>
    <div class="num-desc">代码 review 场景<br>公开宣传口径</div>
  </div>
  <div class="num-card">
    <div class="num-big black">20<span style="font-size:36px">分钟</span></div>
    <div class="num-unit">上百万行账单</div>
    <div class="num-desc">财务对账场景<br>公开宣传口径</div>
  </div>
</div>

<div class="qa">
  <div class="qa-col good">
    <div class="qa-title">该先问的三件事</div>
    <ul class="qa-list">
      <li>1. 我要解决的具体场景是什么？</li>
      <li>2. 数据安全合规谁给我兜底？</li>
      <li>3. 员工现在的协作工具是哪家？</li>
    </ul>
  </div>
  <div class="qa-col bad">
    <div class="qa-title">不该先问的</div>
    <ul class="qa-list">
      <li>× 哪个产品功能多</li>
      <li>× 哪个模型跑分高</li>
      <li>× 哪家便宜</li>
    </ul>
  </div>
</div>

<div class="source">素材出处：正文第 6 节 · <span style="color:#d71a1b">提效数字为公开宣传口径，非作者实测</span></div>
```

### 2.3 卡片矩阵（Card Matrix）

**用途**：三件事 / 五检查 / 多维度清单。
**关键结构**：2×N 或 3×N grid，每卡标题 + 2~3 行说明 + 序号。

```html
<style>
.matrix{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
.m-card{background:#fff;border:1px solid #E6E8EA;border-radius:6px;padding:20px 22px;position:relative}
.m-num{position:absolute;top:16px;right:20px;font-size:36px;font-weight:800;color:#E6E8EA;line-height:1}
.m-title{font-size:17px;font-weight:700;color:#1A1A1A;margin-bottom:8px;padding-right:40px}
.m-desc{font-size:14px;color:#7A8087;line-height:1.7}
.m-card.hi{border-left:4px solid #d71a1b}
.m-card.hi .m-num{color:#d71a1b;opacity:0.3}
</style>

<h1>选 Work Agent 的<span style="color:#d71a1b">五条检查清单</span></h1>
<div class="sub">不是选功能最多的，是选最贴合你已有工作流的。</div>

<div class="matrix">
  <div class="m-card hi"><div class="m-num">01</div>
    <div class="m-title">生态兼容</div>
    <div class="m-desc">公司用什么协作工具，就选同生态的 Agent</div>
  </div>
  <div class="m-card"><div class="m-num">02</div>
    <div class="m-title">数据边界</div>
    <div class="m-desc">敏感数据是否留本地，云端传输如何加密</div>
  </div>
  <div class="m-card"><div class="m-num">03</div>
    <div class="m-title">扩展能力</div>
    <div class="m-desc">能不能自建 skill / 接入内部系统</div>
  </div>
  <div class="m-card"><div class="m-num">04</div>
    <div class="m-title">协作模式</div>
    <div class="m-desc">单人用还是团队用，权限怎么分</div>
  </div>
  <div class="m-card" style="grid-column:span 2"><div class="m-num">05</div>
    <div class="m-title">长期成本</div>
    <div class="m-desc">订阅费 + 学习成本 + 迁移成本，算三年账</div>
  </div>
</div>

<div class="source">素材出处：正文第 8 节</div>
```

### 2.4 概念示意（Concept Diagram）

**用途**：两层框架 / 趋同 vs 分化 / 生态位。
**关键结构**：分层横条 + 空位红虚线框 + 底句论点。

```html
<style>
.layer{margin-bottom:16px;position:relative}
.layer-label{font-size:13px;color:#A8ADB3;margin-bottom:6px;letter-spacing:1px}
.layer-bar{background:#1A1A1A;color:#FFFFFF;padding:20px 24px;border-radius:4px;font-size:16px;font-weight:600;display:flex;justify-content:space-between;align-items:center}
.layer-bar.void{background:transparent;border:2px dashed #d71a1b;color:#d71a1b}
.layer-bar .tags{display:flex;gap:10px}
.layer-bar .tag{background:rgba(255,255,255,0.15);padding:4px 10px;border-radius:3px;font-size:13px;font-weight:500}
.arrow{text-align:center;font-size:20px;color:#A8ADB3;margin:6px 0}
.thesis{background:#d71a1b;color:#fff;padding:16px 24px;font-size:16px;font-weight:600;text-align:center;border-radius:4px;margin-top:20px;margin-bottom:16px}
</style>

<h1>三国杀的<span style="color:#d71a1b">真正棋盘</span></h1>
<div class="sub">入口层已被大厂占满，工程化这一层还是空位。</div>

<div class="layer">
  <div class="layer-label">入口层 · 已被大厂占据</div>
  <div class="layer-bar">
    <span>办公 Agent 入口</span>
    <div class="tags">
      <span class="tag">WorkBuddy（微信）</span>
      <span class="tag">豆包工作（飞书）</span>
      <span class="tag">千问办公（钉钉）</span>
    </div>
  </div>
</div>

<div class="arrow">↓</div>

<div class="layer">
  <div class="layer-label">核心层 · 工程化空位</div>
  <div class="layer-bar void">
    <span>Agent 工程化 / FDE 交付 / 长期资产</span>
    <span style="font-size:14px">现在没人占</span>
  </div>
</div>

<div class="thesis">选哪家看公司用什么协作工具；选完之后怎么办，才是没人占的空位。</div>

<div class="source">素材出处：正文第 1 节 + 第 10 节 · logo 来源：各产品官方</div>
```

### 2.5 引子图（首屏论点图 · 结论先行）

**用途**：全文第一张图，插在「一句话摘要之后、先说结论之前」（`DESIGN.md` §五 首屏公式）。
**关键结构**：**结论先行** —— 标题 → **通栏一句话结论横条** → 主体（三栏 / 分层 / 卡片）→ `.source`。

> **为什么只有引子图结论前置**（boss 09-16 指令）：引子图出现在读者决定「读不读下去」的首屏 3 秒内，论点是它唯一的功能，所以结论必须在**视觉上先到手**；正文配图是读者读完所在段落才看到，论点已在上下文里给过，结论放 `.bottom` 做收束即可。**这条不对称是刻意的**，别"统一优化"把正文图的底句也搬到顶上。
>
> **重排凭证**：已发 AGENT-03 `00-引子图-三家生态位.html` 原结构是「标题→三栏→分层→底部 `.foot` 结论」，结论压在最下方，首屏只看到三个 logo——本模板即该实物的结论先行重排版。**色值不照抄实物**：实物用的是 PUB-045 旧橙红 `#F2644F`，`DESIGN.md` §一 已定强调色为行途红 `#d71a1b`，新图一律按现行值。

```html
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;background:#FFFFFF;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB",Arial,sans-serif;-webkit-font-smoothing:antialiased;padding:44px 52px 38px}
h1{font-size:34px;font-weight:800;color:#1A1A1A;margin-bottom:14px;letter-spacing:-0.5px}
/* 结论横条：通栏 = 占满 content 宽（1080-52*2=976px），不留左右间隙 */
.lede{background:#1A1A1A;color:#FFFFFF;padding:20px 26px;font-size:21px;font-weight:700;
      line-height:1.45;border-radius:4px;margin-bottom:30px}
.lede .k{color:#ff6b6b}                 /* 横条内关键词：亮红，纯 #d71a1b 在黑底上偏暗 */
.eco{display:flex;gap:20px;margin-bottom:26px}
.e{flex:1;background:#FFFFFF;border:1px solid #E6E8EA;border-top:4px solid #1A1A1A;
   border-radius:6px;padding:20px;display:flex;align-items:center;gap:14px}
.e.hi{border-top-color:#d71a1b}
.e img{width:52px;height:52px;border-radius:12px}
.e .n{font-size:20px;font-weight:800;color:#1A1A1A}
.e .g{font-size:14px;color:#7A8087;margin-top:3px}
.e .g b{color:#d71a1b}
.source{font-size:13px;color:#A8ADB3;border-top:1px solid #E6E8EA;padding-top:12px;line-height:1.6}
</style></head><body>

<!-- ① 标题：主题名词短句，不塞论点（论点交给横条） -->
<h1>选型的真正棋盘</h1>

<!-- ② 结论先行：通栏一句话横条，紧跟标题 -->
<div class="lede">选哪家，看公司用什么协作工具；<span class="k">选完之后怎么办</span>，才是没人占的空位。</div>

<!-- ③ 主体：三栏 / 分层 / 卡片矩阵，承载论据 -->
<div class="eco">
  <div class="e"><img src="_assets/app-workbuddy.png"><div><div class="n">WorkBuddy</div><div class="g">腾讯 · 底牌 <b>微信</b></div></div></div>
  <div class="e"><img src="_assets/app-doubao.png"><div><div class="n">豆包工作</div><div class="g">字节 · 底牌 <b>飞书</b></div></div></div>
  <div class="e"><img src="_assets/app-qianwen.png"><div><div class="n">千问办公</div><div class="g">阿里 · 底牌 <b>钉钉</b></div></div></div>
</div>

<div class="source">全文一张图 · 行途 · 看懂 AI Agent · logo 来源：各产品官方</div>

</body></html>
```

**引子图三条自检**（Step 5 逐张 Read 时额外核）：

- [ ] **横条在 DOM 顺序上紧跟 `h1`、位于主体之前**——是结构前置，不是"看着在上面"；结论仍写在末尾 = 未改
- [ ] **一图一论点不重复**：有 `.lede` 就**不再放**底部 `.bottom` / `.foot` 结论条，同一句话上下出现两遍是缺陷
- [ ] **横条通栏**：宽度等于 content 宽（976px），不是半宽色块；黑条 + 白字 + 亮红关键词，无渐变阴影

## 三、完整双同步插入脚本（可直接跑）

```python
#!/usr/bin/env python3
"""
双同步插占位：MD + 排版 HTML 各插一份，before/after 锚点。
断言 count==1 通过后才写盘 —— 部分失败 = 半坏状态。
"""
import re
from pathlib import Path

P = Path("outputs/发布包_YYYY-MM/<包名>")
MD_FILE = P / "01_正文/正文_vN.md"
HTML_FILE = P / "02_排版HTML/公众号_发布版.html"
P_HTML = '<p style="margin:0 0 22px 0;text-align:justify;">'

# (图名, MD 锚点, HTML 锚点（None = 与 MD 相同）, 模式)
INS = [
    ("05-三工具会话对比.png",
     "看出区别了吗？办公 Agent 里我是在",
     None, "before"),
    ("06-老板三问数字卡.png",
     "**第二件事：数据安全合规",       # MD 里粗体标记保留
     "第二件事：数据安全合规",          # HTML 里粗体已渲成 <strong>，锚点去 **
     "before"),
    ("07-两种物种两笔预算.png",
     "后者是给公司建能力。两件事都要做，但它们是两笔不同的预算。",
     None, "after"),
    ("08-功能趋同壁垒分化.png",
     "差异化和壁垒不在功能清单，在生态、商业模式、toB 的进展。",
     None, "after"),
]

def insert_md(md: str, fig: str, anchor: str, mode: str) -> str:
    n = md.count(anchor)
    assert n == 1, f"MD 锚点 count={n}（应=1）: {anchor[:40]!r}"
    ph = f"\n\n【配图：{fig}】\n\n"
    return md.replace(anchor, ph + anchor) if mode == "before" \
              else md.replace(anchor, anchor + ph)

def insert_html(html: str, fig: str, anchor: str, mode: str) -> str:
    n = html.count(anchor)
    assert n == 1, f"HTML 锚点 count={n}（应=1）: {anchor[:40]!r}"
    ph = f'{P_HTML}【配图：{fig}】</p>'
    if mode == "before":
        # 找锚点所在 <p> 的起点，在其前插入新 <p>
        i = html.find(anchor)
        p_start = html.rfind("<p", 0, i)
        assert p_start != -1, f"before 模式找不到 <p> 起点：{anchor[:40]!r}"
        return html[:p_start] + ph + html[p_start:]
    else:  # after
        # 找锚点所在 </p> 的终点，在其后插入新 <p>
        i = html.find(anchor)
        p_end = html.find("</p>", i)
        assert p_end != -1, f"after 模式找不到 </p>: {anchor[:40]!r}"
        p_end += len("</p>")
        return html[:p_end] + ph + html[p_end:]

# --- 先全部断言，再统一写盘（防部分失败） ---
md = MD_FILE.read_text(encoding="utf-8")
html = HTML_FILE.read_text(encoding="utf-8")

md_new, html_new = md, html
for fig, md_anc, html_anc, mode in INS:
    html_anc = html_anc or md_anc
    # 断言阶段（不修改）
    assert md_new.count(md_anc) == 1, f"MD 锚点异常: {md_anc[:40]!r}"
    assert html_new.count(html_anc) == 1, f"HTML 锚点异常: {html_anc[:40]!r}"
    # 插入
    md_new = insert_md(md_new, fig, md_anc, mode)
    html_new = insert_html(html_new, fig, html_anc, mode)

MD_FILE.write_text(md_new, encoding="utf-8")
HTML_FILE.write_text(html_new, encoding="utf-8")

# 验证
md_cnt = md_new.count("【配图：")
html_cnt = html_new.count("【配图：")
png_cnt = len(list((P / "04_配图").glob("*.png")))
print(f"MD 占位: {md_cnt} / HTML 占位: {html_cnt} / PNG 数: {png_cnt}")
assert md_cnt == html_cnt == png_cnt, "三数不等，双同步失败"
print("✅ 双同步通过")
```

## 四、md2wechat 重渲支路（完整脚本）

**触发时机**：改排版主题（如从 pure 换到 review）、批量重渲排版 HTML。

**坑**：md2wechat 会把 `【配图：x】` 渲成灰框占位卡（含「公众号后台此处插入」提示），wx_draft_api 靠文本占位替换 → 嵌图 0 + 正文里一堆灰框。

**处置**（`@@PH@@` 标记法）：

```bash
#!/usr/bin/env bash
set -euo pipefail

P="outputs/发布包_YYYY-MM/<包名>"
MD="$P/01_正文/正文_vN.md"
HTML="$P/02_排版HTML/公众号_发布版.html"
THEME="review"  # or pure / reviewBlack

# 1) 渲染前：MD 里 【配图：x】 → @@PH:x@@
python3 <<PY
import re
s = open("$MD", encoding="utf-8").read()
s2 = re.sub(r"【配图：(.+?)】", r"@@PH:\1@@", s)
open("/tmp/render_input.md", "w", encoding="utf-8").write(s2)
print(f"渲染输入占位标记数: {s2.count('@@PH:')}")
PY

# 2) md2wechat 渲染（@@PH@@ 是普通文本，不会被识别为占位）
cd md2wechat
node bin/md2wechat.js /tmp/render_input.md --theme "$THEME" -o "../$HTML"
cd ..

# 3) 渲染后：HTML 里 @@PH:x@@ → <p>【配图：x】</p>
python3 <<PY
import re
h = open("$HTML", encoding="utf-8").read()
h2 = re.sub(
    r"@@PH:(.+?)@@",
    r'<p style="margin:0 0 22px 0;text-align:justify;">【配图：\1】</p>',
    h,
)
open("$HTML", "w", encoding="utf-8").write(h2)
print(f"占位还原: {h2.count('【配图：')} / 残留标记: {h2.count('@@PH:')}")
assert h2.count("@@PH:") == 0, "残留 @@PH@@ 标记"
PY

# 4) 验证主题色 + 占位数
echo "主题色（review 应>0，pure 应=0）:"
grep -oc "d71a1b" "$HTML" || true
echo "占位数（应等于 MD 占位数）:"
grep -oc "【配图：" "$HTML"
grep -oc "【配图：" "$MD"
```

**md2wechat CLI 参数速查**：
- `--theme <name>`：`review`（评测风，红 #d71a1b）/ `reviewBlack`（评测黑）/ `pure`（极简黑 #1a1a1a）
- `-o <path>`：输出文件；不给则 `--stdout`
- `--images <mode>`：`placeholder`（默认，占位卡）/ `drop`（删）/ `keep`（保留 MD 图片语法）——**只作用于 `![alt](url)`，不影响 `【配图：x】`**

## 五、素材标注用语库（诚实红线）

**必标场景 → 用语**：

| 场景 | 标注用语 | 位置 |
|---|---|---|
| 官方宣传数字（提效倍数、时长、行数） | `公开宣传口径，非作者实测` | `.source` 区，红色 |
| 本地会话引文 | `引文来自作者本地会话记录（已脱敏）` | `.source` 区，灰色 |
| 第三方榜单数据 | `数据来源：<机构名> <期数> 榜单` | `.source` 区，灰色 |
| 作者主观判断 | `作者观察 / 作者判断` | `.source` 区，灰色 |
| 未点名从业者访谈 | `来自大厂离职与在职资深从业者的公开访谈` | `.source` 区，灰色 |
| 官方图标 / logo | `logo 来源：各产品官方` | `.source` 区，灰色 |

**禁用**：
- 冒充引用（如把作者观察写成「某博主说」）
- 无出处数字（违 B-009）
- 「现任产品负责人口径」（除非确证）—— 用「离职与在职资深从业者」更稳
- 具体人名 / 手机号 / 内部邮箱（违 SAF-004/010）

## 六、图型选择决策表

| 正文素材形态 | 推荐图型 | 例子 |
|---|---|---|
| 三个及以上并列对象 + 各自特征 | 三栏对比 | 三个工具 / 三家生态 / 三个方案 |
| 关键数字 + 场景说明 | 数字卡 | 提效数据 / 榜单数字 / 用户量 |
| N 条清单 / 检查项 / 步骤 | 卡片矩阵 | 五检查 / 三件事 / 七步骤 |
| 分层结构 / 空位 / 演化 | 概念示意 | 两层框架 / 生态位 / 趋同分化 |
| **全文核心论点（首屏那张）** | **引子图（§2.5，结论先行）** | 全文一张图 / 选型棋盘 / 一句判断 + 三栏论据 |
| 时间线 / 版本演化 | 时间轴（本 reference 未含模板，按需扩） | 产品迭代 / 事件演化 |
| 对比矩阵（多×多） | 表格图（本 reference 未含模板，按需扩） | 功能对照 / 参数对比 |

**决策原则**：一张图只承载**一个论点**。多论点 = 拆多张，不塞一张。

**引子图 ≠ 正文配图**：引子图挂在首屏（摘要之后），作用是 3 秒给判断，结构强制**结论先行**（§2.5）；正文配图作用是给已读到的段落收束，结论可放底句。算 PUB-048 密度时引子图通常**不计入**「每大节 ≥1 张」（它不属于任何一节），但计入总图数。

## 七、渲染前 checklist（Step 5 前必过）

- [ ] HTML 里所有 `<img src>` 路径按 **HTML 所在目录**解析——`ls <HTML所在目录>/_assets/` 实测文件确实在（不凭记忆，见 §二 渲染前置块）；assets 若在别处（如 `03_封面/`），先 `mkdir -p + cp` 进 HTML 目录并重验落点，再渲染
- [ ] `body { width: 1080px }` 明确写出
- [ ] 底色**纯白 `#FFFFFF`**（纸白 `#F7F5F2` / 米灰 `#E5E1DA` / 暖米 `#F0EDE7` 均已弃用，见 §一），主色黑红灰，无违和色
- [ ] 纯白底上卡片有层次：`#E6E8EA` 细边或 `border-top` 红线勾出，不是「白压白」糊成一片
- [ ] **引子图（§2.5）**：结论横条在 DOM 里紧跟 `h1`、位于主体之前，且通栏；底部无重复结论条
- [ ] 每张图有 `.source` 区，素材出处 + 宣传口径标注（如需）
- [ ] 数字与正文对回一遍（Step 3 素材清单）
- [ ] 底句 / 论点句 3 秒能读懂
- [ ] 无 emoji / 无渐变 / 无花哨阴影
- [ ] 文件名编号续 `04_配图/` 已有 PNG（如已有 01~04，新图从 05 起）

## 八、渲染后 Read 核验清单（Step 5 后必过）

- [ ] 图片资源全部加载（无破图占位符 / 无 alt 文字裸露）
- [ ] 字号在 2160 宽下清晰可读（正文 ≥ 24px 出图 = 12px 视口）
- [ ] 数字与正文一致（回素材清单逐条对）
- [ ] 宣传口径 / 引文出处标注可见
- [ ] 底句 / 论点句完整未截断
- [ ] 视觉与家族一致（与 04_配图 已有图放一起看不违和）
- [ ] 出图宽度 2160px（`sips -g pixelWidth <PNG>` 或 `file <PNG>`）

**Read 通过前不进 Step 6**——破图 / 错字 / 排版错位一旦进草稿箱，就要走「回查发现 → 修 → 重建 → 回收」的完整闭环，成本高一个数量级。

## 九、相关资产路径速查

| 资产 | 路径 |
|---|---|
| 主技能 | `<工作区>/.agents/skills/pub-infographic-supplement/SKILL.md` |
| 本 reference | `<工作区>/.agents/skills/pub-infographic-supplement/reference.md` |
| 下游技能 | `~/.qwenworkcn/skills/mp-prepublish-draft-verify/SKILL.md` |
| PUB-048 原文 | `<工作区>/rules/RULES.d/01_PUB*.md` |
| fig_fit 工具 | `<工作区>/tools/fig_fit.py` |
| wx_draft_api 工具 | `<工作区>/tools/wx_draft_api.py` |
| md2wechat CLI | `<工作区>/md2wechat/bin/md2wechat.js` |
| 已发正例（8 图家族） | `<工作区>/outputs/发布包_2026-09/AGENT-03_Agent三国杀_WorkBuddy豆包千问/04_配图/` |
| 已发正例（12 图 PEC） | `<工作区>/outputs/发布包_2026-08/PEC*/04_配图/` |

---

**版本**：1.1.0（与 SKILL.md v1.2.2 同批；2026-09-16 建，源出 AGENT-03 补图管线复盘）

- **1.1.0**（2026-09-16 10:5x，qwenwork）：① **配色口径跟 `DESIGN.md` 收口**——底色纸白 `#F7F5F2` → 纯白 `#FFFFFF`，灰阶 `#666`/`#999` → `#7A8087`/`#A8ADB3`，分隔线米灰 `#E5E1DA` → 中性浅灰 `#E6E8EA`，暖米 `#F0EDE7` → `#F5F6F7`，黑条前景字同步纯白；§一 增「禁用弃用色清单」与**纯白底卡片靠细边 + `border-top` 红线做层次**（防白压白，取自 FDE-03 实测）。② **新增 §2.5 引子图模板（结论先行）**——标题 → 通栏一句话结论横条 → 主体三栏 → source，含三条自检与「为何只有引子图结论前置」的不对称说明；§六 决策表补引子图行并注明其不计入「每大节 ≥1 张」；§七 checklist 补纯白、卡片层次、引子图结构三项。基准 = AGENT-03 已发 `00-引子图-三家生态位.html` 的重排版，色值按现行 `#d71a1b` 而非实物旧橙红 `#F2644F`。
- **1.0.1**（2026-09-16）：§二 增 `_assets/` 相对路径渲染前置专坑块（AGENT-03 引子图首案：引子图在 `04_配图/`、assets 在 `03_封面/_assets/`，首渲三 logo 破图，cp + 重渲 + Read 修复）、§七 checklist 首条改 ls 实测口径、§九 主技能/reference 路径修正为工作区 `.agents/skills/`（09-16 已迁出全局池）。
