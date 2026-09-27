---
name: pub-infographic-supplement
description: 公众号长文图文密度补齐管线：按 PUB-048 做图/千字密度对标 → 定位文字墙节 → 素材只取正文原文写信息图 HTML（家族配色：纯白 #FFFFFF 底、黑红灰主色，DESIGN.md §四；1080px 视口 @2x）→ fig_fit 渲染 → 逐张 Read 亲眼看图 → MD + 排版HTML 双同步插占位（before/after 锚点规则）→ 交给 mp-prepublish-draft-verify 走 dry-run/建稿/回查/回收。当用户说"图文偏少 / 密度不够 / 补几张图 / 文字墙太长 / A档要 8-12 张 / 每大节至少 1 张讲解图 / 信息图 / 讲解图 / 补配图 / 图/千字不达标"时触发。与 mp-prepublish-draft-verify 互补：本技能管上游（该不该补、补哪节、图怎么做、占位怎么插），后者管下游（能不能发、名字对不对、嵌图几张）。
version: 1.2.2
---

# 公众号长文图文密度补齐（pub-infographic-supplement）

## 适用前提（范围守卫，必读）

> **守卫规则**：本技能专为「行途」工作区的公众号发布包结构（PUB-031 六目录规范）与专属工具设计。开工前先读工作区根 `AGENTS.md`，**含「行途」才继续**；否则声明不适用并停止——不套用本流程去操作其他项目的公众号或发布链路，避免个人项目凭据路径、口径渗入非本空间会话。

- 工作区已有发布包目录（六目录：`01_正文/ 02_排版HTML/ 03_封面/ 04_配图/ 06_发布参考/ …`）。
- 必备工具（相对工作区根路径）：`tools/fig_fit.py`、`tools/wx_draft_api.py`、`tools/de_ai_flavor_check.py`、`tools/privacy_scan.py`、`tools/changelog_append.py`。
- 必备规则底座：`PUB-048`（图文密度门禁）、`B-009`（不编造）、`PUB-031`（发布包六目录）、`PUB-027`（去 AI 味量化门禁）。
- **视觉 SSoT = 工作区根 `DESIGN.md`**（§一 三原色 / §四 信息图）：本技能内任何色值与 `DESIGN.md` 冲突时，**以 `DESIGN.md` 为准并回改本技能**（§八 变更纪律）。
- 核心原则：**完成判定查凭证，不问模型自述**——每一步以「命令输出 / 落盘文件 / 逐张 Read 结果」收口。

## 与 mp-prepublish-draft-verify 的边界（互补，不重叠）

| 阶段 | 归属技能 |
|---|---|
| 该不该补图（密度对标） | **本技能** |
| 补哪节（文字墙定位） | **本技能** |
| 图怎么做（HTML 信息图 + fig_fit 渲染 + 逐张 Read） | **本技能** |
| 占位怎么插（MD + 排版 HTML 双同步、before/after 锚点） | **本技能** |
| 建稿前 dry-run 嵌图 N/N 预检 | mp-prepublish-draft-verify Step 4a |
| 建稿入草稿箱 / API 回查 / 回收旧稿 | mp-prepublish-draft-verify Step 4b~6 |
| 事实回源（产品名 / 榜单数据） | mp-prepublish-draft-verify Step 1 |

**交接点**：本技能 Step 6 结束（占位已双同步插好、逐张 Read 通过），Step 7 显式调用 mp-prepublish-draft-verify 收口。**不重复实现** dry-run / 建稿 / 回查 / 回收逻辑。

## Step 1 密度对标（先量化，再决策）

**目的**：把「感觉图少」变成可算的数字，对标自家门禁 + 已发正例反例。

**跨包对照表脚本**（boss 问"最近图文密度整体如何"时先跑这个）：

