---
name: wechat-mp-publish
description: 微信公众号后台自动化发布 Skill。发前核查（群发额度/发表记录/草稿箱）→ 把一篇成稿（HTML/PM doc JSON/官方草稿 API）导入公众号草稿箱、设置标题/摘要/原创/封面/合集/公众号名片，最终引导人工群发的全流程自动化 + SOP。**默认 bsk 通道；boss 明确指示时可用 Playwright（~/.pw_mp_profile 登录态）**；纯导入到草稿箱可走官方草稿 API 通道（tools/wx_draft_api.py：dry-run→建稿→凭证回查→中间稿回收，见第九节）。适用场景：用户要求"把文章导进公众号草稿""发布到公众号""设置封面/原创/合集""插入公众号名片""今天能不能发/发什么"等。
metadata:
  author: xingtu
  version: "1.1.0"
  argument-hint: <成稿路径> [--draft-only] [--engine playwright|bu]
---

# 微信公众号发布自动化 Skill（行途版）

> ⚠️ **引擎定案（2026-09-06 boss 拍板，最高优先级）**：公众号后台自动化**一律首选 bsk**（腾讯 browser-skill CLI，`~/.local/bin/bsk`，不在 PATH，需 `export PATH="$HOME/.local/bin:$PATH"`）。**Playwright 引擎在 boss 明确指示时可用（使用 ~/.pw_mp_profile 持久化登录态，非模拟登录）；默认仍首选 bsk**。bsk 接管 boss 已登录浏览器：登录态现成、无代理问题。
> **bsk 实战流程（2026-09-06 验证，0907 草稿 appmsgid=100000297）**：`bsk session start` → `bsk navigate "https://mp.weixin.qq.com/"`（根地址自动带 token）→ 草稿箱 `appmsg?...action=list_card` → evaluate 点「新的创作」→ snapshot 点「文章」→ 进 `appmsg_edit_v2&isNew=1` → PM 注入（自建 doc JSON base64 分 13 块 evaluate 设 `__d64_i` → `__mpBodyChecktextView` 事务替换）→ 原生 setter evaluate 填 `textarea.js_title`/`js_desc` → 「保存为草稿」按钮三连鼠标事件 → URL 出 appmsgid 即成功。
> **坑15 补充（bsk 语境）**：点按钮用 evaluate dispatch mousedown→mouseup→click 三连；md2wechat 新版输出整体包在 `#content > section` 里，提取正文用 `id="content"` 定位 + `rfind('</section>')` 截取（外层 section 的基础样式可丢弃）。
> **坑16（2026-09-14 实战，FDE-02 appmsgid=100000566）**：①「新的创作→文章」菜单项可能打开**最近编辑的旧草稿**而非空白新稿（实测打开了已群发 PEC 文的残留编辑页 appmsgid=100000565）——注入前必须校验 `location.href` 含 `isNew=1` **且** 标题框为空、正文为「从这里开始写正文」占位；不满足就弃用重开。②编辑器已改版：`__mpBodyChecktextView` 变纯文本校验视图（schema 无 para/heading），**PM doc JSON 事务注入失效**（BUILD_FAIL:Unknown node type: para）→ 新主路径为**剪贴板 paste 注入**：`#content` 提取正文 HTML → base64 分 12 块 `window.__d64_i` → 页内 `DataTransfer`+`ClipboardEvent('paste')` 派发到 `.ProseMirror`（第 2 个，index 1），md2wechat 样式经编辑器原生粘贴管线保留（这就是官方用户流）。③保存前若编辑器页有脏内容一律 `bsk reload` 丢弃（不点保存），已群发草稿的编辑页是幽灵页、群发后草稿即从箱内移除，勿在其上操作。④注入后必须 `innerText` 校验头/中/尾标记（首段/最后小节/签名尾舱）防粘贴半截。

> 目标：**单篇成稿 → 公众号草稿箱 → 发布前五项待办（原创/封面/合集/名片/预览）** 全流程尽量自动化，把必须人工的部分（群发、扫码登录、个别不稳定操作）收敛成"最小人工清单"。
> 2026-09-03 建立，基于《AI Native 时代》草稿（appmsgid=100000183）实战踩坑沉淀。

## 一、引擎选择（先读这段）

> 📋 **Playwright 能力边界参考**：下表记录 Playwright（持久化 profile 登录态）与 bu/CDP 各能力的优劣，供 boss 明确指示切到 Playwright 时查阅（如 `set_input_files` 曾解决封面上传）。**默认 bsk，boss 明确指示时切换 Playwright。**

| 能力 | Playwright（首选） | bu/CDP（回退） | 说明 |
|---|---|---|---|
| 封面上传（本地文件） | ✅ `set_input_files` 直接注入 | ❌ 卡系统文件选择器 | **Playwright 决定性优势** |
| 原生对话框处理 | ✅ `page.on('dialog')` | ❌ 对话框自动关闭 | 对应公众号名片搜索 |
| 正文注入（PM 事务） | ✅ `page.evaluate` 跑 JS | ✅ 已验证 | 两者都可行 |
| 登录态 | ⚠️ 需独立 profile 扫码一次 | ✅ 复用已登录 Chrome | Playwright 首次需扫码 |
| 复杂 UI 点击 | ✅ selector/坐标 | ⚠️ 需坐标估位 | Playwright 更稳 |
| 前置条件 | `pip3 install playwright` | 无需 | |

