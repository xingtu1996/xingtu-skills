#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZCode 本地 session 抽取器（行途内容资产管线 · 镜像 豆包归档范式）

只读源：
  ~/.zcode/cli/db/db.sqlite        (CLI 侧：18 session / 1022 message / 3932 part)
  ~/.zcode/v2/tasks-index.sqlite  (ADE 图形端：6 task)

落点：
  ~/xingtu/data/zcode_sessions/
    index.json           总览 + 每 session 元数据
    ade_tasks.json       ADE 6 个任务元数据
    sessions/<id>.jsonl  逐行 {role,time,text}
    sessions/<id>.md     可读转写稿
    zcode_sessions_dashboard.html  清单看板（汇报用）

数据主权：会话是个人资产，必须落本地磁盘（2026-09-10 红线）。
脱敏：本脚本只抽取落盘，不做任何发布；若要进素材库/公开内容，
      必须先过 tools/privacy_scan.py（SAF-004/006：禁公司代码/真名/雇主）。
"""
import sqlite3, os, json, datetime

SRC_CLI = os.path.expanduser("~/.zcode/cli/db/db.sqlite")
SRC_ADE = os.path.expanduser("~/.zcode/v2/tasks-index.sqlite")
OUT = os.path.expanduser("~/xingtu/data/zcode_sessions")


def ro(p):
    return sqlite3.connect("file:%s?mode=ro" % p, uri=True)


def iso(ms):
    if not ms:
        return None
    return datetime.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def extract_cli():
    con = ro(SRC_CLI)
    cur = con.cursor()
    cur.execute(
        "SELECT id, title, directory, path, time_created, time_updated FROM session ORDER BY time_created"
    )
    rows = cur.fetchall()
    manifest = []
    for sid, title, directory, path, tc, tu in rows:
        # 用户原话（主来源：session_input 入队且已采纳）
        cur.execute(
            "SELECT time_created, payload FROM session_input WHERE session_id=? AND kind='sendText' ORDER BY time_created",
            (sid,),
        )
        user_seen = set()
        thread = []
        for t, pl in cur.fetchall():
            try:
                pj = json.loads(pl)
                txt = pj.get("text", "")
            except Exception:
                txt = str(pl)
            txt = (txt or "").strip()
            if txt:
                thread.append((t, "user", txt))
                user_seen.add(txt)
        # 兜底：message 表里 role=user 的文本 part（防止 session_input 漏存）
        cur.execute(
            """SELECT m.time_created, p.data FROM message m JOIN part p ON p.message_id=m.id
               WHERE m.session_id=? AND json_extract(m.data,'$.role')='user' ORDER BY m.time_created, p.sequence""",
            (sid,),
        )
        for t, pd in cur.fetchall():
            try:
                d = json.loads(pd)
                if d.get("type") == "text":
                    txt = (d.get("text", "") or "").strip()
                    if txt and txt not in user_seen:
                        thread.append((t, "user", txt))
                        user_seen.add(txt)
            except Exception:
                pass
        # 助手回复（只取 type=text 正文，跳过 reasoning / model_change）
        cur.execute(
            """SELECT m.time_created, p.data FROM message m JOIN part p ON p.message_id=m.id
               WHERE m.session_id=? AND json_extract(m.data,'$.role')='assistant' ORDER BY m.time_created, p.sequence""",
            (sid,),
        )
        asst = []
        for t, pd in cur.fetchall():
            try:
                d = json.loads(pd)
                if d.get("type") == "text":
                    asst.append((t, "assistant", d.get("text", "")))
            except Exception:
                pass
        thread += asst
        thread.sort(key=lambda x: x[0] or 0)

        jl_path = os.path.join(OUT, "sessions", "%s.jsonl" % sid)
        with open(jl_path, "w", encoding="utf-8") as f:
            for t, role, txt in thread:
                f.write(json.dumps({"role": role, "time": iso(t), "text": txt}, ensure_ascii=False) + "\n")

        md_path = os.path.join(OUT, "sessions", "%s.md" % sid)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# %s\n\n" % (title or sid))
            f.write("- session_id: `%s`\n" % sid)
            f.write("- cwd: `%s`\n" % (directory or path or ""))
            f.write("- 创建: %s ｜ 更新: %s\n\n---\n\n" % (iso(tc), iso(tu)))
            for t, role, txt in thread:
                who = "**Boss**" if role == "user" else "**ZCode(GLM)**"
                f.write("### %s · %s\n\n%s\n\n" % (who, iso(t), txt))

        total_chars = sum(len(x[2]) for x in thread)
        manifest.append(
            {
                "id": sid,
                "title": title or sid,
                "source": "cli",
                "cwd": directory or path,
                "created": iso(tc),
                "updated": iso(tu),
                "user_turns": len([x for x in thread if x[1] == "user"]),
                "assistant_turns": len(asst),
                "total_chars": total_chars,
                "jsonl": os.path.relpath(jl_path, OUT),
                "md": os.path.relpath(md_path, OUT),
            }
        )
    con.close()
    return manifest


def extract_ade():
    con = ro(SRC_ADE)
    cur = con.cursor()
    cur.execute(
        "SELECT workspace_path, title, task_status, model, mode, created_at, updated_at, meta_json FROM tasks"
    )
    tasks = []
    for wp, title, status, model, mode, ca, ua, meta in cur.fetchall():
        tasks.append(
            {
                "workspace_path": wp,
                "title": title,
                "status": status,
                "model": model,
                "mode": mode,
                "created": iso(ca),
                "updated": iso(ua),
                "meta": (json.loads(meta) if meta else None),
            }
        )
    con.close()
    return tasks


def build_dashboard(index):
    cli = index["cli_sessions"]
    ade = index["ade_tasks"]
    total_chars = sum(s["total_chars"] for s in cli)
    cards = []
    for s in cli:
        cards.append(
            """<div class="card">
  <div class="ctitle">%s</div>
  <div class="meta">%s ｜ 用户 %d · 助手 %d ｜ %s 字</div>
  <div class="meta">cwd: <code>%s</code></div>
  <a class="link" href="%s">转写稿 MD</a>
