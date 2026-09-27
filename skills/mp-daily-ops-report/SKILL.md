---
name: mp-daily-ops-report
description: 行途每日晨间决策指令 + 封面交替管线（定时 09:30 / 手动补跑）。当用户说"出运营日报/跑日报/补跑今天日报/今天数据怎么样/明日封面什么底色/封面交替判定/日报简报推微信/日报定时任务挂了"时触发。以资深全平台 IP 操盘手角色预设（RULER.md）产出四块决策文档：①下一个档期发什么（1 主推+2 备选各配一句话理由）②怎么发（标题/封面建议+二次群推/多平台动作指令）③数据只在异常与杠杆点时说话 ④待 boss 拍板（≤2 个 A/B 选择题）。严禁"昨天做了啥/进度如何"式流水账。全程只读：不改稿不发布不建草稿不回填台账；群发永远 boss 人工。
version: 2.2.1
---

# 晨间决策指令 + 封面交替管线（mp-daily-ops-report）

> **适用范围守卫**：读当前工作区根 `AGENTS.md`，含「行途」才继续；否则零业务文件读取、直接停止声明不适用。本管线硬依赖行途工作区目录结构（`tools/`、`data/stats_*.json`、`outputs/发布包_2026-09/`、`outputs/本周发布计划_*.md`），在其他项目（如公司侧仓）不可跑。

**定位（2026-09-16 boss 重定义，勿回退）**：这不是进度汇报，是 boss 每天早上打开即知的**决策指令**。角色 = 资深全平台 IP 操盘手（`RULER.md`）：有判断、给选项、把"信息"升级成"动作"。六块数据日报已降级为**内部底座/附录**，四块决策体才是正文。

**分工铁界**：脚本（`tools/dispatch_feed.py` 喂数器、`tools/mp_daily_report.py`、`tools/publish_brief.py`、`tools/cover_next.py`）只聚合事实、算去腐榜/凭证缺口/闭环率并归档 `outputs/今日调度_<date>.md` 候选快照；**四块决策由 agent 综合判断产出**，不追求脚本化（不过度工程，参 legal-compliance-baseline 精度迭代三铁律）。`dispatch_feed` 只喂数不决策：它把三源合并成轨A候选/轨B窗口/轨C去腐榜（单列独立）/凭证唯一化缺口/闭环率，agent 据此定主推与备选、写动作。历史 CHANGELOG/旧简报里"门禁全绿"一律不作豁免——①块候选必须来自 `publish_brief.py` **本轮现跑**。

## 口径先立正：「今天发什么」= 下一个未发档期

群发在每天 08:15，日报 09:30 推送时当日额度已用。故 ① 块对象是**明早 08:15 档**（当日档已发时）；若 boss 拍板改时（见 ④ 块 A/B 池），以配置为准。简报首行必须写清"下一个档期：M/D 08:15"。

## 管线五步

### Step 0 拉快照（失败记因跳过，不重试轰炸）

```bash
cd <xingtu 工作区根> && python3 tools/mp_stats_puller.py --pull
```

- 成功 → `data/stats_YYYY-MM-DD.json`（同日重跑覆盖）
- 失败两类典型：**40164**（IP 白名单，无自救）/ **bsk 未登录**（需 boss 打开 Chrome 登录 mp.weixin.qq.com）——记录原因、跳过，用现有最新快照继续，简报注明数据截止日。禁循环重试。

### Step 1 跑底座（只聚合事实 + 喂数，不做决策）

```bash
python3 tools/mp_daily_report.py            # 六块数据底座 → outputs/运营日报_YYYY-MM-DD.md
python3 tools/publish_brief.py --date <下一档期日>  # 候选包清单：ready_score/现跑门禁/blockers/分发时序窗 external_ok_from → outputs/发布决策简报_*.json
python3 tools/cover_next.py                 # 下一档期应底色 + 包封面就绪（--for <包名> 查指定包；🆕 09-17 22:1x 内置「快照非今日 → 自动 pull 再判定」，不再靠人肉先拉数据）
python3 tools/materials_library_recalc.py   # 🆕 Phase2 派生字段每日重算（不扫源、不碰卡正文/手设研判）：urgency/days_left/publish_priority/tier/active_for_decay → 素材库每日不腐 + 已发/过期自动出去腐榜（AC-3；公式 SSoT=tools/materials_scoring.py，与 gen 同源）
python3 tools/dispatch_feed.py --date <下一档期日>  # 🆕 喂数器：合并素材库+简报+manual_metrics → 轨A候选/轨B窗口/轨C去腐榜/轨C自动成包候选/外部信号反哺/变现daily_action/凭证唯一化缺口/闭环率 → outputs/今日调度_<date>.json+.md（AC-2 输出归档落点）
python3 tools/track_c_autopackage.py --date <下一档期日>  # 🆕 Phase2 轨C 自动成包：对 feed 的达标去腐候选生 PUB-031 六目录『待确认发布包』脚手架+00_待确认交接单（**只到待确认包，绝不写正文/渲图/建草稿/发布**；已有真实正文则 SKIP 不覆盖）
```

