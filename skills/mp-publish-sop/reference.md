# mp-publish-sop · reference（坑位详解 + 可复制片段）

> 本文件是 SKILL.md 的执行附件：可直接复制的代码片段、组件结构、判定阈值。改实现去改 SSoT 工具/技能，这里只存「怎么调 + 坑长什么样」。

## 一、名片 = 后台手动插（API 不插，09-16 02:1x 定）

微信「账号名片」组件依赖编辑器运行时 wrapper class（`appmsg_card_context wx_profile_card wx-root wx_tap_card wx_card_root common-web` + data-weui-theme），API draft/add 只插内层 div 会**渲染错乱**（缺灰底卡片/箭头/原创数）。
SOP 约定：排版 HTML 与草稿 content **不含**名片；boss 后台编辑器 → 工具栏「账号名片」→ 插「关于行途」段后（10 秒）。
若未来微信 API 支持完整组件再改回自动插，并同步 DESIGN.md §六。

## 二、Step 6 排版重渲完整 snippet（@@PH + justify + 名片一次做完）

```python
import re
MD='<包>/01_正文/正文_vN.md'; HTML='<包>/02_排版HTML/公众号_发布版.html'
s=open(MD,encoding='utf-8').read()
open('/tmp/render_input.md','w',encoding='utf-8').write(re.sub(r'【配图：(.+?)】', r'@@PH:\1@@', s))
# shell: cd md2wechat && node bin/md2wechat.js /tmp/render_input.md --theme review --links keep -o "../$HTML"
s=open(HTML,encoding='utf-8').read()
s=re.sub(r'<p[^>]*>@@PH:(.+?)@@</p>', r'<p style="margin:0 0 22px 0;text-align:justify;">【配图：\1】</p>', s)
s=re.sub(r'(<li[^>]*?)text-align:justify', r'\1text-align:left', s)   # 拉宽病
# 名片：不插（boss 后台手动，见 §一）
open(HTML,'w',encoding='utf-8').write(s)
assert s.count('@@PH')==0 and s.count('【配图：')>=1
```

## 三、Step 9 回查九项 snippet（POST！GET 报 43002）

```python
import re,json,urllib.request,os,datetime
B="https://api.weixin.qq.com/cgi-bin"
secret=[t for t in re.findall(r"[A-Za-z0-9]{32}", open(SECRET_FILE,encoding='utf-8').read())][-1]
tok=json.loads(urllib.request.urlopen(f"{B}/token?grant_type=client_credential&appid={APPID}&secret={secret}",timeout=60).read())["access_token"]
def postj(u,p): return json.loads(urllib.request.urlopen(urllib.request.Request(u,data=json.dumps(p,ensure_ascii=False).encode(),headers={"Content-Type":"application/json"}),timeout=90).read())
# batchget 找最新同题稿（认 update_time）→ draft/get 取 content
# 九项：标题/摘要/字数/嵌图=b.count('<img')/占位=b.count('【配图')==0/错名=0/名片='wx_profile_card' in b/首屏图在摘要前/封面字节
req=urllib.request.Request(f"{B}/material/get_material?access_token={tok}",data=json.dumps({"media_id":thumb}).encode(),headers={"Content-Type":"application/json"})
raw=urllib.request.urlopen(req,timeout=60).read()   # 字节流；若返回 dict 即错误体
assert len(raw)==os.path.isfile(COVER) and len(raw)==os.path.getsize(COVER)
```

## 四、首屏公式（09-16 02:00 定版）

顺序：标题 → **引子图**（论点图，非装饰）→ 一句话摘要（≤60 字，信任核心=翻了谁+跑了什么+判断）→ 先说结论 → 我是谁一句 → 目录。
依据：首屏优先级 图>大字>小字；摘要与引子图是接力不是竞争；速评02 旧顺序（摘要在前）104读1分享无优势。
A/B 观察项：新公式篇 vs 旧顺序篇完读率/分享率（数据回流管道可测）。

## 五、封面三检阈值

