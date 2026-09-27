#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xingtu-role-audit — AI 头衔定位自查（三数检查）v1.0
把「自治度 / 护栏密度 / 边际收益」三个数量出来，输出可视化 HTML 报告 + 前进方向。
口径诚实标注：能自动测的自动测，测不到的引导自评，绝不给假数字。

用法:
  python3 audit.py --dir ~/projects/<COMPANY_GITLAB>
  python3 audit.py --dir . --sessions-dir ~/.claude/projects --out ./audit_report.html
"""
import os, sys, json, glob, html, argparse, datetime, re

TOKEN_PER_CHAR = 1.8      # 估算口径：字符数 / 1.8 ≈ token（中英混，保守）
BUDGET_TOKEN = 50000      # 1M 上下文窗口「5% 规则」预算 ≈ 50K token
BRAND = "#056DE8"; ACC = "#FF6B35"; GREEN = "#0C8A3C"; ORANGE = "#E0501E"

def est_tokens(chars):
    return int(chars / TOKEN_PER_CHAR)

def scan_harness(proj):
    """护栏密度：统计 .claude/.workbuddy 下常驻注入 md 的总字符/估 token"""
def scan_harness(proj):
    """护栏密度：只算「常驻注入」——根 CLAUDE.md/AGENTS.md + rules*/ 目录，
    排除 specs/incidents/memory 等按需加载文档（它们不常驻上下文）。"""
    files, total_chars = {}, 0
    for base_d in (".claude", ".workbuddy"):
        d = os.path.join(proj, base_d)
        if not os.path.isdir(d): continue
        # 根级常驻 md（CLAUDE.md / AGENTS.md / 说明）
        for n in os.listdir(d):
            if n.lower() in ("claude.md", "agents.md") and n.endswith(".md"):
                fp = os.path.join(d, n)
                try: txt = open(fp, encoding="utf-8", errors="ignore").read()
                except Exception: continue
                files[os.path.relpath(fp, proj)] = len(txt); total_chars += len(txt)
        # rules 类目录（常驻注入主力）
        for sub in ("rules", "rules-scoped"):
            sd = os.path.join(d, sub)
            if not os.path.isdir(sd): continue
            for root, _, names in os.walk(sd):
                for n in names:
                    if not n.endswith(".md"): continue
                    fp = os.path.join(root, n)
                    try: txt = open(fp, encoding="utf-8", errors="ignore").read()
                    except Exception: continue
                    files[os.path.relpath(fp, proj)] = len(txt); total_chars += len(txt)
    return files, total_chars, est_tokens(total_chars)

def newest_session(roots):
    best = None
    for r in roots:
        if not r or not os.path.isdir(r): continue
        for fp in glob.glob(os.path.join(r, "**", "*.jsonl"), recursive=True):
            try: m = os.path.getmtime(fp)
            except Exception: continue
            if best is None or m > best[1]: best = (fp, m)
    return best[0] if best else None

def find_session_for(proj, roots):
    """优先取与项目同名的会话（~/.claude/projects/<项目名路径>/），没有则全局最新"""
    base = os.path.basename(os.path.abspath(proj).rstrip("/"))
    cands = []
    for r in roots:
        if not r or not os.path.isdir(r): continue
        for fp in glob.glob(os.path.join(r, "**", "*.jsonl"), recursive=True):
            if base and base in fp: cands.append(fp)
    if cands:
        return max(cands, key=os.path.getmtime)
    return newest_session(roots)

def analyze_session(fp, max_lines=4000):
    """自治度：采样最近会话，统计 tool_use 中需人工文本介入的比例（估算口径）"""
    if not fp: return None
    tool_uses = tool_results = human_texts = 0
    try:
        fh = open(fp, encoding="utf-8", errors="ignore")
    except Exception:
        return None
    with fh:
        for i, line in enumerate(fh):
            if i >= max_lines: break
            try: obj = json.loads(line)
            except Exception: continue
            msg = obj.get("message") or {}
            content = msg.get("content")
            role = msg.get("role")
            if isinstance(content, str):
                if role == "user": human_texts += 1
                continue
            if not isinstance(content, list): continue
            kinds = [c.get("type") for c in content if isinstance(c, dict)]
            if role == "assistant" and "tool_use" in kinds: tool_uses += 1
            elif role == "user":
                if "tool_result" in kinds: tool_results += 1
                elif any(k in ("text", "input_text", "prompt") for k in kinds): human_texts += 1
    if tool_uses == 0 and human_texts == 0: return None
    ratio = human_texts / max(tool_uses + human_texts, 1)   # 介入率
    return {"tool_uses": tool_uses, "tool_results": tool_results,
            "human_texts": human_texts, "ratio": ratio}

def read_marginal(proj):
    """边际收益：查找减法实验前后对照（harness-audit.json / audit_before.json）"""
    for pat in ("harness-audit.json", "audit_before.json", "data/harness_audit.json"):
        fp = os.path.join(proj, pat)
        if os.path.isfile(fp):
            try: return json.load(open(fp, encoding="utf-8"))
            except Exception: pass
    return None

def advice(g_tok, ratio, marginal):
    """前进方向：三数 → 行动清单"""
    items = []
    # 护栏密度
    if g_tok > BUDGET_TOKEN:
        items.append(("护栏密度", ORANGE, f"超预算（≈{g_tok//1000}K token > 50K）：做减法——逐个 hook/rules 审计，砍到最小有效集"))
    else:
        items.append(("护栏密度", GREEN, f"在预算内（≈{g_tok//1000}K token ≤ 50K）：保持，别急着加料"))
    # 自治度
    if ratio is None:
        items.append(("自治度", "#8a94a6", "未自动测出（会话不可读）：翻最近一次 Agent 会话，数‘确认类’交互占多少"))
    elif ratio < 0.25:
        items.append(("自治度", ACC, f"介入率 {ratio:.0%}——自治放得开，盯紧护栏别裸奔；验证闭环写进脚本"))
    elif ratio > 0.60:
        items.append(("自治度", ORANGE, f"介入率 {ratio:.0%}——点头太多：能 Bash 就不 Agent，任务整包下发，少拆碎"))
    else:
        items.append(("自治度", GREEN, f"介入率 {ratio:.0%}——适中，继续，重点盯护栏边际"))
    # 边际收益
    if marginal and "after" in marginal and "before" in marginal:
        try:
            delta = float(marginal["after"]) - float(marginal["before"])
            if delta <= 0:
                items.append(("边际收益", ORANGE, "减法后无正收益甚至变差：该护栏可以砍掉或重做"))
            else:
                items.append(("边际收益", GREEN, f"减法后正收益（{marginal['after']} vs {marginal['before']}）：留，记录进护栏清单"))
        except Exception:
            items.append(("边际收益", "#8a94a6", "读到实验记录但格式不明，人工核对"))
    else:
        items.append(("边际收益", "#8a94a6", "未做减法实验：挑一个堆最久的护栏，量纲对齐测 before/after，再让审计照一遍"))
    return items

def quadrant(g_tok, ratio):
    """两轴定位：自治度(介入率反比) × 护栏密度 → 头衔区"""
    if ratio is None: return "待测", "量出三个数才能定位"
    hi_guard = g_tok > 30000
    hi_auto = ratio < 0.35
    if hi_auto and hi_guard: return "Agentic Engineer · 目标区", "高自治 + 高护栏，理想位，保持验证纪律"
    if hi_auto and not hi_guard: return "Vibe Coder · 危险区", "自治放开了但护栏没跟上——先补规则/hooks，再放大自治"
    if not hi_auto and hi_guard: return "Harness Engineer · 护栏过剩区", "护栏堆得比自治快——做减法，验证每个护栏的边际"
    return "AI Native Engineer · 过渡区", "中-中配置：先定你要往目标区（提护栏）还是先放自治"

def render(items, quad, data, proj, session_name, out):
    rows = "".join(f"<tr><td style='white-space:nowrap'><b style='color:{c}'>{t}</b></td>"
                   f"<td>{html.escape(d)}</td></tr>" for t, c, d in items)
    status = html.escape(quad[0]); desc = html.escape(quad[1])
    g_k = data["guard_k"]; ratio_txt = data["ratio_txt"]; mg_txt = data["mg_txt"]
    ratio_pct = int(data["ratio_pct"])
    ratio_y = 240 - min(int(ratio_pct * 1.7), 170) if data["ratio_pct"] is not None else 240
    gx = 130 + min(int(g_k / BUDGET_TOKEN * 255), 255)
    doc = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>AI 头衔定位自查报告 · {html.escape(proj)}</title><style>
body{{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:#f4f7fb;color:#1f2329;margin:0;padding:28px 16px}}
.card{{max-width:760px;margin:0 auto;background:#fff;border:1px solid #e4e9f0;border-radius:16px;padding:30px 34px}}
h1{{font-size:22px;margin:0 0 4px}} .sub{{color:#8a94a6;font-size:13px;margin-bottom:16px}}
.bar{{height:10px;background:#eef2f8;border-radius:6px;overflow:hidden;margin:6px 0 18px}}
.bar i{{display:block;height:100%;background:{BRAND};border-radius:6px;width:0}}
table{{width:100%;border-collapse:collapse;font-size:14px}} td{{padding:9px 10px;border-bottom:1px solid #eef2f8;vertical-align:top}}
.q{{background:#fafcff;border:1px solid #e4e9f0;border-radius:12px;padding:14px 16px;margin:16px 0;font-size:14px}}
.q b{{font-size:16px}} .tag{{font-size:11px;color:#8a94a6}} .foot{{font-size:12px;color:#8a94a6;text-align:center;margin-top:18px}}
.cta{{background:linear-gradient(120deg,#eaf2ff,#f4f8ff);border:1px solid #d6e4ff;border-radius:12px;padding:14px 18px;margin:18px 0;font-size:13.5px;color:#23467e;line-height:2}}
.cta b{{color:#056DE8}}
svg{{width:100%;height:auto}}</style></head><body><div class="card">
<h1>AI 头衔定位自查报告</h1><div class="sub">{html.escape(proj)} · 生成于 {datetime.datetime.now():%Y-%m-%d %H:%M} · 行途 xingtu-role-audit v1.0</div>
<div class="q"><b>定位：{status}</b><br><span class="tag">两轴坐标</span><br>{desc}
<svg viewBox="0 0 680 300" xmlns="http://www.w3.org/2000/svg">
<rect x="360" y="40" width="260" height="90" fill="#E3F5EA" rx="8"/><text x="370" y="62" font-size="12" fill="#0C8A3C">目标区</text>
<rect x="360" y="130" width="260" height="100" fill="#FBEDE4" rx="8"/><text x="370" y="150" font-size="12" fill="#E0501E">危险区</text>
<line x1="120" y1="230" x2="640" y2="230" stroke="#c9d4e2" stroke-dasharray="4 5"/><line x1="360" y1="40" x2="360" y2="230" stroke="#c9d4e2" stroke-dasharray="4 5"/>
<line x1="120" y1="230" x2="648" y2="230" stroke="#98a3b3" stroke-width="1.6"/><line x1="120" y1="230" x2="120" y2="34" stroke="#98a3b3" stroke-width="1.6"/>
<circle cx="{gx}" cy="{ratio_y}" r="10" fill="{BRAND}" stroke="#fff" stroke-width="2.5"/>
<text x="360" y="262" font-size="12" fill="#3f4756" text-anchor="middle">护栏密度（token 预算占比）→</text>
<text x="28" y="132" font-size="12" fill="#3f4756" transform="rotate(-90 28 132)">自治度（1−介入率）→</text>
</svg></div>
<h3 style="margin:6px 0 2px;font-size:15px">三个数</h3>
<table><tr><td style="white-space:nowrap"><b>护栏密度</b></td><td>{g_k}K token（估算口径：字符/1.8，预算 50K）</td></tr>
<tr><td><b>自治度</b></td><td>{ratio_txt}</td></tr>
<tr><td><b>边际收益</b></td><td>{mg_txt}</td></tr></table>
<h3 style="margin:16px 0 6px;font-size:15px">前进方向</h3>
<table>{rows}</table>
<div class="sub" style="margin-top:14px">会话样本：{html.escape(session_name or '未找到')}</div>
<div class="cta"><b>报告只是起点。</b>三个数量出来，你知道自己在哪一档了。但「下一步先动哪个数、怎么改、你的项目适合什么路线」——每个项目不一样，写不成通用答案。<br>想认真推进：加微信 <b>xingtu_note</b>（备注「定位」）约 30 分钟咨询，我会提前读你的仓库和会话，聊完给你一页行动计划（按次收费）。不想付费也没关系——自查卡和公众号原文，够你先动手了。</div>
<div class="foot">by 行途 · 公众号回复「角色」领自查卡 · 数据为估算口径，与实测冲突以实测为准</div>
</div></body></html>"""
    open(out, "w", encoding="utf-8").write(doc)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".", help="项目目录（扫 .claude/.workbuddy 常驻 md）")
    ap.add_argument("--sessions-dir", default=os.path.expanduser("~/.claude/projects"), help="Claude Code 会话根目录")
    ap.add_argument("--out", default=None, help="报告输出路径（默认 项目目录/ai_role_audit_report.html）")
    a = ap.parse_args()
    proj = os.path.abspath(a.dir)
    files, chars, g_tok = scan_harness(proj)
    sess = find_session_for(proj, [a.sessions_dir, os.path.join(proj, ".claude")])
    an = analyze_session(sess)
    ratio = an["ratio"] if an else None
    ratio_pct = int(ratio * 100) if ratio is not None else None
    mg = read_marginal(proj)
    mg_txt = "无实验记录（减法是必做项）"
    if mg and "after" in mg and "before" in mg:
        mg_txt = f"before {mg['before']} → after {mg['after']}"
    quad = quadrant(g_tok, ratio)
    items = advice(g_tok, ratio, mg)
    out = a.out or os.path.join(proj, "ai_role_audit_report.html")
    data = {"guard_k": round(g_tok / 1000, 1),
            "ratio_pct": ratio_pct,
            "ratio_txt": (f"介入率 {ratio_pct}%（样本 {an['human_texts']} 人工输入 / {an['tool_uses']} 次工具调用）" if an else "会话不可读，未自动测出"),
            "mg_txt": mg_txt}
    render(items, quad, data, proj, sess, out)
    print(f"[xingtu-role-audit] 护栏≈{data['guard_k']}K token | 自治度: {data['ratio_txt']} | 定位: {quad[0]}")
    print(f"报告: {out}")

if __name__ == "__main__":
    main()
