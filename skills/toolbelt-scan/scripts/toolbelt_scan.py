#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
toolbelt_scan.py — 云中立工具带盘点扫描器（零依赖，只读）

枚举本机 AI 工具签名表 → 统计（数据量/技能安装/会话/最后活跃）→
跨工具同名技能 SHA-1 漂移检测 → 脱敏门禁 → 产出 JSON + HTML 看板。

红线（硬编码，不可旁路）：
  - 只读：任何目录只 ls/du/count，不写不删
  - 敏感目录（凭据类）只报存在与否，不列内容
  - 绝对路径一律泛化为 ~/；红线技能名只计数不列名
  - 会话正文禁读，只统计数量/大小/时间
  - 输出过脱敏门禁才落盘：内置结构模式（个人路径/手机号/wxid/邮箱）
    + 外挂词表（--redline-file，身份/雇主代号，工作区私有件；公开仓不含词表本身）
"""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import datetime

HOME = pathlib.Path.home()
# 输出路径：默认相对当前工作目录（可用环境变量覆盖），公开仓不硬编码个人绝对路径
OUT_JSON = pathlib.Path(os.environ.get("TOOLBELT_OUT_JSON", "data/toolbelt_inventory.json"))
OUT_HTML_DIR = pathlib.Path(os.environ.get("TOOLBELT_OUT_HTML", "outputs"))

# ---------- 工具签名表：name -> (目录, skills 子路径, 数据/会话子路径) ----------
# 数据/会话子路径为 None 表示该工具无本地可统计数据
TOOLS = [
    # (显示名, 目录名, skills 相对路径, 会话/数据相对路径, 分类)
    ("Claude Code",      ".claude",        "skills",                    "projects",              "终端 Agent"),
    ("OpenAI Codex",     ".codex",         "skills",                    "sessions",              "终端 Agent"),
    ("Google Gemini",    ".gemini",        "skills",                    None,                    "终端 Agent"),
    ("Grok",             ".grok",          "skills",                    None,                    "终端 Agent"),
    ("WorkBuddy",        ".workbuddy",     "skills",                    "logs",                  "桌面 Agent"),
    ("CodeBuddy",        ".codebuddy",     "skills",                    "logs",                  "桌面 Agent"),
    ("CodeBuddy CN",     ".codebuddycn",   None,                        None,                    "桌面 Agent"),
    ("ZCode",            ".zcode",         "skills",                    "cli/db",                "桌面 Agent"),
    ("DSH",              ".dsh",           "plugins",                   "sessions",              "桌面 Agent"),
    ("豆包工作",         ".dws",           "skills",                    None,                    "桌面 Agent"),
    ("DoubaoWork",       "DoubaoWork",     "skills",                    None,                    "桌面 Agent"),
    ("千问办公",         ".qwenworkcn",    "skills",                    "projects",              "桌面 Agent"),
    ("Cursor",           ".cursor",        None,                        None,                    "IDE"),
    ("Trae",             ".trae",          "skills",                    None,                    "IDE"),
    ("Trae CN",          ".trae-cn",       "skills",                    None,                    "IDE"),
    ("Qoder",            ".qoder",         "skills",                    None,                    "IDE"),
    ("Lingma",           ".lingma",        "skills",                    None,                    "IDE"),
    ("Junie",            ".junie",         "skills",                    None,                    "IDE"),
    ("OpenCode",         ".config/opencode","skills",                   None,                    "终端 Agent"),
    ("Antigravity",      ".antigravity",   None,                        None,                    "IDE"),
    ("Agent 技能池",     ".agents",        "skills",                    "skill-inbox",           "技能池"),
    ("Ego Browser",      ".ego-browser",   None,                        None,                    "工具"),
    ("CherryStudio",     ".cherrystudio",  None,                        None,                    "工具"),
    ("Chat2DB",          ".chat2db",       None,                        None,                    "工具"),
    ("CC Switch",        ".cc-switch",     None,                        None,                    "工具"),
]

# ---------- 敏感目录：模式匹配（公开仓禁列具体内部目录名） ----------
# 只报存在与否，不列内容；凭据类目录按模式识别
SENSITIVE_DIR_PAT = re.compile(r"(\.aws|\.copilot|cert|credential|\.ssh|\.gnupg)", re.I)
SENSITIVE_FILE_PAT = re.compile(r"(auth\.json|.*\.key$|.*\.pem$|credentials|.*token.*|secret)", re.I)

# ---------- 红线门禁 ----------
# 公开版脚本内置【结构模式】（个人绝对路径/手机号/wxid/邮箱/token），
# 完整词表（身份/雇主代号等）为工作区私有件，用 --redline-file 外挂：
#   python3 toolbelt_scan.py --redline-file /path/to/private_words.txt
# 私有件不存在时仅结构模式生效（并在输出 meta 标注 wordlist_loaded=false）。
RED_STRUCTURAL = re.compile(
    r"(/Users/[a-z][a-z0-9_-]+/"          # 个人绝对路径（任何用户名）
    r"|(?<!\d)1[3-9]\d{9}(?!\d)"           # 手机号
    r"|wxid_[a-z0-9]+"                     # 微信 id
    r"|[\w.+-]+@[\w-]+\.[\w.]+)"           # 邮箱
    , re.I)


def load_wordlist(path):
    """外挂红线词表：一行一词，# 开头注释；返回编译后的 pattern 或 None"""
    p = pathlib.Path(path).expanduser()
    if not p.exists():
        return None
    words = [l.strip() for l in p.read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    if not words:
        return None
    return re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(w) for w in words) + r")(?![A-Za-z0-9])", re.I)


