---
name: xingtu-article-sync
description: 行途文章库发布同步总控——发文后一条命令完成：新文章收编（年月归位/素材包/frontmatter 规范化）→ prev/next 与开源仓互链 → index.json → 三处展示层（articles README / 个人主页最新10 / 文章星图页）→ Data API 推送三仓。触发词：文章归档、发文同步、article sync、收编文章、文章库更新、星图页更新、主页文章同步。
version: 1.0.0
metadata:
  author: xingtu
  agent_created: true
---

# xingtu-article-sync · 文章库发布同步总控

> **工作空间锚点**：`<工作区根>`（唯一根）。
> **SSoT 分工**：结构规范 = `github/xingtu-articles/CONTRIBUTING.md`；
> 执行体 = `tools/articles_publish_sync.py`；推送 = `tools/github_data_push.py`。
> 本 skill 只管「发文之后到公开矩阵」这段，不管写稿与公众号后台（那是 mp-publish-sop / mp-prepublish-draft-verify 的事）。

## 何时用我

公众号文章**发布成功后**（或发布当天收尾时）跑一次。别每天空跑——`--check` 无缺口时它什么都不做，幂等。

## 一条命令（常规路径）

```bash
cd <工作区根>
python3 tools/articles_publish_sync.py --full --push
```

`--full` 幂等重建五层：①frontmatter 规范化（多行字段压平、slug/date 以文件名优先）②文末 prev/next + 「🔗 相关仓库」互链 ③`index.json`（含 related_repos）④articles README（最新10+分类+按月）⑤个人主页最新文章（封顶10行）+ 星图页 `articles.html`（最新10直出+更早折叠）。
`--push` 经 Data API 推 `xingtu-articles` / `xingtu1996.github.io` / `xingtu1996` 三仓（沙箱 git push 走 443 会被拦，禁直接 push）。

## 新文章收编（非常规路径）

```bash
python3 tools/articles_publish_sync.py --article <稿件md路径> [--images <配图目录>]
python3 tools/articles_publish_sync.py --full --push
```

前置硬约束（不满足会拒收）：
- 文件名 `YYYY-MM-DD-<英文slug>.md`；
- 有 frontmatter（title/date/slug/summary/category 必含）；
- 配图放独立目录，工具收进 `assets/YYYY/MM/<同名slug>/`，封面命名 `cover.png`。

## 核对缺口（发布后自查）

```bash
python3 tools/articles_publish_sync.py --check
```

数据源 = 最新 `data/stats_*.json`，已发布口径 = `msg_status==2 且 excluded_reason 为空`（`is_published` 恒 0，勿用）。
**履历指纹忽略名单 `IGNORE_DATES`（2020-08-08/09、2026-05-08）禁删**——那几篇含「电脑城学徒/学历」等三段式履历指纹，公开归档 = SAF-010 红线。

## 互链怎么长出来的

文章 ↔ 仓库双向：
- 正文文末「🔗 相关仓库」由工具按 `RELATED` 映射表注入（token 类→tokenhub-bench；harness 认知→xingtu-harness；vibe-coding→xingtu-sdd；FDE 线→xingtu-ai-engineering）。新仓接入 = 在映射表加一行。
- 反向「📖 延伸阅读」已手插在 4 个仓 README（harness/sdd/ai-engineering/tokenhub-bench），新文章要反链时手动补一行即可（工具不管反向，避免改动他仓 README 结构）。

## 红线与坑（2026-09-27 实战沉淀）

1. 🔴 **同 basename 图多篇共用 → `assets/shared/`**，不要复制多份（曾出现三篇共享 `00-封面引子图.png`）。
2. 🔴 **`【配图：…】`占位符是发布包软引用**，转真嵌入前先从 `outputs/发布包_2026-09/_archive/已发布/*/04_配图/` 补图，否则 75 断链。
3. 🔴 frontmatter 必须**单行字段**；多行 summary 会破 YAML 并让嵌套残留覆盖 date/slug（09-25 事故）。工具已带「文件名优先」守卫，但别手工在 fm 里贴多行。
4. ⚠️ Data API 大推送偶发 **422 瞬态**，重跑即过；推送后本地 HEAD 与远端分叉（blob 树一致），巡检只看树不看 HEAD SHA。
5. ⚠️ 改了 harness 子仓（如 tokenhub-bench）记得 Data API 更新 harness gitlink（`160000`），否则 clone 拿到旧子仓。
6. 兜底：若 `--push` 因 Data API 异常中断，**先 `--check` + 远端 tree 比对再重推**，勿盲目连推。

## 与其他 skill 的边界

- 写稿/去AI味 → `xingtu-content-craft` / `de-ai-flavor`
- 公众号后台发布/建稿核验 → `mp-prepublish-draft-verify` / `wechat-mp-publish`
- 全矩阵巡检（含本链路健康度） → `xingtu-oss-guard`
- 本 skill = **发布完成后**的公开矩阵同步层。
