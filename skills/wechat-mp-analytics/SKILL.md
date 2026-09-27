---
name: wechat-mp-analytics
description: 公众号后台只读数据分析（行途）——用 bsk 接管已登录 Chrome，拉取阅读/分享/粉丝/图文明细，回流舆情与内容战略研判。触发词：查公众号后台、拉后台数据、阅读分析、粉丝数据、数据分析、舆情回流、图文分析、已发表内容、mp.weixin 数据。与 `wechat-mp-publish`（写操作：群发/草稿）严格分离——本 skill **只读取、绝不发布**。适用于任何 Agent 需要把真实后台数据（而非平台记账或猜测）作为内容决策/选题研判/发布时间判定的事实源。
---

# 公众号后台数据分析（wechat-mp-analytics）

> 定位：把公众号后台变成任意 Agent 可调用的**只读**数据通道——阅读 / 分享 / 粉丝 / 图文明细。
> 原则：**只读不写（绝不点群发/发表/存草稿）**｜**数据以后台为准（排期✅≠已发，平台记账≠官方账单）**｜**复用 bsk 既有通道，不重写**｜**操作可复现、留痕**。

## 为什么需要独立 skill（与 wechat-mp-publish 分离）

`wechat-mp-publish` 是**写操作**（导入草稿、设封面、群发），且默认 bsk 通道。
但"只读拉数据"是高频、零风险、且**绝不能误触发布**的一类操作。混在同一 skill 里，
Agent 在"读数据"时可能误激活发布流程。故单列：**读归读、写归写**，触发表各自独立。

## 环境 prerequisites

```bash
# bsk 二进制位置（关键坑：默认不在 agent shell 的 PATH 里，必须绝对路径或 export）
BSK=${HOME}/.local/bin/bsk
# 验证：bsk 守护进程通常已在跑（ps 可见 bsk daemon pid）；bsk 命令会自动拉起依赖服务
$BSK --version        # 期望 ~0.2.x
$BSK session start --no-focus   # 复用你 Chrome 的登录态/cookie，开 Agent Window
```

- **复用已登录 Chrome**：bsk 接管的是你日常用的 Chrome（Default profile，已登录 mp.weixin.qq.com），无需重新登录。
- **daemon 自愈**：任何 `bsk` 命令会自动启动所需后台服务，**不要手动管理 daemon**。
- **多浏览器**：`bsk browsers` 列可用浏览器，`bsk session start --browser <id>` 指定；默认即可。

## 安全铁律（红线，违反即可能误群发）

1. **只读不写**：本 skill 下**绝不允许**执行任何会触发「群发 / 发表 / 存为草稿 / 改封面」的动作。
2. **用完即停**：`bsk session stop <id>` 必须在成功与失败两条路径都执行——既释放 Agent Window，也归还借用的 tab。
3. **不提取凭据**：页面上的 cookie / token / 密码一律不抓取、不落盘。
4. **数据以后台为准**：拿到的数字直接作为事实源；不要和"平台记账价""发布日志预估"混用，差异要标注来源与口径。

## 生命周期（bsk 标准三段）

```text
1. $BSK session start --no-focus     # 保留打印的 4 字母 session id
2. $BSK ... --session <id>           # 每个 session 作用域命令都带 --session
3. $BSK session stop <id>            # 成功/失败都要跑
```

## 实测导航路径（数据分析 → 内容分析 → 已发表内容 → 最近30天）

> ⚠️ `observe` 返回的 `@eN` 元素 ID 是**快照相关、会变**的，**不要硬编码**。
> 跨会话复用的健壮做法是：用 `evaluate` 按**可见文本**定位点击（见下）。

```bash
BSK=${HOME}/.local/bin/bsk
ID=egwh   # 替换为实际 session id

# 0) 进后台首页（已登录会直接进「行途」概览：总用户数 / 昨日阅读分享新增）
$BSK navigate "https://mp.weixin.qq.com/" --session $ID
sleep 3; $BSK observe --session $ID

# 1) 左侧「数据分析」→ 展开后点「内容分析」→「已发表内容」
#    （用 observe 看真实文案后，优先用 evaluate 按文本点击，避免 @eN 漂移）
$BSK evaluate --json 'Array.from(document.querySelectorAll("li,span,a")).forEach(e=>{const t=e.textContent.trim();if(t==="数据分析"||t==="内容分析"||t==="已发表内容")e.click()})' --session $ID
sleep 3; $BSK observe --session $ID

# 2) 切「最近 30 天」时间窗，才能看到全部已发文章的单篇对比
$BSK evaluate --json 'Array.from(document.querySelectorAll("li")).forEach(e=>{if(e.textContent.trim()==="最近 30 天")e.click()})' --session $ID
sleep 4; $BSK observe --session $ID

# 3) 表格在页面下方，observe 会被截断 → 滚动 + grep 过滤关键行
$BSK evaluate --json 'window.scrollTo(0,1400)' --session $ID
$BSK observe --session $ID | grep -iE "分享|收藏|阅读|篇|%|DeepSeek|Agent|FDE|PEC|V4|三国|退役|已发表"

# 4) 收工
$BSK session stop $ID
```

### 坑速记（2026-09-15 实测踩过）

