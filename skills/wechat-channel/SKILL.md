---
name: wechat-channel
description: 本地微信通道（行途）——读取、萃取、蒸馏、获取本地微信消息，支持按联系人或群（wxid 定位），支持按名字/关键词反查 wxid。触发词：微信通道、读微信、微信消息、微信萃取、微信蒸馏、微信抓取、查微信聊天、导出聊天记录、微信会话盘点、搜微信、wechat channel。适用于任何 Agent 需要读取本地微信指定会话（联系人/群）的聊天内容、萃取原稿、AI 蒸馏提炼、或增量抓取转发给元宝的分享全文。数据全部来自本地已解密微信库，不联网（仅蒸馏时调用 AI）。
---

# 微信通道（wechat-channel）

> 定位：把本地微信变成任意 Agent 可调用的数据通道——**读取 / 萃取 / 蒸馏 / 获取**，支持按联系人/群精确定位。
> 原则：**复用行途既有工具链，不重写**｜**本地零 token**｜**增量不重复**｜**路径以 references/paths.md 为准**。

## 快速开始

```bash
PY=${HOME}/.workbuddy/binaries/python/envs/default/bin/python
WC=${HOME}/.agents/skills/wechat-channel/scripts/wechat_channel.py

# 0) 只记得名字/群名/某句话？用 search 反查 wxid（最常用的入口）
$PY $WC search 某同事              # 搜联系人
$PY $WC search 张硕 硕哥         # 多关键词 OR
$PY $WC search "AI Work"         # 搜群名
$PY $WC search "<PROJECT>" --top 10   # 搜项目关键词

# 1) 枚举所有会话（拿到 wxid + 消息数 + 最近时间）
$PY $WC list

# 2) 读取指定会话（wxid 或自定义微信号，如 custom_id_example1 / custom_id_example2）
$PY $WC read wxid_xxxxxxxxxxxx
$PY $WC read custom_id_example1 --limit 50

# 3) 萃取完整原稿（Markdown + CSV + JSON）
$PY $WC extract custom_id_example1 -o ~/xingtu/outputs/wechat_channel

# 4) AI 蒸馏（分支总结 → 主题/金句提炼）
$PY $WC distill wxid_xxxxxxxxxxxx --model deepseek-v4-pro

# 5) 获取：元宝分享全文增量抓取 + 归档入库（水位线驱动）
$PY $WC fetch

# 6) 重新解密最新微信库（消息滞后时用）
$PY $WC decrypt
```

## 能力与用法

### list — 枚举会话
- 输出所有有消息的会话：`消息数 / 最近消息时间 / wxid（会话ID）`，按消息数降序。
- **会话定位一律用 wxid**（单聊与群都是，群形如 `xxx@chatroom`）。
- 附带"可见名字"清单（来自 FTS 索引，仅展示、无 wxid 映射）。

### search — 按名字/关键词反查 wxid（最常用入口）
- `search <关键词1> [关键词2 ...] [--top N]`，多关键词为 OR 逻辑。
- 跨所有消息表搜索（自动 zstd 解压），返回命中的会话：`命中数 / 最近消息 / wxid / 单聊or群 / 命中样例`。
- **典型场景**：用户只给备注名（"某同事别名"）、群名（"AI Work"）、或某句话，不知道 wxid 时，先用 search 定位，再用 read/extract/distill 操作。
- **样例即证据**：输出包含命中的消息片段，可直接确认身份（如群消息里 `custom_id_example1: 项目：某同事(广州)` 即证明 custom_id_example1 是某同事）。
- 搜索遍历全库，耗时约 30-60 秒；命中为 0 时换关键词或先 `decrypt` 更新库。

### read — 读取
- `read <wxid> [--since YYYY-MM-DD] [--limit N] [-o <输出根>]`
- `<wxid>` 支持三种格式：`wxid_xxx`（系统ID）、自定义微信号（如 `custom_id_example1`、`custom_id_example2`）、`xxx@chatroom`（群）。自定义微信号会先试读消息表确认，有消息即视为有效。
- 导出 Markdown + CSV（`outputs/wechat_channel/<wxid>/read_<时间戳>/`）。
- `--limit N` 取最近 N 条；`--since` 从指定日期起。

### extract — 萃取
- `extract <wxid> [-o <输出根>]`
- 导出完整原稿三件套（Markdown + CSV + JSON），供二次处理/入库。

### distill — 蒸馏
- `distill <wxid> [--model <模型>] [--gap <分钟>] [--max-msgs <条数>] [--mock] [--dry-run]`
- 内部：导出 CSV → `wechat_summary.py --input <csv>`（按时间/话题切分支 → AI 逐分支摘要 → 汇总报告 HTML+MD）。
- 蒸馏完成后按 `references/distill-standards.md` 做主题归类、金句提炼、价值分级（🥇/🔴/🟡/🟢）并落素材库。
- `--mock` 不调真实 LLM，仅验证格式；AI 配置支持 `WORKBUDDY_API_KEY` 环境变量。

### fetch — 获取（元宝全文）
- `fetch`：运行元宝增量抓取管道（解密→提取卡片→水位线增量抓全文→归档→入库）。
- 增量逻辑：只抓分享时间 > `.yuanbao_watermark.json` 中 `last_card_time` 的新卡片；无新增时如实说明，不强抓。
- 产物：`outputs/yuanbao_inventory/增量批次/YYYY-MM-DD/` + 全量主仓库 + 蒸馏报告。

