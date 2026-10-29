#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""workspace_inventory.py —— 通用工作空间盘点与健康巡检（开源中立版）

职责：
  1. 枚举仓库根目录下全部 git 仓库：远程地址 / 分支 / 提交总数 / 最近提交日期 / ahead、behind / 未提交改动数
  2. 统计若干非 git 资产目录的文件规模
  3. 探测归档区 / 内嵌遗留克隆（不计入现役仓库矩阵）
  4. 健康分级（🔴 分叉 / 🟠 本地领先未推 / 🟡 未提交改动 / 无远程本地仓 / 🟢 正常）
  5. 与上一期 JSON 台账做跨期对比（仓数、提交总量、ahead 清单增删）
  6. 产出 JSON 台账 + Markdown 盘点报告；可选仅 JSON（定时任务 / CI 机器消费）

只读不写业务文件：不改仓库、不推送、不删文件。零依赖（Python 标准库）。
所有数字均来自本机 git / 文件系统实测，不估算、不编造。

用法：
  python3 workspace_inventory.py                          # 全量：JSON 台账 + Markdown 报告
  python3 workspace_inventory.py --root <工作区根>         # 指定工作区根（默认自动探测）
  python3 workspace_inventory.py --repo-root <目录>        # 仓库扫描根（默认 <root>/github）
  python3 workspace_inventory.py --json-only              # 只写 JSON（定时任务机器消费）
  python3 workspace_inventory.py --md-only                # 只写 Markdown 报告

退出码：
  0  无 🔴 分叉仓
  1  存在 🔴 本地与远端分叉（ahead>0 且 behind>0）——供定时任务告警
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, date
from pathlib import Path


# ---------------------------------------------------------------- 工作区根探测

def detect_root(start: Path) -> Path:
    """从脚本位置向上逐级探测：同时含 `github` 与 `rules` 的目录即工作区根。"""
    p = start.resolve()
    for cand in [p, *p.parents]:
        if (cand / "github").is_dir() and (cand / "rules").is_dir():
            return cand
    # 兜底：脚本位于 <root>/.agents/skills/<skill>/scripts/，向上 4 级
    return p.parents[3]


ROOT = detect_root(Path(__file__))

# 通用非 git 资产目录标签（相对工作区根）；可由使用者按自身布局替换
DEFAULT_NON_GIT_DIRS = {
    "rules": "rules",
    "workflows": "workflows",
    "tools": "tools",
    "data": "data",
    "outputs": "outputs",
    "skills": "skills",
}

# 归档区遗留克隆探测根（相对工作区根；不计入现役矩阵，单列一节）
LEGACY_SCAN_ROOTS = ["_archive", "_deprecated"]
LEGACY_INLINE_HINTS: list[Path] = []


# ---------------------------------------------------------------- git 采集工具

def git(repo: Path, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=30,
        )
        return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def count_files(p: Path) -> int:
    if not p.exists():
        return 0
    n = 0
    for _root, _dirs, files in os.walk(p):
        n += len(files)
    return n


def scan_repo(repo: Path) -> dict:
    name = repo.name
    remote = git(repo, "remote", "get-url", "origin")
    branch = git(repo, "branch", "--show-current")
    commit_count_raw = git(repo, "rev-list", "--count", "HEAD")
    try:
        commit_count = int(commit_count_raw) if commit_count_raw else None
    except ValueError:
        commit_count = None
    last_date = git(repo, "log", "-1", "--format=%ad", "--date=short")

    status_line = git(repo, "status", "-sb").splitlines()[0] if git(repo, "status", "-sb") else ""
    ahead = behind = 0
    no_remote = not remote
    m = re.search(r"\[ahead (\d+)(?:, behind (\d+))?\]", status_line)
    if m:
        ahead = int(m.group(1))
        behind = int(m.group(2) or 0)
    else:
        m2 = re.search(r"\[behind (\d+)(?:, ahead (\d+))?\]", status_line)
        if m2:
            behind = int(m2.group(1))
            ahead = int(m2.group(2) or 0)
    dirty = len(git(repo, "status", "--porcelain").splitlines())

    # 健康分级
    if ahead > 0 and behind > 0:
        health = "🔴 分叉"
    elif ahead > 0:
        health = "🟠 本地领先未推送"
    elif no_remote:
        health = "🟡 无远程（本地仓）"
    elif dirty > 0:
        health = "🟡 有未提交改动"
    else:
        health = "🟢 正常"

    return {
        "name": name,
        "group": "未分组",
        "path": str(repo),
        "remote": remote or None,
        "branch": branch or None,
        "commit_count": commit_count,
        "last_commit": last_date or None,
        "ahead": ahead,
        "behind": behind,
        "dirty": dirty,
        "no_remote": no_remote,
        "health": health,
    }


