---
name: yuanbao-archive-pipeline
description: 元宝分享内容全流程自动化：本地解密提取 → 水位线增量抓全文 → vault 归档 → 蒸馏入库。触发词：抓元宝/元宝抓取/元宝入库/元宝归档/定时抓元宝/元宝全文抓取/元宝会话盘点。
metadata:
  author: xingtu
  version: "1.1.0"
  created: 2026-09-07
  updated: 2026-11-05
  argument-hint: <无参数，按流程执行>
---

# 元宝归档入库全流程 Skill（行途版）

> 定位：把用户转发给元宝 AI 的微信消息，自动化完成**解密→提取→增量抓取→归档→蒸馏→入库**。
> 原则：**增量不重复**｜**水位线驱动**｜**本地采集 / 处理可上云**｜**故障可追溯**

## 触发条件

- 用户说：抓元宝 / 元宝抓取 / 元宝入库 / 元宝归档 / 定时抓元宝 / 元宝全文抓取 / 元宝会话盘点
- 本地定时任务「元宝会话自动化抓取入库」到时触发（cron `45 7 * * *`，必须本地执行）
- 用户说「盘点一下我跟元宝的沟通」「把元宝分析的内容入库」

## 双阶段分工（2026-11-05 定）

| 阶段 | 能上云 | 做什么 |
|---|---|---|
| **阶段1 采集** | 不能 | 解密微信库 + 提取元宝卡片 → `yuanbao_cards.json` |
| **阶段2 处理** | 能 | 增量抓全文 + 同步 vault + 归档 + 推进水位线 |

上云边界 = 卡片全集是唯一跨环境契约；微信库与密钥（`data/wechat_decrypted/keys.json`）永不上云、永不入库。
可运行的工具版本（去绝对路径、双阶段脚本、README）在 `github/xingtu-tools/yuanbao-pipeline/`（仓库 `xingtu1996/xingtu-tools` 的 `yuanbao-pipeline/` 目录）。

## 核心流程

### Step 1 本地采集

```bash
XT_ROOT=<工作区根> WECHAT_DB_DIR=<微信 db_storage> \
  bash github/xingtu-tools/yuanbao-pipeline/stage1_local_collect.sh
```

- 解密最新微信库 → `data/wechat_decrypted_latest/`（解密前清空旧副本，B-008 修复）
- 提取卡片 → `outputs/yuanbao_inventory/yuanbao_cards.json`
- 密钥：`data/wechat_decrypted/keys.json`；微信库在本地微信容器内（路径按机器不同，用环境变量传）
- 阶段1 不抓全文、不推进水位线

### Step 2 增量抓取（核心，绝不重抓全量）

```bash
XT_ROOT=<工作区根> bash github/xingtu-tools/yuanbao-pipeline/stage2_cloud_process.sh
```

- 读水位线 `github/xingtu-vault/12_工具研究室/yuanbao_inventory/.yuanbao_watermark.json` 的 `last_card_time`
- 只抓分享时间 > `last_card_time` 的卡片全文（伪装微信 UA 直抓，零 token）
- 按日归档 `.../yuanbao_inventory/增量批次/YYYY-MM-DD/`，同时并入 `.../元宝全文抓取/`
- 抓完推进水位线（`last_card_time` / `last_run` / `last_batch` / `last_count`）
- **待抓为 0** 时直接说明「水位线已到最新」，不强行抓取

### Step 3 vault 归档（幂等）

- 阶段2 脚本把增量批次新全文按 vault 命名规范 `元宝分享文章_标题_token.md` 同步到
  `github/xingtu-vault/02_内容仓库 (Content Hub)/06_元宝对话挖掘/`（已存在则跳过）
- 再跑 `ingest_yuanbao_archive.py yuanbao`：追加会话归档、AI 进化时间线、选题池、素材库索引

### Step 4 蒸馏提炼（agent 判断，非脚本）

1. 主题归类（AI 工程化 / 工具实践 / 知识复利 / 商业化 / 技术选型 / 其他）
2. 金句与方法论提炼，价值分级：🥇黄金（可直接成文）/ 🟡关键 / 🟢重点 / ⚪高知
3. 生成 `素材卡_*.md` 落 `素材库/`，登记 `素材库/素材库索引.md`
4. 选题建议登记 `02_内容仓库 (Content Hub)/01_灵感与选题池/`
5. 蒸馏报告落 `.../增量批次/YYYY-MM-DD/_蒸馏报告.md`

### Step 5 反哺简报 + 增量摘要

- 简报落 **vault**：`12_工具研究室/yuanbao_inventory/反哺简报/元宝卡片反哺_YYYY-MM-DD.md`
  （2026-11-05 起从 `outputs/` 迁入仓库：产出要能随 git 上云）
