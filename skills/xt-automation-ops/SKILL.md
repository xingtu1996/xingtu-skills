---
name: xt-automation-ops
description: "行途 XingTu 空间定时任务/自动化的创建、排查、盘点 SOP——cwd 纪律、接口层入口、留痕、规模告警、SAF-010 脱敏闸"
version: 1.0.0
---

# xt-automation-ops — 行途 XingTu 定时任务运维 SOP

触发词：定时任务、自动化、automation、每日同步、盘点任务、新建任务、任务调度、LaunchAgent、jobapi、每日 08:00。

**唯一事实源：`~/xingtu/rules/AUTOMATIONS.md`**（任务卡片 + 完整铁律）。本 skill 是操作路由，详情回读台账。

## 0. 先读再动

1. 读 `rules/AUTOMATIONS.md` 确认现有任务，**优先 update 已有 automation，不建重复**。
2. 结构性改动前先 `bash tools/safety/backup-before-op.sh '<描述>' <路径...>`。

## 1. 新建/修改 automation 铁律（违反必翻车）

| # | 铁律 | 动因 |
|---|------|------|
| 1 | **cwd 显式 = `~/xingtu`** | 新建默认指向孤儿目录 `~/工作室/xingtu`（双目录事故，飞轮读过 5.6KB 损坏素材库半个月） |
| 2 | 入口统一 `python3 tools/xt_job_api.py --run <job>` | 接口层自动留痕 `tools/xt_runs.jsonl`；直调底层脚本无痕迹 |
| 3 | prompt 自包含四段：路径纪律 / 成功标准 / 失败处理 / 规模告警 | 未来运行看不到当前会话 |
| 4 | 规模告警：素材卡约 1466（查 xt_runs.jsonl 最新值），±30% 即停止报告 | 防读残留目录/损坏副本 |
| 5 | 禁绕过同步脚本直接写资料库表（SAF-010 中央脱敏闸）；脱敏/归一**前置到建 key 之前** | 幂等第四坑：脱敏标题塌缩同 key 重复灌行 12 条 |
| 6 | 失败处理：exit≠0 → 读 xt_runs.jsonl 定位 → 排查一次+重试一次 → 仍失败**停止报告，禁止反复重试** | 防静默放大 |
| 7 | 接口层只绑 127.0.0.1:8731，不改 0.0.0.0 | 本地私有接口 |
| 8 | 完工三件套：automation 本体 + 台账登记 + CHANGELOG 回写 | 不回写 = 变更未发生 |

## 2. 常用操作

- **手动跑每日全量**：`python3 ~/xingtu/tools/xt_job_api.py --run daily`
- **单步**：`--run sync`（灌 5 表）/ `--run materials`（素材抓取）/ `--run analyze`（一键分析）
- **查最近执行**：`tail -5 ~/xingtu/tools/xt_runs.jsonl`
- **查服务存活**：`curl -s -m 3 http://127.0.0.1:8731/ -o /dev/null -w "%{http_code}"`（200 = 在线）
- **HTTP 控制台**：`outputs/行途 XingTu 本地控制台.html` 或 http://127.0.0.1:8731/

## 3. LaunchAgent（jobapi 常驻）

- plist：`~/Library/LaunchAgents/com.xingtu.jobapi.plist`
- 🔴 **沙箱内 `launchctl load` 必失败（error 5）**——不要重试，请 boss 在终端亲自执行：
  `launchctl load -w ~/Library/LaunchAgents/com.xingtu.jobapi.plist`
- 未加载的降级：`python3 tools/xt_job_api.py &`（手动起进程）

## 4. 排查路由

| 症状 | 先查 |
|------|------|
| 每日同步没跑 | automation 状态/cwd → `xt_runs.jsonl` 有无当日记录 |
| 灌表重复行 | 是否脱敏/归一在建 key 之后（铁律 5） |
| 控制台按钮无响应 | 8731 端口存活？jobapi 进程在否 |
| 数据明显偏少/偏多 | 素材卡数 vs 最新基线（±30% 告警），疑似读到 `~/工作室/xingtu` 残留 |

## 5. 反模式

- ❌ 建 automation 不改 cwd（默认即错）
- ❌ 直调 `workbench_sync.py` 等底层脚本（无留痕、绕过脱敏闸）
- ❌ 失败后循环重试（放大错误写入）
- ❌ 一个逻辑任务拆成多个 automation（同日多时刻用单条 rrule 表达）

<!-- public-sync: 2026-10-12 | 脱敏版本 | 源 ~/.workbuddy/skills/xt-automation-ops -->