### decrypt — 重解密
- `decrypt`：用已有密钥把最新微信库解到 `data/wechat_decrypted_latest/`（清旧副本后全量重解）。
- 平时无需手动跑；read/extract/distill 自动使用现有解密库。**注意**：全量重解密会新增数百 MB 磁盘占用（当前磁盘紧张时慎用）；消息滞后时优先确认微信是否已同步。

## 会话定位（指定聊天人 / 群）

**标准流程：search → 确认 wxid → read/extract/distill**

1. 用户给名字/群名/关键词 → `search <关键词>` 反查，从命中样例确认身份和 wxid。
2. 用户直接给 wxid → 跳过 search，直接 `read/extract/distill <wxid>`。
3. wxid 三种格式都支持：`wxid_xxx`（系统ID）、自定义微信号（`custom_id_example1` 等）、`xxx@chatroom`（群）。
4. 若 search 无命中：换同义词/简称（如"某同事别名"也可搜"另一别名""<PROJECT> PM"）；或确认消息是否在解密库时间范围内（见数据新鲜度自检）。
5. 当前解密库缺 `contact.db`（密钥未覆盖），无法直接"昵称→wxid"查表；search 是不依赖 contact.db 的可靠替代方案。

## 自然语言意图编排（Agent 自动执行）

用户通常不会说"运行 extract 子命令"，而是说自然语言。Agent 应按以下映射自动编排，无需用户手动敲命令。

| 用户意图（示例） | 自动编排流程 |
|-----------------|-------------|
| "看看某同事最近聊了什么" / "某同事最新消息" | `search 某同事` → 确认 wxid → `read <wxid> --limit 50` → 直接在回复中摘要 |
| "张硕那边项目有啥进展" / "张硕最新项目动向" | `search 张硕` → `read <wxid> --limit 100` → 按项目/时间线提炼进展 |
| "AI Work 群今天聊了啥" / "群聊总结" | `search "AI Work"` → `read <wxid> --since 今天` → 按话题聚类总结 |
| "把我和郭总的聊天全部导出" | `search 郭总` → `extract <wxid> -o <目录>` → 告知产物路径 |
| "蒸馏一下元宝的对话" / "提炼金句" | `distill wxid_xxxxxxxxxxxx` → 按 distill-standards 分级落素材库 |
| "微信里搜一下<PROJECT>相关的" | `search <PROJECT> --top 10` → 列出命中会话，等用户指定再深入 |
| "有谁找我" / "未读消息摘要" | `list --top 20` → 按最近消息时间排序，标注需要回复的会话 |

**编排铁律**：
1. 用户给名字时**必须先 search**，不要猜 wxid；search 样例确认身份后再 read/extract。
2. 只是"看看/聊聊/摘要"类意图用 `read --limit`（轻量），"导出/备份/全量"类意图用 `extract`（完整三件套）。
3. read 结果直接在回复中结构化摘要（按时间/话题/项目），不需要把原始 MD 全贴出来。
4. 涉及多个人/群时，逐个 search 确认后并行 read，最后合并摘要。

## 数据新鲜度自检

- `list` 的"最近消息"列即为解密库数据时间。若明显早于当前日期：
  1. 确认微信客户端已同步新消息；
  2. `decrypt` 重新解密（前提：磁盘余量充足）。
- 元宝水位线（`.yuanbao_watermark.json`）与解密库独立：fetch 抓全文按水位线走。

## 铁律

1. **不重写**：微信读取/解析复用 `yuanbao_full_extract.extract`（zstd + appmsg XML + 跨库去重），不手写 SQL 猜表结构（4.x 表名按会话 hash 变动）。
2. **本地优先**：解密、提取、读取零 token、零联网；只有 distill 才调用 AI。
3. **增量不重复**：fetch 走水位线；蒸馏/入库按"追加式不覆盖"。
4. **脱敏**：涉及当前雇主/薪资/隐私按用户偏好模糊化后才对外使用。
5. **只读真相源**：不修改 `~/Library/Containers/.../xinWeChat` 原始库；解密库可重建。

## 故障排查

| 症状 | 处理 |
|------|------|
| 只知道名字/群名，不知道 wxid | 用 `search <关键词>` 反查，从命中样例确认身份 |
| search 无命中 | 换同义词/简称；确认消息是否在解密库时间范围内（先 `list` 看最近消息时间） |
| read/extract 报"不是 wxid 且未找到" | 先用 `search` 反查；自定义微信号（非 wxid_ 开头）会自动试读确认 |
| 消息滞后（读不到新消息） | 确认微信已同步 → `decrypt`（注意磁盘余量） |
| distill 报"未找到任何消息" | 确认走的是 CSV 输入（脚本已内置）；检查导出文件非空 |
| distill 调 AI 失败 | 网络/API key（`WORKBUDDY_API_KEY`）；`--mock` 验证格式 |
| fetch 连续"无新增"但实际有新内容 | 参考 B-008：确认解密库最新、`yuanbao_full_extract.py` 同时 glob 根目录与 `message/` 子目录 |
| 归档脚本报"无新增待归档" | 已知疑似 bug：手动 `cp` 增量批次到 vault 归档目录 |

## 关联

- 路径与工具详情：`references/paths.md`
- 蒸馏与入库标准：`references/distill-standards.md`
- 上游 Skill：`yuanbao-archive-pipeline`（元宝抓取全流程）、`xingtu-ingest`（素材入库总控）
- 定时任务：元宝会话自动化抓取入库（ID 11622772118274，cron `45 7 * * *`）

<!-- public-sync: 2026-09-27 | 脱敏版本 | 源 .agents/skills/wechat-channel -->