</div>"""
            % (
                (s["title"] or "").replace("<", "&lt;"),
                s["created"],
                s["user_turns"],
                s["assistant_turns"],
                format(s["total_chars"], ","),
                (s["cwd"] or "").replace("<", "&lt;"),
                s["md"],
            )
        )
    ade_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
        % (
            (t["title"] or "").replace("<", "&lt;"),
            t["created"],
            t["status"],
            (t["model"] or "").replace("<", "&lt;"),
        )
        for t in ade
    )
    html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ZCode 本地 Session 清单</title>
<style>
:root{--blue:#056DE8;--ink:#1a1a1a;--mut:#666;--line:#e5e5e5;--bg:#fff;}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;color:var(--ink);background:var(--bg);padding:32px;}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--mut);font-size:13px;margin-bottom:24px}
.stat{display:flex;gap:16px;margin-bottom:28px;flex-wrap:wrap}
.stat .box{border:1px solid var(--line);border-radius:10px;padding:14px 20px;min-width:120px}
.stat .n{font-size:24px;font-weight:700;color:var(--blue)}
.stat .l{font-size:12px;color:var(--mut);margin-top:2px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;margin-bottom:32px}
.card{border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.ctitle{font-weight:600;font-size:14px;margin-bottom:6px;line-height:1.4}
.meta{font-size:12px;color:var(--mut);margin:2px 0}
code{background:#f4f6f8;padding:1px 5px;border-radius:4px;font-size:11px}
.link{display:inline-block;margin-top:8px;color:var(--blue);font-size:12px;text-decoration:none}
.link:hover{text-decoration:underline}
table{border-collapse:collapse;width:100%%;font-size:13px}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left}
th{background:#f4f6f8;font-weight:600}
.warn{background:#fff7ed;border:1px solid #ffd8a8;color:#9a5b00;padding:10px 14px;border-radius:8px;font-size:12px;margin-bottom:24px}
</style></head><body>
<h1>ZCode 本地 Session 清单</h1>
<div class="sub">生成时间 %s ｜ 源：<code>%s</code> + <code>%s</code></div>
<div class="warn">⚠️ 本清单为本地私有资产，含工作区路径与内部任务。若要蒸馏进素材库或公开内容，必须先过 <code>tools/privacy_scan.py</code>（SAF-004/006：禁公司代码 / 真名 / 雇主）。</div>
<div class="stat">
  <div class="box"><div class="n">%d</div><div class="l">CLI 会话</div></div>
  <div class="box"><div class="n">%d</div><div class="l">ADE 任务</div></div>
  <div class="box"><div class="n">%s</div><div class="l">正文总字数</div></div>
</div>
<h2 style="font-size:16px">CLI 会话（含完整转写）</h2>
<div class="grid">%s</div>
<h2 style="font-size:16px">ADE 图形端任务</h2>
<table><thead><tr><th>标题</th><th>创建</th><th>状态</th><th>模型</th></tr></thead><tbody>%s</tbody></table>
</body></html>""" % (
        index["generated_at"],
        SRC_CLI,
        SRC_ADE,
        len(cli),
        len(ade),
        format(total_chars, ","),
        "\n".join(cards),
        ade_rows,
    )
    with open(os.path.join(OUT, "zcode_sessions_dashboard.html"), "w", encoding="utf-8") as f:
        f.write(html)


def main():
    os.makedirs(os.path.join(OUT, "sessions"), exist_ok=True)
    cli = extract_cli()
    ade = extract_ade()
    index = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sources": {"cli_db": SRC_CLI, "ade_db": SRC_ADE},
        "cli_session_count": len(cli),
        "ade_task_count": len(ade),
        "cli_sessions": cli,
        "ade_tasks": ade,
    }
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT, "ade_tasks.json"), "w", encoding="utf-8") as f:
        json.dump(ade, f, ensure_ascii=False, indent=2)
    build_dashboard(index)
    print("✅ 抽取完成")
    print("CLI 会话: %d ｜ ADE 任务: %d" % (len(cli), len(ade)))
    for s in cli:
        print("  • %s | %s | 用户%d/助手%d | %s 字" % (
            (s["title"][:38]), s["created"], s["user_turns"], s["assistant_turns"],
            format(s["total_chars"], ",")))
    print("\n落点: %s" % OUT)


if __name__ == "__main__":
    main()
