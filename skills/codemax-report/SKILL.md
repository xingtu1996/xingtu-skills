---
name: codemax-report
description: >
  行途自媒体"数据核实 + 用量分析"技能（豆包工作优化版）。两大能力：
  ① cc-switch 本地库核实（~/.cc-switch/cc-switch.db）：核实文章数字——缓存命中率、
  缓存读倍数、成本、Token 量级，防编造（对齐 PUB-018 脱敏 + "凭印象硬编是大忌"红线）。
  ② CodeMax 平台汇报（保留原版 API 直拉能力）：用户/模型/项目/趋势 + 阶段对比 HTML + 模型切换观察。
  触发：核实数字、数字对不对、缓存命中率、cc-switch 数据、token 账单、CodeMax 汇报、AI 用量分析、
  模型对比、模型切换、TTFT、卡顿排查。
  数据源：~/.cc-switch/cc-switch.db（本地 SQLite）+ CodeMax API（codemax_stats.sh）。
  版本：豆包工作优化版 v1.0（2026-09-03）；原版归档 .backups/skills_原版归档_20260903/codemax-report_原版_{tfm-ng,ctf-gitlab}
---

# 数据核实 + CodeMax 汇报 Skill（行途版）

## 一句话

**行途文章里的每个数字都要经得起核实。** 本 skill 用 cc-switch 本地真实数据 + CodeMax API，验证"缓存命中率 97.7%""缓存读是输入 36.8 倍""30 天省 8880 万"这类数字，防止编造和口径混乱。

## 触发条件

- 用户说"核实数字""数字对不对""缓存命中率""cc-switch 数据""token 账单" → 走 **cc-switch 核实**
- 用户说"CodeMax 汇报""AI 用量分析""模型对比""模型切换" → 走 **CodeMax 汇报**（原版能力）

---

## 第一部分：cc-switch 本地库核实（豆包工作优化版新增 · 核心）

> 这是行途最常用的能力：文章里出现任何 token/成本数字，先来这里核实。

### 数据源

```bash
DB="$HOME/.cc-switch/cc-switch.db"   # cc-switch 本地 SQLite（17MB，60 天滚动）
```

### 常用核实 SQL

```bash
# ① 全周期缓存命中率（验证 S02 "缓存读 97.7%"）
sqlite3 ~/.cc-switch/cc-switch.db \
  "SELECT ROUND(100.0*SUM(cache_read_tokens)/(SUM(input_tokens)+SUM(cache_read_tokens)),1) pct FROM usage_daily_rollups;"
# → 实测 98.1%（与 S02 97.7% 高度一致 ✅）

# ② 缓存读是输入多少倍（验证 S12 "缓存读取 36.8 倍"）
sqlite3 ~/.cc-switch/cc-switch.db \
  "SELECT ROUND(1.0*SUM(cache_read_tokens)/SUM(input_tokens),1) ratio FROM usage_daily_rollups WHERE model='deepseek-v4-pro';"
# → 实测 65.0 倍（与 S12 36.8 倍不同——口径不同需说明：36.8 是 tfm-ng $21.84 账单，65.0 是本人 cc-switch 全周期）

# ③ 按模型汇总（成本/请求/Token）
sqlite3 ~/.cc-switch/cc-switch.db \
  "SELECT model, SUM(request_count) req, SUM(input_tokens) inp, SUM(cache_read_tokens) cache_r, ROUND(SUM(CAST(total_cost_usd AS REAL)),2) cost FROM usage_daily_rollups GROUP BY model ORDER BY cost DESC;"

# ④ 某日某模型明细（看某天消耗）
sqlite3 ~/.cc-switch/cc-switch.db \
  "SELECT * FROM usage_daily_rollups WHERE date='2026-08-03' AND model='deepseek-v4-pro';"
```

### 核实流程（对齐 S05 三数口径对比范式）

