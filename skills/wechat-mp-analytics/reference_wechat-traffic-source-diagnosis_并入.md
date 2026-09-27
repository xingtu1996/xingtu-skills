> 🔴 本文件由技能治理(09-19)从孤儿 skill `wechat-traffic-source-diagnosis` **整体并入** `wechat-mp-analytics`，原目录将入回收站。内容逐字保留防 IP 丢失；正牌 SSoT=wechat-mp-analytics/SKILL.md。

---
name: wechat-traffic-source-diagnosis
description: 行途公众号「阅读来源 / 推荐占比」取数与限流恢复诊断固定流程。当 boss 问「限流解除没 / 推荐占比多少 / 洗权重见效没 / 99% 是什么 / 拉一下阅读来源结构 / 流量来源分布」时使用。先跑 tools/mp_datacube_probe.py 判通道 B（个人订阅号→48001 即通道死刑，禁止再撞 API）→ 回退 bsk 只读抓后台「图文分析→阅读来源」→ 每条数据打统计时间(ref_date+pulled_at, T+1)写入 data/stats_*.json，用「推荐占比」这一健康第一指标判限流/洗权重是否解除；盘上无源数字一律标「待核」不臆造。触发词：阅读来源、来源结构、推荐占比、限流、洗权重、流量恢复、99%、进不进推荐池、datacube、48001。
---

# 公众号阅读来源与限流恢复诊断（wechat-traffic-source-diagnosis）

> 定位：回答 boss 最关心的那一问——**「账号还在限流吗？洗权重见效没有？」** 判据是「阅读来源结构」里的**推荐占比**。这是一个**决策 + 取数 + 打标**的 playbook，不重造已现成的通道工具。

## 范围守卫

读根 `AGENTS.md`，不含「行途」二字则**不执行**——本技能依赖行途专属 `tools/mp_datacube_probe.py`、个人订阅号身份、`data/stats_*.json` 台账与钥匙串凭据，其他项目不适用。

## 与既有资产的分工（先划界，勿重复造）

| 资产 | 管什么 | 本技能与它的关系 |
|---|---|---|
| `wechat-mp-analytics` | bsk 只读抓后台**通用**数据（阅读/分享/粉丝/图文明细）的机械操作 | 本技能**交棒它**做 bsk 会话生命周期与 selector，只补「阅读来源结构」这一页 + 通道判定 + 打标 |
| `mp-daily-ops-report` | 晨间决策四块（含封面交替、待拍板） | 本技能供其「推荐占比」数据，不并跑 |
| `.harness/agents/qwenwork/qw-data-diag.md` | 把**推荐占比定为健康第一指标**（口径） | 本技能**引用不重定义**该口径，负责把它落成可跑的取数步骤 |
| `tools/mp_datacube_probe.py` | datacube API 通道 B 可行性探针（只读，注释自带 48001 判定） | 本技能 Step 1 直接实调它 |

## 前提

- 探针：`tools/mp_datacube_probe.py`（AppID 硬编码页面公开值，AppSecret 从 macOS 钥匙串服务 `wechat-mp-appsecret` 读，token 缓存 `/tmp/mp_access_token.json`，默认取前天=T+1）。
- bsk：`${HOME}/.local/bin/bsk`（接管已登录 Chrome，见 `wechat-mp-analytics`）。
- 台账：`data/stats_*.json`（既有已带 `date`+`pulled_at` 底子，但缺来源结构）。
- 背景：账号 2026-09-14 因一篇「送外卖→技术经理/25k 逆袭」稿被风控打上 **「不良信息/网赚」+「低创作度」双标签**→ **限流（只砍推荐池，粉丝推送照常）**→ 定「洗权重」策略：连更纯技术/科普 8–10 篇约两周。诊断即验证该策略是否生效。

## 工作流（五步）

### Step 1 — 通道 B 判定（先跑，一锤定音，别先撞 API 再回退）

```bash
cd ${WORKSPACE}
python3 tools/mp_datacube_probe.py --date <T-1>   # 例 2026-09-15；数据有 T+1 延迟
```

按末行结论分流（错误码全表见 `reference.md` §一）：

- `✅ 通 errcode=0` → 通道 B 可用，走 API 取来源结构（`getarticleread` 等带来源分项），进 Step 3 打标。**注意：个人订阅号通常拿不到，见下。**
- `⛔ 48001 api unauthorized`（全部接口）→ **个人订阅号无 datacube 权限，通道 B 死刑。** 这是账号类型硬限制，**不是配置问题、换 token 也救不了**。→ 立即去 Step 2，且**落 CHANGELOG 一条带时间戳的「通道B死刑」结论**，钉死防止任何后续 agent 再撞 API 浪费时间。
  - 缓存坑：若先报 `42001`（token 过期），挪走 `/tmp/mp_access_token.json` 再打一次；**换出新 token 后仍 48001 才判定死刑**。若报 `40164` → 是 IP 白名单没放开（让 boss 在后台「开发-基础配置」加本机出口 IP，`curl -s ifconfig.me`），与权限无关。
- `🚫 40164`（全） → IP 白名单问题，让 boss 放开后重打，不要误判成无权限。

### Step 2 — 通道 B 死 → bsk 只读抓「图文分析 → 阅读来源」（回退）

机械 bsk 会话生命周期/selector 复用 `wechat-mp-analytics`（`session start --no-focus` → `navigate` → 按可见文本 `evaluate` 点击 → **成功/失败两条路径都 `session stop`**）。本技能只规定要抓的**目标页与字段**：