**结论**：有本地封面/名片插入需求 → **优先 Playwright**；无封面纯正文注入 → bu 更快（已登录）。

## 二、Playwright 登录态复用（关键）

- 公众号后台登录是**扫码**，Playwright 独立 profile 无登录态。
- **首次**：`scripts/mp_publish.py --login` 打开 headful Chrome，用户扫码一次，登录态存进持久化 profile（默认 `~/.pw_mp_profile`），后续免扫码。
- **持久化 profile 目录**：`~/.pw_mp_profile`（Playwright launch_persistent_context）。
- 不要复制系统 Chrome 的 Cookies（Chrome 的 cookie 加密密钥绑定原 profile 的 Local State，复制无效）。

## 三、发布全流程 SOP（五步）

### Step 0 发前核查（必做，30 秒，2026-09-10 新增）

**为什么必做**：订阅号**每天只有 1 次群发额度**，图文与贴图共用。不先核查就排期，会出现「排了今天发，实际今天额度已用完」的硬阻塞。**排期与事实冲突时，永远以后台为准，不信台账。**

```bash
export PATH="$HOME/.local/bin:$PATH"
bsk session start                                        # 返回 session-id（如 uzvc），后续所有命令都要 --session <id>
bsk navigate "https://mp.weixin.qq.com/" --session <id>   # 根地址自动带 token，重定向到 .../home?token=XXXX
bsk evaluate "document.body.innerText.slice(0,2000)" --session <id>
```

首页即可读到三项关键信息：
- **总用户数 / 昨日阅读(人) / 昨日新增关注**（用于数据基线）
- **近期发表**：若顶部出现「今天 HH:MM 已发表」→ **今天群发额度已用**，不能再群发。
- **近期草稿**：判断目标稿是否已在草稿箱。

需要更细时：
- **发表记录页**（含每篇阅读/分享/点赞/在看/评论/赞赏 + 链接）：
  `https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin=0&count=20&token=<token>&lang=zh_CN`
  抓链接：`bsk evaluate "JSON.stringify([...document.querySelectorAll('a')].map(a=>a.getAttribute('href')||'').filter(h=>h.includes('/s/')))" --session <id>`
- **草稿箱页**（`type=77&action=list_card`）：`https://mp.weixin.qq.com/cgi-bin/appmsg?begin=0&count=20&type=77&action=list_card&token=<token>&lang=zh_CN`

**坑（2026-09-10 实测）**：
- 发表记录列表是**懒加载**：`innerText` 只渲染首屏约 10 条。要翻历史换 `begin=` 参数分页，别以为「读到多少就是全部」。
- 同一页两次 `evaluate` 之间 SPA 可能重渲染，`innerText.length` 会突变（实测 3400 → 1498）。**每次读之前先 `navigate` 一次或等 3-5s**，不要跨调用拼数据。
- 发表记录里「**仅自己可见**」的条目是测试发布，**统计与回填时一律剔除**。
- 部分文章的链接不在 `<a href>`，而在列表项的复制链接按钮上；先用上面的 `filter(h=>h.includes('/s/'))` 取，取不到再点复制按钮读剪贴板。

**⏰ 时事时效核查（PUB-051，速评/热点类必做）**：
- 凡正文核心事实依赖正在演进的官方公告/事件/价格政策：**发布前 24h 内回源复查**（官方公告页/后台横幅/多源交叉），**定时动作前最后一查**——定时≠安全，定时发出的是数小时前的事实。
- 复查发现反转/变动 → 正文立即升版重渲，禁「发了再说」。
- 首案教训（2026-09-14 MODEL-02）：下线稿完成待发，当天官方公告反转「继续提供、计费不变」，v3 全文作废重写 v4。

### Step 1 准备成稿 HTML（或 PM doc JSON）
- 本地已生成 `xxx_公众号正文_预览格式版.html`（带 section 样式块）
- **注入红线**：带背景色的理念块/金句块必须用 `<section>`（勿用 blockquote——微信会强制覆盖成灰色引用样式）；section 内裸文本（无 `<p>` 包裹）要兜底转段落，否则变空块。

### Step 2 正文注入（PM 事务）
用 `scripts/mp_publish.py` 或手动 evaluate 实现：
```js
// 找到 PM view（公众号编辑器用 ProseMirror）
const v = window.__mpBodyChecktextView;
// HTML → PM doc JSON（para/heading/image，加粗=textstyle fontWeight:bold）
// base64 分块赋 window.__d64_0..12 → atob → JSON.parse → schema.nodeFromJSON
const tr = v.state.tr; tr.replaceWith(0, v.state.doc.content.size, doc); v.dispatch(tr);
```

