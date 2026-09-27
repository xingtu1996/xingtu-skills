# content-matrix-channel-audit reference

> 本文件承载：数据源路径 SSoT 与缺源降级（§一）、内联统计 snippet（§二）、判据阈值表（§三）、报告骨架模板（§四）、边界与口径细节（§五）、2026-09-16 首案全记录（§六，校准基准）。SKILL.md 只承载流程与纪律，两边不重复维护数字。

## 一、数据源路径 SSoT 与缺源降级

| 源 | 路径（以当轮实测为准） | 缺源降级 |
|---|---|---|
| 素材机读主索引 | `素材库/materials_library.json`（顶层 `{"cards": [...]}`，09-16 计 1484 卡） | 缺文件 → 报告标「缺源」，时效段改用日报 metrics 兜底 |
| 今日调度 | `outputs/今日调度_YYYY-MM-DD.json`，glob 取最新一份（文件名日期可能=明日档期，认 mtime） | 缺 → 用最近一份并在报告标注数据截止 |
| 分发凭证 | `find outputs/发布包_*/多平台分发 -iname "分发凭证*"`；**脏前缀 `凭证_*`（品牌化/认证/隐私截图）必排除** | glob 为空本身即结论（全渠道 0 凭证），不算缺源 |
| 变现盘点 | `specs/20260913-变现盘点与执行规划/00_README.md` + 调度 json 的 `monetization` 块 | 二缺一即用另一个并注明 |
| 分发 spec 群 | `specs/20260915-内容分级分发矩阵规划/`、`specs/20260904-视频号公众号矩阵与视频制作技术栈规划/`、`specs/20260902-开源矩阵SEO与DSH生态优化/`、`specs/20260903-战略落地执行/`（03_售卖渠道与咨询服务.md）；新 spec 用 `ls specs/` 加 grep 关键词（分发/渠道/矩阵）实测补入 | 路径变更属常态（多 agent 并行产物），一律逐词 `grep -ril 分发/渠道/矩阵 specs/` 实测补新，不硬编码记忆 |
| 发布窗口 | `tools/publish_brief.py` 内 distribution/window 相关字段（grep 实现或直接跑脚本输出 JSON） | 脚本挂 → 记故障，用调度 json track_b 兜底 |
| 交叉印证 | 当日 `outputs/运营日报_*.md`、`CHANGELOG.md` 顶部、`data/dispatch_config.json` | 缺不阻塞主链 |

## 二、内联统计 snippet（复制到 python3 - 执行，不落脚本文件）

```python
import json, collections, glob, os, datetime
d = json.load(open("素材库/materials_library.json"))
c = d["cards"]
def dist(f, n=15):
    m = collections.Counter()
    for x in c:
        v = x.get(f)
        m["<list>" if isinstance(v, list) else v] += 1
    return m.most_common(n)
for f in ["tier", "urgency", "status", "publish_priority", "desensitize", "audience"]:
    print("==", f, dist(f))
# platforms 覆盖（多渠道盘点的关键缺口信号）
pm = collections.Counter()
for x in c:
    for p in (x.get("platforms") or []):
        pm[p] += 1
print("== platforms", pm.most_common())
# 时效：只看真临期
def dl(x):
    try: return int(x.get("days_left", 999))
    except (TypeError, ValueError): return 999
print("days_left<7:", sum(1 for x in c if dl(x) < 7),
      "<30:", sum(1 for x in c if dl(x) < 30),
      "total:", len(c))
# 囤稿 vs 吞吐
pkgs = [p for p in glob.glob("outputs/发布包_*/*/") if os.path.isdir(p)]
print("发布包目录数:", len(pkgs))
# 分发凭证真值（排除脏前缀）
ev = glob.glob("outputs/发布包_*/多平台分发/**/分发凭证*", recursive=True)
print("分发凭证计数:", len(ev))
for p in ev: print("  ", p)
```

调度 json 分块摘要：

```python
import json
d = json.load(open(sorted(glob.glob("outputs/今日调度_*.json"))[-1]))
for k in ["mode", "quota", "track_a", "track_b", "track_c_decay",
          "track_c_autopackage", "expiry_reminders", "evidence",
          "monetization", "risk_flags", "metrics"]:
    s = json.dumps(d.get(k), ensure_ascii=False)
    print("====", k, "len", len(s)); print(s[:900], "\n")
```

## 三、判据阈值表

| 判定 | 口径 | 备注 |
|---|---|---|
| 时效压力 | days_left<30 卡数 / 总卡数 | <2% 即"到期腐坏"为假信号，转查三重停滞 |
| 三重停滞 | ① platforms 覆盖渠道集 ⊊ 矩阵渠道全集 ② 囤稿包数:日吞吐 >20:1 ③ 高 ready 分且 blocker 含"无配图"的卡数 | 三条命中任一即在报告点名列举 |
| 真闭环 | 该渠道分发凭证计数 ≥1 且近期有回填 | 0 = "躺着"；有发布无凭证 = "半闭环"（凭证自动化前不计产能） |
| 战略切割候选 | 受众与主 IP 割裂 + 停更 ≥6 个月 + 无凭证 | 三条全中才提名，切割与否归 boss |
| 变现断点归因 | 有商品无读者→流量；有读者无商品→建品产能 | 拿 monetization 块的粉丝/销售/商品状态三数区分 |
| 口径漂移 | 同一事实 ≥2 个互斥值，或同主题 spec ≥2 份无 SSoT 指针 | 逐条列"值—出现位置"对照，只建议立指针 |
| 主杠杆 | 能同时改善 ≥2 段的单一动作 | 论证链写进报告，说不清就不硬凑 |