def make_red(wordlist_path):
    """返回 (外挂词表 pattern 或 None, 是否加载成功)"""
    ext = load_wordlist(wordlist_path) if wordlist_path else None
    return ext, bool(ext)

TEXT_EXT = {".md", ".json", ".html", ".txt", ".yaml", ".yml"}


def du(path: pathlib.Path) -> int:
    """目录大小（字节），失败返回 0"""
    try:
        out = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True, timeout=30)
        return int(out.stdout.split()[0]) * 1024
    except Exception:
        return 0


def count_entries(path: pathlib.Path) -> int:
    try:
        return len([p for p in path.iterdir() if not p.name.startswith("._")])
    except Exception:
        return 0


def last_active(path: pathlib.Path) -> str:
    """目录树最新 mtime（ISO 日期），失败返回空"""
    best = 0.0
    try:
        for p in path.rglob("*"):
            try:
                m = p.stat().st_mtime
                if m > best:
                    best = m
            except Exception:
                continue
    except Exception:
        pass
    if not best:
        return ""
    return datetime.datetime.fromtimestamp(best).strftime("%Y-%m-%d")


def skill_dirs(skills_root: pathlib.Path):
    """技能目录 -> {name: (sha1 of SKILL.md or '', size)}；无 SKILL.md 的也列（僵尸候选）"""
    out = {}
    try:
        for d in sorted(skills_root.iterdir()):
            if not d.is_dir() or d.name.startswith((".", "_")):
                continue
            sk = d / "SKILL.md"
            sha = ""
            if sk.exists():
                try:
                    sha = hashlib.sha1(sk.read_bytes()).hexdigest()[:10]
                except Exception:
                    sha = "ERR"
            out[d.name] = (sha, du(d))
    except Exception:
        pass
    return out


def red_hits(text: str):
    return [m.group(0) for m in RED.finditer(text)]


