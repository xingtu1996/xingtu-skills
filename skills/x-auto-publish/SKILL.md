---
name: x-auto-publish
description: 行途品牌自动宣发：基于本地工作空间素材（发布包/推文素材包/配图/品牌台账），用 bsk 真实浏览器自动发推（Thread 接龙）、同步各平台 profile 资料、小红书图文发布框架。触发词：发推、发 X、宣发、同步 profile、换简介、小红书发布。
version: 1.0.0
updated: 2026-09-06
author: 小研（WorkBuddy）
---

# x-auto-publish：行途自动宣发 SOP

> 前置依赖：`browser-skill`（bsk）已装且 daemon 运行；Chrome 扩展已开「允许访问文件网址」。
> 所有浏览器命令 Bash 必须 `dangerouslyDisableSandbox: true`（否则 SIGKILL）。

## 0. 素材自动读取（本地空间约定）

| 素材 | 路径 | 说明 |
|------|------|------|
| 发布包 | `outputs/发布包_2026-09/<日期_主题>/` | 正文/封面/配图 |
| X 推文素材 | `outputs/发布包_2026-09/X推文素材包_*.md` | 中英双语推文 |
| Thread 文案 | `outputs/发布包_2026-09/X引流内容矩阵_配图/X平台Thread发布文案_*.md` | 每条带配图路径 |
| 配图 | `outputs/发布包_2026-09/X引流内容矩阵_配图/*.png` | 1024×512 / 1024×1024 |
| 品牌标准值 SSoT | `xingtu-vault/13_品牌资产/品牌资产台账_v1.json` | bios.* 为各平台标准 bio |
| 留痕 | `outputs/发布包_2026-09/X引流内容矩阵_配图/发布留痕/` | 截图存这里 |

流程：读素材包 → 选版本 → （可选生成配图：HTML/CSS → Chrome headless 截 PNG，禁 PIL）→ 发布 → 留痕 → 回写。

## 1. X 发推 / Thread 接龙（已实战跑通 2026-09-06）

```bash
# ① 会话（闲置会断，断了就 bsk session start 重开）
bsk session start                      # 记住 4 位 session id
# ② 单条：进 compose；Thread 接龙：进上一条 status 页
bsk navigate "https://x.com/compose/post" --session <id>
# ③ 写文案（X 是 Draft.js，bsk fill 对其无效！必须 execCommand）
bsk click '[data-testid="tweetTextarea_0"]' --session <id>
bsk evaluate --session <id> --json "
(() => { const ed = document.querySelector('[data-testid=\"tweetTextarea_0\"]');
  ed.focus();
  document.execCommand('insertText', false, '推文文案（\n 换行）');
  return {ok:true, len: ed.textContent.length}; })()"
# ④ 上传配图（需扩展开"允许访问文件网址"）
bsk upload '[aria-label="Add photos or video"]' --session <id> --file "<png 路径>"
# ⑤ 发送前核验附件
bsk evaluate --session <id> --json "
(() => ({imgCount: document.querySelectorAll('[data-testid=\"attachments\"] img').length}))()"
# ⑥ 发送（compose 用 tweetButton，status 页回复用 tweetButtonInline）
bsk click '[data-testid="tweetButtonInline"]' --session <id>
# ⑦ 拿新推文链接（⚠️ 禁 parseInt/Number——X snowflake id 超 2^53 会丢精度！只取字符串）
bsk evaluate --session <id> --json "
(() => ({hrefs: [...new Set([...document.querySelectorAll('a[href*=\"/xingtu1996/status/\"]')]
  .map(a => a.getAttribute('href')))].filter(h => /status\/\d+$/.test(h))}))()"
# ⑧ 间隔 20-60s 防 spam；循环 ③-⑦ 直到 Thread 完
bsk session stop <id>                  # 收尾必关
```

**红线**：一(Thread)天最多 1-2 个 thread / 3-6 条；遇验证码用 `bsk request-help` 交还 boss；不发未脱敏内容；素材包内部资产不露出。

## 2. X / GitHub profile 同步（品牌台账驱动）

标准值来源：台账 `bios.*`（en_global→X、github→GitHub、tech_community→掘金/知乎/CSDN、lifestyle_community→小红书/B站）。

