---
name: cc-switch-usage-audit
description: 从 CC Switch 本地数据库聚合真实 API 用量（token / 成本 / 缓存命中率 / 模型分布），产出可入内容的成本评估与配图素材。当用户说「看看我们的 token 消耗」「实际用量统计」「CC Switch 的记录」「成本评估/背书」「一次真实的账单」时使用。
agent_created: true
---

# CC Switch 真实用量审计

把「本地代理日志」变成可对外引用的成本账。适用于：给内容做一手背书、评估换模型/迁档的真实收益、核对第三方面板数字是否可信。

## 数据源（只读）

- 库：`~/.cc-switch/cc-switch.db`（SQLite，随时间增长；另有 `backups/` 快照可对比）
- 关键表：
  - `proxy_request_logs` — 逐条请求（含 input/output/cache_read/cache_creation tokens、各项成本、latency、first_token_ms、status_code、provider_type、model）
  - `usage_daily_rollups` — 按天×模型聚合（字段最全，但可能滞后于明细表）
  - `providers` — 供应商配置（**含密钥，只取 name/app_type/provider_type/cost_multiplier/is_current**）
  - `provider_health` / `stream_check_logs` — 可用性、流检查

## ⚠️ 安全纪律

1. **绝不读 `providers.settings_config`**（内含 API key），查询时列名白名单。
2. **只读**：不加 `-w`、不做任何 UPDATE/DELETE。
3. 输出给人看之前，去掉可能含账号标识的字段。

## 步骤

1. **定位新鲜度**：`ls -la ~/.cc-switch/cc-switch.db`（判断数据截至何时）。
2. **取时段与条数**：
   ```sql
   SELECT datetime(MIN(created_at),'unixepoch','localtime'),
          datetime(MAX(created_at),'unixepoch','localtime'), COUNT(*)
   FROM proxy_request_logs;
   ```
3. **按模型聚合**（核心一刀）：
   ```sql
   SELECT model, COUNT(*) reqs,
          SUM(input_tokens) inp, SUM(output_tokens) outp, SUM(cache_read_tokens) cache_r,
          ROUND(100.0*SUM(cache_read_tokens)/NULLIF(SUM(cache_read_tokens)+SUM(input_tokens),0),1) hit_pct,
          ROUND(SUM(CAST(total_cost_usd AS REAL)),2) cost_usd,
          ROUND(AVG(NULLIF(latency_ms,0))) lat_ms,
          ROUND(AVG(NULLIF(first_token_ms,0))) ttft_ms
   FROM proxy_request_logs GROUP BY model ORDER BY reqs DESC LIMIT 15;
   ```
4. **命中率口径**：`cache_read / (cache_read + input)`。这是成本账的开关——缓存价通常只有新输入价的 1/50。
5. **交叉验证**：与 CC Switch「设置 → 使用统计」页逐项对齐（请求数/总量/命中/成本应一致）；不一致则说明明细与汇总口径不同（如 `data_source` 去重、rollup 滞后）。
6. **产出**：
   - 表格：真实消耗总量 / 命中占比 / 全价输入占比 / 输出 / 总成本 / 模型分布
   - 配图（入内容用）：仿 `tools/fig_fit.py` 的 1080px 白底黑红灰卡，注明「来源：本地代理日志聚合 + 时段 + 条数」；**自制转录，不贴原始面板截图**（风格统一 + 防泄漏）

## 用官方定价重算（必做，别用平台记录的数字）

CC Switch 记录的 `total_cost_usd` 是**平台/中转层计价**，与官方定价可能不同。要写进内容或做决策，必须按**官方价×逐条日志**重算：

1. **拉官方价表**（双轨！）：如 DeepSeek 空闲/高峰两套价，`高峰 = 空闲 × 2`；高峰时段 = 北京时间工作日 9:00-12:00、14:00-18:00。
2. **按 created_at 切时段**（`datetime.fromtimestamp(ts, tz=UTC+8)`；`weekday()<5 and (9<=h<12 or 14<=h<18)` 为高峰）。
3. **计费公式**：`命中×命中价 + (未命中输入 + 缓存创建)×未命中价 + 输出×输出价`，空闲/高峰分别算再加总。
   - ⚠️ `cache_creation_tokens` 按**未命中输入价**计费，别漏。
4. **同量对比**（最有说服力的一刀）：同样的 token 结构，分别代入候选模型的价表 → 得出「Flash 750 元 vs Pro 3,983 元，5.3×」这种可直接引用的结论。
5. **敏感性**：固定用量，让命中率在 97.7% / 90% / 80% / 60% / 0% 之间变，输出账单倍数表——命中率对账单的杠杆一目了然。
6. **时段杠杆**：算「若高峰全挪到空闲」的差额，常能再省 30~50%。

> 实例（2026-09-14 MODEL-02）：77.14 亿 tokens、命中率 97.7%、高峰占 77% → Flash 750 元/月 vs Pro 3,983 元/月；命中率掉到 80% 账单变 3,144 元（4.2×）；全挪空闲降到 421 元。

## 坑

- `latency_ms` / `first_token_ms` 常为空（未记录）→ 四指标框架里「延迟」项如实标注待补，别编。
- `usage_daily_rollups` 可能停在更早日期，明细表更新——**以 `proxy_request_logs` 为准**。
- 同一时间段 `rollups` 与 `logs` 的成本若不等，优先信明细（logs）。
- 库在 App 运行时可能被占用：只读查询无需锁，但拿到 `database is locked` 就先拷一份副本再查。

<!-- public-sync: 2026-10-12 | 脱敏版本 | 源 ~/.workbuddy/skills/cc-switch-usage-audit -->
