#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布包组件健康检查（pkg-healthcheck 技能配套）

用法:
  python3 pkg_healthcheck.py --root <归档区目录> [--full] [--json]

动作:
  1. 扫描 --root 下每个子目录（成稿包），跳过 _废弃副本/_trash/_archive/_backup/_调研_/多平台分发/00_* 等
  2. 对照 references/component-baseline.md 的组件清单逐项 test -f
  3. 输出每包缺项明细 + 统计（全齐包/缺失包）
  4. --json 输出机器可读结果

组件清单与 vault 产出SSoT/发布包组件基线.md 对齐（漂移时同步两处）。
"""
import argparse, json, re, sys
from pathlib import Path

BASELINE = Path(__file__).parent / "../references/component-baseline.md"
EXCLUDE_SUFFIX = ("_废弃副本", "_trash", "_archive", "_backup", "_调研_")
EXCLUDE_PREFIX = ("多平台分发", "00_", "_")

def load_baseline():
    if not BASELINE.exists():
        # 兜底内置清单
        return [
            ("00_README.md", "glob"),
            ("CHANGELOG.md", "glob"),
            ("01_正文/*.md", "glob"),
            ("02_排版HTML/*.html", "glob"),
            ("03_封面/*.png", "glob"),
            ("00_标题摘要/标题摘要.md", "glob"),
            ("06_发布参考/开箱操作单.md", "glob"),
            ("06_发布参考/置顶评论.md", "glob"),
            ("06_发布参考/群推话术.md", "cond"),  # 有则更好
            ("07_作者素材/", "cond"),
            ("08_发布回流/", "cond"),  # 已发布包必选，待发布包发布后补
        ]
    items = []
    for line in BASELINE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("|") or line.startswith(">"): continue
        if re.match(r"^[-*]?\s*\S+", line):
            parts = re.split(r"\s+", line, maxsplit=1)
            pat = parts[0].lstrip("-* ").strip()
            mode = parts[1].strip().lower() if len(parts) > 1 else "glob"
            items.append((pat, mode))
    return items

def check_pkg(pkg_dir, items):
    missing, present = [], []
    for pat, mode in items:
        hits = list(pkg_dir.glob(pat))
        if hits:
            present.append(pat)
        elif mode == "cond":
            pass  # 条件组件不记缺失
        else:
            missing.append(pat)
    return missing, present

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="归档区目录，如 .../发布包归档_2026-10")
    ap.add_argument("--full", action="store_true", help="含条件组件缺失统计")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root = Path(a.root)
    if not root.is_dir():
        print(f"目录不存在: {root}", file=sys.stderr); sys.exit(1)
    items = load_baseline()
    pkgs = sorted([p for p in root.iterdir() if p.is_dir()
                   and not p.name.startswith(EXCLUDE_PREFIX)
                   and not p.name.endswith(EXCLUDE_SUFFIX)])
    results = []
    for p in pkgs:
        missing, present = check_pkg(p, items)
        results.append({"pkg": p.name, "missing": missing, "present_count": len(present), "ok": not missing})
    total, ok = len(results), sum(1 for r in results if r["ok"])
    print(f"== {root.name}: 包总数 {total}，组件全齐 {ok}，缺失 {total-ok} ==")
    for r in results:
        if r["missing"]:
            print(f"- {r['pkg']}: 缺 {', '.join(r['missing'])}")
    if a.json:
        print(json.dumps({"root": str(root), "total": total, "ok": ok, "results": results}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