### Step 3 标题 + 摘要（检索优先）
- 标题：**关键词前置堆叠**（核心词放前 15 字），如 `Vibe Coder、FDE、Harness Engineer……AI 时代的 5 种工程师，你是哪种？`（52/64 字）
- 摘要：**堆叠 2-5 个核心搜索词**，增强微信搜一搜 + AI 检索命中

### Step 4 发布前待办（六项）
| 待办 | 自动化 | 人工 |
|---|---|---|
| 原创声明 | ✅ Playwright 点开关→弹窗→勾协议→确定 | — |
| 封面 | ✅ Playwright `set_input_files` 注入本地封面 | — |
| 合集选择 | ✅ 点合集→选合集（需合集已建且文章已发布才完整） | 若无合集需先建 |
| 公众号名片 | ✅ **已自动化**（见下方"名片插入四步"） | — |
| 赞赏 | ✅ 点赞赏行→弹窗默认选"赞赏作者"+账户"行途"→勾协议→确定 | 若首次需开通赞赏账户 |
| 预览检查 | ✅ 点预览→查渲染 | 手机端确认 |

**名片插入四步（已验证，Playwright 精确 selector）**：
1. 点"更多"：`page.query_selector('#editor_showmore').click()`（勿用文字"更多"匹配，toolbar 布局会漂移）
2. 点"账号名片"：`#js_editor_insertProfile`（此时菜单已展开）
3. 搜索框（placeholder=请输入账号名称或账号ID）输入"行途"→ 点"最近使用"里的 `li.profile_history_item`（选中）
4. 点弹窗"插入"按钮：`[class*=profile_submit]`（需先选中账号才 enabled）

**赞赏开启（已验证）**：
- 设置区点"赞赏"行（值"不开启 >"）→ 弹窗默认已选"赞赏作者"+账户"行途"→ 底部勾选"我已阅读并同意《微信公众平台赞赏功能使用协议》"（**必须点文字左侧的 checkbox 本体**，不是 label 文字）→ 点"确定"
- 成功后设置区显示"赞赏 账户:行途"

### Step 5 保存 + 群发
- 保存为草稿：点「保存为草稿」按钮
- **群发只能人工**（个人号 freepublish 接口已回收）：用户后台手动点群发
- 发布时段：通勤 18:00 或上午 8:00（效果更好）

### Step 6 发布后置顶评论（必做，30 分钟内，PUB-050，2026-09-14 新增）

群发成功 ≠ 流程结束。置顶评论区是公众号**唯一免费的二次推送位**，标签词会进评论区顶部「都在搜」索引面（搜一搜索引），是冷启动期少数不看粉丝量的曝光入口。

**动作清单**：
1. **取用，不现写**：置顶评论文案在**生成发布包时已同步产出**，位于发布包 `06_发布参考/置顶评论.md`（PUB-050 标配交付物）——发布后 30 分钟内直接复制粘贴，作者点「精选/置顶」。
2. 若发布包缺该文件：按下方模板现补一条，并**回填进发布包** `06_发布参考/`，补齐交付物。
3. 结构 = **反问钩子一句**（复用文章核心矛盾，可改写自标题）+ 换行 + **3~5 个长尾标签**。
4. 标签纪律：用搜一搜**长尾词**（模型名+动作/痛点词，如 #AI提效 #组织效率），**禁裸大词**（#AI #管理 挤不进排名还显营销号）；总数 ≤5。
5. **元宝/AI 总结不占置顶位**：通用腔无钩子，可留普通位或不发。

> 依据：PUB-050（rules/RULES.d/01_PUB）；案例实证：乔新亮《全员配AI》作者自评 8 标签 + 顶部「都在搜：ai提效组织效率陷阱」。

## 四、脚本

- `scripts/mp_publish.py` — 主脚本：登录/注入/封面/原创/合集
- 参数见脚本 `--help`

## 五、踩坑记录（务必读）

0. **新建草稿流程（2026-09-06 实战，agent-browser 通道）**：
   - 入口 = 草稿箱列表页 `cgi-bin/appmsg?begin=0&count=10&type=77&action=list_card&token=...`（`action=list_ex` 返回纯 JSON 不是 UI）；点「新的创作」按钮 → 菜单选「文章」→ 进 `appmsg_edit_v2&isNew=1`（此时无 appmsgid，**首次保存后 URL 才生成 appmsgid**）。
   - 新建驱动脚本：`scripts/mp_new_draft.py`（登录检测→新建→注入→保存一条龙）。
   - 登录：agent-browser 自带浏览器里用「微信快捷登录」（需手机确认，约 1 分钟有效）；确认后弹「选择账号登录」列表 → 点目标公众号即进后台。
