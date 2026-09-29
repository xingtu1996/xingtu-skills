---
name: brand-icon-sourcing
name_en: Brand Icon Sourcing
name_zh: 官方品牌图标取源
description: Source and verify real official brand icons/logos for covers, illustrations, and publish packages. Primary channel is the iTunes Search API (term+country=cn, 512px artworkUrl); ImageSearch only yields article illustrations, never clean logos. Use when the user asks for a product's official logo/icon, brand icons for a cover, or verifying which icon belongs to which product.
description_en: Source and verify real official brand icons/logos for covers, illustrations, and publish packages via the iTunes Search API with visual verification. Use when the user asks for official product logos or icon verification.
description_zh: 为封面、配图、发布包获取并核验某产品的真实官方图标/logo。首选 iTunes Search API（term+country=cn，artworkUrl 换 512px）；ImageSearch 只出文章配图不可当 logo。当用户说找logo/官方图标/品牌图标/封面要放产品图标/这个图标是哪个产品的时使用。
argument-hint: 给出产品名列表与落盘位置，如「找 WorkBuddy、豆包、千问办公 三家官方图标，入发布包 03_封面/_assets/」
argument-hint-en: Provide product names and destination, e.g. "fetch official icons for X, Y, Z into the publish package cover assets folder"
argument-hint-zh: 给出产品名列表与落盘位置，如「找三家官方图标入发布包封面资产目录」
user-invocable: true
---

# 官方品牌图标取源（brand-icon-sourcing）

## 适用 / 不适用

**适用**：需要某产品的**真实官方图标/logo**——封面放品牌 logo、配图标注产品、对比图需要各品牌图标。
**不适用**：AI 生成图像（走 `media-generation`）；只要文章氛围配图而非精确品牌标识时 ImageSearch 即可，无需本流程。

## 取源优先级（严格按序）

1. **iTunes Search API（首选）**——来源统一、尺寸高清、卖家名可核验归属
2. **官网静态资源 / favicon（备选）**——注意 SPA 回落陷阱（见下）
3. **ImageSearch（禁作 logo 源）**——返回的全是文章配图（带背景带文字），只能用于普通配图

## 第一步：iTunes Search API 取图

```bash
python3 - <<'PY'
import json, urllib.request, urllib.parse
for kw in ["千问办公", "WorkBuddy", "豆包"]:          # 换成目标产品名
    u = "https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": kw, "country": "cn", "media": "software", "limit": 3})
    d = json.loads(urllib.request.urlopen(u, timeout=25).read())
    for r in d["results"]:
        print(kw, "|", r.get("trackName"), "|", r.get("artistName"),
              "|", r.get("artworkUrl100", "").replace("100x100bb", "512x512bb"))
PY
```

要点：
- `country=cn` 锁中国区；`artworkUrl100` 字符串把 `100x100bb` 替换为 `512x512bb`（或 256/1024）即得高清官方图标
- **读 `artistName` 核验卖家归属**（如 Tencent / 字节系公司名），卖家对不上 = 不是目标产品，弃用
- 多个候选产品名并行查，同源同尺寸，一次拿齐

## 第二步：官网抓取（仅 API 查不到时）

`curl -sL` 抓首页 HTML，grep `og:image` / favicon / `.svg|.png` 引用。下载后**必须核验内容**：透明底白字 PNG 在白底上"看似空白"，需垫深色底再看。

## 陷阱清单（每条都是真实踩过的坑）

- **同名异产品**：域名/名字相似 ≠ 同一产品。案例：`qoder.com` 是阿里 AI 编程平台 **Qoder**（绿色 logo），≠ 千问办公（QwenWork）。拿错 logo 与写错产品名是同一类事故。任何拿不准的候选，先 WebSearch 核实产品归属再用
- **SPA 回落**：JS 渲染站点的任何图标路径都可能原样返回首页 HTML（特征：返回 `text/html`、字节数与首页相同）。识别后即放弃该路径，换 API 或从 HTML 内部 grep 真实资源链接
- **无独立 App ≠ 无此产品**：部分产品无独立 App Store 应用（如某些产品的桌面端/网页端形态）。查无结果时回退官网路径，不要据此怀疑产品真实性
- **ImageSearch 误区**：搜"XX 官方 logo"出来的全是文章配图，不能当封面图标用，别再试第二次

## 第三步：视觉核验（不可跳过）

完成判定查凭证不问印象——图标必须**眼见为实**：

1. 把所有候选图标（含不同来源的同产品候选）写进一张并排 HTML，每个下方标注来源与候选名
2. 用工作区渲染器出探针图（如有 `tools/fig_fit.py`：`python3 tools/fig_fit.py 探针.html`；无则任意 HTML→PNG 渲染或 PIL 拼图均可）
3. **Read 探针图逐张核验**：形状/配色/文字与该产品官方形象一致？卖家名与视觉是否互证？存疑候选直接弃用，宁缺毋错

## 第四步：落盘规范

- 核验通过的图标入发布包资产目录：`<发布包>/03_封面/_assets/`（或对应配图的 `_assets/`），HTML 以**相对路径**引用
- 文件命名 `<产品>-logo.png`，同产品多尺寸不重复存
- 在素材留档（如 `07_作者素材/` 或资产目录内 `来源.md`）记录**来源 URL + 卖家名 + 核验日期**，供后续事实回源

## 验证成功的标准

- 每个入库图标都有：卖家归属（artistName 或官网域名）+ 视觉核验记录（探针图 Read 结论）
- 正文/封面中出现的每个品牌名与其图标**一一对应**，无同名异产品混入
- HTML 引用路径在包内可解析，无绝对路径硬编码