`dispatch_feed` 是 Step 2 四块的**候选喂数源**：agent 读 `今日调度_<date>.json` 的 `track_a/track_b/track_c_decay/track_c_autopackage/external_signal_reflow/monetization/evidence/metrics` 段合成决策，**排序与定稿仍由 agent 判断**（feed 不越界替 boss 拍板）。`materials_library_recalc`/`track_c_autopackage` 是 Phase2 显式执行段（recalc 刷派生、autopackage 只落待确认脚手架），均在只读决策边界内、不发布。

### Step 2 四块决策体（agent 判断，写入日报文件顶部，六块降为「附录 · 数据底座」）

**① 下一个档期发什么（核心）**
- **1 主推 + 2 备选**，每个**一句话理由**（蹭哪个热点/补哪个人群/为什么现在发），扫一眼可拍板。
- 候选来源：`本周发布计划_*.md` 排期行 + `publish_brief` 中 `ready_score≥90` 且 blockers 可当日清零者；理由必须带数据引用（桶中位、分享率、档期节奏，BUL-003）。
- 排期包 blocked 时，备选从 ready 池提，并明说主推降级原因——**不藏**（操盘手先说坏消息）。
- 选题挖掘模式开关见 Step 3（`dig_mode`）：`hot` 才做一轮轻量热点扫描（WebSearch 一次、只取当日 AI 热点，不铺网）映射既有包；`pool` 只在排期池内排优先级。
- **三轨合流（AC-7，读 `dispatch_feed` 段）**：①块同时覆盖三轨，各带一句数据理由——**轨A 首发**（`track_a.candidates`：publish_brief ready 包，1 主推+2 备选）｜**轨B 再铺**（`track_b.list` 中 `window_open` 的已发包 → 跨平台矩阵）｜**轨C 去腐激活**（`track_c_decay.top`：单列独立去腐榜，已产出/过期经 `active_for_decay` 自动出榜；每日 1 张进①，Phase2 起对达标候选（含非平台/脱敏低中/pri≥阈值）由 `track_c_autopackage.py` 生**待确认发布包**，**仍不发布**、交 xingtu-content-craft 等 SOP）。过期提醒（`expiry_reminders`）也在①块露一行。**↩ 外部信号反哺**（`external_signal_reflow`）：轨C 素材外站表现达标 → 升入轨A首发候选建议（feed=external_signal）；无回流数据时诚实空列不虚构。

**② 怎么发（信息 → 动作）**
- 标题/封面：下一档期应底色 + 包就绪结论（来自 cover_next）；涉换题只给方向（阈值与执行归 `mp-title-collision-rename`，勿在日报里跑双查）。
- 二次群推：底座⑤/分享率>12% 篇 → 写成动作指令："X 篇分享率 N%，话术走 `mp-group-push-copy` 生成，boss 手动群发"（列到篇名，不说空话）。
- 多平台：按 `publish_brief.distribution` 的 `external_ok_from`（+24/48h）与时序闸门（一天≤2 平台，PUB-004 禁通稿）给"今天可铺哪 1-2 个平台"；铺图卡/变体执行归 `xingtu-multiplatform-distribution`。

**③ 数据只在异常/杠杆点时说话**
只写命中以下规则的行，无异常就一句"数据无异常信号"：
- 单篇日增量 >50（长尾杠杆，可追推）
- 分享率 >12% 且无群推凭证（漏转发红利）
- 速评类 24h 后才起量（评估窗口教训，勿凭 3h 快照定论）
- 题材桶中位跳变（新主线信号）
- **闭环率（AC-6，必写一行）**：`闭环率 = 已执行输出 ÷ 已给建议`（取 `dispatch_feed.metrics`）；当日累计=0 时显式标 🔴，把"有输入没输出/输出没归档"的断点变成看得见的数字
- **分发凭证真值（AC-5 唯一口径）**：只认 `分发凭证_<平台>_<日期>`；账号品牌化/认证/隐私类 `凭证_*` 脏前缀**一律排除不计**（旧 glob 误计它们=假分发凭证）。凭证=0 即分发未执行（缺口，盯协作方回填截图），非"没记录"
不铺全量增量表——全量在附录，正文只留决策相关。

