#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wechat_channel.py — 微信通道统一 CLI（行途 · 跨 Agent 复用）

定位：给任意 AI Agent（Claude / WorkBuddy / Codex / 豆包）一个统一的本地微信通道。
能力：解密 → 枚举会话 → 按联系人/群（wxid）读取导出 → 萃取原稿 → AI 蒸馏 → 元宝全文获取。

关键机制（微信 4.x，实测验证）：
  - 消息表名 = 'Msg_' + md5(wxid.encode()).hexdigest()
  - 会话清单 = message 库 Name2Id 表 user_name（参与过的会话 id）
  - 读取逻辑复用 tools/wechat_chat_analyzer/yuanbao_full_extract.py（zstd 解压 + appmsg XML 解析）
  - 联系人昵称映射：当前解密库无 contact.db（密钥未覆盖），名字仅作展示/提示，定位一律用 wxid

子命令：
  decrypt   重新解密最新微信库（复用密钥）
  list      枚举所有有消息的会话（wxid + 消息数 + 最近时间），附带可见名字提示
  search    按关键词/名字反查会话 wxid（跨所有消息表搜索，返回命中会话+样例）
  read      按 wxid 读取指定会话 → Markdown + CSV（支持条数/时间过滤）
  extract   萃取：按 wxid 导出完整原稿 → Markdown + CSV + JSON
  distill   AI 蒸馏：导出后走 wechat_summary.py --input 文件模式（主题/金句见 references/distill-standards.md）
  fetch     获取：元宝分享全文增量抓取 + 归档入库（水位线驱动）

用法示例：
  python wechat_channel.py list
  python wechat_channel.py search <COLLEAGUE> <PROJECT>          # 多关键词 OR 搜索，反查 wxid
  python wechat_channel.py search "AI Work" --top 5  # 搜群聊
  python wechat_channel.py read wxid_xxxx
  python wechat_channel.py extract custom_id_example1 -o ~/xingtu/outputs/wechat_channel
  python wechat_channel.py distill wxid_xxxx --model deepseek-v4-pro
  python wechat_channel.py fetch
  python wechat_channel.py decrypt