```bash
cd ${WORKSPACE} && for d in outputs/发布包_2026-*/[A-Z]*/; do
  name=$(basename "$d")
  n=$(ls "$d/04_配图/"*.png 2>/dev/null | wc -l | tr -d ' ')
  md=$(ls "$d/01_正文/"正文_v*.md 2>/dev/null | sort -V | tail -1)
  [ -z "$md" ] && continue
  w=$(wc -m < "$md" | tr -d ' ')
  ratio=$(awk "BEGIN{printf \"%.2f\", $n/($w/1000)}")
  status=$(awk "BEGIN{print ($ratio>=1) ? \"✅\" : ($ratio>=0.7 ? \"⚠️\" : \"❌\")}")
  echo "$status $name : ${n}图 / ${w}字 = $ratio 图/千字"
done | sort
```

**单包速算**：

```bash
P="outputs/发布包_YYYY-MM/<包名>"
# 字数（以 MD 为准，非微信字符）
W=$(wc -m < "$P/01_正文/正文_vN.md" | tr -d ' ')
# 图数（04_配图 下的 PNG，排除 _assets 子目录）
N=$(ls "$P/04_配图/"*.png 2>/dev/null | wc -l | tr -d ' ')
python3 -c "print(f'$N 图 / $W 字 = {round($N/($W/1000),2)} 图/千字')"
```

**对标基准（PUB-048）**：
- 门禁：**≥1 图/千字**
- A 档长文（≥8000 字）：**8~12 张**
- 每大节至少 1 张讲解图

**已发正例反例**（做判断时引用，SSoT 在 `data/manual_metrics.json`）：
- ✅ 正例：MODEL-02 速评02 · 8 图 / 6360 字 = **1.26** → 最近达标样本
- ✅ 正例：PEC 复盘 · 12 图 / 9.8k 字 = 1.22 → 198 读、26 分享（家族最好成绩之一）
- ❌ 反例：FDE-02 · 1 图 / 12.7k 字 = 0.08 → 121 读、完读率低（触发 PUB-048 立规）
- ❌ 反例：AGENT-03 初稿 · 4 图 / 9380 字 = 0.43 → 触发本管线补至 8 图 = 0.85
- ❌ 反例：FDE-03 · 2 图 / 8418 字 = 0.24 → 待补

**结论口径**：低于门禁 = 必须补；达标但节覆盖不均 = 可补可不补（问 boss）；已达标 = 停止，不动。

## Step 2 文字墙节定位（不均匀撒图）

> boss 09-14 纠偏：「密度要服务信息，不均匀撒图」——只补在文字墙最长、论点最该可视化的节。

```bash
# 切节 + 逐节字数 + 标注是否已有图
python3 - <<'PY'
import re, os
P = "outputs/发布包_YYYY-MM/<包名>"
md = open(f"{P}/01_正文/正文_vN.md", encoding="utf-8").read()
# 按 ^## |^# |^\d+\. 切节（依实际正文格式调整）
parts = re.split(r"(?m)^(##? .+|^\d+\.\s.+)$", md)
imgs = set(re.findall(r"【配图：([^】]+)】", md))
print(f"当前占位数：{len(imgs)}")
# 逐节字数排序，top-N 是文字墙候选
sections = []
for i in range(1, len(parts), 2):
    title, body = parts[i].strip(), parts[i+1] if i+1 < len(parts) else ""
    has_fig = "【配图：" in body
    sections.append((len(body), title, has_fig))
sections.sort(reverse=True)
for w, t, has in sections[:10]:
    print(f"{'✅' if has else '❌'} {w:>5}字  {t[:40]}")
PY
```

**决策规则**：
- **候选 = 无图 + 字数 top-N**（N = 目标补图数，通常 2~4 张）
- **可视化价值**：三栏对比 / 数字卡 / 卡片矩阵 / 概念示意 四类之一能承载
- **不均匀撒图**：不为了达标把每节都塞一张；覆盖节数 ≥ 目标数即可

**产出**：一张决策表，落到操作单 `06_发布参考/开箱操作单_*.md`：

| 节号 | 节标题 | 字数 | 图类型 | 拟图名 |
|---|---|---|---|---|
| 5 | 三个工具里的真实会话 | 890 | 三栏对比 | 05-三工具会话对比.png |

