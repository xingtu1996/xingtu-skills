---
name: skill-inbox-triage
description: 跨 Agent 技能建议收件箱双模式：Mode A 分诊拍板落盘（查收件箱/技能拍板/清 inbox）；Mode B 复盘提名建卡（技能复盘/复盘提名）。人审闸门不可旁路：AI 只提名不自我批准。协议唯一权威=PROTOCOL.md。
version: 1.1.0
---

# skill-inbox-triage — 技能建议收件箱分诊

> 定位：跨工具技能复利引擎的人审收口层。提名端（Claude 钩子/千问内置评审/口述"进收件箱"）
> 产建议卡，本技能把卡变成"boss 拍板 → 技能实体 → 多池分发"的闭环。只承载顺序/闸门/凭证；
> 字段与状态机**不在此定义**（唯一权威 `~/.agents/skill-inbox/PROTOCOL.md`）。

## 前置自检（每次运行）

1. `test -f ~/.agents/skill-inbox/PROTOCOL.md || echo "🔴 协议缺失，先恢复基建"`；
2. `python3 ~/.agents/skill-inbox/selfcheck.py` → 畸形卡先报告（只报不改）；
3. （仅 Mode A）无 pending/stale 卡 → 一句话收工："收件箱空，无拍板题"（不许编题刷存在感）；Mode B 不看此条。

## 模式路由

口令含"复盘/发散" → Mode B；含"查收件箱/拍板/处理建议" → Mode A。无 Mode 字样默认 A。

## Mode A · 收敛落盘 Steps

### 1 扫描
读 `cards/*.md` 中 status ∈ {pending, stale}；ts 超 7 天的 pending 就地改 stale（此为状态流转非内容修改，允许）并按 score 降序。

### 2 四池查重（软链感知）
按 PROTOCOL §4 清单比四池；**DUPLICATE/PARTIAL 判定规则引用技能 `cross-repo-skill-curation`（三池模型、DUPLICATE 禁双份造）——先直读其 SKILL.md 再判**，本技能不复述其标准。命中 → 卡 action 转 merge、写 merge 对象实体路径。

### 3 出批（占决策带宽最少的方式）
- 每批 ≤2 题，**A/B 选择题 + 各带默认值与一句话权衡**（推荐项标注理由）；第 3 题起砍掉留到下批，禁开放式；
- 有 AskUserQuestion 类工具用工具，没有就正文列题；
- 卡多时先出 score 高者，批首报"inbox 积压 N 张，本批处理 2"；
- Mode B 产卡通常已带 `## 技能草案`+`## 执行提示词`（PROTOCOL §6）：题目选项直接给"**照草案执行**（提示词内嵌，确认即落盘）"vs"回炉改方向（附一句改什么）"，boss 零再研究成本；钩子卡两节为【待分诊补】时，出题前由当前 agent 先补全草案再出题。

### 4 拍板后落盘（boss 原文逐字回填 `boss_decision`）
- **create/generic**：实体唯一落 `~/.agents/skills/<name>/`（SKILL.md 头加 `<!-- source_card: {id} -->`；正文 grep 不得含任何项目绝对路径/真名/雇主信息——这是 Q1 白名单入池的前提）；
- **create/project:<name>**：落该项目工作区技能池 + 该工作区登记惯例（如 LEDGER/触发表），**绝不进任何全局池**；
- **update**：只 patch 实体（Edit/patch 语义），不建 `-v2` 目录副本；
- **merge**：按 cross-repo-skill-curation 的"只移不删"执行，旧实体入回收站（禁 rm）；
- 分发登记（Q1=A 已拍板，2026-09-16）：generic 实体 → `ln -s ~/.agents/skills/<name> ~/.claude/skills/<name>`；→ 千问池 `~/.qwenworkcn/skills/<name>` **仅当**该技能被要求原生触发或属核心管线时软链（保持白名单克制），且首次建链后用千问侧技能清单查证识别；ZCode/豆包自动可见（原生扫描/路由表）。
- 落 `~/.agents/tools/skill_pool_ledger.py` 重生 `POOL_LEDGER.md` 并核对新行。

### 5 收口
status → done（或 rejected，同样归档）；卡 append 落盘记录（实体路径+链列表+台账行号）；`mv` 卡入 `archive/`；所在工作区有 CHANGELOG 惯例则回写一行（工具身份按各工作区规矩）。

### 6 rejected/merge 不做的也要走
rejected → 回填原因 → archive（防同题重提）；不许静默丢卡。

## Mode B · 发散复盘 Steps（日复盘定时任务同款 playbook；口令"技能复盘/日复盘"亦走此）