"""

import argparse
import csv
import glob
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# 路径常量（与 references/paths.md 保持一致）
# ---------------------------------------------------------------------------
ROOT = "${WORKSPACE}"
VENV_PY = "${HOME}/.workbuddy/binaries/python/envs/default/bin/python"
ANALYZER = os.path.join(ROOT, "tools/wechat_chat_analyzer/wechat_chat_analyzer.py")
SUMMARY = os.path.join(ROOT, "tools/wechat_chat_analyzer/wechat_summary.py")
PIPELINE = os.path.join(ROOT, "tools/wechat_chat_analyzer/run_pipeline.sh")
FULL_EXTRACT = os.path.join(ROOT, "tools/wechat_chat_analyzer/yuanbao_full_extract.py")
KEYS = os.path.join(ROOT, "data/wechat_decrypted/keys.json")
DECRYPT_DIR = os.path.join(ROOT, "data/wechat_decrypted_latest")
PRIVATE_DECRYPT_DIR = os.path.join(os.path.expanduser("~"), "PrivateData/wechat/wechat_decrypted_latest")
WECHAT_DB_DIR = "${HOME}/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/<YOUR_WECHAT_DB_DIR>/db_storage"
DEFAULT_OUT = os.path.join(ROOT, "outputs/wechat_channel")


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def resolve_decrypt_dir():
    """优先 xingtu 解密库；为空壳（无 message 子库）时回退 PrivateData 副本。"""
    if os.path.isdir(DECRYPT_DIR) and glob.glob(os.path.join(DECRYPT_DIR, "message", "message_*.db")):
        return DECRYPT_DIR
    if os.path.isdir(PRIVATE_DECRYPT_DIR) and glob.glob(os.path.join(PRIVATE_DECRYPT_DIR, "message", "message_*.db")):
        return PRIVATE_DECRYPT_DIR
    return DECRYPT_DIR


def _out_dir(base, session, tag):
    session_dir = "".join(c if c.isalnum() or c in "-_" else "_" for c in session)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    d = os.path.join(base, session_dir, f"{tag}_{ts}")
    os.makedirs(d, exist_ok=True)
    return d


def _msg_tables(dbdir):
    """返回 (db_path, table_name) 列表（跳过 fts/resource）。"""
    dbs = glob.glob(os.path.join(dbdir, "message_*.db")) + glob.glob(os.path.join(dbdir, "message", "message_*.db"))
    dbs = list(dict.fromkeys(dbs))
    out = []
    for db in dbs:
        if "fts" in db or "resource" in db:
            continue
        try:
            con = sqlite3.connect(db)
            tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            con.close()
        except Exception:
            continue
        for t in tables:
            if t.startswith("Msg_"):
                out.append((db, t))
    return out


def _collect_name2id(dbdir):
    """收集所有 message 库的 Name2Id.user_name，返回 hash2uid 映射。"""
    dbs = glob.glob(os.path.join(dbdir, "message_*.db")) + glob.glob(os.path.join(dbdir, "message", "message_*.db"))
    dbs = list(dict.fromkeys(dbs))
    uids = []
    for db in dbs:
        if "fts" in db or "resource" in db:
            continue
        try:
            con = sqlite3.connect(db)
            if "Name2Id" in [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
                uids += [r[0] for r in con.execute("SELECT user_name FROM Name2Id")]
            con.close()
        except Exception:
            continue
    uids = list(dict.fromkeys(uids))
    return {hashlib.md5(u.encode()).hexdigest(): u for u in uids}


_ZSTD = None
def _decompress_content(msg, comp, ctflag):
    """统一解压消息内容：WCDB_CT=4 时 compress_content 是 zstd；否则直接读 message_content。"""
    global _ZSTD
    if ctflag == 4:
        data = comp or msg
        if not data:
            return ""
        if isinstance(data, str):
            data = data.encode("latin-1")
        if _ZSTD is None:
            try:
                import zstandard
                _ZSTD = zstandard.ZstdDecompressor()
            except Exception:
                _ZSTD = False
        if _ZSTD is False:
            return ""
        try:
            return _ZSTD.decompress(data).decode("utf-8", errors="replace")
        except Exception:
            return ""
    if isinstance(msg, bytes):
        return msg.decode("utf-8", errors="replace")
    return msg or ""


def list_sessions(dbdir):
    """枚举有消息的会话：Name2Id.user_name → md5 → 消息表存在性 + 计数 + 最近时间。"""
    hash2uid = _collect_name2id(dbdir)

    by_hash = {}
    for db, t in _msg_tables(dbdir):
        try:
            con = sqlite3.connect(db)
            n, mx = con.execute(f'SELECT COUNT(*), MAX(create_time) FROM "{t}"').fetchone()
            con.close()
            # 同一会话可能分布在多个 message 库（如 message_0 与 message_5），须累加计数并取最大时间
            cur_cnt, cur_mx = by_hash.get(t[4:], (0, 0))
            by_hash[t[4:]] = (cur_cnt + (n or 0), max(cur_mx, mx or 0))
        except Exception:
            continue

    rows = []
    for h, uid in hash2uid.items():
        if h in by_hash:
            cnt, last_ts = by_hash[h]
            last = datetime.fromtimestamp(last_ts / 1000 if last_ts and last_ts > 1e12 else (last_ts or 0)).strftime(
                "%Y-%m-%d %H:%M") if last_ts else "-"
            rows.append((uid, cnt, last))
    rows.sort(key=lambda x: -x[1])
    return rows


def collect_visible_names(dbdir):
    """从 FTS 表尽力收集可显示的名字（群/联系人），供用户对照 wxid。"""
    names = []
    fts = glob.glob(os.path.join(dbdir, "contact", "contact_fts.db"))
    if not fts:
        return names
    try:
        con = sqlite3.connect(fts[0])
        for t, c in (("contact_fts_v5_content", "c0"), ("wa_contact_fts_v1_content", "c0")):
            try:
                for (v,) in con.execute(f"SELECT {c} FROM {t} LIMIT 2000"):
                    if v:
                        s = v.replace("\x08", "").strip()
                        if s:
                            names.append(s)
            except Exception:
                continue
        con.close()
    except Exception:
        pass
    return list(dict.fromkeys(names))


def read_session(wxid, dbdir, limit=None, since=None):
    """按 wxid 读取消息，复用 yuanbao_full_extract 的解析（zstd + appmsg XML + 去重）。返回结构化消息列表。"""
    sys.path.insert(0, os.path.dirname(FULL_EXTRACT))
    import yuanbao_full_extract as yf

    msgs = yf.extract(wxid, dbdir)
    if since:
        since_dt = datetime.strptime(since, "%Y-%m-%d")
        msgs = [m for m in msgs if m.get("time", "")[:10] >= since]
    if limit:
        msgs = msgs[-int(limit):]  # 取最近 N 条
    return msgs


def export_msgs(msgs, out_dir, name):
    """写 Markdown + CSV + JSON 三件套。返回主文件路径。"""
    md = os.path.join(out_dir, f"{name}_会话导出.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write(f"# 微信会话导出 · {name}\n总消息 {len(msgs)} 条\n\n")
        for m in msgs:
            tag = f"[{m['type_name']}]" if m["type_name"] != "text" else ""
            f.write(f"### {m['time']}{tag}\n{m['content']}\n\n")
    csvp = os.path.join(out_dir, f"{name}_会话导出.csv")
    with open(csvp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "type", "content"])
        for m in msgs:
            w.writerow([m["time"], m["type_name"], m["content"]])
    jsonp = os.path.join(out_dir, f"{name}_会话导出.json")
    json.dump(msgs, open(jsonp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return md, csvp, jsonp


# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------
def cmd_decrypt(args):
    if not os.path.isfile(KEYS):
        print(f"[!] 密钥缺失：{KEYS}（首次需 sudo 提 key，之后常驻）")
        return 2
    os.makedirs(DECRYPT_DIR, exist_ok=True)
    for f in os.listdir(DECRYPT_DIR):
        p = os.path.join(DECRYPT_DIR, f)
        if os.path.isdir(p):
            subprocess.run(["rm", "-rf", p])
        else:
            os.remove(p)
    code = (
        "import sys; sys.path.insert(0, %r); import decrypt; "
        "decrypt.decrypt_all(%r, %r, %r)"
        % (os.path.join(ROOT, "tools/wechatdecryption"), WECHAT_DB_DIR, KEYS, DECRYPT_DIR)
    )
    r = _run([VENV_PY, "-c", code])
    if r.returncode != 0:
        print("[!] 解密失败/跳过，使用已有解密库")
        print(r.stderr[-500:] if r.stderr else "")
        return 1
    print(f"✅ 解密完成 → {DECRYPT_DIR}")
    return 0


def cmd_list(args):
    dbdir = resolve_decrypt_dir()
    rows = list_sessions(dbdir)
    print(f"共 {len(rows)} 个有消息的会话（解密库：{dbdir}）\n")
    print(f"{'消息数':>8}  {'最近消息':<18}  wxid/会话ID")
    print("-" * 80)
    for uid, cnt, last in rows[: (args.top or 60)]:
        print(f"{cnt:>8}  {last:<18}  {uid}")
    names = collect_visible_names(dbdir)
    if names:
        print(f"\n可见名字（群/联系人，供对照，当前库无 wxid 映射）: {', '.join(names[:60])}")
    return 0


def cmd_search(args):
    """按关键词跨所有消息表搜索，反查命中的会话 wxid。多关键词 OR 逻辑。

    典型用途：用户只记得备注名/群名/某句话，不知道 wxid 时，用关键词定位会话。
    定位后用 read/extract/distill <wxid> 操作。
    """
    dbdir = resolve_decrypt_dir()
    keywords = args.keywords
    hash2uid = _collect_name2id(dbdir)

    hits = {}  # hash -> {"count": int, "samples": [(kw, text)], "last": int}
    for db, t in _msg_tables(dbdir):
        h = t[4:]
        try:
            con = sqlite3.connect(db)
            cur = con.execute(
                f'SELECT message_content, compress_content, WCDB_CT_message_content, create_time FROM "{t}"'
            )
            for msg, comp, ct, ts in cur:
                content = _decompress_content(msg, comp, ct)
                if not content:
                    continue
                matched = [k for k in keywords if k in content]
                if not matched:
                    continue
                rec = hits.setdefault(h, {"count": 0, "samples": [], "last": 0})
                rec["count"] += 1
                rec["last"] = max(rec["last"], ts or 0)
                if len(rec["samples"]) < 3:
                    clean = content.replace("\n", " ")[:120]
                    rec["samples"].append((matched[0], clean))
            con.close()
        except Exception:
            continue

    rows = []
    for h, rec in hits.items():
        uid = hash2uid.get(h, f"(未匹配:{h[:12]}…)")
        last = datetime.fromtimestamp(
            rec["last"] / 1000 if rec["last"] and rec["last"] > 1e12 else (rec["last"] or 0)
        ).strftime("%Y-%m-%d %H:%M") if rec["last"] else "-"
        rows.append((uid, rec["count"], last, rec["samples"]))
    rows.sort(key=lambda x: -x[1])

    print(f"关键词 {keywords} 命中 {len(rows)} 个会话（解密库：{dbdir}）\n")
    print(f"{'命中':>6}  {'最近消息':<18}  wxid/会话ID")
    print("-" * 80)
    for uid, cnt, last, samples in rows[: (args.top or 20)]:
        kind = "群" if "@chatroom" in uid else ("单聊" if uid.startswith("wxid_") or re.match(r"^[a-zA-Z0-9_-]+$", uid) else "?")
        print(f"{cnt:>6}  {last:<18}  {uid}  ({kind})")
        for kw, s in samples:
            print(f"         └─ [{kw}] {s}")
    if not rows:
        print("  （无命中，尝试换关键词或先 decrypt 更新解密库）")
    print(f"\n下一步：用 read/extract/distill <wxid> 操作目标会话。")
    return 0


def _need_wxid(dbdir, session):
    """传入 wxid 直接用；自定义微信号（custom_id_example1 等）先试读消息表确认；传入名字则尽力从 FTS 提示。"""
    if session.startswith("wxid_") or "@" in session:
        return session
    # 自定义微信号（不以 wxid_ 开头、不含 @）：先试读，有消息即视为有效 wxid
    try:
        probe = read_session(session, dbdir, limit=1)
        if probe:
            return session
    except Exception:
        pass
    names = collect_visible_names(dbdir)
    hits = [n for n in names if session in n]
    if hits:
        print(f"[i] 「{session}」匹配到可见名字：{hits[:10]}。")
        print("    当前解密库无昵称→wxid 映射，请先用 list 拿到该会话的 wxid 再读取；")
        print("    或先补解密 contact.db（见 references/paths.md 故障排查）。")
    else:
        print(f"[!] 「{session}」不是 wxid 且未在可见名字中找到。请先运行 list 查看会话 wxid。")
    return None


def cmd_read(args):
    dbdir = resolve_decrypt_dir()
    wxid = _need_wxid(dbdir, args.session)
    if not wxid:
        return 2
    msgs = read_session(wxid, dbdir, limit=args.limit, since=args.since)
    out = _out_dir(args.out or DEFAULT_OUT, wxid, "read")
    md, _, _ = export_msgs(msgs, out, args.session)
    print(f"✅ 读取完成：{len(msgs)} 条 → {md}")
    return 0


def cmd_extract(args):
    dbdir = resolve_decrypt_dir()
    wxid = _need_wxid(dbdir, args.session)
    if not wxid:
        return 2
    msgs = read_session(wxid, dbdir)
    out = _out_dir(args.out or DEFAULT_OUT, wxid, "extract")
    md, _, _ = export_msgs(msgs, out, args.session)
    print(f"✅ 萃取完成（原稿）：{len(msgs)} 条 → {md}")
    return 0


def cmd_distill(args):
    dbdir = resolve_decrypt_dir()
    wxid = _need_wxid(dbdir, args.session)
    if not wxid:
        return 2
    msgs = read_session(wxid, dbdir)
    out = _out_dir(args.out or DEFAULT_OUT, wxid, "distill")
    md, csvp, _ = export_msgs(msgs, out, args.session)
    # wechat_summary 的 MD 解析格式为 `**发送者** · 时间`，与本导出不同；CSV 解析最稳，走 CSV
    cmd = [VENV_PY, SUMMARY, "--input", csvp, "-o", out]
    if args.model:
        cmd += ["--model", args.model]
    if args.gap:
        cmd += ["--gap", str(args.gap)]
    if args.max_msgs:
        cmd += ["--max-msgs", str(args.max_msgs)]
    if args.mock:
        cmd += ["--mock"]
    if args.dry_run:
        cmd += ["--dry-run"]
    if args.verbose:
        cmd += ["-v"]
    print(f"[i] 已导出 {len(msgs)} 条 → {md}，开始 AI 蒸馏…")
    r = _run(cmd)
    print(r.stdout)
    if r.stderr and args.verbose:
        print(r.stderr, file=sys.stderr)
    if r.returncode != 0:
        print(f"[!] 蒸馏失败，stderr：{r.stderr[-800:] if r.stderr else '(无)'}", file=sys.stderr)
        return r.returncode
    print(f"✅ 蒸馏完成 → {out}")
    print("  提示：价值分级/素材卡/选题落点按 references/distill-standards.md 执行")
    return 0


def cmd_fetch(args):
    r = _run(["bash", PIPELINE])
    print(r.stdout)
    if r.stderr:
        print(r.stderr, file=sys.stderr)
    return r.returncode


def main():
    ap = argparse.ArgumentParser(description="微信通道统一 CLI（行途）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ap.add_argument("-v", "--verbose", action="store_true", help="显示详细日志")

    sub.add_parser("decrypt", help="重新解密最新微信库")

    p_list = sub.add_parser("list", help="枚举所有有消息的会话")
    p_list.add_argument("--top", type=int, default=60, help="最多显示条数")

    p_search = sub.add_parser("search", help="按关键词/名字反查会话 wxid（跨消息表搜索）")
    p_search.add_argument("keywords", nargs="+", help="搜索关键词（多个为 OR 逻辑）")
    p_search.add_argument("--top", type=int, default=20, help="最多显示会话数")

    p_read = sub.add_parser("read", help="读取指定会话（wxid）→ Markdown+CSV")
    p_read.add_argument("session", help="wxid 或会话ID（优先 wxid）")
    p_read.add_argument("--since", help="起始日期 YYYY-MM-DD")
    p_read.add_argument("--limit", type=int, help="只取最近 N 条")
    p_read.add_argument("-o", "--out", default=None, help="输出根目录")

    p_ext = sub.add_parser("extract", help="萃取：导出指定会话完整原稿")
    p_ext.add_argument("session", help="wxid 或会话ID")
    p_ext.add_argument("-o", "--out", default=None, help="输出根目录")

    p_dis = sub.add_parser("distill", help="AI 蒸馏：导出 + 分支总结")
    p_dis.add_argument("session", help="wxid 或会话ID")
    p_dis.add_argument("--model", help="模型名（默认 deepseek-v4-pro）")
    p_dis.add_argument("--gap", type=int, help="分支切分间隔分钟（默认 60）")
    p_dis.add_argument("--max-msgs", type=int, help="每分支最大消息数（默认 200）")
    p_dis.add_argument("--mock", action="store_true", help="mock 模式，不调用真实 LLM")
    p_dis.add_argument("--dry-run", action="store_true", help="只输出分支结构，不调 AI")
    p_dis.add_argument("-o", "--out", default=None, help="输出根目录")

    sub.add_parser("fetch", help="获取：元宝分享全文增量抓取+归档")

    args = ap.parse_args()
    handlers = {
        "decrypt": cmd_decrypt,
        "list": cmd_list,
        "search": cmd_search,
        "read": cmd_read,
        "extract": cmd_extract,
        "distill": cmd_distill,
        "fetch": cmd_fetch,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
