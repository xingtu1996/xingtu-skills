---
name: wechat-tuitu-publish
description: 用 bsk 接管已登录浏览器，代发微信公众号「贴图」（小绿书/图片消息）：上传本地图卡、填标题描述、挂原文链接、核验平台推荐开关，发表或存草稿。触发词：发贴图、发小绿书、贴图发布、公众号图片消息、一图一观点发布。
---

# 公众号贴图代发（bsk 路线）

## 背景（为什么走 bsk）

- 公众号贴图 = 2026-02 升级的「小绿书」：走**发表**不占每日群发次数，纯看一看/搜一搜算法推荐，低粉号也有公域曝光。行途贴图战略 spec：`~/xingtu/specs/20260906-公众号贴图流量与封面优化发布规划.md`。
- Playwright 新开 tab 会 `ERR_PROXY_CONNECTION_FAILED`（本机代理环境）；bsk 接管 boss 已登录的浏览器无此问题，且登录态现成。**bsk 在 `~/.local/bin/bsk`**（不在 PATH）。
- 图卡生产：HTML(1080×1440) → Chrome headless `--force-device-scale-factor=2 --window-size=1080,1440 --screenshot` 出 PNG。存量卡在 `~/xingtu/outputs/贴图卡片_一图一观点/`。

## 流程

1. `export PATH="$HOME/.local/bin:$PATH"; bsk session start` → 记 4 位 session id。所有 Bash 调 bsk 需 `dangerouslyDisableSandbox: true`。
2. `bsk navigate "https://mp.weixin.qq.com/" --session <id>` —— **必须走根地址**（自动带 token 跳转）；直拼 `/cgi-bin/home?...` 无有效 token 会显示「请重新登录」。
3. `bsk observe` → 点首页「新的创作」区的**贴图**按钮（约 `@eN button "贴图"`）。
4. 上传图片：编辑页的 `input[type=file]` 隐藏且 upload 报 no visible geometry。**正确做法**：用 evaluate 给上传区容器（class 含 `image-selector__add`）打 `data-bsk-drop="1"` 标，然后 `bsk upload '[data-bsk-drop="1"]' --file <png> --session <id>`（drop 模式，实测成功）。
5. 填标题（≤20 字）与描述（≤1000 字，建议 ≤300 + #话题标签）：均为 ProseMirror，`bsk click` + `bsk fill` 直接可用。标题选择器 `div.ProseMirror[data-placeholder="请在这里输入标题"]`；**描述无 data-placeholder**，先用 evaluate 按 textContent 含「填写描述信息」找到并打 `data-bsk-desc="1"` 标再 fill。
6. 挂原文链接：点「支持添加内容链接…」→ 下拉点「内容链接」→ 弹窗列表选目标文章 → 点「完成」。
7. 核验：平台推荐=已开启、留言=自动精选公开（默认即开）。`bsk screenshot` 终检。
8. **发表前必须经 boss 确认**（默认先存草稿给 boss 手发，或 boss 明确说发再点「发表」）。点「保存为草稿」后看「历史版本」出现记录即成功。
9. `bsk session stop <id>` 收尾（成功/失败都要）。

## 重做已有贴图草稿（2026-09-06 验证）

适用：草稿箱里系统自动生成的贴图要换图/换文案。
1. 列表页 `https://mp.weixin.qq.com/cgi-bin/appmsg?begin=0&count=10&type=77&action=list_card&token=<token>` → 点「贴图 N」tab。**点卡片标题只会打开预览**；编辑入口是卡片 hover 出现的图标钮（无文字，ico0=删除、ico1=编辑，用 evaluate 给 `.weui-desktop-icon-btn` 打 data 标后 hover 读 tooltip 确认）。列表 URL 会漂移成 `action=list`，空列表时 reload。
2. 删旧图：合成 mouseevent 无效，**必须真实 hover** 图片容器 `.image-selector__preview-center-img`（bsk hover），再 evaluate 找文字为「删除」的 `.weui-desktop-tooltip__wrp` 里的 `<a>` 本体 `.click()`。每张图一轮，直到 `.image-selector__add` 恢复可见（width≈148）。
3. 上传新图：给 `.image-selector__add` 打 data 标后 `bsk upload <sel> --mode drop --file <png>`（有时必须显式 `--mode drop`，否则报 did not activate a file input）。
4. 换标题/描述：同新发流程（ProseMirror fill 会整段替换，已验证）。原贴图自带的「原文」链接保留即可。
5. 保存：evaluate 点「保存为草稿」按钮，页面出现「手动保存」历史记录即成功。

## 挂原文链接（2026-09-09 验证）

1. 入口：点「链接」区 `.wording`（文字含「支持添加内容链接」）→ 下拉点 `.btm-card-link_item`（「内容链接」）→ 弹出「编辑超链接」弹窗。
2. 选文章：弹窗默认列表按发布时间倒序分页（约 5 条/页）。**翻页比搜索可靠**——搜索框 Enter 不触发、放大镜 CDP click 偶发丢事件，且关键词可能搜不到（显示「暂无数据」）。直接点「下一页」遍历最稳；要选中的行打 data 标后 `bsk click`，再点「完成」。
3. 关弹窗：真实选择器 `.weui-desktop-dialog__close-btn`（可能报 no visible geometry，**Escape 键可直接关**）。
4. 核验：弹窗关闭且页面「链接」行显示目标文章标题、平台推荐=已开启。
5. 换卡重填：编辑页内删图=hover 预览图出删除钮；标题/描述 ProseMirror fill 整段替换。

## 出卡生成器（配套）

`~/xingtu/tools/tuitu_card_gen.py`：一条命令出 P028 风格贴图卡（1080×1440@2x）：
`python3 tools/tuitu_card_gen.py --num 005 --big "<大字>" --big-sub "<副标>" --title "<标题HTML>" --sub "<支撑>" --quote "<金句>"`

## 红线

- 群发（长文）只能 boss 人工点；贴图「发表」按钮也须经 boss 逐次确认后才可代点。
- 描述禁私人微信/外链引流私域（违规限流）；挂站内文章链接合规。
- 图卡风格守 P028：黑白极简、活人感、行途蓝 #056DE8 点缀、无 emoji。