1. **blockquote 强制灰样式**：微信编辑器把 blockquote 覆盖成默认引用（背景透明+灰边），带色块一律用 section。
2. **section 裸文本空块**：section 内若无 `<p>` 包裹的裸文本，转换脚本要兜底成段落，否则空块。
2b. **md2wechat 输出不能直接喂 html_to_pm_doc**：其外层是 `<div id="content">` + p/h2/blockquote/ul/div 结构，函数只认 p/h2/section 且会漏 blockquote/ul。直接自建 PM doc（blockquote→带样式 para、li→'· '前缀 para、页脚 div 按行拆）更稳，参考 /tmp/build_doc.py 模式。
3. **图片"1有效+1空"假象**：编辑器 DOM 每张图显示双份 img 是渲染层 artifact，PM doc 只有有效节点，保存正常。
4. **heading DOM 显示 H1，PM doc 是 h2**：保存序列化正常，不用管。
5. **navigate 回编辑器会丢未保存内容**：先保存再 navigate。
6. **bu.js 不支持传参对象**：数据内联进 JS；含引号/emoji 用 \uXXXX 转义。
7. **名片插入关键在 selector**：入口是 `#editor_showmore`（li 元素），不是文字"更多"；账号名片项 `#js_editor_insertProfile`；搜索后点 `li.profile_history_item` 选中 → 再点 `[class*=profile_submit]`"插入"。**必须先选中账号，"插入"按钮才 enabled**。
8. **合集只能收已发布内容**：发布后才能加入合集、回编辑器插合集卡片。
9. **常驻 Chrome daemon 会闪退**：`launch_persistent_context(channel='chrome', args=['--no-sandbox','--remote-debugging-port=9222'])` 用 nohup 起；脚本里 `time.sleep` 兜底。若 CDP 9222 拒连 → 直接重启 daemon（profile `~/.pw_mp_profile` 登录态保留），再 `connect_over_cdp`。
10. **正文文本编辑用 DOM Range 选中，勿用三击**：三击在含名片 iframe 的文末不可靠。正确姿势：`page.evaluate` 里 `createTreeWalker` 找到含目标子串的文本节点 → `Range.selectNodeContents(node)` → `getSelection().addRange` → `keyboard.press('Delete')` → `keyboard.type(新文本)`。**每步用 `page.evaluate` 读 innerText 验证，别靠截图**。
11. **纯文本读取优先于截图**：Playwright/CDP 可直接 `page.evaluate` 读 DOM 文本/结构（innerText、querySelector、getBoundingClientRect），比截图更快更准。截图仅用于"最终视觉确认"。诊断界面一律走文本读取。
12. **赞赏弹窗协议 checkbox**：必须点"我已阅读并同意"左侧的 checkbox 本体（label 文字左侧 14px 处），点文字不生效（会弹"请勾选协议"黄色提示）。
13. **[新编辑器] 正文 file input 会吞 upload**：appmsg_edit_v2 编辑器里 `input[type=file]` 是**正文图片**的——对它 upload 会把图插进正文**且清空已注入正文**。封面别走这条路：留作人工（后台点封面→传本地 PNG，5 秒），或找到封面专属 dialog 内 input 再注入。
14. **[新编辑器] 原创弹窗的作者字段**：弹窗内直接赋值会被组件回滚（受限于顶部状态源）。正确做法：先在**编辑器顶部 `input.js_author`** 真实输入（agent-browser fill）→ 再开原创弹窗，作者自动联动带出。
15. **[新编辑器] 弹窗确定按钮**：页面上有多个 `.weui-desktop-btn_primary`，agent-browser click 会点中第一个（不在弹窗内）→ 无效。必须在**弹窗容器内**找到确定按钮，dispatch 完整鼠标事件序列（mousedown→mouseup→click）才生效。

## 五·补 · 编辑器注入实战补充（2026-09-10，bsk 通道实测）

> 本次为「B15 全流程自动化尝试」，结论：**注入段全通，保存段被服务端拒**。以下为可复用结论 + 未解问题。

### 通的（照做即可）

1. **不要走 UI 下拉菜单**。草稿箱「新的创作」下拉里的菜单项在 DOM 里是**隐藏模板**（`getBoundingClientRect()` 全为 0），`bsk click` 会报 `target element has no visible geometry`，evaluate 三连事件也无效。
   → **直接 navigate 编辑器 URL**：`https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=10&token=<TOKEN>&lang=zh_CN`
2. **正文注入用 ClipboardEvent + text/html**（本次验证可行）：
   ```js
   var v = window.__mpBodyChecktextView;   // 正文 ProseMirror view（编辑器自带全局）
   var dt = new DataTransfer(); dt.setData('text/html', html);
   v.focus();
   v.dom.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles:true, cancelable:true}));
   ```
   - ⚠️ **只设 `text/html`，不要再设 `text/plain`**：两者都设时 ProseMirror 会走纯文本路径，把整篇压成**一个段落**（换行变硬回车）。只给 html 才能保留 `<p>/<h2>/<hr>` 结构。
   - ⚠️ **不要按 `childCount` 判断是否成功**：公众号 schema 把 `md2wechat` 的外层 `<section>` 建模成 `para` 节点嵌套，顶层 childCount 常只有 1–4，看起来像失败其实是成功的。
   - ✅ **正确的验收方式**：数 `v.dom` 里的元素 —— `getElementsByTagName('p'|'h2'|'h3'|'hr').length`，与源 md 的段落/标题数对齐。本次 76 p / 7 h2 / 2 h3 / 7 hr 全部对上。
