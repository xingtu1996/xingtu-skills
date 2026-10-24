---
name: yuanbao-article-fetch
description: 抓取并留存元宝（腾讯 Yuanbao）AI 分享文章。当用户给出 yb.tencent.com/wx/ct/ 开头的分享链接（或 ID），或说"提取元宝文章/把元宝总结的文章存下来/抓取元宝分享链接"时使用。核心技巧：伪装微信 iOS User-Agent 绕过微信客户端围栏，无需登录即可拿到全文。
---

# 元宝分享文章抓取（yuanbao-article-fetch）

## 何时用
- 用户提供 `https://yb.tencent.com/wx/ct/<ID>` 或 `https://yb.tencent.com/wx/ct/f/<ID>` 链接
- 用户说"把元宝总结的文章存下来 / 提取元宝对话文章 / 抓取元宝分享链接"
- 作为自媒体内容流水线的"内容源"步骤：抓取 → 入库 → 后续改写发布

## 关键事实（已实测，2026-07-09）
- 元宝分享链接**默认只能在微信内置浏览器打开**，普通浏览器返回"请在微信客户端打开该链接"（`err_code: notInWX`）。
- **根因：服务端仅做 User-Agent 检测**，未做微信环境校验。伪装成微信 iOS UA 后，Next.js SSR 直接渲染全文，**无需微信客户端、无需登录**。
- 页面含 `__NEXT_DATA__` JSON（`props.pageProps.data.conversation_info`），但实测 `chatInfo[0].convs` **为空**——文章正文由服务端 **HTML 渲染**在页面里。因此正文从 HTML 可见文本提取（`shareCardInfo.title` 取标题/摘要），不依赖 JSON 对话数组。
- 可见文本在 `听全文` 标记之后。
- 适用路径：`/wx/ct/<ID>` 与 `/wx/ct/f/<ID>` 两种均已批量验证通过。
- **数据一致性已校验**：同目录 `verify_consistency.py` 证明导出的 Markdown 与「微信里看到的内容」100% 一致（字符级覆盖、零噪点）。

## 通用工具（优先用这个）
脚本位置（项目内）：
`02_内容仓库 (Content Hub)/06_元宝对话挖掘/yuanbao_fetch.py`

仅依赖 Python 标准库 + 系统 curl，无需安装包。用法：

```bash
PY=~/.workbuddy/binaries/python/versions/3.13.12/bin/python3
DIR="02_内容仓库 (Content Hub)/06_元宝对话挖掘"

# 直接传链接/ID（空格分隔，支持 /wx/ct/ 与 /wx/ct/f/）
$PY "$DIR/yuanbao_fetch.py" "https://yb.tencent.com/wx/ct/YFnyfQjixc8X9g" "YFbuq5aDkcSfnM"

# 从文件批量（每行一个链接或 ID，# 开头忽略）
$PY "$DIR/yuanbao_fetch.py" -i links.txt

# 先试跑不落盘（验证解析）
$PY "$DIR/yuanbao_fetch.py" --dry-run "https://yb.tencent.com/wx/ct/f/YFQ10ilFfvOa8n"

# 指定输出目录
$PY "$DIR/yuanbao_fetch.py" -o /other/path "https://..."
```

工具行为：伪装微信 UA 抓取 → 解析 HTML 提取标题正文（保留表格/标题/列表结构）→ 按 `元宝分享文章_<标题>_<6位ID>.md` 命名 → **按 6 位短 ID 去重**（只匹配本工具产出的 `元宝分享文章_` 前缀文件，避免误匹配同目录校验报告）→ 追加 `manifest.csv` 实时清单。

## 数据一致性校验（交付前建议跑一次）
```bash
PY=~/.workbuddy/binaries/python/versions/3.13.12/bin/python3
DIR="02_内容仓库 (Content Hub)/06_元宝对话挖掘"
# 带截图真值清单（逐条核对微信里看到的元素）
$PY "$DIR/verify_consistency.py" "https://yb.tencent.com/wx/ct/YFnyfQjixc8X9g" \
  --truth "$DIR/truth_yfnyfq.json" --html "$DIR/一致性样例_YFnyfQ_公众号排版.html"
# 任意链接（自动项：标题识别/字符级覆盖/无噪点）
$PY "$DIR/verify_consistency.py" "https://yb.tencent.com/wx/ct/f/YFbuq5aDkcSfnM"
```
原理：微信视图等价于「同一份 HTML 的可见文本」，导出物同源；覆盖率为 100% 且无界面噪点即判定一致。

## 如果脚本不可用（手写兜底）
手动 curl（微信 UA）：
```bash
curl -s -A "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.38(0x18002623) NetType/WIFI Language/zh_CN" "https://yb.tencent.com/wx/ct/<ID>"
```
保存 HTML 后用正则提取 `<script id="__NEXT_DATA__">` 内 JSON 的 `conversation_info`。

## 风险与边界（务必告知用户）
- **脆弱性**：腾讯目前只校验 UA，随时可能升级为微信环境校验（WeixinJSBridge/签名），届时纯 UA 失效 → 回退 `yuanbao.tencent.com` 网页版登录态兜底。
- **仅适用已分享链接**：未分享的对话历史仍走网页版登录态读取。
- **隐私**：文章可能含个人信息，发布前必须脱敏（过滤账号/家人/公司敏感/客户名）。
- **合规**：个人内容归档自用没问题；批量抓取注意频率，避免触发限流。

## 输出落点
文章 md + `manifest.csv` 统一放在 `02_内容仓库 (Content Hub)/06_元宝对话挖掘/`，`README_元宝对话挖掘.md` 为该留存库索引。

---

> 作者：行途 XingTu（一线 AI 工程化实践者 · FDE 方向）· 开源于 [xingtu-skills](https://github.com/xingtu1996/xingtu-skills)
