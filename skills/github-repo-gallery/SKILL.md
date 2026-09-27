---
name: github-repo-gallery
description: "给 GitHub 仓库做「看效果」画廊（大量可播放 demo + 截图）的可复用 SOP。覆盖 GitHub Markdown 富媒体的硬边界（<video> 被剥、只有 GIF 会自动播、reduce-motion 会让动图停在首帧、loading=lazy 被剥）、封面帧自动挑选（中部墨量指标）、ffmpeg 出 GIF 配方、以及「仓库自洽」纪律。触发词：给仓库加 demo、README 里放视频/截图、看效果画廊、demo gallery、点击就能播、仓库门面。"
description_zh: "GitHub 仓库「看效果」画廊的搭建 SOP（GIF/截图/本地播放器）"
description_en: "Build a click-to-play demo gallery inside a GitHub repo"
agent_created: true
version: 1.0.0
---

# GitHub 仓库「看效果」画廊 SOP

## 何时用

需求信号：「让访客打开仓库就知道它长什么样」「大量 demo + 截图直接放 GitHub 里」「**点击就能放**」「slogan 说清楚」。
典型对象：xingtu 矩阵里的**产品型**仓库（md2wechat / text2vido / tokenhub-bench …）。
**纯代码库不需要**——没有可看的产出就没有画廊。

---

## 0 · 先接受四条平台事实（全部实测，别重复试错）

1. **`<video>` 标签会被 GitHub 的 Markdown 清洗器整个剥掉**（渲染成空 `<p dir="auto"></p>`）。
   复现：`gh api -X POST /markdown -f mode=gfm -f context=<owner>/<repo> -f text='<video controls src="a.mp4"></video>'`
   ⚠️ 该接口返回的是 **HTML 文本**，**不要加 `--jq`**，否则 jq 报 `invalid character '<' looking for beginning of value`。
2. **`![](x.mp4)` 渲染成坏图**；点仓库视图里的 mp4 只给下载按钮。
   → **仓库内唯一「打开就动」的形态只有 GIF。**（这是平台行为，不是配置问题，绕不过去。）
3. **GIF 自动播放不是无条件的**（GitHub 官方 changelog 2022-05-19）：读者若在系统里开「减少动态效果」，
   或在 GitHub 无障碍设置里关掉自动播放，动图会**停在第一帧**并显示播放按钮
   （即返回 HTML 里那个 `data-animated-image=""` 属性）。
   → **GIF 的第一帧必须本身就是一张合格封面**，否则这部分用户只看到空白。
4. **`loading="lazy"` 会被剥掉**（`width` / `data-animated-image` 保留）→ N 张 GIF 会**同时加载**，
   做画廊必须主动压体积，不要指望懒加载兜底。

### 推论：三层结构，缺一不可

| 层 | 形态 | 覆盖的需求 |
|---|---|---|
| **GIF** | 自动播、点开可放大 | 「打开就动」——**免点击**（唯一免点击层） |
| **mp4 封面卡** | 静态封面 + 链接到文件页 | 「想看完整片 / 带声音 / 更多条」 |
| **`demo/index.html`** | 单文件零依赖本地播放器 | 「**点一下就能播**」——GitHub 做不到，本地补 |

⚠️ **不要把 `<video>` 写进 README 当"以后可能会支持"** —— 它现在就被剥掉，读者看到的是空白。

---

## 1 · 封面帧自动挑选（不要定格抽帧）

**坑**：固定抽 1.5s 会落到卡片与卡片之间的**交叉淡入**，实测得到近空白帧。

**指标**：中部 ROI 的**非白墨量**，在约 45 个时间点采样取最大值。

```python
def ink(png_path):
    a = np.asarray(Image.open(png_path).convert("RGB"), dtype=np.int16)
    h, w, _ = a.shape
    roi = a[int(0.12*h):int(0.80*h), int(0.08*w):int(0.92*w)]   # 排除上下版式条
    return float((roi.min(axis=2) < 215).mean())
```

- **正常成片：0.05–0.07；空白/坏帧：0.0000–0.0002** → 该指标**顺带能筛出坏片**，
  比肉眼翻看可靠（曾靠它发现两条历史样片整帧只有序号+水印）。
- 抽帧到内存：`ffmpeg -v error -ss <t> -i x.mp4 -frames:v 1 -f image2pipe -vcodec png -`
- 封面导出：`Image.crop` 到 9:16 后 `resize((540,960)).save(p, quality=88)`

---

## 2 · GIF 配方（实测可用）