## 四、报告骨架模板

```markdown
# 全渠道内容矩阵环境审计 YYYY-MM-DD
> 只读盘点｜数据截止 X｜凭证：分发计数 X｜六段判据见 skill reference §三

## ① 素材时效现状
（分布数字 + 时效压力判定 + 三重停滞命中项）
## ② 全渠道矩阵盘点
| 渠道 | 受众-时效适配 | 真闭环凭证 | 归类 |
（后附：多 IP 警示——若有休眠割裂 IP 单独成段）
## ③ 变现承接链路断点
（归因 + 死线 + 风控标签史）
## ④ 结构性瓶颈 Top3
1. …（证据数字）
## ⑤ 口径漂移清单
| 事实 | 值A@出处 | 值B@出处 | 建议 SSoT |
## ⑥ 操盘手结论
主杠杆：一句话。
待 boss 拍板（A/B，≤2）：Q1 … Q2 …（未拍板前报告按 X 侧假设）
已按可逆默认推进/仅建议未执行：…
```

## 五、边界与口径细节

- **与 mp-daily-ops-report**：日报回答"下一个档期发什么+怎么发"（日频、行动导向）；本技能回答"整个矩阵环境什么现状、瓶颈与断点在哪"（周/月频或 boss 喊"理清环境"时、战略导向）。日报的 metrics 可作本技能输入，反之本技能结论可反哺日报权重建议，但不改 `dispatch_config.json`（改权重另起基建轮）。
- **与 content-format-audit**：那个评估"稿子长什么样"（格式层），本技能评估"盘子怎么摆的"（矩阵层）。两者都是"只评估不动手 + 复跑不豁免"。
- **与 spec-driven-adversarial-workflow**：若 boss 拍板后要修口径漂移（立 SSoT、收敛 spec、凭证自动化），那是工程任务，走 spec 流程；本技能只负责把漂移暴露出来。
- **数字口径**：报告中所有数字带出处编号（§一表内 1-7）；粉丝数等漂移项**并列各源值不取平均不选边**。
- **工具身份**：CHANGELOG `--tool` 按实际操作工具填（qwenwork/doubao/workbuddy/zcode/cli）。

## 六、首案全记录（2026-09-16，校准基准）

来源会话：「全矩阵调度与变现闭环」（chatId 55f7e31c）。boss 原话诉求：「这个环境超杂……从专业的内容运营专家角度来看，且发布的渠道和通道有很多，不仅仅是这一个通道，综合看看。」当时分析轮实测结论（复跑时须重新核实，数字仅作对照不作豁免）：

1. **时效**：1484 卡中 days_left<30 仅 14 张、<7 仅 3 张——腐坏焦虑为假信号；真瓶颈是三重停滞：platforms 只标了公众号/掘金/CSDN/知乎/小红书（视频号/抖音/X/GitHub 空白）、囤稿 42 包 vs 群发 1 篇/天、一批 ready=90 卡死在"无配图"。
2. **矩阵**：真闭环仅两条——公众号（17 篇在发）+ GitHub 开源矩阵（15 仓 public、`dsh-xingtu-skills` 真发布，被低估的唯一非公众号闭环）；掘金半闭环（发了没回填链接）；CSDN/知乎/小红书/抖音/X 全 0 凭证躺着；**视频号/抖音实为另一条休眠娱乐 IP**（书影剧/短剧《末世狗粮》停更近一年、受众割裂）——"两个不同的人在抢注意力"，非渠道运营问题。
3. **变现**：30 粉/¥5/全销售 0；断点在建品不在流量（L2 面包多商品未建、小册正文 0/10 章）；风控有"不良信息/网赚"标签史，急推预售有限流风险。
4. **瓶颈 Top3**：分发凭证 0→1、吞吐 42:1、双 IP 抢注意力。
5. **口径漂移**：粉丝数三处打架（20/30/54）、分发相关 spec ≥4 份无 SSoT、渠道主次新旧冲突（旧 spec 推小报童、新规划改面包多）。
6. **主杠杆**：把"分发凭证 0→1"做出来——同时解吞吐、时效假信号、变现引流三件事。战略级 A/B 呈 boss：休眠娱乐号切割与否、变现开卖时点（先连更洗权重 vs 按期硬上）。
7. 当轮只读边界执行到位：全部落盘动作仅 `dig_mode=pool` 定版与标记建议，均人审后另行；分析 agent 直言「别再写第十份分发了，先建商品/补正文产能」——该"基建已够、缺执行"的判断模式值得保留。