**AskUserQuestion 时机**：候选 ≥ 3 类不同图型 / 补图数 ≥ 4 / 时间盒紧张（凌晨或发布前 8h 内）——先给 boss 拍板补几张、补哪节，再动手。

## Step 3 素材取自正文原文（B-009 硬约束）

**红线**：图上每个数字、每句引文、每个论断都必须能在正文找到出处；找不到的一律不写、不编。

```bash
# 逐节 sed 出原文，做图上素材清单
sed -n '/^5\. /,/^6\. /p' "$P/01_正文/正文_vN.md"
```

**素材清单模板**（每张图动手前先写这个）：

```
拟图：05-三工具会话对比.png
素材出处（逐条对回正文行号）：
- 豆包工作 = 内容活    ← L99「用豆包工作写稿、改标题」
- WorkBuddy = 流水线   ← L102「WorkBuddy 上跑定时任务、看数据」
- Claude Code = 造工具 ← L105「Claude Code 里在写 skill、改工具」
- 底句「同一个我在三个工具里干完全不同的活」 ← L97 节标题
禁止上图：正文没写的对比维度（如「价格」「学习曲线」）
```

**节号核对**：切完节先跑 `grep -n '^## \|^\d+\. ' 正文_vN.md` 拿实际节号——**曾把「第 6 节」误当「第 7 节」导致图放错位置**。

**宣传口径标注**（诚实红线）：
- 官方宣传数字（提效倍数、时长、行数）→ 图上必须标 **「公开宣传口径，非作者实测」**
- 本地会话引文 → 图上标 **「引文来自作者本地会话记录（已脱敏）」**
- 榜单数据 → 图上标 **「数据来源：AICPB 2026.07 榜单」** + 期数

## Step 4 HTML 信息图设计（家族规范 + 五类模板）

**家族视觉规范**（SSoT 在工作区根 `DESIGN.md` §一/§四，与 04 榜单图 / 03 封面同族）：

- 底色 `#FFFFFF`（纯白）——**纸白 `#F7F5F2` 已于 09-16 弃用**（偏灰，与 boss 已发 14 篇「白就是纯白、黑就是纯黑」不一致）
- 主色 `#1A1A1A`（纯黑）+ `#d71a1b`（红，重点/警示）+ 灰阶（`#7A8087` 次文本 / `#A8ADB3` 弱文本 / `#E6E8EA` 分隔线与卡片边）
- **纯白底上的卡片分层**（改纯白后的必带坑）：卡片底仍是 `#FFFFFF`，与页面同色 → 靠 `border:1px solid #E6E8EA` 勾边 + `border-top:4px solid #d71a1b` 做红色层级，**不靠底色差**（FDE-03 实测方案）
- `body { width: 1080px; padding: 44px 52px 38px; }`
- 字体 `-apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", Arial, sans-serif`
- `-webkit-font-smoothing: antialiased`
- fig_fit 出图 2160 宽 = **1080 视口 @2x**（PUB-048 硬要求）

**图片资源铁律**（跨发布包坑）：
- HTML 里 `<img src="_assets/xxx.png">` 是**相对 HTML 所在目录**
- fig_fit 用 Chrome headless 打开 `file://` URL，跨目录不共享 `_assets/`
- 引子图/配图需要 logo 时，**必须先 `cp 03_封面/_assets/*.png 04_配图/_assets/`**，否则破图
- **cp 前先 `ls` 实测 assets 实际落点、cp 后再 `ls` 验证到位——不凭记忆**（AGENT-03 首案：凭「记得在配图目录下」的假设直接渲，实际 `_assets` 在 `03_封面/`，白渲一张三 logo 全破；完整修复管线见 `reference.md` §二 渲染前置块）
- 破图核验方式：Read PNG 肉眼看（脚本不会报错，图会静默显示为占位符）

**五类信息图模板**（详见 `reference.md`）：

