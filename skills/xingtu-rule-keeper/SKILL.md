---
name: xingtu-rule-keeper
description: 行途规则管家——规则体系的「管理者」（不是又一份规则副本）。当需要①查询某项任务要守哪些规则（写稿/选题/封面/发布/复盘/数据/品牌/变现）②给规则体系做一致性体检（计数漂移、ID 孤儿悬空、档期事实源指针、冻结口径、手册状态、skill 违规复制正文）③新增/修改一条编号规则并要求分册/索引/计数/CHANGELOG 一次改齐时使用。触发词：规则体检、规则lint、规则查询、我要守哪些规则、加规则、新增规则、规则漂移、规则一致性、rule-keeper。注意：规则正文 SSoT 永远在 rules/RULES.d，本 skill 只实时抽取、检查、编排，绝不复制正文。
---

# xingtu-rule-keeper · 规则管家

> 定位：规则体系的**管理者**。其他 skill（content-craft / writing-guidelines 等）是规则的**消费者**；本 skill 保证规则体系自身「可查、一致、改不漏」。
> 铁律：**规则正文只存在于 `rules/RULES.d/`，本 skill 不缓存、不复制正文**（复制 = 第二份 SSoT = 漂移源，参见 BCI 示例句扩散事故）。

## 何时用哪个脚本（都在 `tools/rule_keeper/`）

| 意图 | 命令 |
|---|---|
| 我这个任务要守哪些规则 | `python3 tools/rule_keeper/rule_query.py --task writing`（先 `--list` 看全部任务类型） |
| 查单条规则（自动带补丁） | `python3 tools/rule_keeper/rule_query.py --task PUB-029` |
| 规则体系体检（改完规则/开工前/怀疑漂移时） | `python3 tools/rule_keeper/rule_lint.py`（`--json` 结构化；`--md 报告.md` 落盘） |
| 新增一条规则（四联动一次改齐） | 先 dry-run：`rule_add.py --family PUB --text "…" --severity 高 --source "动因" --label "速查标签"`，确认后加 `--apply` |
| 给已有规则加补丁 | `rule_add.py --patch-to PUB-029 …`（补丁号自动 -补/-补2） |

## 三种使用场景的标准动作

### 场景 1：开工要规则（替代「自己翻 RULES.md 再翻分册」两步）
1. `rule_query.py --list` 确认任务类型；
2. `--task <类型>` 拿到**实时抽取**的最小规则集，直接据此执行；
3. 不要把输出另存成新文件——每次现抽，规则更新后自动是最新。

任务映射（SSoT = `rules/RULES.md §二`，改映射改 rule_query 顶部 TASK_MAP）：
writing 写稿=约定+SAF+PUB ｜ topic 选题 ｜ cover 封面排版 ｜ publish 发布分发 ｜ review 复盘调研 ｜ data 数据结论 ｜ brand 品牌人设 ｜ money 变现 ｜ light 轻任务。

### 场景 2：规则体检（六类检查，P0 必清零才可继续）
- **L1 ID 闭环**：分册 ↔ RULES.md §三速查，孤儿/悬空即 P0。
- **L2 计数一致**：§一总表 / §三标题 / 分册实际主编号三处对齐。
- **L3 事实源指针**：档期日历唯一事实源 = vault `00_全局发布日历`（约定16），指 outputs 旧日历即 P0。
- **L4 冻结口径**：`frozen_terms.txt` × 待发布 `正文_v*.md`，命中即 P1（成长线等已冻结叙事不得复发）。
- **L5 手册状态**：vault `02_排版与设计/` 规范手册类文件头部须有现行/冻结/作废/版本声明，否则 P2。
- **L6 违规复制正文**：skill 内嵌 ≥6 条规则 ID 且含规则正文特征 → P2，提示改为向 rule_query 实时抽取。
- 退出码：有 P0 = 1（可接 CI / 发布前 gate）。

### 场景 3：加/改规则（防漂移闭环，对应约定 15）
1. 规则类变更属「自进化内容」，免逐条确认，但必须：先备份 → 写分册（ID 递增）→ 回 RULES.md §三速查 + §一计数 → 回写 CHANGELOG。
2. `rule_add.py` 把这四步做成一条命令：**默认 dry-run**，逐处打印 old→new；`--apply` 才落盘（自动 tar 备份 `.backups/`、自动回写 CHANGELOG、落盘后自跑 lint 自证）。
3. 每个定位串必须**唯一匹配**，匹配 0 或多处会中止，不写任何文件（防弹）。
4. 边界：`约定` 册是有序列表、结构不同，**不自动改**（脚本会提示手动维护）；规则的业务内容增删仍需人判断，工具只保证「动作不漏项」。

## 维护说明
- 冻结词表：`tools/rule_keeper/frozen_terms.txt`（一行一词，# 注释）；新增/解除冻结都改这里并回写 CHANGELOG。
- 新增任务类型路由：改 `rule_query.py` 顶部 `TASK_MAP / TASK_DESC`。
- 新增检查类别：在 `rule_lint.py` 加 `check_lX` 并挂进 `run()`，级别只取 P0/P1/P2。
- 实体在项目 `.agents/skills/xingtu-rule-keeper/`，`.workbuddy/skills/` 为软链；不进全局 `~/.agents/skills`（行途专用）。