3. **md2wechat 会把 `【配图：xxx.png】` 转成「图 N · 图片占位」预览块**（占位文案在，文件名也在，仍可定位），注入后按「占位粘贴替换法」处理，或改从 md 自建。
4. **标题 / 摘要 / 作者填法**（原生 setter + input 事件，三个字段都验证联动成功）：
   - 标题：`.ProseMirror`[0]（或 `textarea#title` / `.js_title`），`execCommand('insertText')` 可用，**会联动隐藏 textarea**
   - 摘要：`textarea#js_description`（**上限 120 字**，超了会被拒）
   - 作者：`input#author`
   ```js
   var setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;
   setter.call(el, val);
   el.dispatchEvent(new Event('input',{bubbles:true}));
   el.dispatchEvent(new Event('change',{bubbles:true}));
   ```
5. **草稿列表校验走同源 fetch**（比截图快且准）：
   ```js
   fetch("/cgi-bin/appmsg?token=<TOKEN>&lang=zh_CN&f=json&ajax=1&random="+Math.random()
        +"&action=list_ex&begin=0&count=10&type=77&sub=all").then(r=>r.json())
   ```
6. **bsk session 生命周期**：Agent Window 被关掉后 session 立刻失效（daemon 日志 `session removed: user closed Agent Window`）。**同一轮的多步动作尽量串在同一条命令里**，或每步前重新 `session start`。

### 未解（下次接着查）

- 🔴 **`保存为草稿` 点击后请求发出但被服务端拒**：`POST /cgi-bin/operate_appmsg?t=ajax-response&sub=create&type=10` 返回 200，但页面把 `ret=200002` 上报 badjs，前端抛 `TypeError: Cannot read properties of undefined (reading 'data')`，草稿未落库（`list_ex` 查无新条目）。**原因未定位**（曾怀疑封面必填，未证实）。
- 🔴 **`BROWSER-SKILL-OVERLAY` 遮罩**：bsk 会往页面注入一个覆盖层，`document.elementFromPoint()` 命中它。虽然 `bsk click` 报 `click ok`，但需警惕坐标类点击被拦。
- 🔴 **XHR/fetch 钩子抓不到 `operate_appmsg` 请求体**（patch `XMLHttpRequest.prototype.send` 与 `window.fetch` 均未捕获），导致无法回放请求看错误详情。**下一步可试**：CDP Network.getRequestPostData，或直接手工构造该接口请求。

## 六、公众号设置页 DOM 操作 SOP（slogan / 自动回复 / 合规）

> 2026-09-03 实战验证。核心原则：**全程 `page.evaluate` 读 DOM 文本 + 原生 `.click()`，禁用像素坐标**（公众号后台布局漂移、坐标点击易错）。

### 6.1 公众号简介（slogan）修改
1. 入口：`设置与开发 → 账号设置 → 账号详情`，简介行"修改"按钮 = `<a id="modifyUserInfo" href="javascript:;">修改</a>`（DOM 原生 click）。
2. 编辑框是 `[contenteditable=true].ProseMirror`（非 textarea！）。用 DOM Range 全选 → `keyboard.press("Delete")` → `keyboard.type(新文本)`。
3. 保存：点弹窗内"确定"按钮。
4. 字数限制 120 字；修改次数每月 5 次（官方注释在 HTML 里）。

### 6.2 自动回复页入口（重要）
- **直接 `page.goto` 自动回复 URL 会跳回账号设置页**（`settingpage?t=setting/autoreply` 无效）。
- 正确入口：**hover 左侧"互动管理"菜单项 → 点"自动回复"链接**（href=`/advanced/autoreply?t=ivr/reply&action=beadded&token=...`，id=`menu_10006`）。hover 用 `page.locator('li:has-text("互动管理")').hover()`，点击用 `page.locator('a:has-text("自动回复")').click()`。
- 进入后 tab 有：被关注回复 / AI回复 / 关键词回复。点"编辑回复"进入 ProseMirror 编辑框（600 字上限，实时 `N/600` 计数器）。

### 6.3 关键词自动回复：新增规则（【角色】类钩子）
入口同 6.2（关键词回复 URL：`advanced/autoreply?action=smartreply&t=ivr/keywords`）。完整 SOP（2026-09-03 验证）：
1. 点"添加回复"：**必须用 Playwright locator `button.weui-desktop-btn_primary:has-text("添加回复").click()`**——原生 JS `.click()` 触发不了弹窗（Vue 绑定，需真实事件序列）。
2. 规则名称：`input[placeholder="输入规则名称"]`；关键词：`input[placeholder="输入关键词"]`（默认半匹配=包含即触发）。
3. 回复内容：**hover `.msg_sender_area__add-target` 展开下拉**（不是 click）→ 点 `li.weui-desktop-msg-sender__tab_text`（文字）→ 在 `[contenteditable=true].edit_area` 用 DOM Range + `keyboard.type` 输入文本。
4. 保存：`button.weui-desktop-btn_primary:has-text("保存").click()`；保存后等 4-5 秒再验证（异步刷新列表）。
5. 验证：列表出现规则名、退出编辑态（`输入规则名称` 不再出现）。
> 坑：文字 tab 需 hover 才显示；原生 click"添加回复"无效必须 locator；daemon 闪退后弹窗状态会丢（填完尽快保存）。

