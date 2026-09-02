# XingTu Skills · 专业自述

> 定位：行途开源矩阵的 AI Agent 技能聚合仓，收录 26 个生产级 SKILL.md，一份发布、多工具通用（Claude Code / CodeBuddy / Codex / Cursor / Gemini CLI），find-skills 可检索。

## 1. 这个项目是干什么的（作用）

- **给谁用**：靠 AI Agent 写代码、做调研、跑工作流的工程师——想复用别人踩过坑沉淀下来的"Agent 行为方式"，而不是每个会话重新调教。
- **解决什么问题**：Agent 的能力上限取决于它的行为方式。技能（skill）把"遇到 X 情况应该怎么处理"写成 Agent 可自动检索、按需加载的 SKILL.md，让 Agent 从"泛泛地聪明"变成"在关键场景下按正确方法干活"。
- **核心价值**：
  1. **一套技能，多工具通用**：遵循跨工具事实标准（name + description + when_to_use），Claude Code / CodeBuddy / Codex / Cursor / Gemini CLI 都能用，不绑平台。
  2. **26 个生产级技能**：Caveman 系列（token 压缩，实测省约 65% 输出 token）、Ponytail 系列（极简与债务）、工程实践六件套（先调查、精益构建、安全重构、精准修补、迁移、验证即止）。
  3. **可检索**：`marketplace.json` 提供 26 条索引，find-skills 可语义检索；SKILL.md 的 description 是唯一被自动检索的字段，每个技能都按"[做什么] + Use when 关键词"写。
  4. **行为可塑**：技能改变 Agent 的**处理方式**（如"先调查再动手""验证即止不扩范围"），比单纯给工具更能提升结果质量。
  5. **与 harness 打通**：作为核心子模块被 xingtu-harness 聚合，`install.sh` 一键拉全。

## 2. 在行途 harness 中的定位

- **位置**：执行层（L3）的技能供给端。harness 六层架构里，skills 与 mcps / tools 共同构成"Agent 能干活的能力面"；skills 特指**行为方式能力**——教 Agent 怎么想、怎么做、怎么收尾。
- **协作关系**：

```
             ┌─────────────────────────────────────────────┐
             │  Agent 宿主（Claude Code / Cursor / ...）      │
             │  find-skills 检索 → 读 SKILL.md → 按需加载     │
             └──────────────────┬──────────────────────────┘
                                │
        ┌───────────────────────┴──────────────────────────┐
        │  xingtu-skills（本仓） 26 个技能                    │
        │  Caveman 系列（token 压缩/子代理）                  │
        │  Ponytail 系列（极简/债务审计）                     │
        │  工程实践六件套（调查→构建→重构→修补→迁移→验证）      │
        │  marketplace.json（find-skills 索引）              │
        └───────────────────────┬──────────────────────────┘
                                │
        ┌───────────────────────┴──────────────────────────┐
        │  xingtu-mcps（服务化工具） xingtu-rules（常驻约束）  │
        │  xingtu-hooks（确定性事件钩子）                     │
        └──────────────────────────────────────────────────┘
```

- **与相邻仓的关系**：skills 是"**按需改变行为**"，mcps 是"**给外部工具**"，rules 是"**常驻约束**"，hooks 是"**确定性事件拦截**"——四者触发机制不同：skills 靠 LLM 检索命中，mcps 靠工具调用，rules 靠文件位置加载，hooks 靠宿主在事件时机硬触发。

## 3. 与其他项目的差异与区别

| 对比项 | xingtu-skills | xingtu-rules | xingtu-mcps | xingtu-hooks |
|--------|--------------|--------------|-------------|--------------|
| 能力本质 | 行为方式（方法/流程/判断） | 边界与禁止项 | 外部服务化工具 | 事件驱动的确定逻辑 |
| 触发机制 | LLM 检索 description 后加载（概率性） | 放对目录即加载（确定性） | 宿主侧工具调用 | 宿主在工具调用前后/停止等时机硬触发 |
| 生效范围 | 触发时生效，用完即止 | 常驻，作用于所有/特定上下文 | 挂载即常驻的工具集 | 绑定的生命周期事件 |
| 能否产生副作用 | 通常不直接做外部副作用，靠 Agent 执行 | 不产生，纯约束 | 直接读写外部系统 | 可拦截/改写/放行 |
| 何时选它 | 想让 Agent "在合适场景用对方法" | 想让 Agent "一直守规矩" | 想让 Agent "能真正操作外部系统" | 想在特定时机强制插入/阻断逻辑 |

一句话：**skills 给"怎么做"，rules 给"不能做什么"，mcps 给"能操作什么"，hooks 给"什么时候强制做什么"**。Caveman/Ponytail 系列这类"行为模式类"技能，本质是把它从 prompt 口头叮嘱升级为可检索、可复用、可版本化的资产——这正是本仓区别于其它仓的核心。

## 4. 在 Agent 体系中的应用

### 4.1 Work Agent（业务/内容工作流）

