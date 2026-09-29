---
name: mp-prepublish-draft-verify
description: 公众号发文前凭证闭环核验：事实回源 → 图文同步修正 → 建稿前 dry-run 预检（嵌图 N/N）→ 建稿入草稿箱 → API 回查 → 回收缺陷稿。当用户说"检查这篇文章能不能发/发前核验/确认配图和封面有没有错/重建草稿/稿子里产品名对不对/榜单数据有没有漏/dry-run/建稿前预检/嵌图几张对不对/排版主题对不对/图文密度够不够/法律合规扫描/有没有极限词或侵权/标题撞题/标题重名核查/封面主标断行溢出孤字"时触发。建稿前预检含 md2wechat 灰框占位卡还原（@@PH@@）、排版主题判定（数 d71a1b）、PUB-048 图文密度门禁、legal_compliance_scan 第⑦法律门禁。专治"稿件看似就绪、实则名字错/榜单漏/图会静默消失/图变灰框卡/主题不对/密度不达标/带法律风险"，补齐 PUB-051 只核事件时效、不核产品名与榜单位次的缺口。与 wechat-mp-publish（bsk 后台自动化发布）互补：本技能走 API 通道做核验闭环，不管后台 UI 操作；上游对接 pub-infographic-supplement 交棒；Step 3e 只做撞题判定，🔴 撞题的换题执行（候选与拍板、六载体同步、封面重渲、重建草稿）走 mp-title-collision-rename；Step 2 含封面主标改动后的断行孤字与残留旧 span 自检。
version: 1.6.0
---

# 公众号发文前凭证闭环核验（mp-prepublish-draft-verify）

## 适用前提

> **范围守卫**：本技能专为「行途」工作区的发布包结构（六目录规范）与专属工具（`tools/wx_draft_api.py` 等）设计。当前工作区不存在这些工具/目录时（如公司侧仓），声明不适用并停止——不套用本流程去操作其他项目的公众号或发布链路，避免个人项目凭据路径、口径渗入非本空间会话。

- 工作区已有发布包目录（六目录规范：`01_正文/ 02_排版HTML/ 03_封面/ 04_配图/ 06_发布参考/ …`）与工具：`tools/wx_draft_api.py`、`tools/fig_fit.py`、`tools/privacy_scan.py`、`tools/legal_compliance_scan.py`、`tools/content_gate.sh`（含第⑦法律门禁）、`tools/changelog_append.py`、`tools/safety/safe-delete.sh`。
- 上游 `pub-infographic-supplement`（工作区技能 `.agents/skills/`）持有 `@@PH@@` 占位还原脚本与图文密度补图逻辑（Step 6e / Step 1）；本技能只做发前判定与路由，**不复制其脚本**。
- 公众号 AppSecret 存于工作区凭据文件（路径写入操作单/配置，**绝不硬编码进任何会提交的文件、绝不上公网**）。
- 核心原则：**完成判定查凭证，不问模型自述**。每一步以"命令输出 / 落盘文件 / 字节比对结果"收口。

## 工作流（六步，按序执行）

### Step 1 事实回源（不只正文，全载体核名字）

用户一句质疑（如"文章里没有 XX 吧"）即推翻"已就绪"结论，逐类核：

1. **产品名/关键名词**：对正文 MD、封面 HTML 源、每张配图的 HTML 源、已渲染 PNG **全部** grep 错名候选（如 `千问工作` vs 正确 `千问办公`）。名字错在封面/配图源上时，只改正文=没改。
2. **外部硬数据**（月活、榜单名次、并购/上线事件）：逐条 WebSearch 回源，记录来源+验证程度。注意"官方渠道查无"≠"非官方产品"（如豆包工作走桌面端+飞书集成，App Store 无独立 App 属正常）。
3. **漏掉的头部对象**：先定它是**并列项还是分类项**再补写。用排名/榜单口径解释自己的选择标准 = 自贬（等于承认自己选的是三四五名）+ 标准失据（读者追问入选依据）。正确处置是把并列关系改成分类关系（各盘各称王），而非删掉（回到漏榜）也非加第四张卡（不可比硬比）。

### Step 2 图文同步修正

改 HTML 源后重渲并亲眼确认：

