---
name: xingtu-oss-guard
description: 行途开源矩阵的一体式安全与卫生巡检 + 历史清洗。四条检查面（工作区隐私 / git 提交历史 / 远程状态 / 外部部署面）串成一条命令，解决「各工具各报各的绿、合起来仍漏」的问题。触发词：开源巡检、oss guard、矩阵体检、历史清污、身份泄漏检查、force-push 前检查、发布前安全扫描、仓库卫生。
version: 1.0.0
metadata:
  author: xingtu
  agent_created: true
---

# xingtu-oss-guard · 开源矩阵守卫

> **工作空间锚点**：本 Skill 的服务对象是 `${WORKSPACE}`（唯一工作区根）。
> 文中所有相对路径（如 `tools/oss_guard.py`）均以该根为基准。
> ⚠️ 曾出现 `${STALE_WORKSPACE}` 残留目录导致自动化任务读到残缺数据，
> 动手前先确认根路径，不要在两个 xingtu 之间反复横跳。

## 它属于哪一层（避免误用）

**不是内容生产工具，是 IP 资产安全层。** 行的不是"写稿/排版/发布"那条线：

| 层 | 代表 Skill | 产出 |
|---|---|---|
| 内容生产 | `xingtu-content-craft` / `wechat-mp-publish` / `x-auto-publish` | 文章、图文、发布 |
| 素材供给 | `xingtu-ingest` / `yuanbao-archive-pipeline` | 素材卡、选题池 |
| **IP 资产安全** | **本 Skill** | **"能不能安全地对外"** |

它守的是「个人 IP 与真实身份分离」这条红线（SAF-004/006/010）——
**IP 能对外做多大的前提，是它不会反噬到本人的在职身份**。
所以归自媒体体系没错，但属于**地基**，不直接产出内容。

## 何时用

- 任何**公开动作之前**（新建仓、force-push、转公开、发解读文）——跑一遍再动
- 周期性巡检（已配「开源矩阵周巡检」自动化任务，周六 21:00）
- boss 问「我的开源还有没有泄漏 / 仓库还有哪些没补」
- 发现某个仓有身份或路径泄漏，需要清历史

## 三十秒上手

```bash
python3 tools/oss_guard.py                # 全量巡检，人读报告
python3 tools/oss_guard.py --json         # 机器可读（CI / 自动化任务用）
python3 tools/oss_guard.py --only history # 只跑某一面：workspace|history|remote|deploy
python3 tools/oss_guard.py --fail-fast    # 有 🔴/🟠 即 exit 1
```

发现问题要清历史：

```bash
bash tools/oss_history_purge.sh                          # dry-run（自动判定待清洗仓）
bash tools/oss_history_purge.sh --confirm --repo X       # 真跑（不 push）
bash tools/oss_history_purge.sh --confirm --repo X --push # 连带强推
```

## 为什么是四个面（不是三个、不是一个）

2026-09-14 那轮清污的血泪：**每个单点工具都报绿，合起来仍在大漏。**

| 面 | 查什么 | 单点工具查不到它的原因 |
|---|---|---|
| A 工作区 | 当前文件里的真名/英文名/本地路径 | — |
| B git 历史 | **曾经写进去过**的敏感串 | `privacy_scan` 只看当前文件，GitHub 却允许逐条浏览旧 commit |
| C 远程 | 可见性/描述/LICENSE/落后本地/SSH 死链 | 本地干净 ≠ 推送成功；remote 是 SSH 时永远推不上去且无报错 |
| D 部署面 | pages.dev 等外部托管活体 | 仓库删了、转私有、历史重写，**pages.dev 照样 200** |

一句话记住：**泄漏严重性 = 内容 × 可见性**。私有仓里的真名不算事故，公开仓的历史才算。

## 判级口径

- 🔴 致命：公开可见的真名 / 英文名 行途 / 公司项目代号 / 本地绝对路径 → 拦截
- 🟠 高危：公开仓缺 LICENSE、remote 是 SSH、无 origin → 拦截
- 🟡 提示：私有仓敏感串、本地领先远程、缺 description → 不拦截

**私有仓降级规则**（`is_public()`）：本地目录名 ≠ 远程仓名（如 `xingtu-github-io` → `xingtu1996.github.io`），
必须走 remote 反查；查不到按**公开从严**处理——宁可多报，不可漏报。

## 踩过的坑（不要重蹈）

1. **`users/{owner}/repos` 只返回公开仓。** 私有仓"不在列表里"会被判为未知从严 → 私有仓刷出一片假红。
   必须用 `user/repos?visibility=all&affiliation=owner`。
2. **`git filter-repo` 会被超时杀在半路**（exit 137），留下改了一半的仓库。
   历史无价值的场景一律用孤儿重建（`checkout --orphan`），原子且更彻底——
   filter-repo 只能替换你枚举到的串，漏了照样留；孤儿重建不管历史里有什么，整段丢。
3. **改完分支不等于删掉旧对象。** `refs/remotes/origin/*` 还吊着旧 commit，
   必须 `update-ref -d` + `reflog expire --expire=now --all` + `gc --prune=now`，否则等于没删。
4. **force-push ≠ 物理删除。** 旧 commit 用完整 SHA 调 API 仍返回 200 完整数据，等 GitHub 官方 GC。
   是"不可达"不是"不存在"。