- **作用方法**：用 Caveman 系技能压缩沟通与输出（省 token、省上下文）、用 investigate-first 做调研、用 verify-and-stop 做交付前收敛——把"怎么干活"标准化，而不是每次靠口头要求。
- **触发方法**：显式命令（如 `/caveman`、`/ponytail`）或自然语言关键词（"省 token""be lazy"）；也可由 marketplace.json + find-skills 被自动检索到。
- **典型场景**：长会话省 token 保持上下文、调研类任务先调查后下结论、内容交付前只验证不扩范围、把 Agent 工作流按 Caveman 模式委派给子代理以压缩回灌上下文。

### 4.2 Coding Agent（编码 Agent，如 Claude Code）

- **作用方法**：Caveman 系（commit 压缩、代码审查压缩、仓库探索由 haiku 子代理只读执行）、Ponytail 系（防过度工程、债务审计）、工程实践系（surgical-patch 精准修补、safe-refactor 行为保持重构、migration 兼容性迁移、lean-build 精益构建、verify-and-stop 验证即止）。
- **触发方法**：`claude` 装进 `~/.claude/skills/` 或项目 `.claude/skills/` 后，Agent 按任务情境自动检索加载；部分技能（如 caveman-explore）由主线程委派给低成本子代理执行，结果压缩后回灌，主上下文占用更小。
- **典型场景**：提交信息与 PR 评论降噪、跨文件定位代码（子代理并行探索）、重构前先定行为保持边界、修复 bug 只动最小层、迁移前先定义回滚路径、验收通过立即收手。

## 5. 升级方法与迭代开发

- **新增技能**：从 `skills/_TEMPLATE` 复制，写 SKILL.md（frontmatter 必填 name + description），再同步 `marketplace.json` 索引。
- **质量门禁**：
  - description 必须按"[做什么] + Use when 关键词"公式写——它是唯一被自动检索的字段，写不准等于技能不存在。
  - 技能要被真实任务验证过：执行结果可复现、副作用可控、不破坏既有行为。
  - 保持单一职责：一个 SKILL.md 只做一件事，避免"全能技能"稀释检索命中率。
- **演进路径**：从真实项目的"踩坑→方法"蒸馏新技能；系列内做收敛（Caveman/Ponytail 各有 help 速查卡，防止技能膨胀）；每版本核对 marketplace.json 与 skills/ 目录一致。
- **当前状态**：26 个技能 + marketplace.json 已入库，属四个仓中完成度最高者；后续按场景补充与跨工具兼容性测试是主方向。

## 6. 基础概念

- **Agent Skills（技能）**：一个目录 + SKILL.md，描述 Agent 在什么场景采用什么方法的可复用能力单元，由 LLM 按需加载。为什么重要：技能是"把行为方式版本化"的最小单元，是 prompt 工程的下一个进化形态。
- **SKILL.md**：技能的主文件，头部 YAML frontmatter（name / description 等）是机器检索的依据，正文是给 Agent 的指令。
- **frontmatter（name / description）**：技能元数据，description 唯一承担"被检索命中"的职责——它是技能能否在正确时机被调起的胜负手。
- **find-skills**：按语义检索技能的搜索工具，配合 marketplace.json 让技能被"发现"，而不是靠人记名字。
- **触发机制**：显式（用户命令 / 关键词）与隐式（LLM 按任务情境自动检索加载）。为什么重要：理解触发机制，才能设计出"该被触发时不缺席、不该触发时不打扰"的技能。
- **子代理委派（subagent delegation）**：把探索/构建/审查拆给专用子代理，主线程只收结果。为什么重要：隔离上下文、并行提效；配合压缩输出（如 caveman-explore），主上下文占用大幅下降。
- **上下文压缩（context compression）**：在长会话里用极简表达保留全部技术实质、只丢废话，延长主上下文可用时长。为什么重要：上下文窗口是硬约束，压缩即提效。
- **YAGNI（You Aren't Gonna Need It）与技术债（technical debt）**：Ponytail 系列的两大支点——不预先做用不到的东西；已存在的过度设计用债务台账记下来、按优先级偿还。

## 7. 专业背书

- **Agent Skills 规范**：Anthropic 于 2025 年 10 月开源 Agent Skills 规范（SKILL.md + frontmatter + 可选脚本/子代理），随后被 OpenAI Codex、Cursor、Gemini CLI 等跨工具采纳，成为跨平台事实标准。本仓的 SKILL.md 结构、frontmatter 公式、marketplace.json 索引与其完全对齐。
- **Caveman 系列的 token 压缩**呼应 Anthropic 官方 Context Engineering 实践（上下文压缩、prompt caching 的"省 token 提效"方向），压缩输出子代理（cavecrew / caveman-explore）呼应 Anthropic "Building effective agents" 中关于 subagent 委派与隔离上下文的建议。
- **工程实践六件套**（investigate-first / lean-build / safe-refactor / surgical-patch / migration / verify-and-stop）分别对应软件工程与 AI 工程公认实践：证据驱动排查、YAGNI、行为保持重构、最小修复、expand-contract 迁移、验收即停——均可在 TDD / 重构（如 Fowler 的重构原则）与业界 Agent 编码最佳实践中找到依据。
- **Ponytail 系列**与 YAGNI / 最简可行方案（MVP 精神）一致，债务审计呼应业界 technical debt 治理方法论。
