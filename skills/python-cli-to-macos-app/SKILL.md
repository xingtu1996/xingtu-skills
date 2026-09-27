---
name: python-cli-to-macos-app
summary: "把本地 Python/CLI 项目打包成「用户双击即用、零依赖」的 macOS .app —— 内置 Python 运行时、最小依赖、原生二进制，模型等大资产按需下载。含三条生死线检测（standalone python 能否 relocate / otool -L 外部依赖 / 静态二进制识别）、.app 目录布局与路径回溯规则、launcher 设计要点（PATH 收窄、vendor 优先、模型复用、失败留痕）、体积账算法与分发形态对比。触发词：打包成 app、做成安装包、一键安装、macOS 分发、dmg、pkg、用户不用装 python、拖拽打开、把工具给朋友用、零依赖分发。"
agent_created: true
read_when:
  - 要把本地脚本/CLI/工具交给「不懂命令行的人」使用
  - 用户问「能不能做成一键安装 / 安装包 / .dmg / .pkg」
  - 要把 Python 项目打包成 .app（用户不装 Python）
  - 打包后在新机器上报「找不到 ffmpeg / 找不到模块」
  - 打包体积过大，需要瘦身
  - 大模型 / 大权重文件要不要塞进安装包
---

# Python CLI → macOS .app（零依赖分发）

> 真实案例：`text2vido`（文本→视频）打包成 **114MB** 的 `Text2Vido.app`，拖 PDF 到图标即出片，
> 用户**不需装 Python / Ollama / 任何依赖**。产物见 `~/xingtu/text2vido/packaging/`。

---

## 第 0 步：先算体积账（这一步决定方案成立与否）

**最容易犯的错：拿开发 venv 的体积当安装包体积。**
开发 venv 常是多项目混用，里面一堆无关大包；而**分发只需要代码真正 import 的那几个**。

```bash
# ① 代码真正依赖什么（唯一可信来源）
grep -rhoE "^(import|from) [a-zA-Z_][a-zA-Z0-9_]*" src/**/*.py | awk '{print $2}' | sort -u

# ② 对比：venv 里最大的包 vs 直接依赖
du -sm <venv>/lib/python*/site-packages/* | sort -rn | head -10
```

**真实对照**：venv 1.4 GB（含 torch 437M / mlx 179M / playwright 133M —— 全是别的项目的），
实际只需 4 个包 ≈ **25 MB**。

| 组件 | 典型体积 | 是否内置 |
|---|---|---|
| Python 运行时（python-build-standalone） | 70–80 MB | ✅ |
| 最小依赖集 | 按实际 import 算 | ✅ |
| 原生二进制（ollama / 静态 ffmpeg 等） | 30–100 MB | ✅ |
| LLM 权重 | **GB 级** | ❌ **绝不内置** |

**模型/权重的判断铁律**：**不内置**。所有同类工具（LM Studio / Ollama / ComfyUI）都不内置模型。
安装包保持百 MB 级，权重首次运行下载，并**复用系统已有缓存目录**（别覆盖它的环境变量，否则用户白下几个 G）。

---

## 第 1 步：三条生死线（打包前必验，否则做完才发现不可分发）

### ① Python 运行时换目录还能跑吗？（relocatable）
```bash
cp -R <python-standalone> /tmp/relocate_test/py
/tmp/relocate_test/py/bin/python3 -c "import json, sqlite3, ssl; print('ok')"
cd /tmp && /tmp/relocate_test/py/bin/python3 -c "print('cwd-independent ok')"
```
✅ 通过 → 可内置（python-build-standalone 通常可）。
❌ 失败 → 需 `install_name_tool` 修 rpath，或改用 PyInstaller。

### ② 原生二进制能只拷一个文件吗？
```bash
otool -L $(readlink -f $(which <binary>)) | tail -n +2 | grep -c "/opt/homebrew\|/usr/local"
```
- **0** → 静态，直接拷 ✅
- **>0** → 绑定了包管理器的 dylib，**拷走必崩** ❌

### ③ 反直觉警告
> **体积小 ≠ 可移植。**
> 实测：ffmpeg **420 KB** 但链接 **18 个** homebrew dylib → **不可分发**；
> ollama **32 MB** 静态 → **可分发**。

**ffmpeg 的正确解法**（按推荐度）：
1. **static build**（arm64 静态版，单文件约 80MB，无外部依赖）← 推荐
2. 连带打包 dylib + `install_name_tool` 改 18 个 rpath（脆）
3. 不内置，运行时检测并弹窗引导 `brew install ffmpeg`（违背"一键"）

---

## 第 2 步：`.app` 目录布局与路径规则

```
MyApp.app/
└── Contents/
    ├── Info.plist              # 声明接收的文件类型 → 拖拽才响应
    ├── MacOS/MyApp             # 可执行 shell 启动器
    └── Resources/
        ├── runtime/            # Python（sys.prefix）
        ├── vendor/             # 原生二进制（ollama / ffmpeg…）
        ├── app/<pkg>/          # 源码
        ├── config.yaml         # ← 见下方路径规则
        └── assets/             # 图标等随包资产
```

### 路径规则（最关键，也最容易错）
**所有内部路径必须用 `__file__` 回溯定位，绝不能用相对 cwd 的路径**
——`.app` 双击时 **cwd = `/`**。