```bash
# 必须从工作区根目录 + 相对发布包的完整路径跑，fig_fit 按内容高度量裁
python3 tools/fig_fit.py "outputs/发布包_YYYY-MM/<包名>/03_封面/<封面>.html" --width 900 --bg "#F7F5F2"
```

然后 **Read 渲染出的 PNG 逐张看图**——不是看源码猜。封面比例核 2.35:1（如 1800×766），非标准比例会被后台左右裁切。深浅底交替**以后台实际已发状态为准**，不信包内旧备注。

**封面主标若发生改动，必做断行与残留 span 自检**（换题全管线与字号-字数口径 SSoT 在 `mp-title-collision-rename`，此处只贴症状+去向）：① 主标**字数 × font-size 必须 < content 宽**，超宽会断出孤字（实测 12 字 @46px 断出孤零零一个「态」→ 字号降 38px 解决）；② 批量替换文案后 grep title2/subtitle 的**残留旧 `<span>`**——class 未必是记忆里的那个（实测残留 `class="em"` 而非 `hl`，按猜的 class 写 assert 会 count=0 假通过，必须先读源行看实际标签再替换）；③ `fig_fit` 重渲后 Read PNG **眼见**确认：单行不断字、副行干净无串字。

### Step 3 建稿前预检（占位 / 灰框 / 主题 / 密度 / 撞题，五查齐才进建稿）

任何一项不过都不建稿，修好回本步复检。**只贴症状 + 去向，`@@PH@@` 重渲脚本与密度补图 SSoT 在 `pub-infographic-supplement`，本技能不复制。**

**3a. 占位名与实际文件逐一比对（防静默删段）**

```bash
# 正文占位与 04_配图/ 实际文件名逐一比对，任何一条对不上都会被建稿工具静默删除整段
grep -oE '【配图：[^】]+】' 01_正文/正文_vN.md
ls 04_配图/
```

**3b. md2wechat 灰框占位卡检测（防图会静默消失 + 灰框漏进正文）**

若本包走过 md2wechat 重渲排版（换主题/批量重渲），`【配图：x】` 会被渲成灰框占位卡（含「公众号后台此处插入」提示），`wx_draft_api` 找不到文本占位 → dry-run 嵌图 0/N，且正文里漏一堆灰框。发前必查：

```bash
H="02_排版HTML/公众号_发布版.html"
grep -c "公众号后台此处插入" "$H"        # 命中 >0 = 有未还原的灰框占位卡
grep -c "@@PH:" "$H"                     # 命中 >0 = @@PH@@ 标记忘了还原回正文
grep -c "<p>【配图：" "$H"               # 应 = 正文占位数（占位已还原回 HTML 供建稿识别）
```

任一不对 → **交棒 `pub-infographic-supplement` Step 6e 的 `@@PH@@` 标记法**（渲染前 `【配图：x】`→`@@PH:x@@`、md2wechat 渲、渲染后 HTML 里 `@@PH:x@@`→`<p>【配图：x】</p>`，残留标记 assert=0）。本技能只判定与路由，不重写脚本。

**3c. 排版主题判定（数 d71a1b，凭证不信备注）**

评测风 `review` 排版以主色 `#d71a1b`（红）为指纹；理念成长文 `pure` 主题（#1a1a1a）应无红。用计数判主题与文风是否匹配，别只看文件名或包内旧备注：

```bash
grep -oc "d71a1b" 02_排版HTML/公众号_发布版.html   # review/评测风 应 >0；pure 应 =0
```

计数与本篇目标主题不符 → 排版没渲对，回 `pub-infographic-supplement` Step 6e 用正确 `--theme` 重渲（Boss 要求排版对齐已发评测风时，此项是硬凭证）。

**3d. PUB-048 图文密度预检（防文字墙）**

```bash
P="outputs/发布包_YYYY-MM/<包名>"
W=$(wc -m < "$P/01_正文/正文_vN.md" | tr -d ' ')
N=$(ls "$P/04_配图/"*.png 2>/dev/null | wc -l | tr -d ' ')
python3 -c "print(f'$N 图 / $W 字 = {round($N/($W/1000),2)} 图/千字')"
```