| 类型 | 用途 | 关键结构 |
|---|---|---|
| 三栏对比 | 三个工具/方案/生态位并列 | 三列 grid，每列 logo + 一句定位 + 3~4 条要点 |
| 数字卡 | 提效数据 / 榜单数字 / 关键指标 | 大字号数字（72~96px 红/黑）+ 小字说明 + 来源标注 |
| 卡片矩阵 | 三件事 / 五检查 / 多维度清单 | 2×N 或 3×N grid，每卡标题 + 2~3 行说明 |
| 概念示意 | 两层框架 / 趋同 vs 分化 / 生态位 | 分层横条 + 空位红虚线框 + 底句 |
| **引子图**（首屏论点图） | **全文第一张图，3 秒给判断** | **结论先行**：标题 → **通栏一句话结论横条**（黑底白字 + 亮红关键词）→ 主体三栏 → source；**底部不再放重复结论**（`reference.md` §2.5） |

> **引子图与正文配图的结构不对称是刻意的**：引子图在首屏（一句话摘要之后、先说结论之前，`DESIGN.md` §五），读者还没读正文，论点是它唯一功能 → 结论必须前置；正文配图读者已读到该段 → 结论放 `.bottom` 收束即可。**别把正文图的底句也统一搬到顶上**。

**HTML 骨架**（复制起步，具体见 `reference.md`）：

```html
<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;background:#FFFFFF;font-family:-apple-system,"PingFang SC",sans-serif;
     -webkit-font-smoothing:antialiased;padding:44px 52px 38px}
h1{font-size:34px;font-weight:800;color:#1A1A1A;margin-bottom:8px}
.sub{font-size:16px;color:#7A8087;margin-bottom:28px}
.accent{color:#d71a1b}
.source{margin-top:24px;font-size:13px;color:#A8ADB3;border-top:1px solid #E6E8EA;padding-top:12px}
</style></head><body>
<h1>标题</h1>
<div class="sub">副标题 / 论点句</div>
<!-- 主体：三栏 / 数字卡 / 卡片矩阵 / 概念示意 -->
<div class="source">素材出处：正文第 N 节 · <span class="accent">宣传口径标注（如需）</span></div>
</body></html>
```

**落盘位置**：`$P/04_配图/0X-图名.html`（编号续 `04_配图/` 已有 PNG 序号）。**引子图固定用 `00-引子图-<主题>.html`**——`00` 前缀保证它排在正文配图 `01` 之前，与它在首屏的位置一致（Step 6 插占位时它的锚点在「一句话摘要」之后、`先说结论` 之前，不在任何一节内）。

## Step 5 fig_fit 渲染 + 逐张 Read 核验（凭证）

```bash
cd ${WORKSPACE}
python3 tools/fig_fit.py "$P/04_配图/0X-图名.html" --width 1080 --bg "#FFFFFF"
```

**渲染后必做**：对每张 PNG 单独调用 Read 工具**亲眼看一次**——不是看 HTML 源码猜。

**逐张核验清单**：
- [ ] 图片资源全部加载（无破图占位符）
- [ ] 数字与正文一致（回 Step 3 素材清单逐条对）
- [ ] 宣传口径已标注「非作者实测」（如需）
- [ ] 引文标注「已脱敏」（如需）
- [ ] 底句有力（3 秒能读懂论点）
- [ ] 视觉与家族一致（**纯白 `#FFFFFF` 底** / 黑红灰 / 无花哨色；**不得出现纸白 `#F7F5F2` 偏灰底**）
- [ ] 纯白底上卡片有层次（`#E6E8EA` 细边或顶部红线勾出，非「白压白」糊成一片）
- [ ] **引子图专项**：结论横条在 DOM 里紧跟 `h1`、位于主体之前（结构前置，不是视觉错觉）；横条通栏；底部无重复结论条
- [ ] 出图宽度 2160px（1080 @2x）

**核验失败的处置**：改 HTML → 重跑 fig_fit → 再 Read。**Read 通过前不进 Step 6**。

## Step 6 MD + 排版 HTML 双同步插占位（关键坑最多）

### 6a. 占位形态

- MD 里：`【配图：0X-图名.png】`（单独成段，前后各空一行）
- 排版 HTML 里：`<p style="margin:0 0 22px 0;text-align:justify;">【配图：0X-图名.png】</p>`
- **wx_draft_api.py 靠 MD/HTML 里的 `【配图：x】` 文本替换成 mmbiz `<img>`**——占位丢失 = 静默删段（不报错）