1. 底色：纯白 `#FFFFFF` / 纯黑；fig_fit 一律 `--bg "#FFFFFF"`；纸白 #F7F5F2 弃用（偏灰，与已发 14 篇不一致）。
2. 交替：以后台「近期发表」实发封面为准；包内「上篇浅底」备注发新篇后即过期（AGENT-03 曾据此误选深底被 boss 截图纠正）。
3. 尺寸：头条封面 900×383@1x（2.35:1）；更宽（如 1080×383=2.82）被左右裁。主标 字数×字号 < 470px（content 宽），12 字用 ≤38px；改标题后重渲必 Read 眼见 + grep 残留 `<span class="em">`/旧红 span。

## 六、撞题阈值（与 mp-title-collision-rename Step 1 唯一口径）

同题判定：同对象组合 / 同框架词 / 同「怎么选·横评·对比」结构；含大媒体（澎湃/虎嗅/腾讯新闻/网易/36氪/掘金/CSDN/知乎专栏）≥3 = 🔴 回炉；1-2 小媒体 = 🟡；0 = ✅。
换题后六载体同步：正文 frontmatter+H1+引用块 / 00_标题摘要/标题摘要.md（此后 --desc 以该文件为 SSoT）/ 合集卡 / 引子图主标 / 封面三层 / 排版重渲。

## 七、通道故障决策树

```
draft/add 报 40164 → 出口 IP 不在白名单 → 停下报告 boss 加 IP（无自救）
bsk 报「未找到文章按钮」→ Chrome 后台未登录 → 停下报告 boss 登录
material/get 返回 103 字节 → 用了 GET → 改 POST 重试（别误判封面损坏）
dry-run 嵌图 <N → 占位名≠04_配图文件名 → 回 Step 6 前核占位（静默删段无报错）
草稿箱同题多份 → 认 update_time 最新 → 删旧前确认本地有底稿
日报/排期输出疑似没更新或某段为空 → 先去掉 >/dev/null 重定向跑一遍看真错误（格式串百分号未转义类异常会被静默吞掉），再查文件 mtime 是否早于最近一次运行
```

## 八、首实例凭证索引

AGENT-03《员工比功能，老板看生态：WorkBuddy、豆包工作、千问办公选型账本》：
- 十步全凭证：`outputs/发布包_2026-09/AGENT-03_.../06_发布参考/开箱操作单_2026-09-16.md`（01:00/01:23/01:34/01:56/02:00 五轮认稿记录）
- CHANGELOG 09-16 各轮（撞题换题/节标题 h2/pure 主题/纯白底/名片/首屏公式）
- 终稿 media_id 与认稿时间以操作单末行为准（草稿箱同题旧稿已回收，09-14 两份待 boss 授权删）

## 九、Step 9b/9c 三工具 pitfalls 详解（09-16 FDE-03 + 日报自动化实测）

> 承载工具：`tools/draft_visual_check.py`、`tools/mp_daily_report.py`、`tools/cover_next.py`。以下修法已进工具代码，本文**只记坑形与检查点**，改实现去改 tools/ SSoT，别在这里维护第二份。

### 9.1 stats 快照结构键 = `articles`（mp_daily_report + cover_next 同源）

- **症状**：工具能跑通不报错，但日报②段（单篇榜）为空、昨日增量恒 0；cover_next 最新实发解析不到。
- **根因**：`data/stats_YYYY-MM-DD.json` 快照是 dict，文章列表挂在 `articles` 键下；解析按 `d.get("items") or d.get("list")` 取，全部取空且不抛异常（静默）。
- **修法**：两处 load 均改为 `d.get("articles") or d.get("items") or d.get("list") or []`（兼容 list 直挂）。注意 `reward_money` 是字符串 `"0.00"`，`float()` 转换不能省。
- **复跑检查点**：新快照结构若再变，先 `python3 -c` 打印 `list(d.keys())` 对键名，别猜。

### 9.2 格式串裸 `%` 未转义 + 重定向吞异常 → 日报静默出旧文件

- **症状**：日报文件存在但内容是旧的（mtime 早于最近一次「运行」），无任何报错。
- **根因**：两层叠加——运营建议行模板 `"分享率%.0f%%>12%，值得二次群推"` 尾部「12%，」里的裸 `%` 未写成 `%%`，`%` 后跟中文逗号成为非法格式符，`%` 格式化抛 `ValueError`；而调用命令带 `>/dev/null 2>&1`，异常整个被吞，退出码非 0 没人看。
- **修法**：字面百分号一律写 `%%`（如 `（>12%%）`）。
- **复跑检查点**：怀疑「跑了但没更新」时，第一步**去掉重定向**（或改 `2>&1 | tail`）直接跑看真错误；第二步 `ls -l` 比对输出文件 mtime 与本次运行时间。定时任务侧同理——payload 命令少用 `>/dev/null`。

