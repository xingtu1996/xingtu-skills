# skill-inbox-triage reference

## 首案全记录（2026-09-16，作校准基准）

- **立项背景**：spec `xingtu/specs/202609161140-qwenwork-跨Agent技能复利引擎/`（机制拆解：千问=会话内主动沉淀+后台 awareness review 提名队列+人拍板落池路由+importance 分级/驱逐/反射防腐；本地选"文件协议中枢"方案，否掉自建复盘引擎）。
- **首张真实卡**：`dedup-harness-neighbors`（merge 类）——红队实测 harness-governance / cross-repo-skill-curation 在 Claude 池↔千问池各有一份实体（inode 284880224/225、284895372/449），属"两池同源镜像"双副本。**教训当场生效**：初版卡把 evidence 写成 `~/.agents/skills/...`，被 selfcheck.py 以"evidence 不可达"打回——提名前先 `stat/readlink` 实测，B-009 的机器化形态。
- **Q1/Q2 拍板**：A=白名单软链进千问池（首链需千问侧查证识别，不识别退化路由直读）；A=挂 Claude Stop/PreCompact 钩子+修 09:30 日报 cron（当时 lastRunStatus=error）。

## 查重 grep 清单（软链感知，按 PROTOCOL §4）

```bash
ls ~/.agents/skills/                          # ①实体池
for d in ~/.claude/skills/*/; do [ -L "$d" ] || echo "REAL(claude): $d"; done   # ②跳软链
for d in ~/.qwenworkcn/skills/*/; do [ -L "$d" ] || echo "REAL(qw): $d"; done   # ③千问池照查
ls <当前工作区>/.agents/skills/ 2>/dev/null    # ④项目池
grep -ril "<关键词>" ~/.agents/skills/*/description 亦可扫 frontmatter
```

## 批题模板（正文呈现时用）

```
📥 收件箱 pending N 张（本批 2）：
题1 [卡id|score] 一句话标题
  A 处置方案（推荐，理由一句）
  B 替代方案（权衡一句）
  默认：A（未回按 A 执行）
```

## 落盘工具备忘

- 千问侧建/改技能可用其 `qwenwork_skill_manage`（create/patch/edit/delete，delete 走回收站）；Claude 侧新技能可用 skill-creator 评测触发质量（非必选）；两法产物都回同一实体目录，**不许产生第二实体**。
- 软链命令（macOS）：`ln -s ~/.agents/skills/<name> ~/.claude/skills/<name>`；千问池同式，建后用千问技能清单/`ls -la` 双验证。
- 台账：`python3 ~/.agents/tools/skill_pool_ledger.py` → `~/.agents/skills/POOL_LEDGER.md`；镜像风险列由它机械检出，人工裁决处置。

## 边界（防与邻居打架）

| 事 | 归谁 |
|---|---|
| 新建议卡 → 拍板 → 新技能出 | 本技能 |
| 存量池"要不要瘦身/合并/删除"的方法与判重 | `cross-repo-skill-curation`（引用不复制） |
| harness 配置层（rules/入口文件/常驻上下文）审计 | `harness-governance` |
| 会话成果写项目记忆/CHANGELOG | `session-sediment` / 各工作区收尾铁律 |
| 单篇稿件/发布核验 | 各项目内容线技能，本技能不碰 |
