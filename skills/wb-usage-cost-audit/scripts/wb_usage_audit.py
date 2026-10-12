#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkBuddy / CodeBuddy 用量取证脚本（只读）

读取本机三本账：
  1. ~/.workbuddy/workbuddy.db  -> session_usage（积分账）
  2. ~/.workbuddy/traces/**     -> trace.modelInfo（Token 账）
  3. ~/.workbuddy/models.json   -> 自定义模型（不扣积分）

输出 JSON + 人类可读摘要。不改任何文件。

用法:
  python3 wb_usage_audit.py                    # 摘要 + 写入 /tmp/wb_audit.json
  python3 wb_usage_audit.py --json out.json    # 指定输出路径
  python3 wb_usage_audit.py --flash-prices 0.02 1.0 4.0 --peak-mult 2
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

WB = os.path.expanduser("~/.workbuddy")
DB = os.path.join(WB, "workbuddy.db")
TRACES = os.path.join(WB, "traces")
MODELS = os.path.join(WB, "models.json")
CST = timezone(timedelta(hours=8))

# 视为"无成本"的模型（实测不扣积分，可由 --free-models 覆盖）
DEFAULT_FREE = ("hy3", "hy4-preview", "hy4", "hy3-preview")


def _ts(ms_or_s: int) -> datetime:
    """session_usage.updated_at 是毫秒；兼容秒。"""
    v = ms_or_s
    if v > 10_000_000_000:
        v /= 1000
    return datetime.fromtimestamp(v, timezone.utc).astimezone(CST)


# ---------------------------------------------------------------- 1. 积分账
def read_credit_ledger() -> dict:
    if not os.path.exists(DB):
        return {"error": f"找不到 {DB}"}
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    rows = con.execute(
        "SELECT session_id, credit_json, used, size, updated_at "
        "FROM session_usage WHERE credit_json IS NOT NULL AND credit_json != ''"
    ).fetchall()

    per_session: list[tuple[str, float, int, str]] = []
    by_day: dict[str, float] = collections.defaultdict(float)
    by_model: dict[str, float] = collections.defaultdict(float)
    total_credits = 0.0
    total_calls = 0

    # 模型名需要 JOIN sessions
    model_of = {
        r["id"]: (r["model"] or "")
        for r in con.execute("SELECT id, model FROM sessions").fetchall()
    }

    for r in rows:
        try:
            d = json.loads(r["credit_json"])
        except Exception:
            continue
        if not d:
            continue
        c = sum(float(v) for v in d.values())
        total_credits += c
        total_calls += len(d)
        day = _ts(r["updated_at"]).strftime("%Y-%m-%d")
        by_day[day] += c
        m = model_of.get(r["session_id"]) or "(未知/悬空会话)"
        by_model[m] += c
        per_session.append(
            (r["session_id"], c, r["used"] or 0, _ts(r["updated_at"]).strftime("%Y-%m-%d"))
        )

    # 悬空会话统计（在 session_usage 但不在 sessions）
    dangling = [s for s, _, _, _ in per_session if s not in model_of]

    days = sorted(by_day)
    return {
        "total_credits": round(total_credits, 2),
        "total_calls": total_calls,
        "sessions_with_credit": len(per_session),
        "dangling_sessions": len(dangling),
        "first_day": days[0] if days else None,
        "last_day": days[-1] if days else None,
        "active_days": len(days),
        "by_day": {k: round(v, 2) for k, v in sorted(by_day.items())},
        "by_model": {k: round(v, 2) for k, v in sorted(by_model.items(), key=lambda x: -x[1])},
        "per_session": [
            {"session_id": s, "credits": round(c, 2), "used_ctx_tokens": u, "day": d}
            for s, c, u, d in sorted(per_session, key=lambda x: -x[1])
        ],
    }


# ---------------------------------------------------------------- 2. Token 账
def read_token_ledger() -> dict:
    files = glob.glob(os.path.join(TRACES, "*", "*.json"))
    sessions: dict[str, dict] = {}
    bad = 0
    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                d = json.load(fh)
        except Exception:
            bad += 1
            continue
        t = d.get("trace") or {}
        mi = t.get("modelInfo")
        sid = t.get("sessionId")
        if not mi or not sid:
            continue
        rec = sessions.setdefault(
            sid,
            {
                "models": set(),
                "in": 0,
                "out": 0,
                "cached": 0,
                "calls": 0,
                "traces": 0,
                "first": None,
                "last": None,
            },
        )
        rec["models"].update(mi.get("models") or [])
        rec["in"] += mi.get("totalInputTokens") or 0
        rec["out"] += mi.get("totalOutputTokens") or 0
        rec["cached"] += mi.get("totalCachedTokens") or 0
        rec["calls"] += mi.get("callCount") or 0
        rec["traces"] += 1
        if t.get("startedAt") and (rec["first"] is None or t["startedAt"] < rec["first"]):
            rec["first"] = t["startedAt"]
        if t.get("endedAt") and (rec["last"] is None or t["endedAt"] > rec["last"]):
            rec["last"] = t["endedAt"]

    tin = sum(r["in"] for r in sessions.values())
    tout = sum(r["out"] for r in sessions.values())
    tca = sum(r["cached"] for r in sessions.values())
    tcalls = sum(r["calls"] for r in sessions.values())

    return {
        "trace_files": len(files),
        "unparsable": bad,
        "sessions_with_modelinfo": len(sessions),
        "input_tokens": tin,
        "output_tokens": tout,
        "cached_tokens": tca,
        "uncached_input_tokens": tin - tca,
        "total_tokens": tin + tout,
        "total_calls": tcalls,
        "cache_hit_rate": round(tca / tin * 100, 2) if tin else 0.0,
        "sessions": {
            sid: {
                "models": sorted(r["models"]),
                "in": r["in"],
                "out": r["out"],
                "cached": r["cached"],
                "calls": r["calls"],
                "first": r["first"],
                "last": r["last"],
            }
            for sid, r in sessions.items()
        },
    }


# ------------------------------------------------------- 3. 免费模型核验
def verify_free_models(token_led: dict, credit_led: dict, free_names) -> dict:
    paid_ids = {
        p["session_id"] for p in credit_led.get("per_session", [])
    }
    table: dict[str, dict] = collections.defaultdict(lambda: {"paid": 0, "free": 0})
    for sid, s in token_led.get("sessions", {}).items():
        ms = s["models"]
        if len(ms) != 1:
            continue
        tbl = table[ms[0]]
        tbl["paid" if sid in paid_ids else "free"] += 1

    out = {}
    for m, c in sorted(table.items(), key=lambda x: -(x[1]["paid"] + x[1]["free"])):
        if c["free"] and not c["paid"]:
            verdict = "free"
        elif c["paid"] and not c["free"]:
            verdict = "paid"
        else:
            verdict = "mixed"
        out[m] = {**c, "verdict": verdict}
    return {
        "by_model": out,
        "observed_free": [m for m, v in out.items() if v["verdict"] == "free"],
        "observed_paid": [m for m, v in out.items() if v["verdict"] == "paid"],
        "hint_free_names": list(free_names),
    }


# ------------------------------------------------------- 4. 自定义模型
def read_custom_models() -> dict:
    if not os.path.exists(MODELS):
        return {"exists": False, "count": 0, "models": []}
    try:
        with open(MODELS, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        return {"exists": True, "error": str(e), "count": 0, "models": []}

    # 兼容 list 或 {"models":[...]}
    items = raw if isinstance(raw, list) else raw.get("models", [])
    safe = []
    for m in items:
        mm = dict(m)
        for k in ("apiKey", "apikey"):
            if k in mm and isinstance(mm[k], str) and mm[k]:
                v = mm[k]
                mm[k] = (v[:6] + "***" + v[-4:]) if len(v) > 12 else "***"
        safe.append(mm)
    return {"exists": True, "count": len(safe), "models": safe}


# ------------------------------------------------------- 5. 成本对撞
def cost_compare(
    token_led: dict,
    credit_led: dict,
    family: set[str],
    prices: dict,
    tiers: dict,
    peak_mult: float,
) -> dict:
    """取「模型全属 family」的会话做可比子集，算直充 vs 订阅。"""
    paid = {p["session_id"]: p["credits"] for p in credit_led.get("per_session", [])}
    sub = [
        (s, paid[s], v)
        for s, v in token_led.get("sessions", {}).items()
        if s in paid and v["models"] and set(v["models"]) <= family
    ]
    if not sub:
        return {"error": "没有可用于该模型家族的可比子集（intersection 为空）"}

    cr = sum(c for _, c, _ in sub)
    tin = sum(v["in"] for _, _, v in sub)
    tout = sum(v["out"] for _, _, v in sub)
    tca = sum(v["cached"] for _, _, v in sub)
    unc = tin - tca
    tot = tin + tout

    def direct(mult: float) -> float:
        return (
            tca / 1e6 * prices["cache_hit"] * mult
            + unc / 1e6 * prices["cache_miss"] * mult
            + tout / 1e6 * prices["output"] * mult
        )

    off, pk = direct(1.0), direct(peak_mult)
    per_m = tot / 1e6 if tot else 0

    rows = []
    rows.append(
        {
            "plan": "厂商直充 · 空闲",
            "cost": round(off, 2),
            "per_million": round(off / per_m, 4) if per_m else None,
            "vs_off": 1.0,
            "vs_peak": round(off / pk, 2) if pk else None,
        }
    )
    for name, unit in tiers.items():
        c = cr * unit
        rows.append(
            {
                "plan": f"WorkBuddy {name}",
                "cost": round(c, 2),
                "unit_price": unit,
                "per_million": round(c / per_m, 4) if per_m else None,
                "vs_off": round(c / off, 2) if off else None,
                "vs_peak": round(c / pk, 2) if pk else None,
            }
        )
    rows.append(
        {
            "plan": "厂商直充 · 高峰",
            "cost": round(pk, 2),
            "per_million": round(pk / per_m, 4) if per_m else None,
            "vs_off": round(pk / off, 2) if off else None,
            "vs_peak": 1.0,
        }
    )

    return {
        "family": sorted(family),
        "sessions": len(sub),
        "credits": round(cr, 2),
        "input": tin,
        "output": tout,
        "cached": tca,
        "uncached_input": unc,
        "total_tokens": tot,
        "cache_hit_rate": round(tca / tin * 100, 2) if tin else 0,
        "credits_per_million_tokens": round(cr / per_m, 2) if per_m else None,
        "prices": prices,
        "peak_multiplier": peak_mult,
        "rows": rows,
    }


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/wb_audit.json")
    ap.add_argument("--flash-prices", nargs=3, type=float, default=[0.02, 1.0, 4.0],
                    metavar=("CACHE_HIT", "CACHE_MISS", "OUTPUT"),
                    help="厂商空闲单价 元/百万token")
    ap.add_argument("--peak-mult", type=float, default=2.0, help="高峰相对空闲的倍率")
    ap.add_argument("--tiers", default="旗舰版·连续包年=0.0112,高级版·连续包年=0.01244,"
                                      "标准版·连续包年=0.014,标准版·连续包月=0.0175,加量包=0.05",
                    help="订阅档位 名称=积分单价, 逗号分隔")
    ap.add_argument("--family", default="deepseek-v4-flash,deepseek-v4.1-flash,deepseek-flash",
                    help="可比模型家族（逗号分隔）")
    ap.add_argument("--free-models", default=",".join(DEFAULT_FREE))
    args = ap.parse_args()

    tiers = {}
    for kv in args.tiers.split(","):
        if "=" in kv:
            k, v = kv.split("=", 1)
            tiers[k.strip()] = float(v)

    print("[*] 读取积分账 ...", file=sys.stderr)
    credit_led = read_credit_ledger()
    print("[*] 读取 Token 账（traces，可能较慢）...", file=sys.stderr)
    token_led = read_token_ledger()
    print("[*] 核验免费模型 ...", file=sys.stderr)
    free = verify_free_models(token_led, credit_led, args.free_models.split(","))
    custom = read_custom_models()

    prices = {
        "cache_hit": args.flash_prices[0],
        "cache_miss": args.flash_prices[1],
        "output": args.flash_prices[2],
    }
    compare = cost_compare(
        token_led, credit_led,
        {s.strip() for s in args.family.split(",") if s.strip()},
        prices, tiers, args.peak_mult,
    )

    report = {
        "generated_at": datetime.now(CST).isoformat(),
        "credit_ledger": {k: v for k, v in credit_led.items() if k != "per_session"},
        "token_ledger": {k: v for k, v in token_led.items() if k != "sessions"},
        "free_model_check": free,
        "custom_models": custom,
        "cost_compare": compare,
        "raw": {
            "credit_per_session": credit_led.get("per_session", []),
            "token_sessions": token_led.get("sessions", {}),
        },
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # ---------------- 人类可读摘要 ----------------
    P = print
    P("=" * 66)
    P("  WorkBuddy 用量取证报告")
    P("=" * 66)

    if "error" in credit_led:
        P(f"[!] 积分账读取失败: {credit_led['error']}")
    else:
        P(f"\n【积分账】{DB}")
        P(f"  累计消耗      : {credit_led['total_credits']:>12,.2f} 积分")
        P(f"  记账会话      : {credit_led['sessions_with_credit']:>12,}")
        P(f"  调用次数      : {credit_led['total_calls']:>12,}")
        P(f"  活跃记账日    : {credit_led['active_days']:>12,}")
        P(f"  时间范围      : {credit_led['first_day']} → {credit_led['last_day']}")
        if credit_led["dangling_sessions"]:
            P(f"  ⚠ 悬空会话    : {credit_led['dangling_sessions']}（在积分账但 sessions 表无记录）")
        P("\n  -- 按模型 --")
        for m, v in list(credit_led["by_model"].items())[:12]:
            pct = v / credit_led["total_credits"] * 100 if credit_led["total_credits"] else 0
            P(f"    {m:<34s} {v:>10,.2f}  ({pct:4.1f}%)")

    P(f"\n【Token 账】{TRACES}")
    P(f"  trace 文件    : {token_led['trace_files']:>12,}")
    P(f"  带 modelInfo  : {token_led['sessions_with_modelinfo']:>12,} 会话")
    P(f"  输入 Token    : {token_led['input_tokens']:>12,}")
    P(f"    其中缓存命中: {token_led['cached_tokens']:>12,}  ({token_led['cache_hit_rate']}%)")
    P(f"  输出 Token    : {token_led['output_tokens']:>12,}")
    P(f"  总 Token      : {token_led['total_tokens']:>12,}")
    P(f"  调用次数      : {token_led['total_calls']:>12,}")
    if token_led["cache_hit_rate"] > 80:
        P("  ★ 缓存命中率极高 —— 这是最大的成本杠杆，直充路线会因此大幅获益")

    P("\n【免费模型核验】（单一模型会话）")
    for m, v in free["by_model"].items():
        mark = {"free": "免费", "paid": "扣分", "mixed": "混合"}[v["verdict"]]
        P(f"    {m:<28s} 扣分 {v['paid']:>3d} / 免费 {v['free']:>3d}   {mark}")

    P(f"\n【自定义模型】{MODELS}")
    if not custom.get("exists"):
        P("    未创建（当前所有调用都走平台内置模型，按积分计费）")
    elif custom.get("count") == 0:
        P("    存在但为空 —— 尚未接入任何自定义模型")
    else:
        P(f"    已配置 {custom['count']} 个：")
        for m in custom["models"]:
            P(f"      - {m.get('name') or m.get('id')}  ({m.get('vendor','?')})")

    P("\n【成本对撞】")
    if "error" in compare:
        P(f"    [!] {compare['error']}")
    else:
        P(f"    模型家族      : {', '.join(compare['family'])}")
        P(f"    可比会话      : {compare['sessions']} 个")
        P(f"    积分 / Token  : {compare['credits']:,.2f} 分 / {compare['total_tokens']:,} token")
        P(f"    缓存命中率    : {compare['cache_hit_rate']}%")
        P(f"    换算率        : {compare['credits_per_million_tokens']} 积分 / 百万 token")
        P("")
        P(f"    {'方案':<26s}{'总成本':>10s}{'¥/百万':>10s}{'vs空闲':>9s}{'vs高峰':>9s}")
        P("    " + "-" * 62)
        for r in compare["rows"]:
            pm = f"{r['per_million']:.4f}" if r.get("per_million") is not None else "-"
            vo = f"{r['vs_off']:.2f}x" if r.get("vs_off") is not None else "-"
            vp = f"{r['vs_peak']:.2f}x" if r.get("vs_peak") is not None else "-"
            P(f"    {r['plan']:<26s}{r['cost']:>10,.2f}{pm:>10s}{vo:>9s}{vp:>9s}")
        P("\n    提示：直充空闲价最省；订阅价可能低于直充高峰价；加量包通常最贵。")

    # 月度外推
    if credit_led.get("by_day"):
        days = sorted(credit_led["by_day"])
        last = credit_led["by_day"][days[-1]]
        month_prefix = days[-1][:7]
        mtd = sum(v for k, v in credit_led["by_day"].items() if k.startswith(month_prefix))
        day_of_month = int(days[-1][-2:])
        monthly = mtd / day_of_month * 30
        P(f"\n【月度外推】{month_prefix} 前 {day_of_month} 天已用 {mtd:,.2f} 分")
        P(f"    → 月化 ≈ {monthly:,.0f} 积分/月")
        P("    -- 各档月成本 --")
        for name, unit in tiers.items():
            P(f"      {name:<20s} ¥{monthly*unit:>8,.2f}/月   (年化 ¥{monthly*unit*12:>9,.0f})")

    P(f"\n[*] 完整 JSON 已写入: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
