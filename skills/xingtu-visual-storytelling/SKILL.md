---
name: xingtu-visual-storytelling
description: "行途技术视觉叙事编排：当用户说技术文章配图、架构动态分镜、精美长图、公众号与小红书图卡、X配图、朋友圈主图、找技能做流程动图、按行途design规范出图或跨平台视觉发布包时使用。读取实际母稿与证据→确定视觉信息增量→发现已安装可信Skills→分镜源图与跨平台素材→版权/隐私/事实/移动端验收→回写发布包。只编排现有能力，不自动群发。"
version: 0.2.0
status: pilot
user-invocable: true
argument-hint: "文章/发布包路径或 PR、目标平台、当前版本与是否允许写入草稿箱（默认否）"
---

# 行途视觉叙事编排（xingtu-visual-storytelling） · PILOT

> **直接调用示例**：「调用 xingtu-visual-storytelling，基于当前发布包的最终稿，做公众号架构分镜 + 小红书图卡 + X 单图；保持仅审稿，不建微信草稿。」
>
> **执行边界**：这是可被 Agent 加载的声明式 Skill，**不是** GIF 渲染器、自动发布器，也不是“find-skills 已安装”的证明。v0.2.0 的端到端运行、实际发布平台兼容性尚未实测，不能宣称生产级就绪。需要先合并/安装到当前 Agent 可用 Skills 目录，单靠 GitHub PR 不会自动触发。

## 优先读取的 System Design / 具体调用入口（v0.2）

