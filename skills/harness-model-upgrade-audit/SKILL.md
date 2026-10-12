---
name: harness-model-upgrade-audit
description: 模型换代后对 harness（CLAUDE.md / AGENTS.md / rules / skills / memory / hooks）做「减法」审计与精简，删掉为旧模型能力不足而写的兜底规则。触发词：模型换代、新模型上线、harness 精简、删规则、旧的 prompts skills 是负资产、prompt 迁移、模型升级后优化、harness 减肥、unhobbling、model upgrade audit。适用于任何"人带 AI 长期协作、持久化指令只增不减"的工作空间。
agent_created: true
---

# harness-model-upgrade-audit · 模型换代 harness 减法审计

## 何时用

新模型上线后。核心判断：**旧提示词/技能对新模型可能是负资产**——它们互相冲突，让模型把算力花在仲裁而不是干活上。

不需要等大版本。任何"模型能力明显跃迁"的换代都值得跑一遍（30 分钟量级）。

## 第一性原理

> 持久化指令存在的唯一理由：**编码「模型自己推不出来、且答错代价高」的信息**。
> 其余一切——可推断的（目录树/路径表/架构图/技术栈）、模型已具备的能力（教学/禁令/兜底）、同一工具内的复述——都是每轮会话都在付费的成本。

**核心问句**：删掉这条规则，模型会犯错吗？会→留；不会→删。

## 五步流程

### Step 0 · 先确认"真正生效的指令面"（最容易漏）

不要相信记忆里的路径。**实测**：

```bash
# 找所有指令文件（注意家目录可能同时存在多个工作空间副本！）
find ~ -maxdepth 4 \( -name "CLAUDE.md" -o -name "AGENTS.md" -o -name "SKILL.md" \) \
  -not -path "*/Library/*" -not -path "*/node_modules/*" 2>/dev/null
# 找规则/记忆/hooks
ls -la .claude/ .agents/ .workbuddy/ .harness/ 2>/dev/null
cat ~/.claude/settings.json | python3 -c "import json,sys;print(json.load(sys.stdin).get('hooks',{}))"
```

**逐文件问：这个文件的加载者是谁？**
- Claude Code 只自动读 `.claude/CLAUDE.md`（项目级）+ 全局 `~/.claude/CLAUDE.md`
- WorkBuddy 读 `.workbuddy/*` 与项目 `.workbuddy/memory/*`
- Codex / OpenCode / 豆包 读 `AGENTS.md`
- `trigger: always_on` 的规则文件（如 `.agents/rules/*.md`）会被支持的工具有效强制加载

先画一张「文件 → 加载者 → 常驻还是按需」的表，再谈删。**跳过这一步必然误删。**

### Step 0.5 · 先确认「技能与标准」在各平台是否可见（跨工具盲区排查）

**做完 Step 0 的加载面分析后，必须再查一步：本任务要用的 skill / 方法论 / spec 模板，在当前工具的 skill 目录里存在吗？**

同机常见 skill 目录（各工具只认自己的）：
- `~/.claude/skills/`（Claude Code 全局）
- `~/.workbuddy/skills/`（WorkBuddy 全局）
- `<项目>/.claude/skills/` 与 `<项目>/.workbuddy/skills/`（项目级）
- `~/.agents/skills/`（跨工具约定，作为中立实体层）

```bash
# 一眼看出某 skill 在哪些平台可见
for s in <skill名...>; do printf "%-26s" "$s"
  for d in ~/.claude/skills ~/.workbuddy/skills ~/.agents/skills; do
    [ -e "$d/$s" ] && printf "$d:✓ " || printf "$d:✗ "; done; echo; done
```

**结论常是：技能"全局"其实只在某一个工具里全局。** 典型症状：用户说"按 specs 标准推进"，AI 却自造了一套 spec 组件——因为标准 skill（`specs-engine`）住在另一个工具的目录里，本工具根本看不见。

**修复方式（不改实体、零漂移）**：
```bash
ln -s <实体所在目录>/<skill> <本工具 skill 目录>/<skill>
```
> ⚠️ 优先软链而非复制。若 skill 的文档/脚本里**硬编码了自己的路径**（如 `~/.claude/skills/x/scripts/y.sh`），就**不能挪实体**，只能加链——挪了会打断所有引用。

**顺带产出**：把这份"技能 × 平台可见性矩阵"给用户看，比讲原理有用得多。注意提醒：给某平台多挂 skill 会**增大该平台每次会话的注入量**，所以要按需挂，不要无脑全量同步。

### Step 1 · 外部依据研究

查官方对该模型的提示词指引 + 生态里"为新模型重构 prompts"的实践。产出**可执行的删/留判定标准**（问句清单，每条带出处）。

> 参考：Anthropic 2026-07-24 context engineering（Claude 5 代删除 80%+ 系统提示而编码评测无损失，术语 "unhobbling"）；社区 CLAUDE.md 1204→151 行案例的四桶法（Delete / Relocate / Rewrite / Keep）。
> ⚠️ 注意区分「官方明确主张」与「社区推测」——不要把自己想表达的结论安到官方头上。

### Step 2 · 条目级盘点（并行做，产出成本表）

对每条独立指令输出一行：`规则ID/摘要 | 出处(文件:行号) | 类型 | 是否常驻 | 重复于 | 初判 | 理由`

类型 6 类：
① 安全/隐私红线（不可逆）② 业务/品牌约束（模型推不出来的事实）③ 工作流/流程 ④ **模型能力补丁（为旧模型缺陷写的教学/禁令/兜底）** ⑤ 纯背景/目录/路径表 ⑥ 重复或冲突