```bash
FF=/opt/homebrew/bin/ffmpeg     # ⚠️ /opt/homebrew/bin 常不在沙箱 PATH → 必须用绝对路径
$FF -y -v error -ss <起帧> -i demo/videos/NN.mp4 -t 6 \
  -vf "fps=12,scale=640:-1:flags=lanczos,split[s0][s1];\
[s0]palettegen=max_colors=96:stats_mode=diff[p];\
[s1][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" \
  -loop 0 demo/gifs/NN_语义.gif
```

- **起帧 = 最佳帧 − 0.6 s**（保证第一帧就是正文卡，兜住 reduce-motion 用户）。
- `scale=640` + `-t 6` + 96 色 + `fps=12` → 单张约 **90–160 KB**；**九张合计约 1 MB 是可接受上限**。
- 有声音不是目标，GIF 只负责「会动」；声音与全片交给 mp4。
- 生成后**逐张验首帧**：`$FF -i x.gif -frames:v 1 /tmp/f.png` → 跑 §1 的 `ink()`，
  应落在 0.04–0.07（< 0.02 说明起帧挑错了）。

---

## 3 · 仓库自洽（引用 ≠ 拷贝）

- 画廊引用的**所有实体资产必须拷进画廊目录**（`videos/ posters/ gifs/ shots/`）。
  只写「引用自 `../samples/xxx`」＝**没做**：单独分享 `demo/index.html` 或只拷 `demo/` 时取不到。
- 命名统一 `NN_语义`（序号 = 上传/排序顺序），三套资产（videos / gifs / posters）**同名对齐**；
  改了命名方案就**一并删旧名、改所有引用**（旧名残留 = 死链）。
- 副本入库须注明 **SSoT 仍是原目录**，否则日后两边各改一版、互相漂移。
- 画廊 README 用**可点封面的 HTML 表格**（GitHub 支持 `<img width>` 与 `<table>`）；
  纯 markdown `![](a.gif)` 也行，但表格能排版九宫格。

---

## 4 · 交付前校验清单

```bash
# ① 引用零缺失（md 链接 + HTML src + ![]() 三种写法都要扫）
python3 - <<'PY'
import re, pathlib
for doc in ["README.md", "demo/README.md", "demo/index.html"]:
    p = pathlib.Path(doc); t = p.read_text(encoding="utf-8"); r = p.parent
    refs = (set(re.findall(r'src="([^"#:]+)"', t))
          | set(re.findall(r'!\[[^\]]*\]\(([^)\s#]+)', t))
          | set(re.findall(r'\]\(([^)\s#:]+)\)', t)))
    miss = [x for x in sorted(refs)
            if not x.startswith(("http", "mailto", "#")) and not (r / x.split("#")[0]).exists()]
    print(doc, len(refs), "缺失:", miss or "无")
PY
```

- **改了标题必须同步改写锚点内链**（`](#5--...)`），否则静默死链——锚点不会报错，只是点了没反应。
- 对外数字（时长 / 体积 / 条数）**回填实测值并附口径命令**，不写死；文档计数改成「以某文件为准」的点指针。
- 脱敏扫描：真名 / 拼音 / `/Users/<user>` 绝对路径 / 公司平台名（SAF-010）。
- 推送后 `gh api` 复验：远端 HEAD = 本地、`private`、目标目录条数、提交作者是品牌身份。
  沙箱内 `git push` 会被拦 → 见 skill `git-push-in-sandbox`。

---

## 5 · 常见翻车

| 现象 | 真因 |
|---|---|
| `gh api POST /markdown` 报 `invalid character '<'` | 返回是 HTML 文本，**别加 `--jq`** |
| `ffprobe: No such file or directory` | 沙箱 PATH 无 `/opt/homebrew/bin` → 用绝对路径 |
| `ModuleNotFoundError: numpy` | 用 `<工作区根>/.workbuddy/binaries/python/envs/default/bin/python`（含 numpy+PIL） |
| 九宫格动图加载慢 / 卡顿 | `loading="lazy"` 被剥 → 只能压体积（640px / 6s / 96 色） |
| reduce-motion 用户看到空白 | 首帧没挑过 → 用 §1 指标定起帧 |
| GIF 第一帧是好帧、后面是空白 | 起帧落在片头淡入区 → 起帧改取「最佳帧 − 0.6s」 |
| 分享单个 `index.html` 播不了 | 视频没拷进画廊目录（引用 ≠ 拷贝） |

---

## 6 · 已有先例（照抄结构即可）

`~/xingtu/text2vido` 的 `demo/` ——
`README.md`（§0 slogan 拆解 / §1 hero 动图 / §2 九宫格全动图 / §3 截图 / §4 真实 CLI 输出 / §5 数字口径 / §6 版权披露 / §7 相关文档）
+ `index.html`（本地播放器）+ `videos/ gifs/ posters/ shots/`。