### 6b. before/after 锚点规则

| 场景 | 锚点模式 | 锚点选择 |
|---|---|---|
| 图插在段前 | `before` | 该段首 10~20 字（含标点） |
| 图插在段后 | `after` | 该段末句（含句号） |
| 引号字节纠缠失败 | 换 `before` | **下一节标题**（如 `**第二件事：数据安全合规`） |

### 6c. 双同步插入脚本（防呆版）

```python
# 落盘前 assert count==1，写盘前失败 = 安全
P_html = '<p style="margin:0 0 22px 0;text-align:justify;">'
INS = [
    # (图名, MD 锚点, HTML 锚点（可与 MD 不同）, 模式)
    ("05-三工具会话对比.png",
     "看出区别了吗？办公 Agent 里我是在",
     "看出区别了吗？办公 Agent 里我是在",
     "before"),
    ("06-老板三问数字卡.png",
     "**第二件事：数据安全合规",      # MD 用粗体标记
     "第二件事：数据安全合规",         # HTML 里粗体已渲成 <strong>，锚点去 **
     "before"),
    ("07-两种物种两笔预算.png",
     "后者是给公司建能力。两件事都要做，但它们是两笔不同的预算。",
     None,  # None = 与 MD 锚点相同
     "after"),
]

for fig, md_anc, html_anc, mode in INS:
    html_anc = html_anc or md_anc
    # --- MD 侧 ---
    md = open(f"{P}/01_正文/正文_vN.md", encoding="utf-8").read()
    assert md.count(md_anc) == 1, f"MD 锚点 count={md.count(md_anc)}: {md_anc[:30]}"
    ph_md = f"\n\n【配图：{fig}】\n\n"
    md_new = md.replace(md_anc, ph_md + md_anc) if mode == "before" \
               else md.replace(md_anc, md_anc + ph_md)
    open(f"{P}/01_正文/正文_vN.md", "w", encoding="utf-8").write(md_new)
    # --- HTML 侧 ---
    h = open(f"{P}/02_排版HTML/公众号_发布版.html", encoding="utf-8").read()
    assert h.count(html_anc) == 1, f"HTML 锚点 count={h.count(html_anc)}: {html_anc[:30]}"
    ph_h = f'{P_html}【配图：{fig}】</p>'
    # HTML 里 before = 锚点所在 <p> 之前插新 <p>；after = 锚点所在 </p> 之后插新 <p>
    # 简化：找到锚点后，向前/向后寻到最近的 <p>/</p> 边界插入
    # （具体实现见 reference.md 完整脚本）
```

### 6d. 引号字节坑（BCI 已录）

- 中文引号 U+201C `"` / U+201D `"` vs 直引号 `"` 肉眼难辨
- heredoc 里 `\u201c` 转义与原文字节可能对不上 → assert count=0 失败
- **处置**：先 `python3 -c "s=open(...).read(); i=s.find('关键字'); print(repr(s[i-6:i+20]))"` 拿确切字节，再决定锚点；仍纠缠则**换下一节标题做 before 锚点**（标题里没有引号）

### 6e. md2wechat 重渲支路（仅在改排版主题时用）

**坑**：md2wechat 会把 `【配图：x】` 渲成灰框占位卡（含「公众号后台此处插入」提示），wx_draft_api 找不到文本占位 → 嵌图 0 + 正文里一堆灰框。

**处置**（`@@PH@@` 标记法）：

```bash
# 1) 渲染前：MD 里 【配图：x】 → @@PH:x@@
python3 -c "
import re
s = open('$P/01_正文/正文_vN.md', encoding='utf-8').read()
s = re.sub(r'【配图：(.+?)】', r'@@PH:\1@@', s)
open('/tmp/render_input.md', 'w', encoding='utf-8').write(s)
"
# 2) 补完图后重新排版——09-27 起走一键脚本，不要手动跑 md2wechat
python3 tools/render_wechat.py --pkg "$P" --keywords "词1 / 词2 / 词3"
python3 tools/prepublish_html_check.py --pkg "$P"
# （render_wechat.py 自动处理：占位替换/md2wechat渲染/颜色/justify/空p/h2通栏/tail_v5）
print('占位还原:', h.count('【配图：'), '/ 残留标记:', h.count('@@PH:'))
"
```