1. **定位文章数字**：从正文提取要核实的数字 + 声称口径
2. **查 cc-switch 实测**：跑上面 SQL 拿到本人真实数据
3. **口径对比**：
   - 同一口径 → 标注"✅ 已核实：cc-switch 实测 X%"
   - 不同口径 → 明确说明差异来源（如"36.8 倍是 tfm-ng $21.84 账单，65.0 倍是本人 cc-switch 全周期"），**不混用**
4. **脱敏检查（PUB-018）**：公开发布只留量级，费用金额不公开
5. **写回**：文章数据口径标注 + 可核验背书（可选：附 SQL 或来源说明）

### 核实铁律

| # | 铁律 |
|---|------|
| 1 | **cc-switch 数据只到 60 天滚动窗口**——超过窗口的历史数字（如 8 个月账单）需用素材矿/CodeMax 补 |
| 2 | **缓存命中率口径** = cache_read/(input+cache_read)，与平台显示可能不同，先确认口径 |
| 3 | **rtk gain 节省量 ≠ cc-switch 真实消耗**——rtk 是"省下的"，cc-switch 是"实际花的"，两者不同维度不互比 |
| 4 | 口径不一致 → 回数据源核对，不猜（对齐原版写作纪律 #8） |
| 5 | 封面数字与正文主数字不一致 → 跑 `check_cover_consistency.py` 修复 |

---

## 第二部分：CodeMax 平台汇报（原版能力保留）

> 原版 codemax-report（tfm-ng/ctf-gitlab）的 API 直拉 + HTML 汇报能力完整保留，供职场汇报/模型切换观察使用。

### 数据源与脚本

| 资源 | 路径 | 用途 |
|------|------|------|
| **一键拉取（主）** | `scripts/codemax_pull.sh` | **API 直拉全维度**：summary/users/models/projects/趋势 |
| 单接口拉取 | `scripts/codemax_stats.sh` | summary/users/models/pm-options/pm-projects/pm-staffs/log-stat/api-models |
| 数据库查询 | `scripts/codemax_db.sh` | users/logs 表直查（身份/注册数/流水） |
| 认证配置 | `settings.local.json` env | CODEMAX_ADMIN_TOKEN + CODEMAX_ADMIN_USER（admin 全解锁） |
| 广分名单映射 | `scripts/gz_roster.txt` | 用户→姓名/岗位/团队（核心资产，改这里） |

### 工作流程（简要）

```bash
# ① 拉取权威数据（API 直拉，替代 CSV）
bash scripts/codemax_pull.sh -s 2026-08-14 -e 2026-08-28 -o .report/工作汇报/828

# ② 单接口
bash scripts/codemax_stats.sh pm-staffs -p 952 -s 2026-08-14 -e 2026-08-28
bash scripts/codemax_stats.sh log-all -m glm-5.3-flash -s 2026-08-31 -e 2026-08-31

# ③ 计算核心维度：次均费用 / 每请求 Token / token工时密度 / 帕累托集中度 / 效率分层
# ④ 生成两套 HTML（阶段对比版 1200px + 同事版速览 780px）
# ⑤ 写作纪律：脚本口径为准，负面不点名，跨期对比先确认口径清洗
```

> 详细方法论见原版（归档 .backups/skills_原版归档_20260903/codemax-report_原版_tfm-ng）或 ctf-gitlab 版 §六 模型切换观察。

---

## 与其它行途 Skill 联动

| Skill | 联动 |
|-------|------|
| **de-ai-flavor** | 去 AI 味时数字来源存疑 → 回 codemax-report 核实 |
| **adversarial-review** | 审计员角色核数字 → 调用本 skill 的 cc-switch SQL |
| **check_cover_consistency.py** | 封面 vs 正文数字一致性校验（a1 产线） |

---

## 版本历史

| 日期 | 版本 | 变更 | 来源 |
|------|:---:|------|------|
| 2026-09-03 | v1.0 | 豆包工作优化版：新增 cc-switch 本地库核实（第一部分）+ 保留 CodeMax API 汇报能力（第二部分） | 原版 tfm-ng + ctf-gitlab |

> **豆包工作优化版**：新增"数据核实"场景（行途文章数字可验证），原版已归档 `.backups/skills_原版归档_20260903/`。