#### 6.3-补 · bsk 通道批量建规则 SOP（2026-09-11 实战验证，一次 7 条全过）

Playwright locator 流程之外的 bsk 纯 evaluate 打法（无需扫码登录态）：

1. **点「添加回复」**：dispatch mousedown→mouseup→click 三连（合成事件有效，此按钮不吃 isTrusted）。
2. **填名称/关键词**：原生 setter + input/change 事件（标准打法）。
3. **媒体菜单**：dispatch mouseover/mouseenter → dispatch click `li.weui-desktop-msg-sender__tab_text`（文字）。
4. **编辑器激活（关键坑）**：新开弹窗的 `edit_area` 未激活时，`bsk fill` 内容进得了 DOM 但 **Vue 模型不更新**（点确定报「内容不能为空」）。激活法：`ed.focus()` + `document.execCommand('insertText',false,'测')` 且 innerText 确认 >0（DEAD 则重试）；再用 `bsk press Meta+A` + `Backspace` 清空 + `bsk fill` 全文。
5. **备用填充**：合成 `ClipboardEvent('paste')` + DataTransfer text/plain 也验证可行（rule 3 成功案例）；execCommand 激活法优先。
6. **点「确定」/「保存」（关键坑）**：弹窗按钮是 Vue `mp-button` 组件，**合成事件与 bsk 真实坐标点击都可能无效**（坐标被 devicePixelRatio 缩放错位 + `browser-skill-overlay` 自定义标签盖在最上层拦截 elementFromPoint）。**必杀技：Vue 组件直调**——找到可见按钮后向上爬 ≤8 层找 `__vue__`（mp-button，有 `click` 方法），直接 `el.__vue__.click()`。
7. **overlay 拦截排查**：`document.elementFromPoint(按钮中心)` 若返回 `BROWSER-SKILL-OVERLAY`，它是**自定义标签**（不是 class/id！），`document.getElementsByTagName('browser-skill-overlay')` 才能抓到 → `.remove()`。
8. **验证闭环**：确定成功 = edit_area 不可见；保存成功 = 列表 innerText 含规则名。失败先查「内容不能为空」toast（模型空 = 回到第 4 步重激活）。
9. 整条规则失败就**整页 navigate 刷新重来**（弹窗 DOM 会被反复开关搞脏，残留栈叠实例）。
10. 合规红线同样适用：回复文案禁私人微信/导流（见 6.4）。

### 6.4 被关注回复 / 简介 导流红线（必读 · 2026-09-14 事实订正）

- **规范依据**：《微信公众号和服务号**推荐**运营规范》第 **5.4 条 · 导流内容**。
  ⚠️ **不是**《微信公众平台运营规范》——那份管**账号处罚**；5.4 管的是**推荐资格**，两者后果完全不同。
- **三类导流**：① **内容导流**（发不完整内容再引去别处）② **互动导流**（在**账号简介 / 正文 / 评论 / 公众号消息 / 菜单**中嵌入**微信号、二维码、外部链接**，把用户引向私人账号或站外）③ **多重嵌套导流**（A→B 跳转规避检测）。2026-06 细化为 3 类 9 个动作。
- **后果分级（关键）**：触发 5.4 的后果是「**不符合内容推荐条件**」→ **停止推荐（限流）**，**不是封号**。在本号意味着**主动放弃推荐曝光**（行途推荐占比基线仅 1.1%，见 PUB-041）。
- **适用范围**：5.4 **不区分「私人微信」还是「品牌 / 商务微信」**——只要是微信号、二维码、外链，就落在互动导流里。品牌专用号（如 `xingtu_note`）**同样适用**。旧文案写「私人微信」易被误读成"换个号就豁免"，2026-09-14 订正。
- **谐音 / 变体同样封堵**：V我、+v、薇信、wx 等。
- **站内关键词互动是合规形态**：回复【关键词】领资料 / 合集卡片，属官方鼓励的互动。
- **合规出口**：视频号、未来企业微信、评论区互动；**商务联系优先用品牌邮箱**（邮箱未被 5.4 点名，风险显著低于微信号）。
- **溯源**：2026-09-03 已删违规「回复【交流】获取私人微信」→ 改站内「回复【角色】领《AI 头衔定位自查卡》」。**行为判断正确，当时的标签「私人微信」不准确**。
- **校验**：保存后 `page.evaluate` 读 innerText，确认正则 `私人微信|xingtu_note|微信号|wx[:_：=]|薇|VX` 均**不在**，且 `【角色】` 在。

## 七、SEO / GEO 优化红线（发布前过一遍）

见 `xingtu-vault/03_运营工具箱 (Operations Toolkit)/02_排版与设计/行途公众号SEO与GEO规范.md`：
- **SEO（搜一搜）**：标题前 15 字含核心关键词、首段 100 字内自然出现 2-3 次、每 300 字一个含词小标题、密度 2-3%
- **GEO（AI 检索）**：开头用 1-2 句直接给"可引用的结论"（引用钩子）、问答式小标题、术语标准口径、结构化分点、文末金句收束

