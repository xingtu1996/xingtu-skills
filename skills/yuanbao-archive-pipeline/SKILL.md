---
name: yuanbao-archive-pipeline
description: 元宝分享内容全流程自动化抓取→解密→提取→增量抓取→蒸馏→入库。触发词：抓元宝/元宝抓取/元宝入库/元宝归档/定时抓元宝/元宝全文抓取/元宝会话盘点。适用于用户转发给元宝AI的微信消息的自动化抓取、解析原稿、蒸馏提炼、入库到素材库。
metadata:
  author: xingtu
  version: "1.0.0"
  created: 2026-09-07
  argument-hint: <无参数，按流程执行>
---

# 元宝归档入库全流程 Skill（行途版）

> 定位：把用户转发给元宝 AI 的微信消息，自动化完成**解密→提取→增量抓取→蒸馏→入库**全流程，产物归入素材库供行途自媒体内容创作使用。
> 原则：**增量抓取不重复**｜**水位线驱动**｜**本地零 token**｜**故障可追溯**

## 触发条件

以下任一触发：
- 用户说：抓元宝 / 元宝抓取 / 元宝入库 / 元宝归档 / 定时抓元宝 / 元宝全文抓取 / 元宝会话盘点
- 定时任务「元宝会话自动化抓取入库」到时触发（ID 11622772118274，cron `45 7 * * *`）
- 用户说"盘点一下我跟元宝的沟通"或"把元宝分析的内容入库"

## 核心流程（五步）

### Step 1：全自动解密微信库

```bash
bash tools/wechat_chat_analyzer/run_pipeline.sh
```

- 内部先解密最新微信库到 `data/wechat_decrypted_latest/`
- 再提取元宝卡片到 `outputs/yuanbao_inventory/yuanbao_cards.json`
- **关键**：pipeline 解密前会 `rm -rf "$DECRYPT_DIR"/*` 清空旧副本，确保从原始加密库重新解密（B-008 修复）
- 密钥文件：`data/wechat_decrypted/keys.json`
- 微信原始库路径：`${HOME}/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/<YOUR_WECHAT_DB_DIR>/db_storage`

### Step 2：增量抓取（核心，绝不重复抓全量）

```bash
${HOME}/.workbuddy/binaries/python/envs/default/bin/python tools/yuanbao_incremental_fetch.py
```

- 读取水位线 `outputs/yuanbao_inventory/.yuanbao_watermark.json` 中的 `last_card_time`
- 只抓取分享时间 > `last_card_time` 的新卡片全文
- 产物按时间归档到 `outputs/yuanbao_inventory/增量批次/YYYY-MM-DD/`（每次运行一个文件夹）
- 同时同步进全量主仓库 `outputs/yuanbao_inventory/元宝全文抓取/`
- 抓取完成后自动把水位线推进到本次最新卡片时间
- **若待抓为 0**：直接说明"水位线已到最新，无新增"，不强行抓取

### Step 3：归档入库到 vault

```bash
${HOME}/.workbuddy/binaries/python/envs/default/bin/python tools/wechat_chat_analyzer/ingest_yuanbao_archive.py yuanbao
```

- 把新增全文归档到 `xingtu-vault/02_内容仓库 (Content Hub)/06_元宝对话挖掘/`
- 命名格式：`元宝分享文章_标题_token.md`
- 若脚本报"无新增待归档"（已知疑似 bug），手动用 cp 归档到 vault

### Step 4：蒸馏提炼

对本次新增卡片做：
1. **主题归类**：按 AI工程化/WorkBuddy/知识复利/AI工具/AI商业化/技术工具/其他 等主题分类
2. **金句/方法论提炼**：提取可复用的金句、方法论、框架
3. **价值分级**：🥇黄金（可直接出文章/课程）/ 🟡关键（重要参考）/ 🟢重点（可复用角度）/ ⚪高知（信息储备）
4. **生成素材卡**：高价值内容生成 `素材库/素材卡_*.md`，登记到 `素材库/素材库索引.md`
5. **新增选题**：提炼选题建议，登记到 `xingtu-vault/02_内容仓库 (Content Hub)/01_灵感与选题池/`

蒸馏报告输出到：`outputs/yuanbao_inventory/增量批次/YYYY-MM-DD/_蒸馏报告.md`

### Step 5：输出增量摘要

固定格式：
```
## 本次增量摘要
- 新增 X 篇（跳过 Y 篇，失败 Z 篇）
- 水位线：从 A 推进到 B
- 归档路径：outputs/yuanbao_inventory/增量批次/YYYY-MM-DD/
- 主题分布：主题1 N篇 / 主题2 N篇 / ...
- 新增素材卡：X 张（黄金 Y / 关键 Z / 重点 W）
- 新增选题：T-xxx ~ T-xxx
```

## 关键路径与文件