请按以下**版本显式**的顺序读取，不凭记忆补全：
1. [xingtu-design PR #4｜04 System Design](https://github.com/xingtu1996/xingtu-design/pull/4)：架构、组件、契约、状态机、发布边界。
2. 同 PR 的 `05_提示词与多Agent交接手册.md`：提供普通配图、专业动态图、跨平台、独立审图、Work 接力、迭代复盘的**可直接复制提示词**。
3. 同 PR 的 `06_持续迭代_验收与版本治理.md`：每篇文章的质量反馈、回退和变更传播。
4. 同 PR 的 `07_动态工具评估与质量基线.md`：`diagram-animation`、`diagram-animate`、Remotion、`motion-design-principles` 的源码、用途、限制；目前仅为**候选，非已安装**。
5. 同 PR 的 `visual-asset-contract.schema.json` 与 `visual-plan.example.json`：机器可读的计划结构；填入真实 article_ref 的实例**只放授权私有包**。

**权威状态**：正式已合并规范优先于 Draft 设计提案。此 Skill 也是 PR #10 的 PILOT 候选；如果只在 GitHub 能读到但并未实际安装，请明确称“按候选 Skill 文档手动执行”，不要声称自动触发或已完成安装。**双向链接**：[Design PR #4](https://github.com/xingtu1996/xingtu-design/pull/4) ↔ [Skills PR #10](https://github.com/xingtu1996/xingtu-skills/pull/10) ↔ [发布会话 Vault PR #24（持权访问）](https://github.com/xingtu1996/xingtu-vault/pull/24)。

**最短路由**：
`文章事实与现有版本 → visual-plan → 已审制图能力 → SVG/HTML静态图 → 必要时GIF/MP4 → 平台变体 → 真实验收 → 发布包回执 → Design缺陷Issue`。
未经审核的动画候选不自动安装，不依赖微信正文运行 JS/CSS 动画。动态失效先回退静态，不让动画质量问题阻断正文。

## 0. 首先定位现有文章和授权（避免重复建稿）

1. 读取当前工作区 `AGENTS.md`、出版/隐私规则；确认使用者拥有文章、资源、草稿读写权限；没有就仅输出设计计划。
2. 查目标文章的**现行发布包、最新母稿、manifest、审核状态、既有草稿与版本号**。不能拿历史已归档发布包替换当前文章，也不能让多 Agent 覆盖同一包。
3. 如已有开放 Work 发文任务，接力该任务；只在用户明确允许的范围内修改。**公开发表、群发、朋友圈/X/小红书外发始终要人工审核**，本 Skill 不执行。
4. 输入不全时尽可能从有权访问的项目记录读取；仍缺事实来源则标 `UNVERIFIED`，不用猜测填图。

**最小输入**：母稿或发布包路径/PR、目标平台集合、版本/日期、授权边界。 
**基础输出**：`06_发布参考/视觉叙事决策与验收.md`，并按上述 System Design 的 `visual-asset-contract.schema.json` 结构组织计划（若当前包未规定目录，记为待落盘并说明）。已完成物料必须按现有发布包结构归档，不能另外造一套公开正文库。

## 1. 读取唯一设计源，处理新旧冲突

按顺序读取：
- [xingtu-design 正本](https://github.com/xingtu1996/xingtu-design) 的已生效版本与 [Design PR #2](https://github.com/xingtu1996/xingtu-design/pull/2)、[PR #3](https://github.com/xingtu1996/xingtu-design/pull/3)、[视觉叙事 PR #4](https://github.com/xingtu1996/xingtu-design/pull/4) 的**提案**。
- [现行发布管线](https://github.com/xingtu1996/xingtu-skills/blob/main/PUBLISHING-PIPELINE.md) 和当前已安装本地 Skill 版本。
- 必要时复核 `harness-kit/docs/brand-visual.md` 镜像漂移。

**冲突处理**：已合并生效的规则和当前发布审批门禁优先，Draft PR 仅为设计候选；发现旧的“黑白严格交替”“一千字一图/A档8–12张”“旧红+蓝”必须列入冲突清单，**不得悄悄全局修改其他 Skills 或声称已经完成升级**。设计建议可先用于独立可审核样稿，不强制替换已获批发布包。

## 2. 从事实到视觉蓝图

先给文章定位：`architecture` 架构、`practice` 工程实践、`whitepaper` 产品白皮书、`news` 技术资讯；再按节提炼“场景→问题→机制→证据→反例/边界”。

写 `视觉叙事决策与验收.md` 的矩阵，逐项包含：

| claim_id | 主张/状态变化 | 事实来源及验证等级 | 读者最难理解之处 | 推荐视觉 | 插入位置 | 许可/脱敏 | 不能声称 |
|---|---|---|---|---|---|---|---|

**一图一增量**：图用来承担路径/状态/对比，文字负责动机、条件、后果。没有独立信息价值时删图。官方文档截图只能说明文档当时的陈述，不能冒充自行实测；未经核实的数据、曲线、客户规模、模型能力、稳定性一律不能作为实测画进图。

## 3. 挑选图形和媒介

- **封面隐喻**：少字/无重复标题，白黑橙红 `#FFFFFF/#1A1A1A/#F2644F`，优先真实有权使用的素材；AI 概念画面标注身份。
- **概念锚点**：调用已审查的 `concept-anchor-figure`，注意其当前旧配色要人工校正，不继承错误为新标准。
- **连续分镜**：同一结构化画布，按 F0 触发→F1 入口→F2 决策→F3 Worker 执行→F4 回执/失败依次高亮。不是所有文章都必须五帧。
- **GIF/视频**：仅当状态变化确实更适合动态、宿主环境有已审核渲染能力、目标平台实测显示正常时增产；无论是否有 GIF 都需要可独立理解的静态替代。
- **数据图/证据截图**：仅用经核实的原始数据与真实采集；遵循 Design PR #3 的图注、授权、原图与编辑图哈希规则。

关于别人的公众号案例：可学习**场景化解释、逐状态高亮、单隐喻封面、图注边界**，不得复制外部截图、动图和版权受保护的特定视觉作品作为自己的素材；本会话里的 Super Agent 长图 V1 是概念样稿，未验证曲线不可直接发布。

## 4. Find Skill 只是发现入口

1. **先查本地已安装能力与仓库**：`concept-anchor-figure`、`pub-infographic-supplement`、`wechat-cover-gen`、`xingtu-multiplatform-distribution`、`mp-prepublish-draft-verify`；按真实工作环境确认路径和版本。
2. 用户提到 `find skill` 时，在实际支持的平台上寻找候选；**没有工具就记录 NOT_AVAILABLE**，不要编造“找到了/已安装/已运行”。
3. 候选逐项记：名称、上游 URL、commit/版本、许可、可写目录、shell/网络/依赖/凭据权限、输入输出契约、实测记录；分为 `TRUSTED` / `PILOT` / `REJECT`。
4. 第三方技能不经审查不自动安装/执行，不向其发送私有 vault 文本、截图或密钥；失败立即回退至已审技能或手动静态分镜。
5. 执行工具依赖本机/Work 真实环境，先给出命令与检查预期；**没有实跑的检查标 NOT_RUN**。

## 5. 渲染与跨平台变体

复用真实发布包格式，不要求每次四平台全发：
- **公众号**：语义清楚的可复制正文 HTML + 真实证据/结构图/图注。移动预览 375/414px，图片加载与段落可读。动图失败时仍有静态帧。
- **小红书**：一页一个问题的 3:4 竖图（既有 Skill 示例 1080×1440），图卡内容需重新组织，不把全文缩小截图。
- **X**：单图或 Thread 组合，图说明与正文要互补；图片 alt 与事实链接独立核对。
- **朋友圈**：一张易扫读的主图 + 一段个人判断；无凭空编造的互动、收益或“我实测”。
- 沿用 `xingtu-multiplatform-distribution` 既有时序与分发硬门禁；本技能**只生成可审核变体，不授权外发**。

具体出图由现有技能和工具完成，不能把描述文字冒充生成的 PNG/GIF。每图留可编辑 SVG/HTML/数据源、PNG/GIF/视频（如有）、配图清单、图注、哈希、真实许可、版本。

### 动效高级感的最小增量

只有“节点依次高亮”而没有因果、路径、并行或失败信息的 GIF，不应作为“专业动图”通过。请分别评审：`storyboard`（解释什么） / `motion`（如何动） / `renderer`（实际导出） / `wechat`（真实播放）。动图需要同一源导出的 PNG 静态回退；检查真实首/中/末帧、中文排印、循环点、长度与体积，不因浏览器或公众号后台显示 GIF 就认定微信手机持续播放通过。详细质量准则在 Design `07_动态工具评估与质量基线.md`。

## 6. 完成验收与接力

- [ ] 目标文章版本/现有草稿已核实，无重复建稿和并行覆盖
- [ ] claim→source→asset 映射齐全；事实、示意、推断、未证实边界清晰
- [ ] 品牌色/封面文字与当前获批规则一致；若使用 PR #2 提案则列明
- [ ] 图中中文、数字、路径、箭头、状态、隐私与版权逐张校对
- [ ] 公众号 375/414、小红书 3:4、X/朋友圈预览：实测状态如实留痕
- [ ] 若用 GIF/视频，保存帧清单与静态替代；真实微信播放状态未验则标 NOT_RUN
- [ ] 公开发布一律人工批准；私人草稿只有明确授权+现行验收通过才允许建稿/更新
- [ ] 输出 `PASS/FAIL/NOT_RUN`、文件路径、commit/SHA、回滚点及下一步接力说明

输出按中文「结论→证据→风险→建议动作」。**GitHub 入库≠已经在当前 Agent 安装≠生成图片≠微信草稿已建≠公开发布**。

## 参考与不重复实现

- 设计单一事实源：<https://github.com/xingtu1996/xingtu-design/pull/4>
- 既有截图治理：<https://github.com/xingtu1996/xingtu-design/pull/3>
- 发布规划：`publish-pack-planning`；正文审核：`fact-check-gate`、`de-ai-flavor`
- 原图/配图：`concept-anchor-figure`、`pub-infographic-supplement`、`wechat-cover-gen`
- 草稿核验：`mp-prepublish-draft-verify`；多平台：`xingtu-multiplatform-distribution`
- 会话归档：`session-sediment`（本 Skill 不重新处理会话转录）
