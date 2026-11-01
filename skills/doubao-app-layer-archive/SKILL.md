---
name: doubao-app-layer-archive
description: >
  豆包工作（DoubaoWork）应用层全量落档：扫描 3 个 Profile 的 .sessions 目录，
  输出账号使用情况、规划周期（按 ISO 周）、会话清单、技能/工具调用链频次、
  board.md 产物路径与会话绝对路径索引。只收应用层元数据，不做内容挖掘。
  触发词：豆包落档、应用层盘点、会话元数据落档、Profile 盘点、trajectory 统计、
  技能调用链统计、豆包会话全量索引、账号使用情况盘点、.sessions 扫描。
  与 session-distill 划界：本档管元数据/路径/工具调用；session-distill 管会话内容挖掘与选稿。
version: 1.0.0
metadata:
  author: xingtu
  agent_created: true
---

# doubao-app-layer-archive（豆包应用层全量落档）

把散落在 3 个 DoubaoWork Profile 下的 100+ 会话目录，扫成一份可索引的元数据落档。
**只收元数据，不做内容提炼**——内容侧归 `session-distill`。

## 何时用 / 何时不用

**用**：
- boss 说「豆包落档 / 应用层盘点 / 会话元数据落档 / Profile 盘点 / 技能调用链统计」
- 月度/季度复盘需要看账号使用情况、规划周期、工具调用重心迁移
- 需要一份会话绝对路径索引，给后续 session-distill / 内容挖掘当跳转入口
- 新接入机器或迁移前，需要盘点本地豆包数据家底

**不用**：
- 要从某会话里挖选题、提炼素材、做内容蒸馏 → 走 `session-distill`
- xingtu-vault 既有「豆包 166 会话盘点台账」的业务维度维护 → 直接改那份台账，本档只交叉引用
- 单会话内容问答 → 直接读对应 trajectory.jsonl，不用跑全量

## 怎么跑

脚本纯标准库，python3 直接跑，流式逐行读 trajectory.jsonl，不整读大文件。

```bash
# 全量落档（月度/季度跑一次）
python3 /Users/<user>/xingtu/.agents/skills/doubao-app-layer-archive/scripts/scan_sessions.py \
  --full \
  --out-md /Users/<user>/xingtu/.harness/archive/doubao-app-layer/$(date +%Y-%m-%d).md \
  --out-json /Users/<user>/xingtu/.harness/archive/doubao-app-layer/$(date +%Y-%m-%d).json

# 冒烟/抽样（每 Profile 抽 N 个会话，验证脚本或快速看样）
python3 /Users/<user>/xingtu/.agents/skills/doubao-app-layer-archive/scripts/scan_sessions.py \
  --sample 3 \
  --out-md /tmp/sample.md --out-json /tmp/sample.json
```

参数：
- `--full`：全量扫 3 个 Profile 所有会话（约 105 个，578M，流式不爆内存）
- `--sample N`：每个 Profile 抽前 N 个会话（与 `--full` 二选一）
- `--out-md / --out-json`：输出路径（必填）
- `--top N`：全局工具调用 top N（默认 20）
- `--profiles`：自定义 Profile 根目录列表（默认 3 个 DoubaoWork Profile）

## 输出落哪

- 落档 MD：`/Users/<user>/xingtu/.harness/archive/doubao-app-layer/YYYY-MM-DD.md`
- 原始 JSON：同目录同名 `.json`（保留结构化数据，供后续脚本二次加工）
- 模板：`assets/template.md`（人工补注骨架，脚本不写第六节）

## 多久跑一次

- **月度例行**：每月 1 号跑一次全量，覆盖上月规划周期
- **触发式**：大版本升级、换机器、清理附件前跑一次
- **不跑**：日常单会话操作不需要跑；session-distill 挖内容时直接按路径跳

## 落档章节（脚本自动生成一~五，人工补六）

1. **账号使用情况**：每 Profile 会话数/总大小/时间跨度
2. **规划周期**：按 ISO 周聚合新会话数，看工作节奏
3. **技能/工具调用 Top N**：从所有 trajectory.jsonl 流式统计 `assistant.tool_calls[*].function.name`
4. **会话清单**：一行一会话（Profile / session_id / 创建时间 / 大小 / agent 数 / 需求条数 / 主题摘要）
5. **产物与路径索引**：
   - 5.1 board.md 登记的产物路径
   - 5.2 所有会话目录的绝对路径（供后续跳转）
6. **备忘与解读**（人工）：本期观察、异常、候选会话清单交 session-distill、下一步

## 自检清单（跑完必核）

- [ ] MD 一表三行（Profile 1/2/3 各一行），会话数合计 ≈ 105
- [ ] §三工具表非空（空说明 trajectory 解析挂了）
- [ ] §五.2 路径索引条数 = §四会话清单条数
- [ ] 生成的 JSON 能被 `python3 -m json.tool` 正常解析
- [ ] 第六节人工补注已写（哪怕写「本期无异常」）

## 与既有资产的关系

- `session-distill`（`/Users/<user>/xingtu/.agents/skills/session-distill/`）：内容侧，从会话挖选题/素材。本档 §五.2 的路径索引是它的输入入口。
- xingtu-vault「豆包 166 会话盘点台账」：业务维度台账（选题/产出/发布）。本档是技术维度补充，不重复建台账内容，交叉引用即可。
- `.harness/scheduled/AUTOMATIONS.yaml`：若后续要挂定时任务（月度自动跑），在此登记；当前手动触发。

## 数据结构备忘（脚本据此解析，字段变化时改这里）

```
<profile>/.doubaowork/agent_mode/workspace/.sessions/<session_id>/
├── board.md                     # 任务板表格：任务ID|标题|Organizer|状态|产物路径|产物链接
├── memory/MEMORY.md             # 会话记忆（可能为空）
├── attachments/                 # 附件（可能为空）
└── agents/<agent_id>/
    └── system/
        ├── assignment.md        # 头部 Agent ID/Role/Assigned by/Created；body 按 ## [时间戳] 需求 追加
        └── trajectory.jsonl     # JSONL 每行 {role, content, tool_calls?, tool_call_id?, image_link_list?}
                                  # assistant.tool_calls = [{id, type:function, function:{name, arguments}}]
```

## 版本历史

| 日期 | 版本 | 变更 |
|------|:---:|------|
| 2026-11-01 | V1.0 | 新建：流式扫描脚本 + 落档模板 + SKILL；覆盖账号/规划周期/工具调用链/路径索引；与 session-distill 划界 |
