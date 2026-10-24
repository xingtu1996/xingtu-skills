---
name: xingtu-article-archive
description: 把公众号已发布文章归档同步到 GitHub 公开仓（xingtu-articles）+ 个人站（xingtu-site）并维护封面。当用户说"归档已发布文章""同步文章到 GitHub""补文章镜像""更新个人站文章列表""维护封面""其他文章排版/配图/素材没做好"时使用。覆盖：从发布档案台账核对已发布清单 → 比对 xingtu-articles 缺口 → 取本地成稿镜像（frontmatter/配图/结尾模块）→ 脱敏 → privacy_scan → 个人站 ARTICLES 同步 → SSH 推送 → CHANGELOG。
---

# 已发布文章归档同步

把「公众号已群发」的文章，规范地镜像到 GitHub 公开仓 + 个人站，并维护封面与配图。

## 红线（动手前必读）

- **原创首发闸门**：仅镜像「已群发」文章；未发布的排期稿（B12/B02/B09 等）全文禁上公网站点，只放 teaser。
- **隐私扫描**：对外前必跑 `python3 tools/privacy_scan.py --fail-fast`，全绿才允许 `git add`。
- **Git 身份**：两仓已钉死「行途 XingTu」；GitHub 走 SSH：`ssh://git@ssh.github.com:443/xingtu1996/<repo>.git`（HTTPS 被代理挡）。
- **脱敏**：雇主/真名/薪资用「某快消巨头」等模糊化（SAF-004/006）。

## 流程

1. **核对清单**：读 `github/xingtu-vault/09_个人台账/03_已发布文章档案/已发布文章档案.md` 拿已发布全量。
2. **比缺口**：`ls github/xingtu-articles/articles/` 比对。⚠️ 台账短码（如 `yXs9NZ`/`KBEzL9`）与仓内 `original` 长链接常不一致，勿误判缺失——先读仓内 md 的 `original` 字段核对。
3. **取成稿**：本地发布包 `outputs/发布包_*/_archive/已发布/<日期>_<标题>/01_正文/*.md`；检查【配图】占位与本地 png，图随文复制到 `articles/` 同目录。
4. **Frontmatter**：`title/date/original/views/category/author` 齐全（早期旧文可能用 `collection` 代替 `category`，补 `author` 即可）；结尾保留「关于行途 XingTu/延伸阅读/数据来源/搜一搜/©/排版引擎」模块；清掉「公众号卡片占位」残留行。
5. **封面**：复制发布包 `03_封面/*.png` 到 `articles/covers/<slug>-cover.png`，README 加封面画廊。
6. **个人站**：同步 `github/xingtu-site/index.html` 的 `ARTICLES` 数组（补齐新发布批次）；名片站 `xingtu-github-io` 是纯卡片落地页，无需改。
7. **扫描+提交**：`privacy_scan` 通过后 `git add` + `commit`（只 commit 不 push，push 需 boss 授权）。
8. **推送**：`git push ssh://git@ssh.github.com:443/xingtu1996/<repo>.git HEAD:main`。
9. **收尾**：回写 CHANGELOG（`tools/changelog_append.py`）与当日记忆。

## 关键命令

- 隐私扫描：`cd ~/xingtu && python3 tools/privacy_scan.py --fail-fast`
- 推送：`git push ssh://git@ssh.github.com:443/xingtu1996/xingtu-articles.git HEAD:main`
- CHANGELOG：`python3 tools/changelog_append.py --type "🆕" --path <路径> --desc "<因为什么改了什么>" --tool workbuddy`

## 体检脚本（可选）

批量检查 frontmatter 完整性 / 【配图】占位残留 / 图片断链 / 结尾模块缺失，逻辑见本工作区 `tools/` 或按需重跑诊断。

<!-- public-sync: 2026-10-12 | 脱敏版本 | 源 ~/.workbuddy/skills/xingtu-article-archive -->
