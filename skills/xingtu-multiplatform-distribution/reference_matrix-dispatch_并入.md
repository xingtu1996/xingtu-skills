> 🔴 本文件由技能治理(09-19)从孤儿 skill `matrix-dispatch` **整体并入** `xingtu-multiplatform-distribution`，原目录将入回收站。内容逐字保留防 IP 丢失；正牌 SSoT=xingtu-multiplatform-distribution/SKILL.md。

---
name: matrix-dispatch
description: 行途「公众号首发 → 多平台差异化改写推送」总装流水线 Skill。单入口编排四环节：①三 agent 本地会话取证（豆包/千问/WorkBuddy 对矩阵+台账的认知）②全平台已发布盘点（公众号+掘金+知乎+CSDN+小红书+抖音+X，闭环率真值）③按平台属性生成 30–35% 结构级变体（禁通稿、标原创）④凭证登记+闭环率刷新。系统永不代发，只到草稿箱/预填，最终发布 boss 人工点。适用场景：用户说"启动矩阵分发""铺外站""跨平台改写推送""盘点已发布""刷闭环率""登记分发凭证""别串错平台"。
metadata:
  author: xingtu
  version: "1.0.0"
  argument-hint: "<公众号文章标题或路径> [--platform 掘金|知乎|CSDN|小红书|抖音|X] [--inventory] [--evidence <截图路径>]"
---

# 矩阵分发总装 Skill（行途版）

> ⚠️ **范围守卫**：读工作区根 `AGENTS.md`，确认含「行途」才执行。否则拒绝（避免串到其他项目）。
> ⚠️ **第一铁律**：本 skill **永不代发**。所有外站发布、公众号群发，最终由 boss 人工在后台点。系统只做：取证、盘点、生成变体、预填草稿箱、登记凭证、刷新闭环率。

## 一、为什么需要它（核心认知）

战略层早已完备，但执行层长期=0：**闭环率真值=0**（除 2 篇历史外站 8/27 掘金、8/6 CSDN）。根因不是"没规划"，而是**备稿就绪后卡在 boss 没点发布 + 没登记凭证**。本 skill 把"取证→盘点→改写→凭证"固化成一键可跑的流水线，让首篇分发从 0 破零。

- 战略 SSoT：`specs/20260917-矩阵分发启动/02_矩阵战略SSoT_结构铁律台账闭环率.md`
- 现状盘点 SSoT：`specs/20260917-矩阵分发启动/01_现状盘点_三agent认知与已发布清单.md`
- 分发 SOP SSoT：`specs/20260917-矩阵分发启动/03_分发SOP_首发到改写推送.md`
- 首篇方案 SSoT：`specs/20260917-矩阵分发启动/04_首篇分发方案_候选与待拍板.md`

## 二、触发词 → 路由

| 用户说 | 路由到 |
|---|---|
| 启动矩阵分发 / 铺外站 / 跨平台改写推送 | §三 全链路跑一篇 |
| 盘点已发布 / 全平台发了啥 / 闭环率多少 | §四 盘点（或 `python3 scripts/inventory_matrix.py`） |
| 三 agent 怎么看矩阵 / 豆包千问认知 | §三 Step 0 取证 |
| 登记凭证 / 刷闭环率 / 凭证落盘 | §三 Step 4 + `tools/evidence_register.py` |
| 别串错平台 / 这版发哪 | §五 防串校验 |

## 三、全链路 5 步 SOP（每篇外站分发）

### Step 0 取证（可选，首次/有分歧时）
核对三 agent 对矩阵+台账的认知是否一致，避免"各 agent 各说各话"。
- 加载 `desktop-ai-forensics` skill，解析本地会话库：
  - 豆包工作：`~/Library/Application Support/DoubaoWork/Default/IndexedDB/`（chrome_doubaowork-chat / general-agent-cot）
  - 千问办公：`~/Library/Application Support/QwenWorkCN/`（Local/Session Storage leveldb，先 `find` 确子路径）
  - WorkBuddy：`~/.workbuddy/memory/`、`${WORKSPACE}/.workbuddy/memory/`、本空间 spec
- 抽关键词：矩阵/分发/台账/多平台/首发/改写/闭环。产出"三 agent 认知对比 + 分歧点"。
- 已知共识：结构（公众号首发→外站差异化）+ 铁律（≥24h/标原创/API仅草稿箱）+ 台账字段一致；唯一"24h vs 12h"不冲突（≥24h 是公众号闸门，≥12h 是同源错峰）。

### Step 1 取已发文（盘点闸门）
- 选**公众号已发 ≥24h** 且**原创标识已勾**的 A/B 级文（C 档不分发）。
- 一键盘点：`python3 scripts/inventory_matrix.py --root <xingtu根>` → 输出平台×文章表 + 闭环率缺口 + 具备分发条件的文章清单。
- 候选（实测 7 篇 ≥24h）：F10 FDE 国家点名(9-10) / P13 PEC2026 复盘(9-13) / B15 斩杀线(9-11) / B16 删306行(9-12) / V9 V4.1Flash(9-9) / A8 AI Agent是什么(9-8) / F7 Fable5.1提示词(9-7)。

