# reference — 公众号阅读来源与限流恢复诊断

SKILL.md 的附表与实测凭证。阈值口径以 `qw-data-diag` 为准，本文件只承载「怎么判 / 判过什么 / 落什么盘」。

## 一、datacube 错误码决策全表

| errcode | 含义 | 处置 |
|---|---|---|
| `0` | 通了 | 走 API 取来源结构，进 Step 3 打标 |
| `48001` | api unauthorized（**账号无 datacube 权限**） | 个人订阅号典型值 → **通道 B 死刑**，回退 bsk（Step 2），并落 CHANGELOG 钉死，勿再撞 |
| `40164` | IP 不在白名单 | **配置问题非权限**：让 boss 后台加本机出口 IP（`curl -s ifconfig.me`），重打；不要误判成无权限 |
| `42001` | access_token 无效/过期 | 缓存坑：`mv /tmp/mp_access_token.json /tmp/mp_access_token.stale.$(date +%s).json` 换张新 token 再打 |
| `40066` | invalid url | 该接口路径/名可能已变；其余接口仍 48001 则整通道死刑结论不变 |
| `61503` / date 相关 | 参数形态不对 | 探针内置单 `date` 参数重试 |

## 二、通道 B 死刑实测凭证（2026-09-16，本技能首案来源）

- 会话 chatId `55f7e31c-029e-4a7d-a379-b147dcce2450` 实跑 `tools/mp_datacube_probe.py --date 2026-09-15`：
  - 第一次：`/tmp` 旧 token → `42001`（挪缓存换 token）。
  - 换新鲜 token 后：**全部 6 个 datacube 接口 `48001 api unauthorized`**（`getarticleread/share/total/summary/getusersummary/...`），`getarticlebizsummary` 报 `40066`。
  - **全程无 `40164`** → boss 确已放开 IP 白名单；墙是**权限**不是白名单。
- 结论：个人订阅号**拿不到 datacube 数据分析 API 权限**，「阅读来源结构 / 99%」只存在于后台「图文分析→阅读来源」网页，能抓它的只有 bsk 只读通道。此结论已带时间戳落 `CHANGELOG.md`（type 📊）。
- 教训：boss 追问「不是可以直接通过 API 抓么」时，**用实调证据回**（48001 全灭），不空口说「API 不行」。

## 三、stats_*.json 打标 schema（增补 read_source，不覆盖原结构）

既有 `data/stats_<date>.json` 顶层含 `date`/`pulled_at` + `articles[]`（每篇 `read`/`share` 等，**无来源结构**）。本技能在其上**新增** `read_source` 块：

```json
{
  "ref_date": "2026-09-15",
  "pulled_at": "2026-09-16T14:20:00+08:00",
  "data_delay": "T+1",
  "source_page": "图文分析→阅读来源",
  "channel": "bsk",
  "read_source": {
    "推荐": 0.053,
    "朋友圈": 0.82,
    "公众号会话": 0.09,
    "好友": 0.0,
    "搜一搜": 0.02,
    "历史消息": 0.0,
    "其他": 0.017
  },
  "note": "占比之和应≈1；缺失维度记 null 并在 note 说明，不补 0 假装采到"
}
```

- `pulled_at` 用带时区 ISO8601（Asia/Shanghai, UTC+08:00）。
- `ref_date` = 数据日期（T+1：09-16 能拉到的最新完整数据日 = 09-15）。
- `channel` 取值 = 数据来源层级，溯源时一眼辨可信度：`api`（datacube，个人订阅号通常拿不到）/ `bsk`（只读抓来源页）/ `manual-screenshot`（扩展没连、boss 截图+日期回传人工记账）。
- 单日快照不足以判限流——**跨日累积**才是洗权重曲线。

## 四、推荐占比健康基线与洗权重对照（口径引 qw-data-diag，此处只留参照点）