## 八、配图自动上传「占位粘贴替换法」（2026-09-06 验证，0907 草稿 5 图全成功）

正文里预留【配图：xxx.png】文字占位 → bsk 自动化替换为真实图片：

1. **图片进页面**：本地 PNG base64 分 30 块 `bsk evaluate` 设 `window.__img64_i` → 页内拼接 `atob` → `Uint8Array` → `new File(...)` 存 `window.__pf`。
2. **选中占位**：TreeWalker 找含 `【配图：xxx.png】` 的文本节点（注意：粘贴过一次后 PM 重渲染会把后续文本节点打散，**每张图都要 fresh navigate 后操作**，或用段落级跨节点偏移映射）。
3. **粘贴替换**：`el.focus()` → DOM Range 选中占位 → `new ClipboardEvent('paste', {clipboardData: dt, bubbles:true})` dispatch 到占位的父元素 → 编辑器自动上传图片并替换占位。
4. **等上传完成**：paste 后 sleep ≥12s（图片要传微信服务器），再保存。
5. **占位残留清理（必做）**：粘贴有时只插入不删除选区（DOM 选区未同步 PM state）→ 用 PM 事务删除：`v.state.doc.descendants((n,pos)=>{if(n.isText)spans.push({from:pos,text:n.textContent})})` 收集文本 span → 拼接定位占位 → `toPM(offset)` 映射位置 → **从后往前** `tr.delete()` → dispatch → 保存。
6. **保存纪律**：任何修改后立即「保存为草稿」（三连鼠标事件）；会话中途死掉未保存的修改会全丢（实测教训）。

已知不可自动化（留人工 5 分钟）：封面上传（drop/file input 三路均不通）、赞赏（新编辑器弹窗结构变化）、合集勾选、定时群发。

## 九、官方草稿 API 通道 + 建稿后凭证回查（2026-09-15 实战全链验证）

> 与 bsk/Playwright 的关系：**09-06 引擎定案不变**（后台 UI 自动化默认 bsk）。本节是「纯导入到草稿箱」的第三条通道：`tools/wx_draft_api.py` 直接把发布包建成公众号草稿（图片自动上传内嵌、封面自动挂），单会话实测 4 轮建稿全通、零浏览器零扫码。**API 到草稿箱为止**：勾原创、选合集、设定时、点群发四个动作 API 做不了（合集/定时接口本号无权限或已回收），仍留人工——那几下必须 boss 点。
> 与第八节的关系：第八节「占位粘贴替换法」是**浏览器通道**在编辑器内替换占位；API 通道的占位替换发生在**建稿前的本地正文构建**，两条路互不依赖。

### 9.1 命令与凭据

```bash
cd ${WORKSPACE} && python3 tools/wx_draft_api.py \
  --pkg "outputs/发布包_2026-09/<包目录>" \
  --title "<标题>" --desc "<摘要，≤120字>" \
  --cover-file "<pkg>/03_封面/<选定封面>.png" \
  --dry-run          # 先干跑，去掉此行才真正建稿
```

- 凭据：`--appid` 默认本号 appid；`--secret-file` 默认 `github/xingtu-vault/09_个人台账/04_凭据备忘/公众号AppSecret_2026-09-02_明文.txt`（取其中最后一个 32 位串）。token 走 `GET /cgi-bin/token?grant_type=client_credential`。
- **`--cover-file` 务必显式传**：不传时脚本按 `03_封面/` 内 sorted 末位、排除含「真人/旧」的 png 自动选——封面深浅底交替这类人工决策会被自动逻辑顶掉（9-15 实战即靠显式传参避免选错底）。
- 脚本内部链路：读 `02_排版HTML` 正文 → `media/uploadimg` 逐张传 `04_配图` 并替换【配图：xxx.png】占位 → `material/add_material?type=image` 传封面拿 thumb_media_id → `draft/add`。成功输出 `⑤ ✅ 草稿已建：draft media_id = ...`。

### 9.2 dry-run 闸门：必看「嵌图 N/N」（首案大坑）

🔴 **占位名不匹配 = 配图连提示一起凭空消失，且无任何报错。** 脚本正文构建末尾有一条 `re.sub(r"<p[^>]*>【配图：[^<]*</p>", "", body)`——凡占位里的文件名与 `04_配图/` 实际文件名对不上（uploadimg 没跑、占位未被替换），**整个占位段落被静默删除**。首案（2026-09-15）：正文写 `三家底牌对比表.png`，实际文件是 `01-三家底牌对比.png`（且带编号前缀），dry-run 显示 **嵌图 0/3**——若直接建稿，得到的是一篇三处图片锚点都不存在的纯文字长文，发布后才发现就晚了。

纪律：
1. 任何建稿前**必跑 `--dry-run`**，核对输出行 `② 正文构建：N chars（嵌图 N/N）`，**分子=分母才许建稿**；
2. 修法优先**对齐文件名**（改正文 MD/排版 HTML 里的占位名 = `04_配图` 实际名），不要指望脚本兜底；
3. MD 与 02_排版HTML 的占位要**同步改**，只改一边等于没改。

