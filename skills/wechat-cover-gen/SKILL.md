---
name: wechat-cover-gen
description: >
  公众号封面生成管线（v1.3.0 配置化双轨 + 全幅布局）：路线A真人剪影场景化（工程师背影+橙红轮廓光）/ 路线B简笔画形象化（一桌杠精/守门人/三岔路口/地基脚手架，boss 10-12 ADV-02 认可方向）
  → **封面配置单驱动**：选构图类型（场景卡/简笔画卡）+ 主词 + 底色 → AI 生图只出**无文字**构图 → curl 下载 scene.png → HTML 覆字压主标 → Chrome headless 渲 900×383@2x → Read 看图+OCR 回查
  → 落 03_封面/。触发：出封面、换封面、封面重渲、封面没真人感、封面太纯图形、黑白交替、引子图同步、封面配置。
  视觉 SSoT = DESIGN.md §二/§二·补；本 skill 只承载"怎么一键出图"的流程，不改规范。
version: 1.3.1
---

# 公众号封面生成（配置化双轨：真人剪影 / 简笔画形象）

> 2026-09-29 boss 拍板：封面要有**真人/可挖掘的点**，不要纯几何图形。纯 HTML 几何封面已证伪（FDE 爆分享封面是真人剪影）。
> 2026-10-12 boss ADV-02 拍板（v1.1.0）：新增路线 B **简笔画形象化**——AI 生图出简笔画人物/场景（一桌杠精、分裂小人），方式/形式/形象描述都对味，后续文章往这个方向靠拢。
> 2026-10-12（v1.2.0）boss 指令：配置单驱动。
> 2026-10-13（v1.3.0）boss 反馈：「插画图太小了」——修复布局：场景图必须**全幅铺满**（不是塞进侧栏小盒子），插画占右半屏才够醒目。同时补 Chrome headless 坑位。
> 🆕 2026-10-14（v1.3.1）boss 纠错反思：「打磨封面却拿包内旧文字版 HTML 重渲，放着已有 handraw 场景图版正确成品不用」——补 **Step 0 开工闸门**（先看现状再动手）+ **渲染源优先级** + **`_旧版_*` 作废目录禁作源** + **陈旧记忆防污染**（终稿认定以 CHANGELOG/打磨日志/状态位为准，不信上下文旧印象）。

## 🔴 铁律（v1.3.1 起强制）

0. **开工先看现状，已有正确成品禁止重渲**（v1.3.1 新增，最高优先级）：动封面第一步 = `ls 03_封面/` + **Read `封面.png` 亲眼看形态**。若包内已存在正确形态（无文字插画 + 覆字成品，如 `封面_场景图版_v*.png`）→ **直接转正/复用，禁止**为「打磨」而重渲另一版。默认动作是「确认 + 复用」，不是「重渲」。
1. **AI 生图只出无文字构图**：prompt 骨架里必须带「无任何文字 / no text / no letters」。AI 中文生图目前仍会糊/错/繁简混（ADV-02「杠精→红娘」实锤），不要指望 AI 把字写对。
2. **正式封面文字一律 HTML 覆字渲染**：主标/副标/tag/footer 全部在 HTML 里用 CSS 写，再渲 PNG。改字改色重渲成本极低（改 HTML 一行即可）。
3. **封面不加「合集」标签**（boss 拍板）：合集后台已有，封面再放=画蛇添足。每次渲封面必 Read 回查 PNG 亲眼确认无合集 tag。
4. **OCR 回查不可跳过**：渲完 PNG 必须 Read 亲眼看——文字无错字、无孤字换行、简笔画风格统一、三原色锁死。
5. **封面=引子图同款**（坑位 67/72）：定稿后 `cp 封面.png → 04_配图/00-封面引子图.png`，改封面必须同步引子图。
6. **插画必须够大**（v1.3.0 新增）：场景图全幅铺满 canvas，插画占右半屏约 50% 宽度。**禁止**把 scene 图塞进一个小侧栏 div（boss 10-13 实锤：塞 420px 盒子里插画缩成小图标，「比例不太好」）。
7. **渲染源优先级**（v1.3.1 新增）：同目录多 HTML 源时选源 = ①优先 `封面_场景图版_v*.html`（handraw 管线成品源）②`封面_文字覆字版_*.html` 仅当场景图版不存在且已 Read 图确认形态才可作源 ③**`_旧版_*/` 归档目录一律禁作渲染源**（作废即弃，改字改色请复制场景图版源改，勿捞旧版）。
8. **终稿认定查状态位，不信上下文旧记忆**（v1.3.1 新增）：「当前哪张是终稿」以包内 CHANGELOG / 打磨日志 / 00_状态.md / spec 状态位为准；上下文里残存的旧版印象（如"文字版曾是终稿"）一律作废，动手前先刷新。