- **已知的限流期基线（09-14 复盘）**：`朋友圈 82% / 推荐仅 5.3%` → 流量几乎全靠私域转发，**推荐池未激活 = 仍在限流**。
- 判读方向：**推荐占比持续回升** = 洗权重见效、限流松动；**长期趴在个位数且朋友圈占比畸高** = 尚未解除。
- 具体「恢复到百分之几算解除」的阈值以 `qw-data-diag` / 运营台账口径为准；本技能不擅自定死数字（防单一信号绑架）。
- 洗权重手段：连更纯技术/科普 8–10 篇约两周（避开「逆袭/高薪/暴富/网赚」措辞，防二次打标签）。

## 五、bsk 抓来源页要点（机械细节交棒 wechat-mp-analytics）

- 生命周期：`$BSK session start --no-focus`（记 **4 位小写码** id，如 `wjky`）→ 作用域命令带 `--session <id>` → **成功/失败都** `$BSK session stop <id>`。
  - 正确提取会话号：`grep -oE '\b[0-9a-z]{4}\b'` 并过滤 `warn|info|http|json|true` 噪声词。**勿**用 `[0-9a-f]{8,}` 之类 8 位十六进制正则——那抓到的是 `bsk browsers` 的浏览器实例号（如 `ffb51c99`），拿去 `--session` 会假报 `session not registered`，误导成"扩展没连"。
- **`navigate` 偶发 30s 超时但 `evaluate` 仍能读到已加载页**：故 `session start → navigate → evaluate(判登录态：读 URL 是否含 `token=` 且无登录按钮)` 应封装在同一条脚本内、同一个会话号一路到底；拆成多次调用既易抓错会话号，又易在调用间被回收（日志里 `session removed: user closed Agent Window` = Agent Window 一关会话即没，属人为可控，趁窗口开着跑）。
- 定位用可见文本 `evaluate` 点击，**不硬编码 observe 的 `@eN`**（快照相关会变）。
- `(no active sessions)` 且起不来已登录会话 → 不硬抓。**尤其 `session start` 停在 `waiting for browser extension to connect… <4位配对码>`（如 `cpkm`）＝扩展没握手**（不同于上面「8 位实例号误判」——那个扩展其实连着、只是解析错；这个是扩展真没连）：请 boss 在 Chrome 的 bsk 扩展弹窗填码/点连接，**别在本侧循环重试**（每回干等 ~90s）。连不上走人工兜底——boss 发「阅读来源」页**截图 + 日期**，按真数记账、`channel` 标 `manual-screenshot`、仍打全 `ref_date/pulled_at`；这比直接标「待核」更能留住洗权重趋势。都拿不到才转「待核」并告知 boss 需其侧 bsk 登录。
- 数据以后台页面为准；口头「99%」不与页面数字混用，除非回源确认同一维度。

## 六、常见坑（BCI 同源）

- **别先撞 API 再回退**：Step 1 就是省这一步；48001 已知死刑，任何 agent 再撞纯属浪费额度与 boss 时间。
- **别把 40164 当无权限**：那是白名单，放开即可，误判会错杀通道。
- **别臆造来源数字**：盘上无源 = 标「待核」，把口头说法当事实是最易犯的幻觉。
- **别只出一天快照就下「解除/未解除」结论**：洗权重是趋势，样本不足就明说不足。
- **token 缓存过期 ≠ 通道死**：先换 token 再判定。
- **别把 8 位实例号当会话号**：`ffb51c99` 是 `bsk browsers` 的浏览器号，会话号是 4 位小写码；用错 → 假报 `session not registered`，白折腾一轮还误判"扩展没连"。
- **别在扩展没握手时反复 `session start`**：`waiting for browser extension to connect…`＋配对码＝要 boss 手动在扩展里配对，不是重试能解的；空转几轮还误判"抓不了"，直接转人工截图兜底（截图+日期回传，标 `manual-screenshot`）留住数据。