**验证**：`grep -oc "【配图：" 公众号_发布版.html` = MD 占位数，`grep -oc "@@PH:" = 0`。

### 6f. 双同步验证

```bash
echo "MD 占位数:"; grep -oc "【配图：" "$P/01_正文/正文_vN.md"
echo "HTML 占位数:"; grep -oc "【配图：" "$P/02_排版HTML/公众号_发布版.html"
echo "04_配图 PNG 数:"; ls "$P/04_配图/"*.png | wc -l
# 三者必须相等
```

## Step 7 交给 mp-prepublish-draft-verify 收口

Step 6 双同步验证通过后，**显式调用** `mp-prepublish-draft-verify` 走：

1. Step 4a：`python3 tools/wx_draft_api.py --pkg "$P" --title "..." --desc "..." --cover-file "..." --dry-run` → 核「嵌图 N/N」（N = 总图数，含新补 + 原有）
2. Step 4b：去 `--dry-run` 正式建稿，记录 draft media_id
3. Step 5：API 回查（错名 0 / 占位残留 0 / 字数 / 封面字节 / 嵌图数）
4. Step 6：回收旧稿（`safe-delete.sh` 或 API 删草稿）
5. 门禁复跑：`de_ai_flavor_check.py` + `privacy_scan.py --fail-fast`（插占位后正文变了必须重跑）
6. 操作单更新：`06_发布参考/开箱操作单_*.md` 记新 mid + 字数 + 嵌图数 + 密度算式
7. CHANGELOG 回写：`python3 tools/changelog_append.py --type "🆕" --path "$P" --desc "补 N 张信息图，密度 X→Y，覆盖 M 节" --tool qwenwork`

**不重复实现** dry-run / 建稿 / 回查 / 回收逻辑——那是 mp-prepublish-draft-verify 的职责。

## 常见坑清单（Bad Case Index）

| 坑 | 症状 | 处置 |
|---|---|---|
| `_assets/` 跨发布包不共享 | HTML 引 logo 破图（占位符） | `cp 03_封面/_assets/*.png 04_配图/_assets/` 后重渲 |
| 引号字节 U+201C/U+201D 纠缠 | assert count=0 | 先 `repr()` 拿确切字节；仍不行换下一节标题做 before 锚点 |
| md2wechat 重渲把占位变卡片 | dry-run 嵌图 0/N + 正文里灰框 | 用 `@@PH@@` 标记法（Step 6e） |
| 均匀撒图 | 密度达标但图无信息量 | 违 boss 09-14 纠偏，只补文字墙最长节 |
| 图上数字无正文出处 | 编造 / 夸大 | 违 B-009，回 Step 3 素材清单核 |
| 宣传口径未标注 | 读者误认为作者实测 | 图上必标「公开宣传口径，非作者实测」 |
| 节号误判 | 图插到错误节 | Step 3 前跑 `grep -n '^## \|^\d+\. '` 拿实际节号 |
| Read 只看 HTML 源码 | 破图 / 排版错位漏检 | Step 5 每张 PNG 必须单独 Read 一次 |
| MD 单同步（漏 HTML） | 排版稿无占位 / 嵌图失败 | Step 6f 三数相等才算通过 |
| 断言前直接写盘 | 部分插入 = 半坏状态 | 全部 assert count==1 通过后才 write |
| 视口错 | 用了 750px 或竖图 900x1600 | PUB-048 强制 1080px 视口 @2x；复用旧图入库前也要重渲，禁窄视口竖图 |
| 跳过 dry-run 直接建稿 | API 回查发现嵌图 3/8 | 建稿后进草稿箱再改要回收重建，代价 5 倍。**dry-run 是硬闸门**，不过绝不建稿 |
| 引子图沿用正文配图的「底句收尾」结构 | 首屏只看到三个 logo / 一张结构图，判断埋在图最下方，读者 3 秒内拿不到论点 | 按 `reference.md` §2.5 **结论先行**重排：标题 → 通栏结论横条 → 主体；且删掉底部重复结论（一图一论点）。AGENT-03 `00-引子图-三家生态位.html` 即此坑实锤（boss 09-16 指令重排） |

