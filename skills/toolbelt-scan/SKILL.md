---
name: toolbelt-scan
description: 云中立工具带盘点：枚举本机所有 AI 工具（~25 签名：Claude Code/Codex/Gemini/Grok/WorkBuddy/CodeBuddy/ZCode/DSH/豆包/千问/Cursor/Trae/Qoder/Lingma/Junie/OpenCode…），统计数据量/技能安装/会话/最后活跃，检测跨工具同名技能版本漂移与僵尸技能，产出 JSON 台账 + 单文件 HTML 看板。当用户说「盘点 AI 工具/工具带/全机 AI 资产/我装了多少 AI 工具/哪些技能重复装了/技能版本漂移」时触发。只读不改；输出聚合数字+路径泛化，过 30 词红线表才落盘。
version: 1.0.0
---

# 云中立工具带盘点（toolbelt-scan）

> **定位**：agent 中立（不绑定任何云/厂商/工具）的落地技能——把散在本机各 AI 工具里的
> 资产盘成一本地账。每周产出落私有金库 `xingtu-vault` 的 `定时任务产出/`（黄金仓），
> 由既有 relay 通道push；跨工具版本漂移检测是核心运维价值（23 个技能存在漂移）。

## 红线（硬编码，不可旁路）

1. **只读**：任何工具目录只 ls/du/count，不写不删不改。
2. **敏感目录只报存在**：凭据类目录（脚本内置敏感模式：cert / credential / .aws / .copilot / .ssh 等）
   输出仅记「存在」，不列内容；`auth.json` / `*.key` / `*.pem` / `*token*` / `*secret*` 文件名禁入输出。
3. **输出脱敏**：绝对路径一律泛化（`/Users/<user>/` → `~/`）；红线技能名与目录名
   **只计数不列名**；输出过脱敏门禁才落盘——内置结构模式（个人绝对路径/手机号/wxid/邮箱）
   + 外挂词表（`--redline-file`，身份/雇主代号类，**工作区私有件**；公开仓不含词表本身，
   防「列禁词=泄词」自指）。
4. **会话正文禁读**：只统计数量/大小/时间；正文挖掘归 `ai-session-material-miner`，别越界。

## 触发时机

- 「盘点一下我的 AI 工具」「工具带扫描」「全机 AI 资产」
- 「哪些技能在多个工具里重复装了」「技能版本漂移」
- 每周一 10:00 定时任务自动跑（定义在 xingtu-automations 仓 registry，slug: toolbelt-weekly-scan）

## 流程

```bash
# 一条命令：枚举 → 盘点 → 漂移检测 → 脱敏门禁 → JSON + HTML
# 外挂词表可选（工作区私有件，身份/雇主代号类；不传则仅结构模式生效）
# 词表路径用占位符，平台侧替换为实际私有件位置
python3 skills/toolbelt-scan/scripts/toolbelt_scan.py --redline-file <私有词表路径>
```

1. **枚举**：内置 ~25 个工具签名表（目录/skills 位置/会话位置/分类），探测存在性。
2. **盘点**：每工具 = 数据量（du）+ 技能安装数 + 会话/项目数 + 最后活跃（mtime 树扫）。
3. **去重**：跨工具同名技能按 SKILL.md SHA-1 比对 → 漂移表（同名不同版）+ 干净重复表 + 僵尸表（装了目录没 SKILL.md）。
4. **门禁**：输出 JSON 自扫 30 词红线，命中即拒写并报告。
5. **产出**：
   - `data/toolbelt_inventory.json`（机器可读，增量对比用）
   - `outputs/云中立工具带盘点_<日期>.html`（单文件零依赖看板：KPI 卡 + 工具矩阵 + 漂移 Top + 僵尸清单）
   - 复制进金库：`cp` 到 `github/xingtu-vault/定时任务产出/工具带盘点_<日期>/`（黄金仓，由 relay 通道push）
6. **增量**：与上周 `toolbelt_inventory.json` 对比，摘要报「新增工具 / 技能变动 / 数据增长 / 新漂移」。

## 看板规格（与工作区视觉律对齐）

单文件、零依赖、离线可用；白底 + 行途技术蓝 #056DE8；KPI 卡（工具数/安装数/去重数/漂移/僵尸/总数据量）；
工具矩阵表（类/目录/量/技能/会话/活跃）；漂移 Top 榜。信息图纯 HTML/CSS，禁 PIL、禁 AI 生图。

## 边界

- 本技能管「盘点」不管「挖掘」：会话内容蒸馏找 `ai-session-material-miner`；
  技能跨仓策展找 `cross-repo-skill-curation`；技能库体检（红线/口径）找 `skill_library_checkup.py`。
- 不替代任何工具自身的功能；不登录、不联网、不动配置。

## 维护

- 签名表新增工具：改 `scripts/toolbelt_scan.py` 的 `TOOLS` 列表（显示名/目录/skills 路径/会话路径/分类）。
- 红线词表扩容：同步改脚本内 `RED` 与 `xingtu-skills` 仓 `tools/skill_library_checkup.py`（两边一致）。
- 每周跑完如发现新工具/新漂移，在金库当周目录的周报记一笔。

<!-- public-sync: 2026-10-12 | 原创首发 | SSoT: xingtu-skills -->