### Step 2 生成平台变体（改写，agent 生成）
- **当前无 `tools/multiplatform_rewrite.py`**（spec 03/04 误引，待建）。改写为 **agent 按 `02_矩阵战略SSoT.md` §一属性表生成 30–35% 结构级变体**（非通稿、标原创、去寒暄、结论先行）。
- 平台属性要点（详 `reference.md` 平台属性表）：
  - 掘金/CSDN：技术深度+代码，SEO 背书；CSDN 已公开雇主→注意 SAF-010
  - 知乎：问答/长文，FDE 人设背书，故事型适配
  - 小红书/抖音：图卡+标题党，泛流量；**禁外链、需打码雇主**
  - X：英文短链 + GitHub 中转，国际线
- 复用骨架：`outputs/发布包_2026-09/多平台分发_MODEL-02_20260915/`（`01_掘金版`~`06_X版` + `07_已发布内容分发backlog.md`）。

### Step 3 出操作单 + 红线自检
落 `outputs/发布包_2026-09/多平台分发_<文章>_<日期>/`，**每平台一文件**（防串错平台）：
```
# <NN>_<平台>版.md
- 源文：公众号 <标题> <URL> <首发日>
- 目标平台：<掘金/知乎/CSDN/小红书/抖音/X>   ← 文件名即平台，发布前 self-check 匹配
- 改写幅度：__%（目标 30–35%，结构级变体）
- 标题：<平台属性标题>
- 正文要点：<3–5 条，去寒暄、结论先行>
- 红线自检：□禁通稿 □禁外链 □禁引流 □标原创 □不露雇主(SAF-010)
- 发布状态：⬜待发 / 📝草稿 / ✅已发(<URL>)
- 凭证：分发凭证_<平台>_<日期>.png
```

### Step 4 boss 人工发布 + 登记凭证 + 刷闭环率
- boss 后台发布（**一天 ≤2 平台，同源错开 ≥12h**）。
- 截图 → 一键登记（自动识别平台、改名、移投放口、重算闭环率）：
  ```bash
  python3 tools/evidence_register.py --register <截图路径> [--platform 掘金] [--date 2026-09-17]
  # 仅盘点：python3 tools/evidence_register.py --list
  ```
- 闭环率 SSoT 在 `tools/dispatch_feed.py` + `data/dispatch_config.json`（AC-6：已执行输出÷已给建议）。`evidence_register.py` 跑完会自动调 `dispatch_feed.py` 打印前后值。

### Step 5 回写（收尾铁律）
- `python3 tools/changelog_append.py --type "📡" --path "outputs/发布包_2026-09/多平台分发_<文章>_<日期>/" --desc "矩阵分发：<平台> 已发+凭证登记，闭环率 <前→后>" --tool workbuddy`
- 同步 `github/xingtu-vault/09_个人台账/03_已发布文章档案/` + 发布日志。

## 四、一键盘点（只读，常用）

```bash
python3 scripts/inventory_matrix.py --root ${WORKSPACE}
```
- 扫描 `outputs/发布包_2026-09/_archive/已发布/` → 公众号已发清单
- 扫描 `outputs/发布包_2026-09/多平台分发*/分发凭证_*` → 外站真实分发（闭环率真值，凭证即铁证）
- 输出：平台×文章 markdown 表 + 闭环率缺口 + 待补凭证清单
- 零依赖（纯 stdlib）、只读、不动盘。

## 五、防串错平台（红线自检）

- **文件名即平台**：操作单 `<NN>_<平台>版.md`、凭证 `分发凭证_<平台>_<日期>.png` 都含平台名，`evidence_register.py` 从文件名/目录自动识别平台，发错平台会露馅。
- **发布前 self-check**：Step 3 红线清单 + 后台发布前核对"此文件平台 == 此后台平台"。
- **一天 ≤2 平台**：避免同源内容短时间铺太密被判定搬运。

## 六、与各平台 owner 协作（不重复造轮子）

| 平台 | owner | 调用现有 skill |
|---|---|---|
| 公众号（首发+草稿箱） | WorkBuddy/bsk | `wechat-mp-publish` |
| X / 小红书（国际+泛流量） | 豆包/WorkBuddy | `x-auto-publish` |
| 元宝归档 | WorkBuddy | `yuanbao-archive-pipeline` |
| 掘金/知乎/CSDN（技术变体） | 千问办公 | agent 生成（待建 `multiplatform_rewrite.py`） |

## 七、闭环率定义（不复制公式，引 SSoT）

- **已执行输出**：存在 `分发凭证_<平台>_<日期>.png` 的外站分发数（脏前缀"品牌化/更名/认证"排除，见 `dispatch_feed.py` AC-5）。
- **已给建议**：矩阵 SOP 建议分发的总数（公众号已发 A/B 级 × 适配平台数）。
- 公式 SSoT：`tools/dispatch_feed.py`（`data/dispatch_config.json` 权重）。本 skill 只触发重算，不重造。

## 八、示例（见 .skill-metadata.yaml）

三示例：①首篇全流程（F10→知乎+掘金）②一键盘点 ③补登记历史凭证。