### 9.3 cover_next「明日」= 今日 + 1 天

- **症状**：封面交替判定把今日排期当成明日排期，输出「明日应白」实际明日应黑，结论看似合理却全错。
- **根因**：查排期表取行时用 `datetime.now(TZ)` 的 date 直接匹配「明日」行（=取成今日行）。
- **修法**：`today = datetime.datetime.now(TZ) + datetime.timedelta(days=1)`，用 +1 天的日期去排期表定位明日行。
- **复跑检查点**：跑完人工核一行输出「明日排期包」的名字是否真是明天那篇（跨零点/周末无排期日尤其易错）。

### 9.4 排期包名带书名号 ≠ 目录名 → 代号前缀模糊匹配

- **症状**：实发篇未映射时 fallback 到「今日/明日排期包」，但 `cover_tone()` 恒返 None → fallback 静默失效，工具误报「明日包缺白底」。
- **根因**：排期表里包名写作 `AGENT-03《Agent 三国杀》…`（含书名号/空格），发布包目录名是 `AGENT-03_Agent三国杀_WorkBuddy豆包千问`，`os.path.join(BASE, 发布包, pkg, "03_封面")` 的 glob 精确匹配恒空。
- **修法**：取代号前缀模糊匹配目录——`code = re.split(r"[《\s]", pkg.strip())[0]`，再对 `outputs/发布包_*/` 下目录名做前缀/包含匹配。
- **复跑检查点**：任何「按名字找目录」的逻辑，先问一句排期/台账里的名字和目录名是不是同一字符串；glob 空要当异常看，不是当无数据。

### 9.5 md2wechat 列表渲为 `<p>•` 非 `<li>` → 结构核查误判

- **症状**：draft_visual_check「延伸阅读带副注」项 ❌，人工看草稿其实正常。
- **根因**：核查按 `ext.count("<li")` 判列表结构，但 md2wechat 把 Markdown 列表渲成 `<p>• …` 段落（无 `<li>` 标签），条件恒假。
- **修法**：判定条件双取 `ext.count("<li") >= 1 or ext.count("<a ") >= 1`（工具已改）。
- **复跑检查点**：给渲染产物写结构断言前，先 grep 一份真实排版 HTML 确认标签形态——同类病还有 Step 6 的 justified 修复只命中 `<li>` 分支，`<p>` 分支是否需同样处理看实物。

### 9.6 mmbiz 防盗链：本地渲染图不显示 = 工具边界，非草稿 bug

- **症状**：draft_visual_check 整页 PNG（file:// 本地打开）里配图区域空白，眼看环节误报「嵌图丢失」。
- **根因**：草稿 content 图片 URL 是 mmbiz 域名（微信 CDN），对非微信域 referer 防盗链拒载；本地浏览器渲染拿不到图。
- **修法/约定**：眼看 PNG **只核版面顺序、样式、留白**；嵌图在位与否以 draft/get 的 `<img` 计数 N/N 为准（Step 9 回查九项已含）。要真看图就在微信客户端/后台预览打开草稿。
- **复跑检查点**：报「图没了」先分清是计数 ❌（真问题，回查占位/上传）还是仅渲染 PNG 空白（边界，放行）。

## 十、Step 1 / Step 9 建稿前三坑（09-16 FDE-03+FDE-07 双案实测）

> 承载工具：`tools/publish_brief.py`（frontmatter 门禁）、`00_标题摘要/标题摘要.md`（摘要 SSoT）、`tools/wx_draft_api.py`（建稿通道）。以下修法已进 SOP 与坑位清单（17/18/19），本节存坑形、snippet、认稿表模板。

### 10.1 frontmatter 中文 `状态:` 键硬约束（坑位 17）

- **症状**：`publish_brief.py` 输出把候选判为「状态未标注」卡在排期外，即使正文 frontmatter 明明写了 `status: 成稿 v1 · 待排版发布`。
- **根因**：门禁读 `fm.get("状态")`——只认中文键；英文 `status:` 视同缺失。FDE-03（09-16 20:4x）与 FDE-07（09-16 21:1x）两次同源踩坑。
- **修法**：就地补一行中文键，原英文键保留（不冲突，只是门禁不读）：

