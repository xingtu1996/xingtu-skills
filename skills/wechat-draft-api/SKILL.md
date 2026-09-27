---
name: wechat-draft-api
description: >
  微信公众号「官方 API 建稿到草稿箱」技能：用公众号 appid + appsecret 调用微信草稿箱
  draft/add 接口，把排版好的 HTML 一键建稿（到草稿箱为止，群发永不自动化）。
  相比浏览器注入法（bsk）更稳定，且能把配图直接嵌入正文（免手动拖图）。
  触发词：微信建稿、草稿箱 API、公众号自动建稿、wx_draft_api、draft/add、把文章发到公众号草稿箱。
  依赖：用户自己的公众号 appid/appsecret（公众号后台「开发→基本配置」获取）；Python 3 标准库（零第三方依赖）。
  红线：只建草稿、绝不自动化群发；appsecret 走外部文件/环境变量，绝不写入代码。
  版本：行途开源矩阵 v1.0（2026-09-27 从 tools/wx_draft_api.py 抽离参数化）。
---

# 微信公众号官方 API 建稿技能（wechat-draft-api）

> 来源：行途内容工程工具链 `tools/wx_draft_api.py` 抽离参数化版本。
> 定位：**确定性发布工具**，不是 AI 智能写作——同样的输入永远产生同样的草稿。
> 设计原则：零第三方依赖（纯 Python 标准库）、凭据不落代码、群发不自动化。

---

## 〇、它解决什么

把一篇**已经排版好**的公众号 HTML（如 md2wechat 产出）通过微信官方 API 建到草稿箱：

- `access_token` → 配图 `uploadimg` 换 mmbiz 链接 → 正文占位替换为 `<img>` →
  封面 `add_material` 拿 `thumb_media_id` → `draft/add` 建稿。
- 优势：比浏览器注入稳定；配图直接嵌入正文（作者免在后台一张张拖图）。
- 终点：**草稿箱**。原创声明/合集/定时群发由人在后台点——群发永不自动化（红线）。

---

## 一、依赖与环境变量

| 变量 / 参数 | 必填 | 说明 |
|---|:--:|---|
| `WX_APPID` 或 `--appid` | ✅ | 公众号 AppID（公众号后台「开发→基本配置」） |
| `WX_SECRET_FILE` 或 `--secret-file` | ✅ | 存 appsecret 的本地文件路径（**绝不写进代码/仓库**） |
| `WX_PROFILE_CARD` 或 `--profile-card-file` | ⬜ | 官方名片卡 HTML 片段路径；不传则不插名片（保留通用性） |

> **凭据红线**：appsecret 等同账号身份。本技能**只从外部文件/环境变量读取**，代码里没有任何硬编码密钥。
> 推荐：把 appsecret 放在工作区 `.gitignore` 忽略的本地文件，或 macOS 钥匙串。

---

## 二、用法

```bash
# 最简：环境变量注入凭据
export WX_APPID="你的appid"
export WX_SECRET_FILE="/path/to/your/appsecret.txt"   # 文件内容=32位secret
python3 scripts/wx_draft_api.py \
  --pkg <发布包目录> --title "标题" --desc "摘要" \
  [--author 行途] [--cover-file <封面.png>] [--profile-card-file <名片卡.html>] \
  [--dry-run]     # 干跑：构建正文但不真正建稿

# 或直接传参
python3 scripts/wx_draft_api.py --appid xxx --secret-file yyy.txt --pkg ... --title ... --desc ...
```

**发布包结构约定**（与 `md2wechat` + 行途发布 SOP 对齐）：

```
发布包/
├── 01_正文/正文_v1.md          # 含 【配图：xxx.png】 占位
├── 02_排版HTML/公众号_发布版.html
├── 03_封面/*.png               # 自动取最新一张（排"真人"/"旧"字样）
└── 04_配图/*.png               # 与正文占位对应
```

---

## 三、红线与边界

1. **群发永不自动化**：脚本终点 = 草稿箱。`draft/add` 成功即停，绝不调用 `masssend`。
2. **凭据不落代码**：appsecret 只从 `--secret-file` / `WX_SECRET_FILE` 读；代码零硬编码密钥。
3. **平台限制前置**：微信对图片/封面有格式与大小限制（jpg/png，封面 ≤2M 等），超限会被接口拒绝——先自查再跑。
4. **macOS 依赖**：配图若为 webp，脚本用 macOS `sips` 转 png（仅 macOS 可用）；其他平台请预先转好。

---

## 四、与其他 skill 的关系（高内聚低耦合）

- **上游**：`md2wechat`（生成排版 HTML）→ 本技能（建稿到草稿箱）。
- **同层**：`wechat-publish-sop`（发布 SOP 总装）、`wechat-bsk-inject`（浏览器注入法的备份通道）。
- **下游**：人在公众号后台设原创/合集/定时群发。

---

_行途开源矩阵 · MIT · 跨工具兼容（Claude Code / CodeBuddy / Codex / Cursor / Gemini CLI / WorkBuddy / 豆包）_