### 9.3 建稿后凭证回查：draft/get 六项（脚本自述不作数）

`draft/add` 打印「已建」≠ 真在箱、≠ 内容对（B-009/查凭证不问模型同源）。建稿后立即用同一 token 调 `POST /cgi-bin/draft/get?media_id=...` 核六项：

| 项 | 取法 |
|---|---|
| 标题 | `item.title` |
| 摘要 | `item.author` / digest 字段 |
| 字数 | `len(content)` 去标签后计数 |
| 嵌图数 | `content.count("<img")`（应 = 预期张数） |
| 残留占位 | `content.count("【配图")` 必为 0 |
| 错名/关键词计数 | 对已知易错词（如产品名错写「千问工作」）逐个 count，错名=0、正确名>0 |

### 9.4 batchget 认稿两坑：字段位置 + 前缀撞车

用 `POST /cgi-bin/draft/batchget`（`{offset,count,no_content:1}`）列草稿箱认稿时：

1. **media_id 在 item 顶层**（`item["media_id"]`），**不在 `content` 里**——按 `item["content"]["media_id"]` 取会拿到空值，导致比对逻辑把终稿误标成「旧稿(删)」（2026-09-15 实测踩过，差点让 boss 删错稿）。
2. **同批草稿 media_id 前 16 位完全相同**（实测「三国杀」三份全部以 `EnzxjcHKb7JLLj5C…` 开头）——后台列表与 batchget 结果**都只能靠 `update_time` 区分**。写进开箱操作单的认稿凭证必须是「更新时间 + 字数 + 嵌图数」三元组（如「发 09-15 22:02 那份，嵌图 3、18739 字」），禁只写 media_id 前缀。旧稿（错名/无嵌图/旧立意）在操作单里列成「❌ 删掉」清单，防手忙点错。

### 9.5 图上眼见为实：从草稿里看图，不看本地文件

本地 PNG 对 ≠ 草稿里的图对（草稿可能嵌着上一轮的旧图 URL，uploadimg 每次返回的 URL 也不保证可回溯比对）。正确链：

1. **正文图**：从 draft/get 的 `content` 里正则抽 `https?://[^"]+mmbiz[^"]+` URL → 逐张下载到临时目录 → Read 看图（多模态核验文字内容/排版/留白）。**草稿图字节比本地小是微信侧压缩，属正常**——新旧之争只能靠眼睛定。
2. **封面 thumb**：`POST /cgi-bin/material/get_material`（body `{"media_id": thumb}`）——🔴 **图片素材返回的是图片字节流，不是 JSON**，`json.loads` 必炸；直接落盘，与本地封面 PNG **比字节数**（如 53391 = 53391 → 逐字节同一文件，最强凭证，无需再看图；若不等再 Read 看）。
3. 临时验证目录用完走 `tools/safety/safe-delete.sh` 回收（禁 rm）。

### 9.6 改稿重建与中间稿回收：先建后删，总数对账

正文/配图/封面任一处变更 → 重跑 9.1–9.3 建新稿；确认新稿回查全绿后，再 `POST /cgi-bin/draft/delete`（body `{"media_id": 旧稿}`）回收中间稿。**顺序绝不能反**——任何时刻草稿箱里必须有一份可发稿。回收后 batchget 核对**草稿箱总数回到原数**（建一删一）作为闭环凭证。

- `draft/update` 原地换封面实测报 **40007 invalid media_id**（add_material 拿到的 media_id 未必可用作 update 的 thumb，未定位）——**勿追未知路径**，兜底就是上面的「add 重建 + delete 回收」，`wx_draft_api.py` 的 add 是已验证可靠路径。

### 9.7 环境与渲染配套坑

- **无 PIL**（`from PIL import Image` 直接 ImportError）：查图片尺寸用 macOS 自带 `sips -g pixelWidth -g pixelHeight <png>`。
- **`tools/fig_fit.py`（量高截图、重渲配图/封面）必须从工作区根运行并传相对路径**：cd 进发布包目录再跑，`tools/fig_fit.py` 相对路径解析失败（实测报路径错）。用法：`cd ${WORKSPACE} && python3 tools/fig_fit.py "outputs/.../04_配图/xx.html" ...`，输出同名 PNG 后用 mtime 复验确已重渲。
- 🔴 **修正文错名必须连图源一起扫**：产品名之类的错字会印在 `03_封面/*.html` 与 `04_配图/*.html` 源里——只改 MD/排版 HTML，封面图和已嵌进草稿的表格图上仍是错的（封面在列表页第一个露出，比正文更致命）。完整动作 = 正文 MD + 02_排版HTML + 00_标题摘要 + **封面/配图 HTML 源**全部替换 → fig_fit 重渲 → **逐张 Read 看图** → 重建草稿（走 9.2–9.5 回查）→ 回收含错图的旧稿。

<!-- public-sync: 2026-09-27 | 脱敏版本 | 源 .agents/skills/wechat-mp-publish -->