## 完成判定（凭证清单）

任务完成的**充要条件**（缺一不可）：

- [ ] 密度算式（补图前 → 补图后）已写入操作单
- [ ] 每张新图有 Read 记录（不是「渲染完了」的自述）
- [ ] MD 占位数 = HTML 占位数 = 04_配图 PNG 数
- [ ] `wx_draft_api --dry-run` 输出「嵌图 N/N」且 N = 总图数
- [ ] 建稿后 API 回查：错名 0 / 占位残留 0 / 字数 / 封面字节
- [ ] 门禁复跑（`de_ai_flavor_check` + `privacy_scan --fail-fast`）未劣化
- [ ] 旧稿已回收（草稿箱总数 = 预期）
- [ ] CHANGELOG 回写（`--tool qwenwork`）+ 操作单更新

**任何一条不满足 = 未完成**，即使模型自述「已做完」。

## 相关资产

- `reference.md`：四类信息图 HTML 模板骨架 + 完整双同步插入脚本 + 素材标注用语库
- 工作区规则：`rules/RULES.d/01_PUB*.md`（PUB-048 / PUB-031 / PUB-027）
- 工作区工具：`tools/fig_fit.py`、`tools/wx_draft_api.py`、`tools/de_ai_flavor_check.py`、`tools/privacy_scan.py`、`tools/changelog_append.py`
- 下游技能：`~/.qwenworkcn/skills/mp-prepublish-draft-verify/SKILL.md`
- 已发正例参考：`outputs/发布包_2026-09/AGENT-03_Agent三国杀_WorkBuddy豆包千问/04_配图/`（8 图完整家族）

## 版本记录

- **v1.2.2**（2026-09-16 10:44~11:0x，qwenwork）：**两批合并条目**（原记 v1.2.0，因并行会话已占 v1.2.1 引用「1.2.0」，本批按顺位让号为 1.2.2，防号序与时序倒挂）。
  - **① 配色口径纸白 `#F7F5F2` → 纯白 `#FFFFFF`**：对齐工作区根 `DESIGN.md` §一（纸白列入禁用：偏灰，与 boss 已发 14 篇「白就是纯白、黑就是纯黑」不一致）与 §四（信息图底 = 纯白，`fig_fit` 一律 `--bg "#FFFFFF"`）。落点：frontmatter description、Step 4 家族视觉规范、HTML 骨架、Step 5 渲染命令与逐张核验清单，`reference.md` 配色速查表 + 五类模板底色/卡片/边线/黑条前景字 + §七 checklist。**连带修正**：灰阶 `#666`/`#999`/`#E5E1DA` → `DESIGN.md` §一 与 FDE-03 实测值 `#7A8087`/`#A8ADB3`/`#E6E8EA`；暖米 `#F0EDE7` → 中性浅灰 `#F5F6F7`；旧橙红 `#F2644F` 列入禁用（PUB-045 旧色板，现行强调色 `#d71a1b`）；新增**纯白底卡片分层**口径（卡片与页面同色 → `#E6E8EA` 细边 + `border-top:4px` 红线，不靠底色差，取自 FDE-03 已过眼凭证，防「白压白」）；适用前提加 `DESIGN.md` 视觉 SSoT 指针与冲突裁决（§八 变更纪律）。
  - **② 引子图模板按「结论先行」重排**（boss 同轮换题指令追加）：新增 `reference.md` **§2.5 引子图（首屏论点图）**——标题 → **通栏一句话结论横条**（黑底白字 + 亮红关键词）→ 主体三栏 → source，**底部不再放重复结论**，附三条自检与「为何只有引子图结论前置、正文配图保留底句」的不对称说明（防后续统一优化把正文图底句也搬顶上）；Step 4 模板表四类 → **五类**，落盘位置定 **`00-引子图-*.html`** 前缀约定（与首屏位置一致，不计入「每大节 ≥1 张」但计入总图数）；Step 5 核验清单加引子图专项；坑清单加「引子图沿用底句收尾结构」一行。基准 = AGENT-03 已发 `00-引子图-三家生态位.html`（原结论压在 `.foot` 最底部）的重排版，**色值按现行而非实物旧橙红**。
  - **同批外部修正**：`mp-title-collision-rename` 封面重渲 `--bg "#F7F5F2"` → `#FFFFFF`、`AGENTS.md` 触发表纸白表述、`LEDGER.md`（`tools/skill_ledger.py` 重生）。
  - **触发原因**：技能内留旧纸白与 `DESIGN.md`/`mp-publish-sop`（09-16 已改纯白）成双口径，产图配色会跑偏；引子图结论埋底部导致首屏拿不到判断。**凭证**：`outputs/发布包_2026-09/AGENT-03_*/06_发布参考/开箱操作单_2026-09-16.md` 01:56 轮（10 张 HTML 改色重渲、封面字节 107107 回查一致）+ `FDE-03_AI落地四个阻力/04_配图/*.html` 实测 `background:#FFFFFF`；§2.5 模板经 `fig_fit` 实渲 + 逐张 Read 通过（预览落 `.tmp_preview/`，不动已发包）。改前快照 `.backups/20260916_104422_信息图配色纸白改纯白-改前快照.tar.gz`。
