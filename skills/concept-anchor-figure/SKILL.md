---
name: concept-anchor-figure
name_en: Concept Anchor Figure
name_zh: 概念锚点图
description: Turn one article's core idea into a single watermark-free vector infographic (HTML -> PNG via fig_fit), in the workspace brand palette (white bg, black/red/gray + journey blue #056DE8). Use when the user asks for a concept anchor figure, "one picture to understand this article", a sketchnote-style summary figure, an abstract illustration with crisp Chinese text, or a watermark-free illustration instead of AI-generated images. Complements pub-infographic-supplement (density backfill); this skill makes ONE anchor figure that explains the article, not per-section density.
description_en: Turn one article's core idea into a single watermark-free vector infographic (HTML -> PNG via fig_fit), in the workspace brand palette (white bg, black/red/gray + journey blue #056DE8). Use when the user asks for a concept anchor figure, "one picture to understand this article", a sketchnote summary figure, or a watermark-free vector illustration with crisp Chinese text instead of AI-generated images.
description_zh: 把一篇文章的核心观点做成一张无水印矢量概念图（HTML 经 fig_fit 渲成 PNG），行途品牌色（白底、黑红灰 + 行途蓝 #056DE8）。当用户说"给这篇做一张概念锚点图/一张图看懂这篇/总结图/讲概念的插图/不要水印不要AI图/手绘风概念图（矢量版）"时触发。与 pub-infographic-supplement（图文密度补齐）互补：本技能只做"讲清全文的一张图"，不管逐节密度。
argument-hint: Give the article file (or package path) and the metaphor style you want
argument-hint-en: Give the article file (or package path) and the metaphor style you want
argument-hint-zh: 给出文章文件（或发布包路径）与想要的隐喻风格
user-invocable: true
version: 1.0.0
---

# 概念锚点图（concept-anchor-figure）

> 适用守卫：专为「行途」工作区设计（fig_fit/发布包结构/品牌色）。先读根 AGENTS.md 含「行途」才继续；其他空间声明不适用。

## 何时用 / 何时不用

- **用**：一篇文章要一张"一眼看懂"的总结图；概念科普类（方法论/框架/分层/流程隐喻）；用户明确要**无水印、中文清晰**的插图。
- **不用**：逐节补图文密度（走 `pub-infographic-supplement`）；头像/封面氛围图（可走生成模型，但注意其水印与中文糊字风险）；带精确数据的图表（数据图也走 HTML，但属密度补齐场景）。

## 设计定则（来自 boss 2026-09-16 拍板）

1. **零水印**：纯 HTML/CSS 渲染，非生成模型；天然无水印，可随时改字改色重渲。
2. **概念图少文字**：文字交给正文，图只放"标签级"短语（每卡 ≤2 行）；**不放数据表**（那是密度补齐的活）。
3. **品牌色锁死**：白底 #FFFFFF、黑 #141414、红 #d71a1b、行途蓝 #056DE8、灰 #555B62/A8ADB3（对齐 DESIGN.md 黑红灰体系 + P028）。
4. **一张图一个隐喻**：从正文提炼一个可转述的核心结构（四道关卡/传送带/漏斗/三层塔…），不贪多。

## 五步流程

1. **读正文提炼隐喻**：通读正文（发布包 `01_正文/正文_v<最大>.md`），找出"这篇文章用一句话说是什么结构"（反常识点优先）。选不出清晰隐喻 → 停下报告，不硬凑。
2. **选模板或自建**：`templates/template_gate-flow.html`（关卡/漏斗/流程隐喻，四卡横排+贯穿箭头+起终点）可直接改；其他隐喻照其结构自建，保持同一 CSS 骨架（头部一行式标题+右侧灰 tag / 主体 / 底部 motto+署名）。
3. **填内容（标签级）**：每卡只放「名称 + 一句症状 + 一句钥匙」；标题红字点题；底部收三词 motto；右下署名 `行途 · <合集名>`。
4. **渲染**：`cd ${WORKSPACE} && python3 tools/fig_fit.py "<html路径>" --width 1280 --bg "#FFFFFF"`（**必须从工作区根跑相对路径**，实测进包内目录跑会路径解析失败）。产出同名 .png。
5. **亲眼看图验收**：Read 打开 PNG 确认：无水印/无乱码/箭头与卡片不错位/中文清晰/品牌色正确——**不许不看图就交付**。通过后 PNG 落发布包 `04_配图/`，命名 `<两位序号>-概念锚点_<主题>.png`（接续现有最大序号）；需要入稿则按 md2wechat 占位规则同步插 MD 与排版 HTML（参照 pub-infographic-supplement 的 before/after 锚点法）。

## 模板速改指引（gate-flow）

- 4 卡：改 `.gate .no`（关卡 n）、`.nm`（名称）、`.sym`（症状一句）、`.key`（钥匙一句）；少于/多于 4 关改 `.gates` 的 `grid-template-columns`。
- 起终点：改 `.start .dot`（左起点）与 `.finish .lb`（右终点）；箭头自动贯穿。
- 标题：`<h1>` 主标题 + `<span class="r">` 红字强调；右侧 `.tag` 写图类型标签。
- 隐喻变体：漏斗=卡宽递减；传送带=起点改"输入"、终点改"交付"；塔=竖排 grid。

## 红线

- 禁用生成模型出最终稿（水印/糊中文风险）；生成图只允许做风格参考。
- 不放公司/项目真名与内部数据（与正文同一脱敏标准，过 `privacy_scan.py` 口径）。
- 每张图交付前必须 Read 自看（视觉验收不可跳过）。

## 收尾留痕

`python3 tools/changelog_append.py --type "🎨" --path "<产物png路径>" --desc "概念锚点图：<文章>·<隐喻>·fig_fit 无水印渲染" --tool qwenwork`（或按所在工作区惯例）。

<!-- public-sync: 2026-09-27 | 脱敏版本 | 源 .agents/skills/concept-anchor-figure -->
