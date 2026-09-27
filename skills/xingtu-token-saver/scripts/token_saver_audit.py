#!/usr/bin/env python3
"""token_saver_audit.py — xingtu-token-saver 诊断脚本（只读，零依赖，标准库）

按八层清单（L1需求/L2检索/L3协议/L4输入/L5散文/L6生成/L7prompt/L8config）
扫描指定工作空间的省 Token 配置成熟度。只读，绝不修改任何文件。

用法:
  python3 token_saver_audit.py --cwd /path/to/workspace --format text|json [--pack lite|full]
  python3 token_saver_audit.py --checklist ~/path/to/checklist.json  # 用自定义清单
"""
import argparse
import json
import os
import sys
from datetime import datetime

HOME = os.path.expanduser("~")
DEFAULT_CHECKLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "checklist.json")


def _expand(p):
    return os.path.expanduser(p)


def check_dir_exists(cwd, target):
    return os.path.isdir(os.path.join(cwd, target))


def check_any_file_exists(cwd, targets):
    return any(os.path.exists(_expand(t if os.path.isabs(t) or t.startswith("~") else os.path.join(cwd, t))) for t in targets)


def check_glob_any(cwd, targets):
    import glob as _glob
    for t in targets:
        pat = os.path.join(cwd, t) if not t.startswith("~") else t
        if _glob.glob(_expand(pat)):
            return True
    return False


def check_settings_contains(cwd, target, pattern):
    path = _expand(target)
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return any(k in text for k in pattern.split("|"))
    except OSError:
        return False


def check_grep_any(cwd, targets, pattern):
    for t in targets:
        path = _expand(t) if t.startswith("~") else os.path.join(cwd, t)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                if any(k in text for k in pattern.split("|")):
                    return True
            except OSError:
                pass
    return False


def run_check(cwd, chk):
    t = chk["type"]
    if t == "dir_exists":
        return check_dir_exists(cwd, chk["target"])
    if t == "dir_or_file_exists":
        return check_dir_exists(cwd, chk["target"]) or os.path.exists(os.path.join(cwd, chk["target"]))
    if t == "any_file_exists":
        return check_any_file_exists(cwd, chk["targets"])
    if t == "glob_any":
        return check_glob_any(cwd, chk["targets"])
    if t == "settings_contains":
        return check_settings_contains(cwd, chk["target"], chk["pattern"])
    if t == "grep_any":
        return check_grep_any(cwd, chk["targets"], chk["pattern"])
    return False


def audit(cwd, checklist, pack="lite"):
    cwd = os.path.abspath(cwd)
    layers_out = []
    for layer in checklist["layers"]:
        results = []
        for chk in layer["checks"]:
            ok = run_check(cwd, chk)
            results.append({"check": chk["key"], "desc": chk["desc"], "pass": ok})
        passed = sum(1 for r in results if r["pass"])
        total = len(results)
        score = round(100.0 * passed / total) if total else 0
        if score >= checklist["score_rule"]["pass"]:
            status = "healthy"
        elif score >= checklist["thresholds"]["patchable"]:
            status = "patchable"
        else:
            status = "priority"
        layers_out.append({
            "layer": layer["id"], "name": layer["name"], "score": score, "status": status,
            "results": results,
            "suggestions": [r["desc"] for r in results if not r["pass"]],
        })
    total_score = round(sum(l["score"] for l in layers_out) / len(layers_out)) if layers_out else 0
    full_extra = {
        "pack": pack,
        "manual_interview_full_only": [
            "会话内 /model 切换频率（缓存杀手：中途切换 = 缓存全失效）",
            "/compact vs /clear 偏好（大任务续跑用 compact；篇章断点用 clear 更省）",
            "是否实测过账单（金额结论须标注来源+日期，BUL-003）",
        ] if pack == "full" else [],
    }
    return {
        "tool": "xingtu-token-saver",
        "version": checklist.get("version", "0.1.0"),
        "audited_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "workspace": cwd,
        "total_score": total_score,
        "verdict": ("healthy" if total_score >= checklist["thresholds"]["healthy"]
                    else "patchable" if total_score >= checklist["thresholds"]["patchable"]
                    else "priority"),
        "layers": layers_out,
        **full_extra,
        "red_lines": checklist.get("red_lines", []),
        "motto": "省 token 是顺便，把『不必要』剥掉才是真本事。",
    }


def render_text(rep):
    icon = {"healthy": "OK", "patchable": "PATCH", "priority": "P0"}
    lines = []
    lines.append("=" * 62)
    lines.append("xingtu-token-saver 省Token成熟度诊断（只读）")
    lines.append("工作空间: %s" % rep["workspace"])
    lines.append("时间: %s    总分: %d/100 [%s]" % (rep["audited_at"], rep["total_score"], icon[rep["verdict"]]))
    lines.append("=" * 62)
    for l in rep["layers"]:
        lines.append("")
        lines.append("[%s] %s  %d分 [%s]" % (l["layer"], l["name"], l["score"], icon[l["status"]]))
        for r in l["results"]:
            lines.append("  %s %s" % ("+" if r["pass"] else "-", r["desc"]))
        for s in l["suggestions"]:
            lines.append("  -> 建议补: %s" % s)
    if rep.get("manual_interview_full_only"):
        lines.append("")
        lines.append("full 包人工访谈项:")
        for m in rep["manual_interview_full_only"]:
            lines.append("  ? %s" % m)
    lines.append("")
    lines.append("红线: %s" % "；".join(rep["red_lines"]))
    lines.append("金句: %s" % rep["motto"])
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="xingtu-token-saver 八层诊断（只读）")
    ap.add_argument("--cwd", default=os.getcwd(), help="待诊断工作空间路径")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--pack", choices=["lite", "full"], default="lite")
    ap.add_argument("--checklist", default=DEFAULT_CHECKLIST, help="自定义 checklist.json")
    args = ap.parse_args()

    if not os.path.isdir(args.cwd):
        print("错误: 工作空间不存在: %s" % args.cwd, file=sys.stderr)
        sys.exit(2)
    with open(_expand(args.checklist), "r", encoding="utf-8") as f:
        checklist = json.load(f)

    rep = audit(args.cwd, checklist, pack=args.pack)
    if args.format == "json":
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(render_text(rep))
    sys.exit(0 if rep["total_score"] >= checklist["thresholds"]["patchable"] else 1)


if __name__ == "__main__":
    main()