对标 **PUB-048**：门禁 **≥1 图/千字**；A 档长文（≥8000 字）8~12 张；每大节至少 1 张。低于门禁 → **交棒 `pub-infographic-supplement`**（按文字墙节补信息图，非均匀撒图），补完回本步复检；已达标即停，不动。

**3e. 标题撞题核查（门禁位；🔴 = 标题回炉，不建稿）**

本步只负责**卡在建稿前**：对候选标题跑工作区技能 `mp-title-collision-rename` Step 1（WebSearch 双查取并集 → 按该步判定表定 🟡/🔴/✅），🔴 即不建稿。**阈值口径与查法唯一承载在 `mp-title-collision-rename/`，本技能不重复维护数字与清单**。撞题后的换题执行（候选与 boss 拍板 → 六载体同步替换 → 封面文案与字号重渲看图 → 排版重渲 → 重建草稿并回收旧标题稿）也归该技能，改完回本步复检。凭证「同题 N 篇（大媒体 M）+ 名单」写进核验报告。

### Step 4 建稿入草稿箱（先 dry-run 预检，再正式建稿）

**4a. dry-run 预检（必做，不带缺陷建稿）**：

```bash
python3 tools/wx_draft_api.py --pkg "<发布包目录>" \
  --title "<标题>" --desc "<摘要>" \
  --cover-file "<发布包目录>/03_封面/<终版封面>.png" --dry-run
```

核对输出「嵌图 N/N」：**分子必须等于分母，且分母 = Step 3 数出的正文【配图：…】占位数**。任何一张没被识别（如 N/M、M>N）都说明占位名与实际文件对不上——建稿时会**静默删除整段且无报错**，必须回 Step 3 修占位后重跑 dry-run，全对才进 4b。

**4b. 正式建稿**：去掉 `--dry-run` 重跑同一条命令。记录返回的 draft media_id。Secret 由 `--secret-file` 指向凭据文件读取。

### Step 5 API 回查（wx_draft_api 无 list/get 能力，自调微信 API）

用下方内联片段（按需改 MID/路径）：核 **错名计数=0、嵌图数、字数、封面逐字节一致**。

```python
import re, json, urllib.request
APPID = "<公众号 appid>"
# 从工作区凭据文件提取 32 位 secret，勿硬编码
secret = [t for t in re.findall(r"[A-Za-z0-9]{32}", open("<凭据文件路径>", encoding="utf-8").read())][-1]
B = "https://api.weixin.qq.com/cgi-bin"
tok = json.loads(urllib.request.urlopen(
    f"{B}/token?grant_type=client_credential&appid={APPID}&secret={secret}", timeout=60).read())["access_token"]

def post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

# 1) 取草稿详情：核错名计数、字数、嵌图数（content 内 mmbiz URL 计数）
d = post(f"{B}/draft/get?access_token={tok}", {"media_id": "<DRAFT_MID>"})["news_item"][0]
assert "千问工作" not in d["content"] and "千问工作" not in d["title"]

# 2) 封面逐字节比对：永久素材取图 material/get_material 必须 POST，media_id 进 JSON body。
#    该接口返回图片字节流，不能用上面的 post()（它对图片 0x89 起首做 json.loads 会崩），另用 post_raw() 读原始字节。
#    ⚠ 防误判：若改用 GET（media_id 拼进 query），接口返回约 103 字节的 {"errcode":43002,"errmsg":"require POST"} 错误体，
#       这不是"封面损坏/取不出"，而是调用方式错了。取真图判 PNG 魔数 \x89PNG 起首；字节数很小且以 { 开头 = 错误响应，别据此回炉改稿。
def post_raw(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    return urllib.request.urlopen(req, timeout=60).read()

raw = post_raw(f"{B}/material/get_material?access_token={tok}", {"media_id": d["thumb_media_id"]})
local = open("<本地终版封面.png>", "rb").read()
assert raw[:4] == b"\x89PNG", f"未取到真图（疑 103 字节错误体）: {raw[:120]!r}"
assert raw == local, f"封面不一致 {len(raw)} vs {len(local)}"

# 3) 正文嵌图：从草稿 content 提取 mmbiz URL 下载，逐张 Read 看图（新图旧图只能靠眼睛定）
for u in re.findall(r"data-src=\"(http[^\"]+)\"", d["content"]):
    fn = u.split("/")[-1].split("?")[0][:24] + ".png"
    open(fn, "wb").write(urllib.request.urlopen(u, timeout=60).read())
    print(fn)

# 4) 列草稿箱 + 回收缺陷稿（本工具是唯一 delete 通道）
lst = post(f"{B}/draft/batchget?access_token={tok}", {"offset": 0, "count": 20})
for it in lst["item"]:
    print(it["media_id"][:16], it["update_time"], it["content"]["news_item"][0]["title"])
# 确认 media_id + 更新时间双因子命中后才删：
# post(f"{B}/draft/delete?access_token={tok}", {"media_id": "<旧缺陷稿MID>"})
```