```bash
python3 - "<包>/01_正文/正文_vN.md" <<'PY'
import sys
p = sys.argv[1]
t = open(p, encoding='utf-8').read()
if '\n状态:' not in t:
    # 在既有 status: 行后追加中文键；值可按实际状态改（待定时发布 / 已发布 等）
    t = t.replace('status: 成稿 v1 · 待排版发布',
                  'status: 成稿 v1 · 待排版发布\n状态: 成稿 v1 · 待定时发布（草稿已建）', 1)
    open(p, 'w', encoding='utf-8').write(t)
    print('已补中文 状态 键')
else:
    print('状态键已存在，跳过')
PY
```

- **复跑检查点**：新建/迁移发布包时，frontmatter 模板默认写中文 `状态:`；旧包批量补键前先 `grep -L "^状态:" outputs/发布包_*/*/01_正文/*.md` 清点。

### 10.2 摘要 SSoT 表格取值规则（坑位 18）

- **症状**：建稿命令带 `--desc "$(grep ...)"` 抓摘要，草稿建成后打开发现摘要是 `| # | 标题 | 引擎 | 理由 | 长度 | 自评 |` 这种表头行，需重推。FDE-07 首建即中招。
- **根因**：`00_标题摘要/标题摘要.md` 常以表格并列多候选摘要（摘要1推荐 / 摘要2 / 摘要3），首个匹配「摘要」关键字的行往往是表头，不是候选正文。
- **修法（强口径）**：
  1. **禁 grep 首个匹配行取 desc**。
  2. `Read` 全文 → 定位标为「摘要1推荐」（或 boss 拍板行）的**单元格正文**取字。
  3. `--desc` 显式传字符串字面量，别用 `$(...)` 命令替换（命令替换的失败模式是静默传空/传错，肉眼看不出来）。

```bash
# 反例（FDE-07 首建踩坑写法）
DESC=$(grep -A2 -E "^摘要|摘要:" "$P/00_标题摘要/标题摘要.md" | head -1)   # ❌ 抓到表头

# 正例：Read 后手工确认单元格正文，字面量传参
python3 tools/wx_draft_api.py --pkg "$P" \
  --title "Palantir 的 FDE 和 Echo：AI 落地最后 100 米，为什么要两个人" \
  --desc  "Palantir 值近 4000 亿美元，靠的不是模型，是两个人：一个懂（Echo），一个造（Delta）。…" \
  --cover-file "$P/03_封面/封面_炭黑红_双角色.png"
```

- **复跑检查点**：dry-run 输出摘要字段后先肉眼核一遍——摘要长度、语义与标题呼应；不像人话（含 `|`、`#`、字段名）就是抓错了。

### 10.3 wx_draft_api 只 add 无 update/get + 认稿表模板（坑位 19）

- **症状**：改了摘要/封面重推，草稿箱出现两份同题；boss 打开旧那份看到废稿，误以为管线出错。
- **根因**：`tools/wx_draft_api.py` 通道**只调 `draft/add`**——微信官方 API 有 `draft/update`、`draft/get`，但本工具未实现。故每次「重推」=**新增一份**，不是覆盖；旧份留在草稿箱。回查也只能靠 `mp-prepublish-draft-verify` 或 reference §三 snippet 自建。
- **修法（强口径）**：
  1. 建稿**前**把 title/desc/cover/嵌图 N/N 全 dry-run 核完再一次真建，尽量避免重推。
  2. 一旦重推（改摘要/改封面/改标题），**必产认稿表**交 boss，明确"开哪份、删哪份"。
  3. 回收按 `update_time` 认旧份调 `draft/delete`（Step 9 现有第 8 坑位口径）——**不认 media_id 前缀**（同批前缀相同）。删前确认本地有底稿。

**认稿表模板**（复制到操作单 `06_发布参考/开箱操作单_<日期>.md`）：

