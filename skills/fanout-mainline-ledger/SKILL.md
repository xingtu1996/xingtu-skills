---
name: fanout-mainline-ledger
name_en: Fanout Mainline Ledger
name_zh: 并行主线台账
description: Keep ONE mainline ledger for parallel work: register each fanout (task/artifact/eta), reconcile on collect, alert on silent loss. Use when: dispatching 2+ parallel agents/background tasks, or reporting current mainline progress. Prefer single-session parallelism.
description_en: Keep ONE mainline ledger whenever work is fanned out to parallel sub-agents or background tasks, so the orchestrator can always answer "what is the mainline now" without session memory. Register each fanout, reconcile on collect, alert on silent loss or timeout, prefer single-session parallelism. Use when dispatching 2+ parallel agents/tasks or when the user asks for the current mainline across parallel work.
description_zh: 把活 fanout 给并行子 agent/后台任务时维护**单一主线台账**，让编排者不靠会话记忆也能随时回答"主线现在到哪了"。每路 fanout 登记（谁/干什么/产物路径/预计回收），回收即核销，静默丢失或超时告警；优先单会话并行而非多开会话。当派发 ≥2 路并行、或用户问"并行主线/进度/有没有丢任务"时触发。
argument-hint: Describe the parallel fanout plan or ask for the current mainline status
argument-hint-en: Describe the parallel fanout plan or ask for the current mainline status
argument-hint-zh: 描述并行派发计划，或询问当前主线状态
user-invocable: true
version: 1.0.0
---
<!-- source_card: 20260916-2133-qwenwork-fanout-mainline-ledger -->

# 并行主线台账（fanout-mainline-ledger）

> 目的：并行编排最常见的失败不是"做错了"，是**主线不可追溯**——子任务静默丢失、上下文跨会话衰减、决策人随时掉线后问不出"现在在解决什么问题"。本技能用一张台账把主线钉死。

## 何时用

- 一次派发 ≥2 路子 agent / 后台任务（fanout）。
- 用户问"主线现在啥样 / 你在解决什么问题 / 有没有任务丢了"。
- 并行队列出现静默失败、超时、或回收时产物对不上。

## 台账位置与格式（单一事实源）

- 落在**当前工作区**一个固定文件：`MAINLINE_LEDGER.md`（无则建；已有则 append，禁重建覆盖）。
- 每路 fanout 一行，字段固定：

```
| id | 派出时间 | owner(子agent/后台) | 任务一句话 | 产物路径(预期) | 状态 | 回收时间 | 备注 |
```

- 状态机：`派出 → 回收(核销) / 丢失(告警) / 挂起(等人)`。**只允许这四种**，禁模糊词。

## 四条硬规则

1. **fanout 前先登记**：没写进台账的路不许派出去（派出去=不可追溯）。
2. **回收即核销**：子任务回来，立刻把状态改`回收`+填产物路径+回收时间；**产物要用磁盘核验**（ls/读回），不认子任务自述。
3. **静默丢失/超时告警**：超过预计回收时间仍`派出`的路，主动标`丢失`并向决策人报一行（哪路/干什么/最后已知状态），**不假装还在跑**。
4. **单会话并行优先**：能在一个会话内并行（并行工具调用/子代理）就不另开会话；跨会话只在确需长后台时用，且交接物必须是自包含提示词（见 spec-driven-adversarial-workflow Step 5）。

## 回答"主线现在啥样"

只从台账答，三句话以内：① 当前在解决什么问题（主线一句话）② 几路在跑/几路已回收/几路丢失 ③ 下一步。**不翻会话历史、不靠记忆**——台账是唯一事实源。

## 红线

- 台账不写项目机密/真名/雇主信息（它是跨工具共享的薄账本）。
- 不删历史行（append-only）；丢失行保留作复盘证据。
- 台账≠执行日志：执行日志记过程细节，台账只记"路"的生命周期，两者指针互引不复制内容。

<!-- 2026-09-23 常驻体积治理：原 description 下沉到正文（内容未删，仅移出被截断的注入面） -->

## 原 description（存档，不注入上下文）

Keep ONE mainline ledger whenever work is fanned out to parallel sub-agents or background tasks, so the orchestrator can always answer "what is the mainline now" without session memory. Register each fanout (owner/task/artifact path/eta), reconcile on collect, alert on silent loss or timeout, and prefer single-session parallelism over many sessions. Use when dispatching 2+ parallel agents/tasks, when the user asks for current mainline/progress across parallel work, or when parallel queues risk silent loss or context decay.

<!-- public-sync: 2026-10-12 | 脱敏版本 | 源 ~/.agents/skills/fanout-mainline-ledger -->