## 〇、配置单驱动

每篇封面开工前先填一张**封面配置单**（落 `03_封面/封面配置单.md`）：

```yaml
article: 文章代号（如 WED）
title: 发布标题（公众号原生标题栏显示，封面不复述）
main_word: 封面主词（可橙红强调；从标题提炼，非标题复述）
sub_line: 一行副标（灰色，≤15字）
route: A 真人剪影 | B 简笔画形象
composition: 构图卡编号（见下方构图库）
bg: black | white（黑白律动，按排期表交替）
note: 特殊要求
```

## 构图库

### 路线 A · 真人剪影场景卡

| 卡号 | 场景 | prompt 骨架片段 |
|---|---|---|
| A1 | 机房背影 | 工程师**背影剪影**站在深色机房，面向屏幕墙，**橙红色逆光从身后打出轮廓光**，不露正脸 |
| A2 | 黄昏窗边 | 工程师**背影剪影**站在黄昏窗边，面向窗外夕阳，橙红轮廓光，右侧大量暗部负空间 |
| A3 | 控制台前 | 工程师**背影剪影**坐在控制台前，屏幕光映轮廓，橙红点缀，整体低照度电影感 |

### 路线 B · 简笔画形象卡

| 卡号 | 构图 | prompt 骨架片段 |
|---|---|---|
| B1 | 一桌杠精（ADV-02 拍板） | 极简黑白简笔画，扁平矢量风，**一桌 4 个卡通小人在吵架/争论**，线条干净，白底，橙色 #F2644F 点缀 1-2 处，无任何文字 |
| B2 | 分裂小人 | 极简黑白简笔画，**一个分裂成两半的工程师小人**（左右各执一词），橙红点缀 1 处 |
| B3 | 排队闯关 | 极简黑白简笔画，**三道关卡前排队的小人**（闸门/箭头/检查点），橙红箭头点缀 |
| B4 | 记忆管理意象 | 极简黑白简笔画，**大脑/记忆盒子 + 时钟 + 收纳格**，橙红点缀 |
| B5 | 守门人（RP-03） | 一道闸门前一人举手拦一人，闸门上橙红圆点，白底黑线 |
| B6 | 单赛道（RP-04） | 三条平行赛道只点亮一条橙红色，小人沿亮道跑，黑底白线 |
| B7 | 三岔路口（RP-06） | Y 形岔路口小人站在分叉处，一条方向有橙红箭头，白底 |
| B8 | 地基脚手架（RP-07） | 小人站在砖块地基上向上砌墙，一处橙红点缀，黑底白线 |
| B9 | AI 乱跑（WED） | 困惑工程师挠头问号 + 机器人朝多方向乱跑（橙红箭头），白底黑线 |

## 七步管线（v1.3.1，含 Step 0 开工闸门）

### Step 0 · 开工闸门（v1.3.1 强制，不可跳过）

任何封面任务（新出/换/重渲/打磨）先过三步，**通过后才知道"到底要不要渲"**：

```bash
ls 03_封面/                                    # ①看目录有哪些源与成品
```

2. **Read `03_封面/封面.png`（或最新成品图）亲眼看形态**——是「无文字插画+覆字」还是「文字大量信息」？风格对味吗？
3. **查包内 CHANGELOG / 打磨日志 / 00_状态.md 确认"当前终稿是哪张"**（不查上下文旧记忆）。

**闸门判定**：
- 已有正确形态成品（场景图版）→ **转正/复用**，不重渲；仅同步引子图/改名落位。
- 无成品或形态错误（如纯文字版、插画太小）→ 才进入 Step 1 重渲；**重渲源按铁律 7 优先级选**（场景图版源优先，禁捞 `_旧版_*`）。
- 只改字/改色 → 复制场景图版源 HTML 修改后重渲，**不新建文字版**。

> 2026-10-14 实锤教训：THU 封面打磨时未过此闸门——凭文件名选了 `封面_文字覆字版_20261014.html` 重渲，而包内 10-13 已产出正确的 `封面_场景图版_v1.png`，最终文字版被归档作废、场景图版转正终稿。闸门存在就是为了杜绝"放着成品不用、重造已作废版"。

### Step 1 · 出场景图（image_gen）