**④ 待 boss 拍板（≤2 个，全部 A/B 选择题）**
- 每题给 A/B 选项 + 各一行权衡，**禁开放式问题**。来源：dig_mode 未定版 / blocked 包补不补 / 死线动作取舍 / 定时任务时点调整。
- **变现动作（轨D·AC-8，每天≤1，读 `dispatch_feed.monetization.daily_action`）**：feed 已按 brief.money.deadlines+status 算出"真有货可推进"的一条（默认序 自查卡 L2 面包多建品 → 小册补章 → 触发式出书/开源），写进正文给死线剩余天数与负责分工；私域承接**仅企业微信/视频号私信，禁个人微信号/二维码，全平台等效**。无到期动作则一句"今日无变现推进动作"，不硬凑。
- boss 微信回复即视为拍板，落对应配置文件或执行，次日不再重复问同一题。

### Step 3 dig_mode 开关（可配置，未定版前占 ④ 块一题）

- 配置：`data/daily_ops_config.json` → `{"dig_mode": "hot" | "pool"}`
- 文件不存在 = 未拍板：① 块按 `pool` 保守跑（只在排期池排优先级），④ 块固定一题「A 主动挖热点（每日 hotspots 扫描映射包）/ B 仅池内排优先级」；boss 拍板后写入配置，此题不再出。
- 修改配置即换模式，无需动本技能。

### Step 4 推「我的微信」+ 核对凭证

- 简报 = 四块正文压缩版（含"下一个档期"首行），**决策文档式**，不是"增量/榜/死线"流水账。投递：定时任务经 `qwenwork_channel_list_conversations` 找「我的微信」后 delegate；主会话直接发。
- **完成判定查凭证（两文件都要当日 mtime）**：`stat -f '%Sm' outputs/运营日报_$(date +%F).md` 与 `outputs/今日调度_$(date +%F).md` mtime 均须是今天，且日报顶部含「① 下一个档期」决策体（只有六块=未转化=未完成；**缺 `今日调度_<date>.md` = 输出没归档 = 未完成，AC-2，不冒充已生成**）。脚本可能静默失败留旧文件。

## 坑位清单（全部实测踩过）

1. **stats 快照结构键是 `articles`**，不是 list/items——解析对不上先打印一层 keys，别猜。
2. **python 格式串字面 `%` 必须写 `%%`**：`"分享率>12%"` 作格式串抛 "not enough arguments"，异常被 `>/dev/null 2>&1` 吞掉 → 日报是旧的。调试时去重定向看真错误。
3. **分发凭证唯一口径（AC-5）**：只认 `分发凭证_<平台>_<日期>`，账号品牌化/认证/隐私类 `凭证_*` 脏前缀**排除不计**（旧 glob 用 `凭证*`/`*凭证*` 会把这些假计成分发，实测脏计 9 项）。凭证=0 即分发未执行——不是"没记录"，是缺口；协作方回填**文章分发**截图（新命名）才算。
4. **memoir 冻结文张力**：已冻结 memoir 路线篇（如「电脑城学徒」）数据可能不低，只进附录作参照，③ 块不作追推信号（品牌红线 SAF/STR 禁 memoir）。
5. **定时任务可能死于基建**：`Runtime initialization network retry exhausted` = 任务启动网络失败，秒级终止、脚本没跑——手动补跑即恢复；但必须核对当日文件真生成（与坑 3 同族：产出 ≠ 计划）。
6. **封面底色只认后台实发**，不认包内备注/排期推断；实发未映射时 fallback 今日排期包，包名用前 12 字模糊匹配（书名号坑精确匹配）。
7. **群发 08:15 vs 日报 09:30 的时差**：当日档通常已发，① 块对象是下一档期；把"今天"理解成当日会产出"今天已发完还发什么"的怪文。
8. **ready_score 高 ≠ 可发**：`无配图` blocker 命中 PUB-048 密度红线时，② 块须给"补图走 `pub-infographic-supplement`"动作而非直接推上台。
9. **cover_next 快照非今日会静默错一档**（09-17 实锤：快照停 09-16，FDE-07 当日 08:25 黑底实发漏库 → FDE-04 误判黑、实应白，boss 当场抓出）。**已内置自动 pull**（stale → 先 `mp_stats_puller --pull` 再判定，失败才降级警告），跑时报 `⚠️ _stats快照非今日_` 后仍出现判定行时，须以 `/s` 页 og:image 像素采样或后台截图核对实发底色，禁静默信。