### Step 6 回收缺陷稿 + 认稿留痕（收口凭证）

0. **boss 疑「草稿没调整/还是旧的」时，先全量列草稿箱同题份数，再谈改**：跑片段 4 的 `draft/batchget`，过滤同题/同系列标题的全部份数，输出「标题 + update_time」清单。旧稿残留是最常见误判源——AGENT-03 本轮 boss 后台点开的是 09-14 旧标题旧排版稿，01:00 新稿其实一直在箱、回查全绿，差点被当成"没调整"回炉。定位后明确告诉 boss「认 <时间戳> 那份」，不要急着动正文。**删旧稿不可逆，须 boss 明确授权后代执行**（本地发布包有底稿 ≠ 可自作主张删）。
1. 回收上一份缺陷稿（见片段 4）。**删前必对**：草稿箱同题多份的 media_id 前 16 位可能完全相同，后台无法靠前缀区分——**只能认更新时间**。
2. 更新开箱操作单：认稿时间（精确到分，如"发 09-15 22:02 那份"）+ 终版 media_id + 字数 + 嵌图数 + 应删旧稿清单。
3. 门禁复跑（隐私 + 法律，全绿才算完）：
   - 隐私：`python3 tools/privacy_scan.py --fail-fast` 全绿（铁律 10）。
   - **法律合规基线（第⑦门禁，🆕）**：`python3 tools/legal_compliance_scan.py "<发布包或正文.md>"`，或一键聚合 `bash tools/content_gate.sh "<发布包>"`（其⑦项即 legal_compliance_scan）。判级 🔴阻断/🟠需改/🟡人工核/✅过；**退出码 0（无🔴）才放行**，🔴 必须改后重跑。🟡 是人工核清单（含「读《AI 生成合成内容标识办法》条文原文」），逐条给 boss 判断、不自动改稿、不出具法律意见。
4. 回写 CHANGELOG（`tools/changelog_append.py`，`--tool qwenwork`）。
5. 临时验证目录走 `bash tools/safety/safe-delete.sh <目录>` 回收（禁 rm）。

## Pitfalls（本轮及历史实测坑）