- 路径：`mp.weixin.qq.com` → 左侧「数据分析 / 图文分析」→ 选定文章或「已发表内容」→ **「阅读来源」分布**。
- 抓这几类来源占比：**公众号会话 / 朋友圈 / 好友 / 推荐（信息流） / 搜一搜 / 历史消息 / 其他**。
- **推荐占比** = 本诊断的第一判据。
- 红线：**只读**，绝不点「群发/发表/存草稿/改封面」；不提取 cookie/token。
- bsk `session list` 若 `(no active sessions)` → 需先起已登录会话。**`session start` 若停在 `waiting for browser extension to connect… <4位配对码>`（如 `cpkm`）＝ Chrome 里那只 bsk 扩展没连/没配对**（与下面「别把 8 位实例号当会话号」是两种病：那个是解析错、扩展其实连着；这个是扩展真没握手）。处置：请 boss 在扩展弹窗填码/点「连接」握手，**本侧别循环重试**（每回干等 ~90s 仍卡）。
- 真连不上（boss 不在场 / 扩展点不亮 / 后台未登录）→ 走**人工兜底**而非直接空标待核：让 boss 把后台「图文分析→阅读来源」页的**百分比截图 + 对应日期**发回，按真数记账并照 Step 3 打标（`channel` 记 `manual-screenshot`）。这比只标「待核」更能留住洗权重趋势；连截图都拿不到才转 Step 5 待核，**全程不臆造数字**。
- **会话号是 4 位小写码**（如 `wjky`），**别**用 8 位十六进制正则去抓 `session start` 的输出——那会误抓成 `bsk browsers` 里的浏览器实例号（如 `ffb51c99`），拿它去 `--session` 会假报 `session not registered`，实际扩展一直连着。正确提取：`grep -oE '\b[0-9a-z]{4}\b'`（并过滤 warn/info/http/json/true 等噪声词）。
- **`navigate` 偶发 30s 超时不等于失败**：超时后 `evaluate` 往往仍能读到已加载页面。故把 `session start → navigate → 判登录态(evaluate 读 URL 里 token 参数)` 封装在**同一条脚本内、同一个会话号一路用到底**，别拆成多次调用（拆开发会话号易抓错、也易在两次调用间被回收）。

### Step 3 — 每条数据打「统计时间」（硬输出规范，供未来回看洗权重趋势）

无论来自 API 还是 bsk，写盘时每条来源记录**必须**带三件时间元数据（对齐既有 `stats_*.json` 的 `date`/`pulled_at` 底子，schema 见 `reference.md` §三）：

```json
{ "ref_date": "2026-09-15", "pulled_at": "2026-09-16T14:20:00+08:00", "data_delay": "T+1",
  "source_page": "图文分析→阅读来源", "channel": "bsk",
  "read_source": { "推荐": 0.053, "朋友圈": 0.82, "公众号会话": 0.09, "搜一搜": 0.02, "其他": 0.017 } }
```

- `ref_date`：数据本身统计日期；`pulled_at`：本次拉取时刻；`data_delay`：注明 T+1（当天数据未出）。
- 落点：`data/stats_<ref_date>.json`，在既有结构上**增补 `read_source` 字段**，不覆盖原 `articles[]`。
- 目的：洗权重是两周曲线，**单日快照无意义**——打标是为了跨日对比推荐占比是否回升。

### Step 4 — 诊断判定（以推荐占比为健康第一指标）

- 判据口径引用 `qw-data-diag`（不在此重定义阈值表，基线对照见 `reference.md` §四）。
- 拿 `ref_date` 最近的推荐占比 vs 历史基线（例：09-14 复盘曾记录 **推荐仅 5.3%、朋友圈 82%** = 几乎全靠私域转发、推荐池未激活 = **仍限流**）。
- 给**结论 + 数据理由**：推荐占比回升 / 持平 / 走低；是否已解除限流；洗权重是否见效。数据不足（仅一两天 / 缺来源页）时明说「样本不足，暂不能判定」，不硬下结论。
- boss 口中的「99%」须回源核实是哪一天的哪篇、哪个来源维度（很可能是单篇推荐占比或某维度），**不默认采信**。

### Step 5 — 待核纪律（完成判定查凭证，不问模型）

- 盘上（`stats_*.json` / 台账 / 抓取页面）**取不到源**的数字，一律在输出里标 **「待核」**，绝不臆造、反推、或把口头说法当既有事实。
- 声称「已拉到来源」的凭证 = `stats_*.json` 里新增了带 `read_source` 与 `ref_date/pulled_at` 的条目（文件 mtime / 字段可 grep 验证），不是模型自述。

## 安全红线

1. 探针与 bsk 全程**只读**，绝不触发发布类动作。
2. AppSecret 只从钥匙串读、**不落盘不打印明文**；页面 cookie/token 不抓取。
3. 通道 B 一旦实测 48001 死刑 → 落 CHANGELOG 钉死，后续不再重复撞 API（省 boss 的时间与额度）。

## 验证 / 留痕

- 通道判定结论（尤其「通道B死刑」）→ `python3 tools/changelog_append.py --type "📊" --path "tools/mp_datacube_probe.py" --desc "<带时间戳判定>" --tool <本工具身份>`。
- 拉到来源数据 → `data/stats_*.json` 落条目即凭证。
- 一轮诊断收尾，按工作区铁律回写 `CHANGELOG.md` 并同步 `产出索引.md`。