- **PATH 缺失**：agent shell 默认 PATH 不含 `~/.local/bin`，`bsk` 报 command not found → 用绝对路径 `${HOME}/.local/bin/bsk` 或先 `export PATH="$HOME/.local/bin:$PATH"`。
- **observe 截断**：长页面（含汇总卡片 + 明细表）observe 只返回视口附近 DOM，明细表要 `scrollTo` + grep。
- **@eN 漂移**：同一流程每次 session 的元素序号不同，健壮做法一律按**可见文本** `evaluate` 点击。
- **数据时效性**：首页「数据统计」常滞后 1 天（停在昨日）；单篇实时表现要去「已发表内容」看。
- **口径差异**：后台「阅读人数」≠ 发布日志里的「送达/阅读」口径，引用时标注来源。

---

## 操作记录（2026-09-15 实测，可直接复现）

**目的**：研判 9/16 发什么——用真实后台数据验证"DeepSeek 系低迷 vs FDE/Agent 高钩子"假设。
**环境**：bsk daemon 已在跑；Chrome Default 已登录；session `egwh`。
**执行命令**：见上方"实测导航路径"全序列（session start → navigate → 三次 evaluate 按文本点击 → scrollTo → grep → session stop）。

### 取数结果（最近 30 天单篇阅读，总阅读 **839 人**，数据截至 9/14）

| 排名 | 文章 | 发表 | 阅读人数 | 占比 |
|---|---|---|---|---|
| 1 | PEC 2026 台下一天（Token工厂/FDE/出海/Harness） | 9/13 | **167** | 19.9% |
| 2 | 国家点名 FDE：缺的不是模型是现场的人 | 9/10 | **161** | 19.2% |
| 3 | 智谱 GLM-5.3 Flash 开源（比 DeepSeek 还便宜） | 8/27 | **152** | 18.1% |
| 4 | FDE 能力模型 8 维度拆解 | 9/14 | **93** | 11.1% |
| 5 | DeepSeek V4.1 Flash 内测上手 | 9/09 | **73** | 8.7% |
| 6 | AI 时代知识复利 | 9/06 | **56** | 6.7% |
| 7 | Anthropic 官方提示词手册 | 9/07 | **32** | 3.8% |

**首页概览（9/14 当日）**：总用户数 **54**（此前记 51，近期 +3）｜昨日阅读 **136**｜分享 **14**｜新增关注 **9**（分享率 ~10%）。
**9/15 速评02 实时（已发表内容）**：后台阅读仅 **4**（发布日志送达 54）。

### 数据得出的三条研判（已反推原假设）

1. **FDE/PEC 系是绝对头部**：PEC 167 + 国家点名 FDE 161 + FDE 模型 93 = 30 天总阅读 **50%** → 高钩子/现场感路线验证对路。
2. **DeepSeek 速评确实弱**：速评02=4、V4.1 Flash=73（8.7%）→ 别追发 DeepSeek 事件稿。
3. **修正"模型快讯整体看衰"误判**：智谱 GLM-5.3 Flash 拿 **152**（第 3），靠"比 DeepSeek 便宜"的**价格对比强钩子** → 结论不是"模型快讯不行"，而是"**无强钩子的模型快讯不行**"。
   → 反而**加强 AGENT-03《Agent 三国杀》推荐**：它是 WorkBuddy/豆包/千问多工具**对比**，自带冲突/对比钩子（与智谱 152 同源逻辑），且三方是稳定产品形态，PUB-051 末查的"数据过期"风险远低于速评类。

**决策落地**：9/16 发 AGENT-03《Agent 三国杀》（与权威排期 `本周发布计划_0915-0921` + 9/14 深夜调整双源一致；发布日志 line 128 错填"六层 Token ⑤"待校正）。

---

## 关联规则（决策前必读）

- **PUB-019**（发布时段）：每天仅 1 次群发额度（图文与贴图共用），主力档早 8:15；本 skill 取数后若要发，走 `wechat-mp-publish` 且先确认额度。
- **PUB-051**（时效门禁）：速评/热点类稿件发布前 24h 必须回源复查；定时稿在定时动作前最后一查。本 skill 的"已发表内容"取数可作为回源核查的事实源之一。
- **PUB-043/044**（合集矩阵）：引用合集名必须与后台真实合集一致，SSoT = 品牌资产台账 `wechat_collections`。
- **数据真实性铁律（STR-012）**：内容决策优先用一手后台数据（本 skill 产出）> 二手转述 > 方法论包装。

## 何时用 / 何时不用

- **用**：选题研判、发布时间判定、复盘取数、验证"阅读低迷是选题问题还是频率问题"、PUB-051 回源核查。
- **不用**：要发文章/改草稿/设封面 → 走 `wechat-mp-publish`；要读**本地微信聊天**（非公众号后台）→ 走 `wechat-channel`。

---

## 并入资源（2026-09-19 技能减法治理）

本 skill 于 09-19 吸收了原孤儿 `wechat-traffic-source-diagnosis` 的全部内容，逐字存于同目录 `reference_wechat-traffic-source-diagnosis_并入.md`（其独有脚本/资源已并入本目录 scripts|templates）。触发本 skill 时若涉及「阅读来源/推荐占比/限流诊断」，先查该并入文件防遗漏。

<!-- public-sync: 2026-09-27 | 脱敏版本 | 源 .agents/skills/wechat-mp-analytics -->
