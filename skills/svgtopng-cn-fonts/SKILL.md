---
title: "SVG 转 PNG（含中文）— macOS 兜底链路"
summary: "把 SVG（含中文字符）转成 PNG 的实战配方：SVG 设计 + cairosvg + Homebrew cairo + DYLD_LIBRARY_PATH。解决 cairosvg 找不到系统库、中文方框、字体名错配三类坑。"
read_when:
  - 需要把 SVG 转 PNG（封面/卡片/图卡/贴纸）
  - 中文字符在导出的 PNG 里变方框
  - cairosvg 报 "no library called cairo-2 was found"
  - 想要一份跨编辑器的纯本地方案（无 Chrome/Playwright 依赖）
---

# SVG → PNG（含中文）macOS 兜底链路

## 适用场景

- ✅ 单文件 SVG → PNG（封面、贴图首图、合集封面、信息图卡）
- ✅ 含中文/日文/韩文文本，无依赖 figma/sketch
- ✅ 想要纯本地、零 UI、CI/脚本可重跑
- ✅ 批量（一次处理 3~20 张）

不适用：需要渐变+滤镜效果（用 Playwright 更准），需要 GL 渲染（用 macOS 原生 sips/ImageMagick）。

## 工作流（5 分钟接线）

```
SVG（含中文字体声明） → cairosvg → cairo (brew) → fontconfig 系统字体 → PNG（任意尺寸）
```

### Step 1 — 安装系统依赖（一次性）

```bash
# 装 cairo 与 fontconfig（如果还没装）
/opt/homebrew/bin/brew install cairo pango fontconfig libffi

# 用 Apple Silicon 默认位置；Intel Mac 改 /usr/local/bin/brew
```

### Step 2 — 装 Python 包（用 managed python）

```bash
<工作区根>/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -m pip install cairosvg
```

### Step 3 — 关键：运行时注入 DYLD_LIBRARY_PATH

cairo 系统库装在 `/opt/homebrew/lib`，但 Python 默认找不到。**必须**在运行时注入：

```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib \
  <工作区根>/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \
  -c "import cairosvg; cairosvg.svg2png(url='in.svg', write_to='out.png', output_width=1080, output_height=1080)"
```

不注入 → 报错：
```
OSError: no library called "cairo-2" was found
cannot load library 'libcairo.so.2'
```

### Step 4 — SVG 内 font-family 必须用 macOS 自带中文字体

```xml
<text style="font-family: 'PingFang SC', 'Heiti SC', 'STHeiti', sans-serif;">AI 时代</text>
```

| 可用系统字体 | 路径关键字 | 适用 |
|---|---|---|
| PingFang SC | `PingFang.ttc` | UI 现代风 |
| Heiti SC (STHeiti) | `STHeiti Medium.ttc` | UI 厚重风 |
| STKaiti | `Kaiti.ttc` | 楷体 |
| Yuppy SC | `YuppySC-Regular.otf` | 杂志感 |

**不要用** `Noto Sans SC / Noto Serif SC / Source Han Serif SC / Microsoft YaHei` —— 这些字体没装，cairosvg 会回退到默认，方框一片。

### Step 5 — 批量处理

```python
import cairosvg, os
os.environ.setdefault('DYLD_LIBRARY_PATH', '/opt/homebrew/lib')  # 部分环境需要
for f in os.listdir('.'):
    if f.endswith('.svg'):
        cairosvg.svg2png(
            url=f,
            write_to=f.replace('.svg', '.png'),
            output_width=1080,
            output_height=1080
        )
```

## 常见坑 & 修复

| 现象 | 原因 | 修复 |
|---|---|---|
| 中文方框 | font-family 用了不存在字体 | 改 `PingFang SC, Heiti SC, STHeiti, sans-serif` |
| 中文字超界 | 字号太大（>140） | 调到 80~120，行高 1.0~1.1 |
| 报 "no library called cairo-2" | 系统 cairo 库未注入 | DYLD_LIBRARY_PATH=/opt/homebrew/lib |
| 整图只有一个颜色 | SVG 标签没有 viewBox | 加 `viewBox="0 0 W H"` |
| PNG 输出体积巨大 | 默认 96dpi 做了大量插值 | 用 `output_width` 明确尺寸 |
| 输出分辨率模糊 | DPI 不够 | 想要"高清" → output_width×2，再让上游压缩 |
| `①` `→` 等符号显示 | 字体不支持符号 | 替换为"系列第1篇"中文，或换字体到 `Arial` 兜底 |

## 设计建议（生成专业封面）

- **配色**：1 主色 + 1 强调色（蓝 #2D7FF9 或暖橙 #D97757），单色禁豪华
- **字号基准**（1080 宽）：主标 110~140，副标 60~90，标签 18~22
- **装饰**：上下双横线（5~6px）+ 字号压缩（letter-spacing -2px）→ 杂志感
- **构图**：左对齐 + 大字 = 「苹果发布会 slide 风」；居中 = 「杂志封面风」
- **必带信息**：品牌（行途）、系列编号、真实案例数（避免空中楼阁）

## 自检清单

- [ ] brew 安装了 cairo + fontconfig
- [ ] Python 安装了 cairosvg
- [ ] 运行时注入了 DYLD_LIBRARY_PATH
- [ ] SVG 中 font-family 是 macOS 自带字体名
- [ ] 确认 SVG viewBox 已设（0 0 W H）
- [ ] `file *.png` 输出尺寸对得上设计意图

## 何时该换路径

- 需要复杂动画 / 滤镜 → 用 Playwright（dangerouslyDisableSandbox）+ Chrome headless
- 需要嵌入图片/位图 → 用 Playwright 或 sips
- 需要 Raster 千万级 → Inkscape（brew install）

## 实际产出参考

- `~/xingtu/outputs/.../07_贴图/封面/贴图首图_*` 三版
- 验证时间：2026-09-06
- 适用于：公众号封面、合集封面、贴图首图、小红书图卡、GitHub README 头图、GitHub Pages banner

---

*创建时间：2026-09-06 · 创建工具：小研*
*维护人：行途工作区*