同时统计：每文件行数/字节/估算 token；**每次会话必然全量加载的总量**（成本大头）；重复对 + 冲突对清单。

> 并行技巧：依据研究 / 指令面盘点 / skills 审计 / 业务内容盘点 四路无依赖，可同时开 4 个 subagent。

### Step 3 · 决策表（提议稿，不执行）

分四类：**A 立即修正（事实纠错）/ B 精简（删·合·降）/ C 待 boss 拍板（业务决策）/ D 不动（边界）**。

**D 类必须明确列出并说明理由**——让用户看见边界在哪。

### Step 4 · 双向对立对抗审查（本流程的核心，不可省）

> **让 AI 审查自己写的规则有天然利益冲突**：它可能替你删掉它看不见原因而加的规则。所以必须只读提议 + 双向对立 + 人工核实。

开两个对立立场的审查者（可并行）：

| 派别 | 立场 | 专找 |
|---|---|---|
| **保守派** | 默认"每条删除都是错的"，任务是**推翻** | 被误判为重复实为跨工具必需的；被误判为背景实为业务事实的；不可逆/高爆炸半径被放进 B 类的 |
| **激进派** | 默认"每条保留都要自证清白"，任务是**论证删得不够** | 漏掉的成本大块；"看起来像红线其实是质量偏好"的；决策表完全没覆盖的层 |

**然后由主控逐条回原始文件核实两派的转述**——两派都会夸大或误报。

### Step 5 · 备份后执行

```bash
# 用工作空间自己的安全脚本，不要手工 cp
bash tools/safety/backup-before-op.sh '模型换代harness精简' <file1> <file2> ...
```

改完必须回写 CHANGELOG（若工作空间有此纪律）+ 落 spec（Reverse Sync）。

## 十大陷阱（实战换来的）

1. **「重复」有两种，绝不能一刀切。** 跨工具重复（AGENTS.md↔CLAUDE.md↔.workbuddy/*）是**必需的**，各工具加载面不同，删一处 = 某工具裸奔；只有**同一工具内**重复才是真冗余。
2. **别信转述的行号。** 动手前用检索工具（Grep 而非被 hook 改写的 shell grep）重新校准。本流程实测遇到盘点表错报行号（标为某内容的行实际是空行）。
3. **最大的收获往往不是"冗余"而是"误导"。** 一个 `always_on` 的规则桥接指向**已废弃目录**（含死路径、停在几个月前的状态），危害远大于浪费 token——它让模型误判当前阶段。
4. **同名不同层的表不是重复。** 先读原文确认两张"重复"的表是否真的管同一件事（如「操作类型→Skill」vs「意图→workflow SOP」是两层）。
5. **"指针"不是"副本"。** 各处只引规则 ID（`SAF-004`）而非复述定义，这已经符合 SSoT 设计，不要再收口。
6. **安全/合规/不可逆约束留在 hook 与权限层，不依赖 prompt。** 这类规则无论模型多强都不该删语义。
7. **别把"动态事实"写进"静态规则"。** 发布时间、当前模型名、排期——写死在规则里就必然漂移（改一次要改多处）。改为指向唯一事实源。
8. **模型换代自带时间炸弹。** 检查所有硬编码的旧模型名（规则、脚本、配置、README 示例），特别是**官方公告了下线日期的模型**。
9. **顺手修"断路"比删规则更值钱。** 盘点时留意：被入口文档/路由表引用、但实际在某层缺失的 skill——那是静默失效，不是冗余。
10. **省字不是目的。** 如果安全红线一条没动，文本只减 10% 是**健康的**。用"模型会犯错吗"问过一遍才是成果；省下的 token 是副产品。
11. **别自造 Spec 组件。** 说"按 specs 标准推进"就一定要找到那个标准 skill（常见是 `specs-engine`）。找不到 = 它在本平台不可见（见 Step 0.5），先修可见性，**不要凭印象发明 `00_SPEC.md / 01~07` 这类自造编号**——那会让团队里每个人拿到不同形状的 spec。
12. **"全局技能"是平台相对的。** 判定某能力是否真的全局，要看它在**当前工具的 skill 目录**里是否存在，而不是看名字里有没有"全局"。

## 交付物模板

> ⚠️ **Spec 目录一律走 `specs-engine` 标准，不要自造组件。** 见下方 Step 0.5。

1. **Spec（用 specs-engine 标准八件套）**：
   ```bash
   bash ~/.claude/skills/specs-engine/scripts/scaffold.sh new <specs父目录> <TICKET>-harness-model-upgrade [--depth standard]
   ```
   推荐落在：`01_analysis`（指令面盘点+成本表+重复冲突对）｜`02_requirements`（该删/该留的 AC）｜`03_design`（精简方案+对抗审查结论）｜`04_tasks`（执行清单打勾）｜`05_validator`（验收：备份/红线未动/冲突消解数）｜`execution-log`（何时改了哪个文件）｜`laws.md`（引擎快照）
   深度裁减参考：纯删改类任务可用 **轻量档**（`01_analysis + 05_validator`）。写完后跑 `scripts/validator-check.sh <spec目录>` 查占位符残留。
2. `outputs/<名称>_<日期>.html`：单文件零依赖看板（KPI 卡 + 判定原则 + 执行结果 + 对抗审查记录 + 待拍板选项 + 故意没动的边界）
3. CHANGELOG 回写 + 备份留存路径记录

<!-- public-sync: 2026-10-12 | 脱敏版本 | 源 ~/.workbuddy/skills/harness-model-upgrade-audit -->