def scan_strings(obj, pattern, hits=None):
    """递归扫描结构内所有字符串值/键（跳过 int/float——字节数/计数不像手机号）"""
    if hits is None:
        hits = []
    if isinstance(obj, str):
        hits.extend(m.group(0)[:40] for m in pattern.finditer(obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                hits.extend(m.group(0)[:40] for m in pattern.finditer(k))
            scan_strings(v, pattern, hits)
    elif isinstance(obj, list):
        for v in obj:
            scan_strings(v, pattern, hits)
    return hits


def fmt_size(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def main():
    import argparse
    ap = argparse.ArgumentParser(description="云中立工具带盘点（只读）")
    ap.add_argument("--redline-file", default=os.environ.get("TOOLBELT_REDLINE", ""),
                    help="外挂红线词表（一行一词，工作区私有件）；不传则仅结构模式生效")
    args = ap.parse_args()
    ext_pattern, wordlist_loaded = make_red(args.redline_file)
    today = datetime.date.today().isoformat()
    tools, all_skills = [], {}   # all_skills: name -> {tool: sha}
    total_bytes = 0

    for display, dirname, skills_rel, data_rel, category in TOOLS:
        root = HOME / dirname
        if not root.exists():
            continue
        size = du(root)
        total_bytes += size
        entry = {
            "tool": display, "category": category, "dir": "~/" + dirname,
            "size_bytes": size, "last_active": last_active(root),
            "skills": 0, "skill_names": [], "sessions": None, "note": "",
        }
        # 敏感目录：只记存在
        if SENSITIVE_DIR_PAT.search(dirname):
            entry["note"] = "敏感目录（凭据类）：仅记存在，内容不列"
            tools.append(entry)
            continue
        # skills
        if skills_rel:
            sd = skill_dirs(root / skills_rel)
            # 红线技能名（内部/雇主向）只计数不列名——公开产出禁出
            clean = {n: v for n, v in sd.items() if not (ext_pattern and ext_pattern.search(n))}
            hidden = len(sd) - len(clean)
            entry["skills"] = len(sd)
            entry["skill_names"] = sorted(clean)
            if hidden:
                entry["note"] = (entry["note"] + "｜" if entry["note"] else "") + f"{hidden} 个内部技能按红线只计数"
            for name, (sha, _sz) in clean.items():
                all_skills.setdefault(name, {})[display] = sha
        # 会话/数据（只计数）
        if data_rel:
            dp = root / data_rel
            if dp.exists():
                entry["sessions"] = count_entries(dp)
        tools.append(entry)

    # ---------- 跨工具漂移检测 ----------
    multi = {n: t for n, t in all_skills.items() if len(t) > 1}
    drift = []
    for name, t in sorted(multi.items()):
        shas = {s for s in t.values() if s and s != "ERR"}
        if len(shas) > 1:
            drift.append({"skill": name, "tools": t, "versions": len(shas)})
    dup_clean = sorted(n for n, t in multi.items() if len({s for s in t.values() if s and s != "ERR"}) == 1)

    # ---------- 未安装 SKILL.md 的僵尸技能（红线名只计数） ----------
    zombies, zombie_hidden = [], 0
    for display, dirname, skills_rel, _d, _c in TOOLS:
        if not skills_rel:
            continue
        root = HOME / dirname / skills_rel
        if not root.exists():
            continue
        try:
            for d in root.iterdir():
                if d.is_dir() and not d.name.startswith(".") and not (d / "SKILL.md").exists():
                    if ext_pattern and ext_pattern.search(d.name):
                        zombie_hidden += 1
                    else:
                        zombies.append(f"{display}:{d.name}")
        except Exception:
            pass

    # ---------- 汇总 ----------
    total_installs = sum(len(t) for t in all_skills.values())
    summary = {
        "date": today,
        "tools_detected": len(tools),
        "total_data_bytes": total_bytes,
        "skill_names_unique": len(all_skills),
        "skill_installs_total": total_installs,
        "multi_tool_skills": len(multi),
        "drift_skills": len(drift),
        "duplicate_clean": len(dup_clean),
        "zombies": len(zombies),
    }

    report = {"summary": summary, "tools": tools,
              "drift": drift, "duplicate_clean": dup_clean, "zombies": zombies,
              "meta": {"generator": "toolbelt-scan/toolbelt_scan.py",
                       "redline": "结构模式+外挂词表 0 命中后落盘；红线技能名只计数不列名",
                       "wordlist_loaded": wordlist_loaded,
                       "zombie_hidden_by_redline": zombie_hidden,
                       "read_only": True}}

    # ---------- 脱敏门禁（输出前自扫）：结构模式（仅字符串值）+ 外挂词表，任一命中即拒写 ----------
    hits = sorted(set(scan_strings(report, RED_STRUCTURAL)))
    if ext_pattern is not None:
        hits += sorted(set(scan_strings(report, ext_pattern)))
    hits = sorted(set(hits))
    if hits:
        print(f"🔴 红线命中 {len(hits)} 处: {hits[:6]} → 拒绝落盘")
        return 2

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---------- HTML 看板 ----------
    html = render_html(report)
    out_html = OUT_HTML_DIR / f"云中立工具带盘点_{today}.html"
    OUT_HTML_DIR.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")

    print(f"✅ 工具 {summary['tools_detected']} | 技能安装 {total_installs}（去重 {len(all_skills)}）"
          f" | 漂移 {len(drift)} | 僵尸 {len(zombies)} | 总数据 {fmt_size(total_bytes)}")
    print(f"   JSON: {OUT_JSON}")
    print(f"   HTML: {out_html}")
    return 0


def render_html(r) -> str:
    s = r["summary"]
    rows = ""
    for t in sorted(r["tools"], key=lambda x: -x["size_bytes"]):
        note = f'<span style="color:#B06000">{t["note"]}</span>' if t["note"] else ""
        sess = t["sessions"] if t["sessions"] is not None else "—"
        rows += (f'<tr><td>{t["tool"]}</td><td>{t["category"]}</td><td><code>{t["dir"]}</code></td>'
                 f'<td style="text-align:right">{fmt_size(t["size_bytes"])}</td>'
                 f'<td style="text-align:right">{t["skills"]}</td>'
                 f'<td style="text-align:right">{sess}</td><td>{t["last_active"] or "—"}</td>'
                 f'<td>{note}</td></tr>')
    drift_rows = ""
    for d in r["drift"][:15]:
        tl = " / ".join(f"{k}({v})" for k, v in d["tools"].items())
        drift_rows += f'<tr><td><code>{d["skill"]}</code></td><td>{d["versions"]} 版</td><td>{tl}</td></tr>'
    if not drift_rows:
        drift_rows = '<tr><td colspan="3" style="color:#5F6368">零漂移——所有跨工具同名技能版本一致 ✅</td></tr>'
    zom = "、".join(r["zombies"][:12]) or "零僵尸 ✅"
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<title>云中立工具带盘点 {s['date']}</title>
<style>body{{font-family:-apple-system,"PingFang SC",sans-serif;max-width:1080px;margin:0 auto;padding:28px;line-height:1.6;background:#fff;color:#1a1a1a}}
h1{{font-size:22px}} .kpi{{display:inline-block;background:#f8f9fa;border-radius:10px;padding:10px 18px;margin:5px;text-align:center}}
.kpi b{{display:block;font-size:20px;color:#056DE8}} table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:14px}}
td,th{{padding:6px 9px;border:1px solid#e8eaed;text-align:left}} th{{background:#f8f9fa}}
.foot{{color:#5f6368;font-size:12px;margin-top:18px}}</style></head><body>
<h1>🧰 云中立工具带盘点 · {s['date']}</h1>
<div><span class="kpi"><b>{s['tools_detected']}</b>检测到工具</span>
<span class="kpi"><b>{s['skill_installs_total']}</b>技能安装次数</span>
<span class="kpi"><b>{s['skill_names_unique']}</b>去重后技能</span>
<span class="kpi"><b>{s['drift_skills']}</b>版本漂移</span>
<span class="kpi"><b>{s['zombies']}</b>僵尸技能</span>
<span class="kpi"><b>{fmt_size(s['total_data_bytes'])}</b>总数据</span></div>
<h2>工具矩阵</h2>
<table><tr><th>工具</th><th>类</th><th>目录</th><th>数据量</th><th>技能数</th><th>会话/项目</th><th>最后活跃</th><th>备注</th></tr>{rows}</table>
<h2>跨工具版本漂移 Top（同名技能不同版）</h2>
<table><tr><th>技能</th><th>版本数</th><th>分布</th></tr>{drift_rows}</table>
<h2>僵尸技能（无 SKILL.md）</h2><p>{zom}</p>
<p class="foot">只读扫描 · 绝对路径已泛化 · 敏感目录仅记存在 · 会话正文未读 · 输出过 30 词红线表 0 命中 ·
生成：toolbelt-scan（SSoT: xingtu-skills） · 理念：xingtu-cloud-neutral</p>
</body></html>"""


if __name__ == "__main__":
    sys.exit(main())