5. **扫描器自己会静默失效。** privacy_scan v1 只扫 3 个目录却报全绿；v2 的 EXEMPT 用精确相等匹配全路径，
   豁免表永远匹配不上。覆盖不完整比不检查更危险，因为它**造安全感**。
   新增规则后，拿一个已知样例反验一次生效。
6. **本地目录可能分裂。** 曾出现 `${WORKSPACE}`（主，2.1G）与
   `${STALE_WORKSPACE}`（残留，4M）并存，自动化任务 cwd 指向残留目录 →
   飞轮读到 5.6KB 残缺 JSON（主库有 1161 张卡）。修路径前先 `du -sh` 两边对比。

## 工具清单

| 工具 | 作用 | 何时用 |
|---|---|---|
| `tools/oss_guard.py` | **四面一体巡检（唯一入口）** | 每次对外动作前 |
| `tools/privacy_scan.py` | 工作区隐私深度扫（15 条规则） | 被 oss_guard A 面自动调用 |
| `tools/oss_history_purge.sh` | 历史孤儿重建（带备份、dry-run 默认） | B 面报 🔴 时 |
| `tools/oss_identity_sanitize.py` | 文件内身份串替换（可逆，不动历史） | 只需改当前文件时 |
| `tools/strip_local_paths.py` | 清 HTML 里泄露的本地路径 token | 发布静态页前 |
| `tools/gh_push_api.py` | git push 被代理拦时的备用通道（Contents API） | push 报 000/超时 |
| `tools/oss_matrix_audit.py` | 矩阵元数据审计（描述/话题/子模块/LICENSE） | 季度盘点 |

## 标准流程

```
1. 备份     bash tools/safety/backup-before-op.sh "<动作描述>" <涉及路径>
2. 巡检     python3 tools/oss_guard.py --json
3. 判级     只看 🔴/🟠；🟡 记录不拦
4. 清洗     文件层 → oss_identity_sanitize / strip_local_paths
            历史层 → oss_history_purge.sh --confirm
5. 复检     python3 tools/oss_guard.py --fail-fast   （必须归零才继续）
6. 推送     git push（或 gh_push_api.py 兜底）
7. 回写     CHANGELOG + 工作日志 + 本 SKILL 的「踩过的坑」（有新坑就加）
```

## 硬约束

- **force-push / 转可见性 = 不可逆对外动作 → 必须 boss 点头**，脚本只打印命令不自动推
- 清洗前必有 `--mirror` 备份，备份失败则中止（宁可不动，不可无退路）
- 一周内新建的仓如需清历史，优先**删仓重建**（省去 GC 等待，代价是丢建仓时间）
- 公司项目代号（<COMPANY_PROJECT> / <COMPANY_GITLAB> / 客户名）属 SAF-006 红线，**任何形态不得进公开仓**

## 网络约束（本机实测，决定了"能用什么手段"）

代理 `127.0.0.1:63774` **只放行 `api.github.com`，拒绝 github.com 的 git 端点**：

```
curl https://api.github.com/     → 200  ✅
git ls-remote origin             → fatal: CONNECT tunnel failed, response 502  ❌
git push（SSH / HTTPS 都一样）    → 同上 ❌
```

推论（2026-09-14 实测，注意代理策略会变，动手前先 `git ls-remote` 探一次）：

| 手段 | 当前可用性 | 说明 |
|---|---|---|
| `gh api` / REST | ✅ | 读写元数据、文件内容、删仓建仓 |
| `gh_push_api.py`（Contents API 传文件） | ✅ | 能改文件内容，**但抹不掉历史** |
| `git push` / `git push --force` | ❌ | 历史重写必须走它，走不通就白改 |
| **删仓 + 重建 + API 传文件** | ✅ | **代理封锁期唯一能彻底清历史的手段**：新仓历史天然为 1 条 |

所以遇到「历史有泄漏但推不上去」时，别在孤儿重建上耗时间——直接走删仓重建
（前提是 0 star / 0 fork，且有 mirror 备份）。

## 发布与更新（对外动作怎么落地）

完整操作手册见仓库根 `PUBLISH.md`。要点：

1. **先探活网络**：`git ls-remote origin main` 通 → 走 `git push`；502 → 走 `gh_push_api.py`（Contents API，能改当前文件但抹不掉历史）。
2. **发布前必跑巡检**：`python3 tools/oss_guard.py --fail-fast`，有 🔴 先处置再发。
3. **历史敏感内容：保管，不物理删除**（boss 2026-09-14 决策）。
   用 `python3 tools/oss_quarantine.py --apply --repos <repo>` 把历史敏感片段**原样抽到 `.hold/`**，
   原始仓库（工作树+历史）一律不动；后续实践后再决定优化/清除。
4. **看板刷新**：`python3 tools/oss_guard.py --json > data/oss_guard_latest.json && python3 tools/skill_ledger.py`。

> 关键判断：force-push / 删仓重建都是**物理删除历史**，需 boss 明确授权；
> 而 `oss_quarantine.py` 是**可逆的保管**，默认即可执行，不改任何远程状态。

## 已知盲区（工具做不到，必须人工）

- base64 内嵌图片/字体里的文字
- 外部托管平台（Cloudflare Pages / Vercel）需登录平台侧删除
- GitHub force-push 后的悬空对象（需联系 Support 触发 GC）