- **配图占位名 ≠ 实际文件名 → 建稿工具静默删除整段**，无任何报错。Step 3 必做。
- **错名印在图片上**：正文改对了，封面/配图 HTML 源还错着——回源必须 grep 全载体。
- **md2wechat 重渲把占位变灰框卡**：换主题/批量重渲后 `【配图：x】` 被渲成灰框占位卡（含「公众号后台此处插入」），dry-run 嵌图 0/N 且灰框漏进正文。用 `@@PH@@` 标记法（Step 3b → 交棒 `pub-infographic-supplement` Step 6e），本技能不重写脚本。
- **主题判定只信 `d71a1b` 计数不信备注**：包内旧备注/文件名写"评测风"不代表渲的就是 review。`grep -oc "d71a1b"` review 应 >0、pure 应 =0，计数不符即回炉重渲（Step 3c）。
- **用错 logo 与写错产品名是同一类事故**：qoder.com 是阿里 AI 编程平台 Qoder，≠ 千问办公，图标不可混用。取官方 App 图标用 iTunes Search API（`term=<名>&country=cn&media=software`，取 512px `artworkUrl`，三家同源同尺寸），**勿用 ImageSearch**（搜回全是带背景的文章配图）。拿不准就渲染并排 probe 图亲眼核。
- **macOS 无 `timeout` 命令**：网络请求用 `curl -m <秒>` 或 Python `urlopen(timeout=…)`。
- **fig_fit 相对路径跑错目录**静默无输出：从工作区根跑、传相对发布包全路径、渲染后必须 Read 图确认。
- **`draft/update` 换封面报 40007**（thumb 字段校验苛刻）：不折腾，直接 `wx_draft_api.py` 重建新稿 + 回收旧稿，更可靠。
- **PIL 不一定可用**：查尺寸用 macOS 自带 `sips -g pixelWidth -g pixelHeight`。
- **本地文件 ≠ 草稿内容**：包内 PNG/MD 改对了不代表草稿箱里那份对了，一切判断以 `draft/get` 回查 + 字节比对为准；同批上传的 media_id 前缀可能相同，认新旧稿只认 `update_time`。
- **完成判定查凭证不问模型**：历史"门禁全绿"记录不作豁免，每轮对候选包**现跑**门禁（PUB-027 去AI味 / privacy_scan / 错名 grep）。
- **回查封面用 GET 取图的假警报（会诱导错误结论）**：微信永久素材接口 `material/get_material` 要求 **POST**（media_id 进 JSON body）。若用 GET（media_id 拼 query），返回约 103 字节的 `{"errcode":43002,"errmsg":"require POST"}` 错误体——极易被误读成"封面损坏/草稿取不出"。真图判 PNG 魔数 `\x89PNG` 起首、字节数正常；字节很小且以 `{` 开头 = 调用方式错了，不是草稿缺陷，别据此回炉改稿。图片字节流不能套 `post()`（它对 0x89 做 json.loads 会崩），须用返回原始字节的 `post_raw()`（Step 5 片段已内置）。
- **草稿箱旧稿残留 = "看起来没调整"的最常见误判源**：同题多份并存时，boss 后台点开的往往是旧标题旧排版稿，误以为新改动没生效（AGENT-03 实案：09-14 两份旧稿还在，01:00 新稿回查全绿）。遇"草稿没调整"的质疑，先按 Step 6.0 列同题全部份数（标题+update_time）认清新旧再谈改；**删旧稿不可逆，须 boss 授权后代执行**。
- **标题撞题靠直觉拦=最后一道防线已失守**：AGENT-03「三国杀」与腾讯新闻等 ≥10 篇同题，是 boss 发布前夜凭感觉问出来才拦住的——本应 Step 3e 机器拦。撞题的代价不止流量：原创审核比对全网增加摩擦、独有论点被用滥框架词埋没。判定归本步，**换题执行（六载体同步 + 封面重渲 + 重建草稿）全管线走 `.agents/skills/mp-title-collision-rename/`**，本技能不双份维护其清单与脚本。

## Verification（本技能自身的成功凭证）

- dry-run 预检：「嵌图 N/N」全对且 N = 正文占位数，才允许正式建稿；
- 占位还原：排版 HTML 无「公众号后台此处插入」灰框卡、`@@PH:` 残留 = 0、`<p>【配图：` 计数 = 正文占位数（Step 3b）；
- 主题判定：`grep -oc "d71a1b"` 计数与目标主题一致（review/评测风 >0，pure =0，Step 3c）；
- 图文密度：图/千字 ≥1（PUB-048），未达标已交棒 `pub-infographic-supplement` 补图并复检（Step 3d）；
- 错名 grep：正文 + 封面 HTML + 配图 HTML 全载体命中 0；
- API 回查四项：标题/摘要、错名 0、嵌图 N 张与本地一致、封面 `raw == local` 逐字节 True；
- 草稿箱状态：目标稿唯一，认稿时间已写入操作单，缺陷稿已 delete 且 batchget 复查不在列；
- 撞题核查（Step 3e）：两次 WebSearch 的同题计数 + 大媒体名单已写入操作单/核验报告；🔴 级撞题已回炉换题并完成六载体同步 + 重建草稿 + 回收旧稿；
- 封面主标改动自检（Step 2）：字数 × font-size < content 宽已核（无孤字断行）、title2/subtitle 残留旧 span grep = 0（class 以源行实际为准）、重渲后 Read 眼见单行干净；
- CHANGELOG 已回写、`privacy_scan --fail-fast` 全绿、`legal_compliance_scan` 无🔴（退出码 0，🟡 已登记人工核）、临时目录已回收。