```python
# __main__.py 位于 Resources/app/<pkg>/__main__.py
DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config.yaml"   # → Resources/config.yaml
def project_root(): return Path(__file__).resolve().parents[2]         # → Resources/

# 启动器里同步设置
export PYTHONPATH="$RES_DIR/app"
```

> 推论：**`parents[N]` 的 N 由源码在包里的深度决定**。挪动 `app/` 的嵌套层级，
> 会同时打断 config 与 assets 两处定位 —— 动结构前先 grep 所有 `parents[`。

### Info.plist 的拖拽声明（不写则拖拽无反应）
```xml
<key>CFBundleDocumentTypes</key>
<array><dict>
  <key>CFBundleTypeRole</key><string>Viewer</string>
  <key>LSItemContentTypes</key>
  <array>
    <string>com.adobe.pdf</string>
    <string>public.plain-text</string>
    <string>net.daringfireball.markdown</string>
  </array>
  <key>CFBundleTypeExtensions</key>
  <array><string>pdf</string><string>md</string><string>txt</string></array>
</dict></array>
```

---

## 第 3 步：launcher 设计要点（6 条硬要求）

```bash
MACOS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RES_DIR="$(cd "$MACOS_DIR/../Resources" && pwd)"
```

| # | 要点 | 为什么 |
|---|---|---|
| 1 | **收窄 PATH**：`$RUNTIME/bin:$VENDOR:/usr/bin:/bin:/usr/sbin:/sbin` | `.app` 双击时 PATH 极窄且不可控；收窄反而让依赖确定 |
| 2 | **环境变量指向 vendor**（`APP_VENDOR=$VENDOR`） | 让代码层优先用随包二进制，而非用户机器上的 |
| 3 | **不覆盖缓存目录变量**（如 `OLLAMA_MODELS`） | 复用用户已有的几 GB 缓存，别让他白下 |
| 4 | **端口/进程先探测再启动** | 用户机器可能已在跑同名服务，避免冲突 |
| 5 | **失败必留痕**：通知 + `~/Library/Logs/<App>/` | 用户看不到终端，静默失败 = 灾难 |
| 6 | **产物校验**（如音频/文件 0 字节当场报错） | 否则崩在很远的后续阶段，极难查 |

**无参数双击** = 显示用法说明 + 打开工作目录；**有参数（拖拽）** = 逐文件处理 + 完成后通知。

---

## 坑清单

| 坑 | 症状 | 解法 |
|---|---|---|
| **PATH 极窄** | 打包后报「找不到 ffmpeg」 | 代码层做**二进制定位层**（见下），别写死绝对路径 |
| **shell 与 Python 两套检测逻辑不一致** | 自检假报「未安装」 | 抽成一个函数，两处共用 |
| **硬编码包管理器路径** | 换机器/Intel/MacPorts 全崩 | 优先级：环境变量 → 随包 vendor → 常见路径 → PATH |
| **cwd 相对路径** | `.app` 里找不到 config/assets | 一律 `__file__` 回溯 |
| **macOS 没有 `timeout`** | 测试脚本 exit 127 | 用 `gtimeout`（coreutils）或后台+kill |
| **签名/公证** | 用户首次打开被 Gatekeeper 拦 | 见下 |

### 二进制定位层（必做，价值独立于打包）
```python
def resolve(name, env_var=None):
    # 1) 环境变量 → 2) 随包 vendor → 3) /opt/homebrew/bin, /usr/local/bin, /opt/local/bin → 4) PATH
```
同时把源码里所有硬编码（含 `DYLD_LIBRARY_PATH=/opt/homebrew/lib` 这类）改为**动态探测**。
好处：Intel Mac / MacPorts / 自定义安装也能跑 —— **这一步本身就是开源项目的必修项**。

---

## 分发形态怎么选

| 形态 | 成本 | 适用阶段 |
|---|---|---|
| **zip / .app 目录** | 0 | 自己 + 朋友 ← **先做这个** |
| `.dmg` | 低（需 `create-dmg`） | 有外部用户后 |
| `.pkg` | 需 Apple 开发者签名 + 公证（年费） | 正式对外 |
| `brew` tap | 低 | 开源引流 |

**Gatekeeper 现实**：未签名 .app 从**网上下载**后会带 quarantine 属性，首次打开被拦：
```bash
xattr -dr com.apple.quarantine /Applications/MyApp.app
```
**本地构建的 .app 不带该属性，双击可直接开**（所以自测通 ≠ 用户能开，要提前告知）。

---

## 自检与验收（交付前必做）

```bash
# 1) 构建脚本支持 --check（只做自检不构建）
# 2) 启动器支持 --selftest（打印每一项依赖解析到哪）
"dist/MyApp.app/Contents/MacOS/MyApp" --selftest

# 3) 真实端到端，且必须「用 .app 内的启动器」而不是源码目录
"dist/MyApp.app/Contents/MacOS/MyApp" <真实输入文件>
```

> **验收标准：用随包运行时跑通真实样例，产出文件规格正常（时长/编码/尺寸）。**
> 只"构建成功"不算通过 —— 本轮就出现过构建成功但自检假报、以及 macOS 无 `timeout` 导致的假失败。