### B1 采集（当日信源，只读；有则采、无则跳并记因）
- 在场工作区时间轴：根 AGENTS.md 所在工作区若有 `CHANGELOG.md`，取其**今日行**（跨工具通用惯例，无则跳过）；
- 会话痕迹抽样：`~/.qwenworkcn/logs/sessions/*/segments/*.jsonl` 中 mtime=今日 的文件（取每个会话最后 200 行，扫纠偏/报错-修复/新流程关键词）；Claude 侧钩子提名日志 **`~/.agents/skill-inbox/signal-log.jsonl`**（sediment-signal.py 的唯一落点，看今日行：written/merged/quota_rejected）；
- 收件箱现状：`cards/` 全量 slug+标题（防重复提名，同题走追加）；
- `POOL_LEDGER.md` 告警项（喂给 merge 候选）。

### B2 提炼候选（发散要宽，落纸要严）
每类至多：新流程跑通→create；纠偏/坑未被任何技能承载→create 或 update 既有技能；台账告警→merge/update。单日提名 **≤5 张**（宁缺毋滥，低于阈值的进简报"未提名候选+理由"，不占池界）。

### B3 查重+建卡
按 Mode A 的 §2 四池查重；命中 DUPLICATE 转 merge 提案。建卡遵循 PROTOCOL §6 **六节填满**：`## 技能草案`=可直接落盘的 SKILL.md 全文（或 update 逐条 patch 要点）、`## 执行提示词`=自包含 prompt（含落盘路径+软链分发+台账重生+CHANGELOG 指针，引用文件路径不粘正文）。evidence 一律真实路径（B-009），落笔前 `test -e` 过一遍。

### B4 产出包
建 `autoskills/{YYYY-MM-DD}/00_复盘简报.md`：信源清单｜候选全表（含砍掉的+理由）｜产卡数｜池界余量。超长草案落 `draft-<slug>.md` 并由卡引用。**包不承载状态、不回填拍板结果**（防双写）。

### B5 投递
定时任务语境：一行摘要发约定通知通道（"📥 复盘产卡 N 张（create x/merge y，草案+提示词已备），说『查收件箱』或等晨间日报出题收敛"）；会话语境：直接对 boss 报。钩子卡与 Mode B 卡同池同状态机，**收敛一律走 Mode A**——发散不设人审，收敛必须人审。

## 红线（Pitfalls）

- **不自批**：任何卡未经 boss 原文回填不得 done；
- **不复制协议**：字段/状态机改动只改 PROTOCOL.md（且需 boss 拍板），本文件与其他文档只放指针；
- **提名器配额**≠本技能限额：钩子被 quota_rejected 的信号若 boss 口头提出，正常建卡（标 human_override）；
- 千问池查重必须照查——即使 Q1 未对其分发，防"同名不同义"污染；
- fixture/演示卡一律不得流入 done（首张真实卡见 reference.md 案例）。

## Verification

done 卡四件凭证齐才算完成：①archive 内文件 mtime=当日 ②技能实体存在且 grep 隐私零命中 ③POOL_LEDGER 有对应行 ④boss_decision 非空。缺任一 = 未完成，回报卡点。

<!-- 2026-09-23 常驻体积治理：原 description 下沉到正文（内容未删，仅移出被截断的注入面） -->

## 原 description（存档，不注入上下文）

> 跨 Agent 技能建议收件箱（~/.agents/skill-inbox/）的双模式管线：Mode A 收敛——分诊与拍板落盘， Mode B 发散——技能日复盘提名（产 autoskills 包+带草案/执行提示词的建议卡）。当用户说 "查收件箱/处理技能建议/清 inbox/技能拍板/沉淀待确认/有没有待办的技能建议"（Mode A），或 "技能复盘/日复盘/复盘提名/现在发散一下"（Mode B，定时任务同款 playbook）时使用。 Mode A：扫 pending 卡→四池查重（引用 cross-repo-skill-curation 判重口径）→每批≤2 道带默认值 A/B 题→确认后落实体到 ~/.agents/skills 并分发登记→归档。Mode B：采当日多源信号→候选提炼→ 查重→建卡(草案+提示词填满)→autoskills/{date}/复盘简报→摘要推送。人审闸门不可旁路：AI 只提名 只执行，不自我批准。工作区无关；协议字段唯一权威=PROTOCOL.md（v1.1），本文件不复述。

<!-- public-sync: 2026-10-12 | 脱敏版本 | 源 ~/.agents/skills/skill-inbox-triage -->