```markdown
## 草稿箱认稿表（<日期> <时间>）

| 开这份（最新、内容对） | 删/忽略这份（旧或错） |
|---|---|
| **<代号>** `…<media_id 后 4 位>`（摘要对、<字数>字、<封面描述>、嵌图 <N/N>） | <代号> `…<media_id 后 4 位>`（<废弃原因，如：摘要误抓表头>） |
| **<代号>** `…<media_id 后 4 位>`（<关键描述>） | <代号> `…<media_id 后 4 位>`（<废弃原因，如：昨晚 20:40 旧版>） |

回收命令（认 update_time）：
- 走 `mp-prepublish-draft-verify` skill 的回收步骤（该 skill 已封装 draft/delete），或按 §三 snippet 自建 token → `POST {B}/draft/delete?access_token={tok}` body `{"media_id": "<旧稿 media_id>"}`。
- **`tools/wx_draft_api.py` 实测无 `--delete` 参数**（只有 `draft/add`），别指望它删。
- 删前确认本地 `<包>/01_正文/正文_vN.md` 存在。
```

- **复跑检查点**：认稿表必须包含 media_id 前 4 后 4 位（草稿箱 UI 显示的是尾缀，全串太长肉眼对不上）+ update_time 精确到分 + 应删旧份的**废弃原因**（防误删最新那份）。缺任一项=boss 打开时可能认错。

### 10.4 首案凭证

- FDE-03（09-16 20:4x→21:1x）：英文 status 键卡门禁 → 补中文键 → v4 终版 7991 字建稿（media `…BIssO`），旧 20:40 稿（`…8EJ4`）待回收。
- FDE-07（09-16 21:1x）：同源补中文键 → 首建摘要误抓表头（media `…r9f75p-`）→ Read 后取「摘要1推荐」重推（media `…BNc9`）→ 认稿表交 boss。
- 详细过程见 chatId `55f7e31c-029e-4a7d-a379-b147dcce2450` 09-16 21:11~21:19 段。

## §十一 TOKEN-08 省 token 横评（2026-09-21 深夜，12 轮重建新增坑位）

### 封面坑（6 个）
- **"行路小人"品牌符号被否**——封面要干净直接放内容，不要抽象小人。
- **icon 不用深色卡片包裹**——直接放原图，不要边框/卡片背景。
- **不要右上角水印**——"公众号·行途"水印 boss 不要。
- **不要合集 tag**——封面不放"省 token 系列"这种 tag。
- **icon 破损/不对**：claude.png 是竖 banner、cursor.png 是横 banner、kiro.svg 是纯紫块、pi 原来是 Google 三色块。**取官方 icon 用 iTunes Search API 或官网 favicon，不用 ImageSearch**。
- **Google 图标不对**——pi.dev 官方 favicon 是黑色 π 形几何 logo。

### 排版坑（4 个）
- **字间距撑开病**——md2wechat 默认 justify，中文段字间距忽宽忽窄。全部改 left，grep 残留=0。
- **空行/换行太多**——配图占位嵌套 p、双层 margin 压到单层 14px。行距 1.8→1.7。
- **空 p 必删**——md2wechat 把 MD 空行渲成空 p，正则 `<p style="[^"]*">\s*</p>` 全删。
- **文末分割线消失**——`border-top:1px solid #d8dce1` 微信编辑器点编辑就洗了。**改用 margin 留白（margin-top:40px）**，微信洗不掉 margin。

### 内容坑（5 个）
- **真实数据贴论点上**——不要单独放一段"说个数据"，融入对应论点位置。
- **截图引导语方向**——图在引导语上面就说"看一下..."，不要说"下图..."。
- **Codex 分类**——大家用 Codex 主要是桌面端形态，不要硬归到"终端 Agent"档。
- **脱敏必查**——雇主名和具体业务名都要模糊化（"某电商平台"），发前跑 privacy_scan。
- **本地 token 统计**——从 `~/.claude/projects/**/*.jsonl` 扫 usage 字段统计。

### 文头结构坑（3 个）
- **目录位置**——过渡段（"我自己用过其中大部分。从最早的 Trae 开始..."）不要被目录劈成两半。正确：使用实录 → 过渡段（一整段）→ 目录 → 第 1 章。
- **HTML 字符串替换不匹配**——样式属性和换行对不上时 replace 静默失败。先 grep 看实际内容，再按行号操作。
- **CC Switch 截图位置**——放对应论点旁边当论据，不放文头。

### 完整复盘
详见 `outputs/发布包_2026-09/TOKEN-08_省token横评_9个编程Agent/06_发布参考/复盘_Token08发布20坑.md`