- 比例 **2350×1000**（2.35:1），prompt 骨架：
  > `极简黑白扁平矢量卡通插画，干净粗线条，<构图卡段>，三原色（黑#1a1a1a/白#fff/橙红#F2644F），无任何文字字母数字，宽屏横幅构图，**画面左侧留出大面积空白区域用于放置文字**`
- 关键：prompt 里说「左侧留空白」比「右侧放插画」更可控——AI 生成的图左侧天然留白，HTML 直接压字。

### Step 2 · 下载

```bash
curl -sL -o scene_base.png <图URL>
```

### Step 3 · HTML 覆字（两个模板）

**🔑 布局核心（v1.3.0）**：scene 图做全幅背景（`position:absolute;inset:0`），**不要**塞进小侧栏 div。文字用 `position:absolute` 压在左侧留白区。

**白底模板**（路线 B 常用）：
```html
<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:900px;height:383px;background:#FFF;font-family:-apple-system,'PingFang SC',sans-serif;position:relative;overflow:hidden}
.bg-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(20,20,20,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(20,20,20,.04) 1px,transparent 1px);background-size:28px 28px;z-index:0}
.scene{position:absolute;inset:0;background:url('scene_base.png') center right/contain no-repeat;z-index:1}
.main{position:absolute;left:48px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;width:420px;z-index:2}
.tag{font-size:14px;font-weight:700;color:#F2644F;letter-spacing:2px;margin-bottom:20px}
h1{font-size:38px;font-weight:800;color:#1a1a1a;line-height:1.35}
h1 .em{color:#F2644F}
h1 .row{display:block}
.redline{width:48px;height:5px;background:#F2644F;border-radius:3px;margin:18px 0 16px}
.sub{font-size:17px;color:#555B62;font-weight:600}
.foot{position:absolute;bottom:16px;right:32px;font-size:12px;font-weight:700;color:#F2644F;z-index:2}
</style></head><body>
<div class="bg-grid"></div><div class="scene"></div>
<div class="main">
  <div class="tag">合集名 · 一线实录</div>
  <h1><span class="row">第一行主标，</span><span class="row"><span class="em">橙红词</span> 其余黑字</span></h1>
  <div class="redline"></div>
  <div class="sub">副标一句话</div>
</div>
<div class="foot">行途技术</div>
</body></html>
```

**黑底模板**（路线 A/B 暗色系）：把 body bg 改 `#1a1a1a`、h1 改 `#FFF`、sub 改 `#9a9a9a`、foot 改 `#6f6f6f`，scene 同理全幅铺。

**排版注意**：
- 标题用 `<span class="row">` 强制换行，**禁止孤字掉行**（一行最后一个字单独蹦到下一行）
- 字号 36-38px，每行 ≤10 个汉字
- 封面不复述公众号标题，只放提炼的 hook

### Step 4 · 渲染

> ⚠️ **fig_fit.py 在 Chrome 已运行时会超时**（v1.3.0 坑位）。直接用 Chrome headless 截图：

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TMPDIR=$(mktemp -d)
"$CHROME" --headless=new --no-sandbox --disable-setuid-sandbox --disable-gpu \
  --disable-dev-shm-usage --hide-scrollbars --user-data-dir="$TMPDIR" \
  --screenshot="封面.png" --window-size=900,383 --force-device-scale-factor=2 \
  --default-background-color=FFFFFFFF "file://$HTML路径" 2>/dev/null
```

- `--user-data-dir` **必须加**（用临时目录），否则跟已开的 Chrome 实例冲突，headless 启动超时 60s 卡死
- `--default-background-color=FFFFFFFF` 白底；黑底用 `FF1a1a1a`
- `--force-device-scale-factor=2` 出 2x 高清图

### Step 5 · 验收（不可跳过）

Read 亲眼看图：
- 插画**占右半屏**（不能是小图标）
- 文字无错字、无孤字换行
- 三原色锁死（黑/白/橙红 #F2644F）
- 无合集 tag、无 AI 生图残留乱码文字

### Step 6 · 落盘 + 同步引子图

```bash
cp 03_封面/封面.png 04_配图/00-封面引子图.png
```

## 黑白律动
一篇黑底一篇白底交替。以公众号后台「近期发表」实发封面为准排下一篇，不查包内旧备注。

## 相关 SSoT
- 视觉规范：`DESIGN.md` §一/§二/§二·补
- 封面决策链：`mp-publish-sop` Step 7b
- 风格样例与坑位：本目录 `reference.md`
- 插画体系探索 spec：`specs/20261013-插画体系探索_从简笔画到手绘风/`