| 内容 | 路径 |
|------|------|
| 水位线文件 | `outputs/yuanbao_inventory/.yuanbao_watermark.json` |
| 卡片索引 | `outputs/yuanbao_inventory/yuanbao_cards.json` |
| 全量消息 | `outputs/yuanbao_inventory/yuanbao_all_messages.json` |
| 增量批次目录 | `outputs/yuanbao_inventory/增量批次/YYYY-MM-DD/` |
| 全量主仓库 | `outputs/yuanbao_inventory/元宝全文抓取/` |
| 蒸馏报告 | `outputs/yuanbao_inventory/增量批次/YYYY-MM-DD/_蒸馏报告.md` |
| 批次摘要 | `outputs/yuanbao_inventory/增量批次/YYYY-MM-DD/_批次摘要.md` |
| 素材卡输出 | `素材库/素材卡_*.md` |
| 素材库索引 | `素材库/素材库索引.md` |
| vault 元宝归档 | `xingtu-vault/02_内容仓库 (Content Hub)/06_元宝对话挖掘/` |
| vault 选题池 | `xingtu-vault/02_内容仓库 (Content Hub)/01_灵感与选题池/` |
| 解密脚本 | `tools/wechat_chat_analyzer/run_pipeline.sh` |
| 提取脚本 | `tools/wechat_chat_analyzer/yuanbao_full_extract.py` |
| 增量抓取脚本 | `tools/yuanbao_incremental_fetch.py` |
| 归档脚本 | `tools/wechat_chat_analyzer/ingest_yuanbao_archive.py` |

## 水位线机制

```json
{
  "last_card_time": "2026-09-06 23:13:37",
  "last_run": "2026-09-07 09:57:44",
  "last_batch": "2026-09-07",
  "last_count": 39
}
```

- `last_card_time`：上次抓到的最后一张卡片分享时间，增量抓取只抓 > 此时间的卡片
- `last_run`：上次运行时间
- `last_batch`：上次增量批次日期
- `last_count`：上次抓取篇数

## 增量批次命名规范

- 全文文件：`YYYYMMDD_HHMM_标题_token.md`（时间戳前置，IDE 自然排序即时间序）
- 批次目录：`outputs/yuanbao_inventory/增量批次/YYYY-MM-DD/`
- 蒸馏报告：`_蒸馏报告.md`（下划线前置，排在目录最前）
- 批次摘要：`_批次摘要.md`

## 故障排查

### 故障 1：连续多次"无新增"但用户确认有新内容（B-008）
- **现象**：定时任务连续 2 次以上报告"无新增"，水位线不推进
- **排查**：
  1. 检查 `data/wechat_decrypted_latest/message/message_*.db` 的修改时间，确认是最新数据
  2. 检查 `data/wechat_decrypted_latest/` 根目录是否有旧的 `message_*.db` 副本
  3. 检查 `yuanbao_full_extract.py` 第 70 行是否同时 glob 根目录和 `message/` 子目录
  4. 检查 `run_pipeline.sh` 解密前是否有 `rm -rf "$DECRYPT_DIR"/*`
- **修复**：按 B-008 预防 Gate 修复脚本，重新从原始加密库解密

### 故障 2：解密失败
- **排查**：检查密钥文件 `data/wechat_decrypted/keys.json` 是否覆盖所有 message 库
- **修复**：重新获取密钥，更新 keys.json

### 故障 3：抓取失败（网络/链接格式）
- **排查**：检查元宝分享链接格式是否为 `https://yb.tencent.com/wx/ct/f/xxx`
- **修复**：用伪装微信 UA 直抓（本地，零 token）

### 故障 4：归档脚本报"无新增待归档"
- **现象**：`ingest_yuanbao_archive.py yuanbao` 报"无新增待归档条目（已全部处理过）"
- **已知问题**：归档脚本的水位线判断疑似有 bug
- **临时方案**：手动用 cp 把增量批次全文归档到 vault，命名格式 `元宝分享文章_标题_token.md`
- **后续**：单独排查修复归档脚本的水位线逻辑

## 增长验证（每次运行后必做）

1. 卡片总数是否比上次增长？（对比 `yuanbao_cards.json` 的卡片数）
2. 水位线是否推进？（对比 `.yuanbao_watermark.json` 的 `last_card_time`）
3. 若连续 2 次无增长，在输出中明确标注："⚠️ 连续 N 次无增长，请检查提取脚本是否读旧副本（B-008）"
4. 解密后检查 `message/message_*.db` 的修改时间，确认是最新数据

## 产物清单（每次运行）

- [ ] 增量批次全文：`outputs/yuanbao_inventory/增量批次/YYYY-MM-DD/*.md`
- [ ] 批次摘要：`_批次摘要.md`
- [ ] 蒸馏报告：`_蒸馏报告.md`
- [ ] 素材卡：`素材库/素材卡_*.md`（高价值内容）
- [ ] 素材库索引更新：`素材库/素材库索引.md`
- [ ] vault 归档：`xingtu-vault/02_内容仓库 (Content Hub)/06_元宝对话挖掘/`
- [ ] 水位线更新：`.yuanbao_watermark.json`
- [ ] CHANGELOG 回写：`CHANGELOG.md`

## 关联

- BCI 案例 B-008：提取脚本只读旧副本 → 连续 4 天误报"无新增"
- 定时任务 ID：11622772118274（cron `45 7 * * *`）
- 定时任务管控库：`.harness/scheduled/yuanbao-archive/`
- Spec：`.harness/specs/SPEC-20260907-HARNESS-SCHEDULED.md`
- 素材入库流程：AGENTS.md「素材入库流程」章节

<!-- public-sync: 2026-09-27 | 脱敏版本 | 源 .agents/skills/yuanbao-archive-pipeline -->