## 红线与纪律

- 只读 + 决策文档 + 推简报：**不改稿、不发布、不建草稿、不回填台账**（台账回填需 boss 确认）
- 群发永远 boss 人工点（个人订阅号群发 API 已回收）
- 禁 `rm`；删除走 `tools/safety/safe-delete.sh`
- 建议/理由必须带数据引用（BUL-003）；编数字 = B-009 违例
- ④ 块每天 ≤2 题，超出砍掉——决策带宽是 boss 的稀缺资源
- 手动补跑属日常只读轮次，不写 CHANGELOG；仅改 `tools/` 脚本或本技能时留痕（`--tool qwenwork`）

## 定时任务配置（verbatim payload，任务丢失/改文案时原样重建）

- 名称：`行途晨间调度决策日报（三轨+闭环率+凭证唯一化+封面交替）`｜schedule：cron `30 9 * * *` tz `Asia/Shanghai`｜missedRunPolicy：`run_latest`｜contextDirs：xingtu 工作区根

```
在 <xingtu 工作区根路径> 工作区执行每日晨间调度决策日报（先读根 AGENTS.md 确认含「行途」，再读 .agents/skills/mp-daily-ops-report/SKILL.md 按四块口径执行，角色=资深全平台IP操盘手，禁流水账）：1) 跑 python3 tools/mp_stats_puller.py --pull 拉最新后台快照（40164 或 bsk 未登录则记录失败原因跳过拉取、用现有快照继续、简报标数据截止日）；2) 跑底座：python3 tools/mp_daily_report.py 与 python3 tools/publish_brief.py（现跑门禁，历史全绿不豁免）与 python3 tools/cover_next.py 与 python3 tools/materials_library_recalc.py（Phase2 派生字段每日重算：urgency/days_left/active_for_decay，不扫源不碰正文/手设研判）与 python3 tools/dispatch_feed.py --date <下一档期日>（喂数器产 outputs/今日调度_<date>.json+.md：轨A候选/轨B窗口/轨C去腐榜/轨C自动成包候选/外部信号反哺/变现daily_action/凭证唯一化缺口/闭环率）与 python3 tools/track_c_autopackage.py --date <下一档期日>（轨C达标去腐候选→PUB-031『待确认发布包』脚手架，只到待确认包、绝不发布，已有真实正文则 SKIP）；3) 把日报文件顶部改写为四块决策体（原六块降为附录），决策由 agent 依 feed 段综合判断（不脚本化）：①下一个未发档期·三轨合流=轨A 1主推+2备选 + 轨B 窗口到期再铺 + 轨C 每日激活1张去腐素材(Phase2 达标者生待确认包·不发布)+过期提醒+外部信号反哺(无回流则空) ②怎么发（封面底色结论+二次群推动作指令+多平台时序）③信号：仅异常/杠杆点 + 闭环率(已执行÷已给建议,累计0标红) + 分发凭证真值(唯一口径 分发凭证_<平台>_<日期>，脏前缀凭证_*不计) ④待拍板 ≤2 个 A/B 选择题（含轨D变现每日≤1动作读 monetization.daily_action，默认序 自查卡L2面包多建品→小册；私域仅企业微信/视频号私信，禁个人微信号/二维码）；4) 四块简报发送到「我的微信」，首行写明下一个档期日期；5) stat 核对 outputs/今日调度_<date>.md 与 outputs/运营日报_<date>.md mtime 均=今天、且日报顶部含「① 下一个档期」才算完成（缺今日调度=未归档=未完成，不冒充）。全程只读：不改稿不发布不建草稿；群发永远 boss 人工。
```

> 重建时把 `<xingtu 工作区根路径>` 换成实际绝对路径。与 20:30「明日稿全管线」任务关系：那条管建稿（写操作，走 `mp-publish-sop`），本技能管晨间决策（只读）；两条独立，不互触发。

---

## 并入资源（2026-09-19 技能减法治理）

本 skill 于 09-19 吸收了原孤儿 `xingtu-publish-next-decision` 的全部内容，逐字存于同目录 `reference_xingtu-publish-next-decision_并入.md`（其独有脚本/资源已并入本目录 scripts|templates）。触发本 skill 时若涉及「排期前appmsgid时序核对/判读纪律」，先查该并入文件防遗漏。

<!-- public-sync: 2026-09-27 | 脱敏版本 | 源 .agents/skills/mp-daily-ops-report -->