def scan_legacy_clones(root: Path) -> list[dict]:
    """归档区与内嵌遗留克隆：只登记，不计入现役矩阵。"""
    legacy: list[dict] = []
    for hint in LEGACY_INLINE_HINTS:
        p = root / hint
        if (p / ".git").is_dir():
            legacy.append({"path": str(p), "remote": git(p, "remote", "get-url", "origin") or None,
                           "note": "内嵌子克隆，随主仓不单列"})
    for rel in LEGACY_SCAN_ROOTS:
        base = root / rel
        if not base.exists():
            continue
        for dotgit in base.rglob(".git"):
            repo = dotgit.parent
            legacy.append({"path": str(repo), "remote": git(repo, "remote", "get-url", "origin") or None,
                           "note": "归档区遗留克隆（退役存档，不参与现役矩阵）"})
    seen, uniq = set(), []
    for item in legacy:
        if item["path"] in seen:
            continue
        seen.add(item["path"])
        uniq.append(item)
    return uniq


def scan_non_git(root: Path) -> dict:
    out: dict[str, int] = {}
    for label, rel in DEFAULT_NON_GIT_DIRS.items():
        out[label] = count_files(root / rel)
    return out


def load_previous(data_dir: Path) -> dict | None:
    if not data_dir.exists():
        return None
    prev = sorted(data_dir.glob("workspace_inventory_*.json"), key=lambda p: p.stat().st_mtime)
    if not prev:
        return None
    try:
        return json.loads(prev[-1].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def diff_previous(prev: dict | None, repos: list[dict]) -> dict:
    if not prev:
        return {"available": False, "note": "无上一期台账，本期为首跑，无跨期对比"}
    prev_repos = {r["name"]: r for r in prev.get("repos", [])}
    cur_names = {r["name"] for r in repos}
    added = sorted(cur_names - set(prev_repos))
    removed = sorted(set(prev_repos) - cur_names)
    prev_total = sum((r.get("commit_count") or 0) for r in prev.get("repos", []))
    cur_total = sum((r.get("commit_count") or 0) for r in repos)
    prev_ahead = {r["name"] for r in prev.get("repos", []) if r.get("ahead", 0) > 0}
    cur_ahead = {r["name"] for r in repos if r.get("ahead", 0) > 0}
    return {
        "available": True,
        "prev_date": prev.get("as_of"),
        "repo_count_delta": len(cur_names) - len(prev_repos),
        "commit_total_prev": prev_total,
        "commit_total_cur": cur_total,
        "commit_total_delta": cur_total - prev_total,
        "repos_added": added,
        "repos_removed": removed,
        "ahead_new": sorted(cur_ahead - prev_ahead),
        "ahead_cleared": sorted(prev_ahead - cur_ahead),
    }


def build(root: Path, repo_root: Path | None) -> dict:
    scan_dir = repo_root or (root / "github")
    repos: list[dict] = []
    skipped_dirs: list[dict] = []
    if scan_dir.exists():
        repos = [scan_repo(p) for p in sorted(scan_dir.iterdir()) if (p / ".git").is_dir()]
        for p in sorted(scan_dir.iterdir()):
            if not p.is_dir() or (p / ".git").is_dir():
                continue
            skipped_dirs.append({"name": p.name, "file_count": count_files(p)})
    legacy = scan_legacy_clones(root)
    non_git = scan_non_git(root)
    total_commits = sum((r["commit_count"] or 0) for r in repos)
    health_summary: dict[str, int] = {}
    for r in repos:
        health_summary[r["health"]] = health_summary.get(r["health"], 0) + 1
    return {
        "as_of": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "root": str(root),
        "summary": {
            "repo_count": len(repos),
            "commit_total": total_commits,
            "legacy_clone_count": len(legacy),
            "skipped_dir_count": len(skipped_dirs),
            "health": health_summary,
        },
        "groups": {"未分组": [r["name"] for r in repos]},
        "repos": repos,
        "non_git_assets": non_git,
        "legacy_clones": legacy,
        "skipped_dirs": skipped_dirs,
        "diff_previous": diff_previous(load_previous(root / "data"), repos),
    }


# ---------------------------------------------------------------- Markdown 报告渲染

def esc(s) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_markdown(d: dict) -> str:
    s = d["summary"]
    L: list[str] = []
    L.append(f"# 工作空间盘点与治理报告（{d['as_of'][:10]}）")
    L.append("")
    L.append(f"> 生成时间：{d['as_of']}　事实源：本机 git / 文件系统实测（非估算）　技能：workspace-inventory-governance")
    L.append("")
    L.append("## 一、盘点概览")
    L.append("")
    L.append(f"- 现役 git 仓库：**{s['repo_count']}** 个；提交总数：**{s['commit_total']}** 次")
    L.append(f"- 归档区 / 内嵌遗留克隆：{s['legacy_clone_count']} 处（退役存档，不计入现役矩阵）")
    L.append(f"- 仓库根下非 git 旁路目录：{s['skipped_dir_count']} 个（散落文档 / 空元数据目录，未纳入矩阵）")
    L.append("")
    L.append("| 健康状态 | 仓数 |")
    L.append("|---|:--:|")
    for k, v in sorted(s["health"].items()):
        L.append(f"| {k} | {v} |")
    L.append("")

    dp = d["diff_previous"]
    L.append("## 二、跨期对比")
    L.append("")
    if not dp.get("available"):
        L.append(f"- {dp['note']}")
    else:
        L.append(f"- 上一期：{dp['prev_date']}；仓数变化：{dp['repo_count_delta']:+d}")
        L.append(f"- 提交总量：{dp['commit_total_prev']} → {dp['commit_total_cur']}（{dp['commit_total_delta']:+d}）")
        if dp["repos_added"]:
            L.append(f"- 本期新增仓：{', '.join(dp['repos_added'])}")
        if dp["repos_removed"]:
            L.append(f"- 本期移除仓：{', '.join(dp['repos_removed'])}")
        if dp["ahead_new"]:
            L.append(f"- 新进入本地领先未推送：{', '.join(dp['ahead_new'])}")
        if dp["ahead_cleared"]:
            L.append(f"- 已推送清掉领先：{', '.join(dp['ahead_cleared'])}")
    L.append("")

    L.append("## 三、仓库矩阵明细")
    L.append("")
    L.append("| 仓库 | 提交数 | 最近提交 | ahead | behind | 未提交 | 状态 |")
    L.append("|---|:--:|:--:|:--:|:--:|:--:|---|")
    for r in d["repos"]:
        L.append(f"| {r['name']} | {r['commit_count']} | {r['last_commit'] or '—'} | "
                 f"{r['ahead']} | {r['behind']} | {r['dirty']} | {r['health']} |")
    L.append("")

    L.append("## 四、非 git 资产规模")
    L.append("")
    L.append("| 资产目录 | 文件数 |")
    L.append("|---|:--:|")
    for k, v in d["non_git_assets"].items():
        L.append(f"| {k} | {v} |")
    L.append("")

    L.append("## 五、归档区 / 内嵌遗留克隆")
    L.append("")
    if d["legacy_clones"]:
        L.append("| 路径 | 远程 | 说明 |")
        L.append("|---|---|---|")
        for item in d["legacy_clones"]:
            L.append(f"| `{esc(item['path'])}` | {esc(item['remote']) or '—'} | {esc(item['note'])} |")
    else:
        L.append("- 未探测到遗留克隆")
    L.append("")

    L.append("## 六、仓库根下非 git 旁路目录（未纳入矩阵）")
    L.append("")
    if d.get("skipped_dirs"):
        L.append("| 目录 | 文件数 | 说明 |")
        L.append("|---|:--:|---|")
        for item in d["skipped_dirs"]:
            note = "空目录 / 元数据目录" if item["file_count"] == 0 else "散落文档或工具配置，非 git 仓"
            L.append(f"| `{esc(item['name'])}` | {item['file_count']} | {note} |")
    else:
        L.append("- 无非 git 旁路目录")
    L.append("")

    action_items: list[str] = []
    for r in d["repos"]:
        if r["health"] == "🔴 分叉":
            action_items.append(f"🔴 **{r['name']}** 本地与远端分叉（ahead {r['ahead']} / behind {r['behind']}）：先 `git fetch` 评估合并或变基，人工确认后再操作")
            if r["dirty"] > 0:
                action_items.append(f"🟡 **{r['name']}** 另有 {r['dirty']} 个未提交改动：分叉处置前先确认这些改动的归属")
        elif r["health"] == "🟠 本地领先未推送":
            action_items.append(f"🟠 **{r['name']}** 本地领先 {r['ahead']} 个提交未推送：核对内容后择机 `git push`")
            if r["dirty"] > 0:
                action_items.append(f"🟡 **{r['name']}** 另有 {r['dirty']} 个未提交改动：确认是进行中工作还是残留，择机提交或丢弃")
        elif r["health"] == "🟡 有未提交改动":
            action_items.append(f"🟡 **{r['name']}** 有 {r['dirty']} 个未提交改动：确认是进行中工作还是残留，择机提交或丢弃")
        elif r["health"] == "🟡 无远程（本地仓）":
            action_items.append(f"🟡 **{r['name']}** 无 origin 远程：确认是有意本地仓，还是漏挂远程")
    L.append("## 七、治理待办清单（只读建议，处置需人工拍板）")
    L.append("")
    if action_items:
        for a in action_items:
            L.append(f"- {a}")
    else:
        L.append("- 无待处理项")
    L.append("")
    L.append("---")
    L.append("")
    L.append("> 本报告由 workspace-inventory-governance 自动采集生成；盘点只读，不执行迁移、删除、推送等写动作。")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="通用工作空间盘点与健康巡检")
    ap.add_argument("--root", default=None, help="工作区根目录（默认自动探测）")
    ap.add_argument("--repo-root", default=None, help="仓库扫描根目录（默认 <root>/github）")
    ap.add_argument("--json-only", action="store_true", help="只写 JSON 台账")
    ap.add_argument("--md-only", action="store_true", help="只写 Markdown 报告")
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else ROOT
    repo_root = Path(args.repo_root).resolve() if args.repo_root else None

    data = build(root, repo_root)
    today = date.today().isoformat()
    data_dir = root / "data"
    out_dir = root / "outputs"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = data_dir / f"workspace_inventory_{today}.json"
    md_path = out_dir / f"workspace_inventory_report_{today}.md"

    if not args.md_only:
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"JSON ledger: {json_path}")
    if not args.json_only:
        md_path.write_text(render_markdown(data), encoding="utf-8")
        print(f"Inventory report: {md_path}")

    red = [r["name"] for r in data["repos"] if r["health"] == "🔴 分叉"]
    print(json.dumps({
        "ok": True, "repo_count": data["summary"]["repo_count"],
        "commit_total": data["summary"]["commit_total"],
        "red_fork": red,
    }, ensure_ascii=False))
    return 1 if red else 0


if __name__ == "__main__":
    raise SystemExit(main())