- 内容：采集状态表 / 高价值卡清单（主题 + 反哺落位）/ 建议选题与排期（不扰动现行发布日历）
- 对话内输出增量摘要：新增 X 篇、跳过 Y、失败 Z、水位线 A→B、主题分布、新增素材卡与选题

## 路径真源表（以此为准，旧 `outputs/yuanbao_inventory/...` 口径作废）

| 内容 | 路径 |
|---|---|
| 水位线 | `github/xingtu-vault/12_工具研究室/yuanbao_inventory/.yuanbao_watermark.json` |
| 卡片全集（提取产物） | `outputs/yuanbao_inventory/yuanbao_cards.json` |
| 全量消息 | `outputs/yuanbao_inventory/yuanbao_all_messages.json` |
| 增量批次 | `github/xingtu-vault/12_工具研究室/yuanbao_inventory/增量批次/YYYY-MM-DD/` |
| 全文主仓库 | `github/xingtu-vault/12_工具研究室/yuanbao_inventory/元宝全文抓取/` |
| 反哺简报 | `github/xingtu-vault/12_工具研究室/yuanbao_inventory/反哺简报/` |
| vault 元宝归档 | `github/xingtu-vault/02_内容仓库 (Content Hub)/06_元宝对话挖掘/` |
| 素材卡 / 索引 | `素材库/素材卡_*.md`、`素材库/素材库索引.md` |
| 工具（可独立运行） | `github/xingtu-tools/yuanbao-pipeline/`（stage1/stage2 + bin/） |
| 任务档案 spec | `github/xingtu-vault/03_运营工具箱 (Operations Toolkit)/定时任务档案/yuanbao-archive/spec.md` |
| 注册表镜像条目 | `github/xingtu-automations/registry/AUTOMATIONS.yaml`（slug `yuanbao-archive`，T-01） |

## 水位线与命名

```json
{"last_card_time":"2026-11-05 13:41:11","last_run":"2026-11-05 13:48:02","last_batch":"2026-11-05","last_count":17}
```

- 全文文件 `YYYYMMDD_HHMM_标题_token.md`（时间戳前置，IDE 排序即时间序）
- `_蒸馏报告.md` / `_批次摘要.md` 下划线前置，排在目录最前

## 故障排查

**1. 连续多次「无新增」但确实有新内容（B-008）**
- 查解密产物 `data/wechat_decrypted_latest/message/message_*.db` 的 mtime 是否为最新
- 查根目录是否残留旧 `message_*.db` 副本；查 `yuanbao_full_extract.py` 是否同时扫根目录与 `message/`
- 确认阶段1 解密前清空了旧目录

**2. 解密失败 / 库被 SKIP**
- `keys.json` 覆盖不全：`biz_message_0~4.db` 无对应密钥属**已知缺口**（SKIP 非失败），但 biz 库更新时会漏采

**3. 抓取失败**
- 分享链接须为 `https://yb.tencent.com/wx/ct/f/xxx`；失败多为网络，重试即可

**4. ingest 报「无新增待归档（已全部处理过）」**
- **这不是 bug，是幂等**：阶段3 已先把全文同步进 `06_元宝对话挖掘`，ingest 自然无新增
- 判据：看增量批次篇数与 `06_元宝对话挖掘` md 增量是否对得上，对得上即正常

## 增长验证（每次运行后必做）

1. 卡片总数是否增长？（`yuanbao_cards.json` len）
2. 水位线是否推进？（`.yuanbao_watermark.json` 的 `last_card_time`）
3. 增量篇数 = 增量批次目录新文件数 = `06_元宝对话挖掘` 新增 md 数
4. 连续 2 次无增长 → 按故障 1 排查，不静默放过

## 产物清单（每批）

- [ ] 增量批次全文 + `_批次摘要.md` + `_蒸馏报告.md`
- [ ] 素材卡（高价值内容）+ `素材库索引.md` 追加
- [ ] vault `06_元宝对话挖掘` 同步 + 会话归档/时间线/选题池更新
- [ ] 水位线推进
- [ ] 反哺简报（vault `反哺简报/`）
- [ ] 三仓提交推送：vault（产出）、xingtu-tools（工具改动时）、xingtu-agent-skills（技能改动时）
- [ ] `CHANGELOG.md` 回写

## 关联

- BCI B-008：提取脚本只读旧副本 → 连续 4 天误报「无新增」
- 触发方式：本地定时任务（cron `45 7 * * *`）或用户手动指名
- 任务注册说明见工作区 `rules/AUTOMATIONS.md`；spec 真源在内容仓 `定时任务档案/yuanbao-archive/spec.md`