**GitHub（gh api，最稳）**：
```bash
/opt/homebrew/bin/gh api -X PATCH /user -f bio="<bios.github.standard>"
```

**X（bsk 改设置页）**：
```bash
bsk navigate "https://x.com/settings/profile" --session <id>
# 字段：input[name="displayName"]、textarea[name="description"]（React 输入用原生 setter + input 事件）
bsk evaluate --session <id> --json "
(() => { function setVal(el, val){ const p = el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(p,'value').set.call(el, val);
  el.dispatchEvent(new Event('input',{bubbles:true})); }
  setVal(document.querySelector('input[name=\"displayName\"]'), '<名称>');
  setVal(document.querySelector('textarea[name=\"description\"]'), '<bio>');
  return 'ok'; })()"
bsk click '[data-testid="Profile_Save_Button"]' --session <id>   # 成功=跳转 /home
```

**✅ 已完成（2026-09-06，2026-09-19 清洗）**：GitHub bio → v2 Builder 标准；X 显示名 → `行途 XingTu`、bio → en_global 标准。（原记 X 名称曾用违禁真名，SAF-004/010 于 09-13 裁决全面禁用 `行途` 及变体，此处按定版对外口径统一为「行途 XingTu」。）
**⏳ 待做**：X 头像/banner 上传（台账：v2 物料已备）；掘金/知乎/CSDN/小红书/B站 bio（各自设置页同法）。

## 3. 小红书发布框架（待首次实战）

路径：`creator.xiaohongshu.com/publish/publish?source=official`（需 Chrome 已登录小红书）。
- 图文：上传图片（`input[type=file]`，bsk upload input 模式）→ 标题（≤20字）→ 正文（≤1000字，emoji 适度）→ 话题标签 → 发布
- 标题公式（生活社区标准 bio 同源）：`Builder · 仍在写代码 | <主题钩子>`
- **先手动登录一次**，登录态复用后同 X 流程；首次跑先发 1 篇探路，观察限流。

## 4. 通用注意

- 所有对外动作（发帖/改资料）前：内容对齐 `rules/RULES.md`（脱敏、原创首发时序、SAF-004 真名不上公网）
- 发完必做：截图留痕 → 回写 CHANGELOG（--tool workbuddy）→ 发布日志登记
- 失败重试 ≤2 次；两次无进展 → 截图 + `bsk request-help` 交 boss
- X snowflake id 永远按字符串处理

## 5. 标题公式（对标张咋啦/Zara Zhang XHS，2026-09-06 沉淀）

小红书/对外标题 4 公式（≤20字，陌生人 3 秒看懂价值，见名知义）：
1. **数字+反差自嘲**：「我在 GitHub 上有 3 万星（虽然并不会写代码）」→ 大数字+意外转折
2. **成果 how-to**：「如何在一年 Twitter 涨粉 7 万」→ 可复制承诺+数字背书
3. **清单数字**：「最近收获最大的 6 个 YouTube 长视频」→ 明确预期带走 N 个
4. **观点金句**：「营销的重要原则：重复重复再重复」→ 冒号后半句是记忆点

规则：①系列编号（Day N）**不进标题**，连续性交给合集承载 ②数字钩子必须进标题 ③冒号后半句放最狠的记忆点

## 6. XHS 创作平台硬限制（2026-09-06 实测）

1. **红色主动作按钮（发布笔记/发布Skill）= 封闭 shadow 组件，只认真人点击**：合成事件/execCommand/CDP 坐标/Enter/Space 全部无效。自动化做到「内容+配置全就绪」，最后一击交 human（request-help 高亮）。
2. **未提交的表单禁导航**：XHS 表单状态不跨页面保持（仅自动暂存草稿箱），跳页=丢失。
3. 昵称/头像/简介改版、笔记设私密 = 仅手机 App；网页创作平台不可改。
4. 草稿双体系：App 草稿 ≠ 网页创作平台草稿，不互通；网页草稿存浏览器本地（清数据即丢）。
5. Vue 表单（合集/Red Skill）必须 execCommand 输入，原生 setter+input 事件不被 v-model 识别。

<!-- public-sync: 2026-09-27 | 脱敏版本 | 源 .agents/skills/x-auto-publish -->