- **v1.2.1**（2026-09-16，qwenwork）：`reference.md` 补 `_assets/` 相对路径渲染前置专坑块（§二 模板开头，AGENT-03 引子图首案：引子图 HTML 在 `04_配图/`、assets 在 `03_封面/_assets/`，首渲三 logo 静默破图——fig_fit 不报错，只 Read 可见；修复三步 = ls 实测落点 → mkdir+cp 进 HTML 目录再 ls 验证 → 重渲 + 逐张 Read）。连带三处：① 本 Step 4 铁律加「cp 前后各跑 ls、不凭记忆」防呆条；② reference §七 渲染前 checklist 首条改 ls 实测口径；③ reference §九 主技能/reference 路径修正为工作区 `.agents/skills/`（09-16 迁出全局池后的腐烂指针）。reference.md 升 1.0.1。块内 fig_fit 示例 `--bg` 按现行纯白口径书写。**触发**：技能进化建议（chatId mu2m4nmqdbyqpnvt），boss 确认四项执行；改前快照 `.backups/20260916_013319_pub-infographic-supplement技能patch前快照.tar.gz`。
- **v1.1.0**（2026-09-16 00:53，qwenwork）：吸收同分钟并行副本 `.agents/skills/mp-figure-density-audit/` 的四条独家增量——① Step 1 跨包对照表 bash 脚本（一次扫全部发布包，输出 ✅/⚠️/❌ 状态）；② MODEL-02 速评02 · 1.26 图/千字 正例数据（原表只有 PEC 一个正例，缺最近达标样本）；③ BCI 表加「视口错」（PUB-048 强制 1080px @2x，复用旧图入库前重渲）；④ BCI 表加「跳过 dry-run 直接建稿」（草稿箱回收重建代价 5 倍）。副本已 safe-delete 至工作区回收站 `20260916_005317_mp-figure-density-audit`。**触发原因**：boss 在两个并行会话里分别请求创建同功能技能，命名撞车（B-044 多 Agent 副本腐烂同源）；收拢原则：SSoT 只留一份，独家内容反向 patch，副本 safe-delete 而非 rm。
- **v1.0.0**（2026-09-16 00:45）：初版从全局池 `~/.qwenworkcn/skills/pub-infographic-supplement/` 迁入工作区（boss 拍板避免污染公司侧会话），加 `reference.md` 四类模板 + 完整脚本 + 用语库。

<!-- public-sync: 2026-09-27 | 脱敏版本 | 源 .agents/skills/pub-infographic-supplement -->
