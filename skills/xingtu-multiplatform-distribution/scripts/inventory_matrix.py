#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inventory_matrix.py · 行途全矩阵已发布盘点（只读，零依赖）
================================================================
一键扫描：
  I  outputs/**/_archive/已发布/       → 公众号已发清单
  I  outputs/**/分发凭证_*             → 外站真实分发（闭环率真值，凭证即铁证）
  O  平台×文章 markdown 表 + 闭环率缺口

红线：只读，不动盘、不改稿、不发布。
范围守卫：根目录无 AGENTS.md 即拒绝（防串错项目）。
闭环率公式 SSoT 在 tools/dispatch_feed.py（本脚本只盘点数，不重造）。

用法：
  python3 scripts/inventory_matrix.py --root ${WORKSPACE}
  python3 scripts/inventory_matrix.py --root . --json
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


def scan_published(root: Path):
    """公众号已发：outputs/**/_archive/已发布/ 下每个子目录 = 一篇已发。"""
    out = []
    for archive in (root / "outputs").rglob("_archive/已发布"):
        for sub in sorted(archive.iterdir()):
            if sub.is_dir():
                out.append(sub.name)
    return out


def scan_evidence(root: Path):
    """全盘分发凭证_*（排除脏前缀 品牌化/更名/认证/隐私）。"""
    dirty = re.compile(r"(品牌化|更名|认证|隐私)")
    ev = []
    for p in root.rglob("分发凭证_*"):
        if p.is_file() and not dirty.search(p.name):
            m = re.match(r"分发凭证_(.+?)_(\d{4}-\d{2}-\d{2})\.", p.name)
            if m:
                ev.append((m.group(1), m.group(2)))
    return ev


def main():
    ap = argparse.ArgumentParser(description="行途全矩阵已发布盘点（只读）")
    ap.add_argument("--root", default=".", help="xingtu 工作区根（默认当前目录）")
    ap.add_argument("--json", action="store_true", help="输出 JSON 而非 markdown")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not (root / "AGENTS.md").exists():
        print("⚠️ 范围守卫：根目录无 AGENTS.md，疑似非行途工作区，拒绝。", file=sys.stderr)
        sys.exit(1)

    published = scan_published(root)
    evidence = scan_evidence(root)
    by_platform = {}
    for plat, dt in evidence:
        by_platform.setdefault(plat, []).append(dt)

    if args.json:
        print(json.dumps(
            {"published": published,
             "evidence": [{"platform": p, "date": d} for p, d in evidence]},
            ensure_ascii=False, indent=2))
        return

    print(f"# 矩阵已发布盘点 · {date.today().isoformat()}\n")
    print(f"## 公众号已发（{len(published)} 篇）")
    for a in published:
        print(f"- {a}")

    print(f"\n## 外站分发凭证（{len(evidence)} 条，闭环率真值）")
    if by_platform:
        for plat in sorted(by_platform):
            dates = ", ".join(sorted(by_platform[plat]))
            print(f"- **{plat}**：{len(by_platform[plat])} 条（{dates}）")
    else:
        print("- （无，闭环率=0）")

    print("\n## 闭环率缺口")
    k, m = len(published), len(evidence)
    print(f"- 公众号已发 {k} 篇；外站凭证 {m} 条")
    print(f"- 预估缺口（每篇 A/B 级铺 2–4 平台）：约 {max(0, k * 3 - m)} 条（以 dispatch_feed 公式为准）")
    print("\n> 凭证即铁证：闭环率真值以 `分发凭证_*` 文件数计，非台账文字。")
    print("> 刷新用 `python3 tools/evidence_register.py --list`。")


if __name__ == "__main__":
    main()
