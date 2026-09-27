---
name: zcode-session-export
description: 抽取智谱 ZCode（GLM 智能体）本地会话记录并归档为结构化文件。当用户说"导出 ZCode 会话""抓取智谱 session""归档 zcode 本地记录""把 ZCode 的 GLM 会话抽出来""ZCode 的本地会议记录操作一下"时使用。只读解析 ~/.zcode/cli/db/db.sqlite（CLI 侧 18 会话/1022 消息）与 ~/.zcode/v2/tasks-index.sqlite（ADE 图形客户端任务），导出 JSONL+MD 转写与清单看板到 ~/xingtu/data/zcode_sessions/。
---

# ZCode 本地 Session 抽取与归档

把智谱 ZCode 智能体在本地跑的真实会话，抽成可检索、可蒸馏的一手素材。

## 数据落点（只读，切勿改写源库）

- CLI 侧会话库：`~/.zcode/cli/db/db.sqlite`
  - 表：`session`(18 行) / `message`(1022) / `part`(3932) / `tool_usage`(965)
  - 用户原话：`session_input.payload.text`
  - 助手回复：`message`(role=assistant) → 关联 `part`(type=text) 的 `data.text`
  - part 还含 `reasoning`(思考) 与 `model_change`(UI 事件)，抽取时只取正文
- ADE 图形客户端任务库：`~/.zcode/v2/tasks-index.sqlite` → 表 `tasks`(6)

## 执行

直接运行脚本（零依赖，输出到 `~/xingtu/data/zcode_sessions/`）：

```
python3 scripts/export.py
```

输出产物：
- `index.json`：总览（会话数、字数、时间）
- `ade_tasks.json`：ADE 任务清单
- `sessions/<slug>.jsonl`：逐轮 `{"role","text","time"}`
- `sessions/<slug>.md`：可读转写稿
- `zcode_sessions_dashboard.html`：清单看板（点击进转写）

## 注意

- 子智能体系统会话（如"你是行途工作区的对抗审查员"）DB 只存 agent 系统提示词，无可读正文，转写显示"助手0"属正常，非 bug。
- 抽取纯只读，不触碰源库。
- 归档属一手证据（STR-012 最高档），对外使用前须按工作空间纪律脱敏 + 过 `tools/privacy_scan.py`。
