---
name: wb-usage-cost-audit
description: >
  从本机取证 WorkBuddy/CodeBuddy 的真实用量（积分 + Token + 缓存命中率），
  并把它折算成人民币，与「模型官方直充价」「WorkBuddy 订阅积分单价」做成本对撞，
  最后产出单文件 HTML 看板 + 路线建议。触发词：用量统计、查我的用量、花了多少积分、
  credits 消耗、token 消耗、WorkBuddy 花费、充值划不划算、直充 vs 订阅、
  自定义模型成本、models.json 成本、usage audit、cost audit。
agent_created: true
---

# WorkBuddy 用量取证与成本审计

把「我用了多少 / 花了多少钱 / 该怎么付」这三件事，从**本机真实数据**里挖出来回答，
而不是靠官方文档推算。

## 何时用

- 用户问：我能看到自己的用量吗？消耗了多少积分/Token？
- 用户问：充 WorkBuddy 积分划算，还是直接给模型厂商充值 + 配自定义模型划算？
- 用户问：某个月的账单为什么这么高？
- 用户要做订阅档位决策（标准版/高级版/旗舰版/加量包）。
- 任何需要「用量 → 成本 → 建议」链条的场景。

## 核心理念：三本账，必须交叉核对

单一数据源一定会得出错误结论。必须同时读三本账：

| 账本 | 位置 | 说明 |
|---|---|---|
| **积分账** | `~/.workbuddy/workbuddy.db` → `session_usage` 表 | `credit_json` 字段 = `{请求hash: 消耗积分}` 的 JSON，**逐次调用**记录。只有被扣费的调用才在这。 |
| **Token 账** | `~/.workbuddy/traces/<pid>/trace_*.json` | `trace.modelInfo` 含 `sessionId` / `totalInputTokens` / `totalOutputTokens` / `totalCachedTokens` / `callCount` / `models[]`。**全部会话**都在这。 |
| **模型账** | `~/.workbuddy/models.json` | 自定义模型配置（OpenAI 兼容）。**走这里的调用完全不消耗积分**。 |

`~/.workbuddy/projects/`（会话消息）、`local_storage/`（无积分余额，余额在服务端）。

### 关键陷阱

1. **两本账的会话数不一样**。积分账只记扣费会话（例：78 个），Token 账记全部（例：94 个）。
   → 做成本换算时必须取**交集**（"可比子集"），否则免费会话会摊薄结论。
2. **`session_usage` 里可能有悬空 session_id**（sessions 表里不存在）。
   → 用纯 `session_usage` 求和拿总数，用 JOIN 拿分类明细，两者差一点点是正常的。
3. **模型的 `credit_json` 和 `session_id` 都对不上 humans 可读名**，要靠 `sessions` 表或 trace 的 `modelInfo.models` 反查。
4. **`traces/` 里大量 trace 的 `totalTokens` 是 0**（只有工具 span），必须筛 `modelInfo` 非空。

## 执行步骤

### 步骤 1 · 摸清账本规模

```bash
ls -la ~/.workbuddy/ | head -50
du -sh ~/.workbuddy/* 2>/dev/null | sort -rh | head -20
sqlite3 ~/.workbuddy/workbuddy.db ".tables"
sqlite3 ~/.workbuddy/workbuddy.db ".schema session_usage"
sqlite3 ~/.workbuddy/workbuddy.db "SELECT COUNT(*) FROM session_usage;"
```

### 步骤 2 · 跑取证脚本

`scripts/wb_usage_audit.py` 一次产出全部结构化数据（积分/Token/缓存/按模型/按天/交集）。
用 managed python：`~/.workbuddy/binaries/python/versions/3.13.12/bin/python3`。
**不要用 pandas**（managed venv 里没有，且 1.4G traces 用 stdlib 更快）——纯 `sqlite3` + `json` + `glob` 即可。

### 步骤 3 · 免费模型核验（最容易出反直觉结论的一步）

只看**单一模型会话**（`len(modelInfo.models)==1`），判断它是否出现在积分账里：

- 有扣分 → 付费模型
- 零扣分 → 免费模型

⚠️ 混元系列（`hy3` / `hy4-preview`）实测**零积分**。用户常以为自己"只用免费模型"，
实则积分被 DeepSeek/GLM/Kimi 吃光——**这个反差本身就是最有价值的结论**。

### 步骤 4 · 拿官方价目（必查，别背）

- WorkBuddy 个人版定价：`https://www.workbuddy.cn/docs/workbuddy/Pricing`
- 积分抵扣规则：`https://www.workbuddy.cn/docs/workbuddy/Credits`
- 模型厂商定价：查其官方 API Docs 的 pricing 页

**关键换算**：积分单价 = 月费 ÷ 每月实得积分。注意"实得"含**限时加赠**，且有有效期。
套餐档位价差极大（实测 4.5 倍：加量包 ¥0.05/积分 vs 旗舰版包年 ¥0.0112/积分）。

### 步骤 5 · 成本对撞（核心产出）

取"某模型家族"的可比子集，算三个数：

```
实测换算率 = 积分 / (输入+输出) 的百万数
直充等价   = 缓存命中×厂价 + 未命中×厂价 + 输出×厂价   ← 厂商侧
订阅等价   = 积分 × 各档积分单价                      ← WorkBuddy 侧
```

**必须区分峰谷时段**（多数厂商有 peak/off-peak）。常见反转结论：
> 直充在空闲时段最省，但 WorkBuddy 订阅价可能**低于**直充高峰价——因为订阅把峰谷差抹平了。

### 步骤 6 · 出看板

用 `outputs/` 下单文件 HTML（零依赖、离线可用）。必备小节：
结论先行 → 账本总览 → 积分按模型 → 免费模型核验 → 燃烧节奏 →
官方价目 → **成本对撞表** → 月度预算 → 三路线卡片 → 待拍板行动项。

## 输出规范

- **结论先行**，把最反直觉的发现放最前面。
- 每个数字都要能追溯到文件 + 字段，看板里标注数据来源。
- 成本对撞表必须给**倍率**（1.56× / 0.78×），不给裸价格。
- 结尾给**选项制**的待拍板项（3 条以内），不要给一大段总结。

## 已验事实（2026-09-13 实测，可作为对照基准）

- WorkBuddy `session_usage.credit_json` 单位 = 积分（Credits），非金额。
- 混元 `hy3` / `hy4-preview` 不扣积分；DeepSeek / GLM / Kimi 扣积分。
- DeepSeek Flash 家族实测换算率 ≈ **16 积分 / 百万 Token**（含缓存口径）。
- 本机缓存命中率可达 **95%+**——这是最大成本杠杆，务必单独指出。
- 加量包（¥0.05/积分）比订阅单价贵 4.5 倍，属"救火专用"，不可作为常态补充。

## 边界

- **只读**。不改数据库、不改配置、不动 `models.json`（除非用户明确要求配置）。
- 余额/账单明细在**服务端**，本地拿不到；本地能拿的只有消耗量。
- 公司中转平台（如 内部 AI 平台）的日志属公司额度，可作 Token 强度参照，但**不要算进个人支出**。
- 报告中若引用用户真实身份/公司信息，遵守该用户的对外隔离规则。

<!-- public-sync: 2026-10-12 | 脱敏版本 | 源 ~/.workbuddy/skills/wb-usage-cost-audit -->
