#!/usr/bin/env python3
"""投入核算 — 从 Claude Code 会话记录还原「哪几天、每天多少有效工时、那天在干什么」。

用法：
  scan-sessions.py                          # 核算当前工作空间，最近 30 天
  scan-sessions.py --since 2026-09-01 --until 2026-09-21
  scan-sessions.py --gap 60                 # 换断点阈值（默认 90 分钟）
  scan-sessions.py --topics                 # 附带每天的头几条用户消息（还原事项）
  scan-sessions.py --selftest               # 自检（不依赖真实数据）

输出：逐日表（日期 / 有效工时 / 会话时段 / 条数），--topics 时附事项摘要。
只读，不修改任何文件。
"""

import argparse
import collections
import datetime
import glob
import json
import os
import re
import sys

PROJECTS = os.path.expanduser("~/.claude/projects")


def munge(path):
    """工作空间路径 → Claude Code 的会话目录名。

    规则：除 [A-Za-z0-9-] 外的字符都变成 '-'（'/' 和中文都走这条）。
    /Users/me/proj/my-app → -Users-me-proj-my-app
    """
    return re.sub(r"[^A-Za-z0-9-]", "-", os.path.abspath(path))


def session_dirs(workdir):
    """当前工作空间及其子目录对应的全部会话目录。

    子目录也要扫：在 <workdir>/specs 里启的会话，目录名是 <munge>-specs。
    """
    base = munge(workdir)
    return sorted(d for d in glob.glob(os.path.join(PROJECTS, base + "*")) if os.path.isdir(d))


def local_dt(raw):
    try:
        dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return dt.astimezone() if dt.tzinfo else dt


def load(dirs, since, until):
    """返回 {日期: {'ts': [时间戳...], 'topics': [(ts, 文本)...]}}"""
    days = collections.defaultdict(lambda: {"ts": [], "topics": []})
    for d in dirs:
        for f in glob.glob(os.path.join(d, "*.jsonl")):
            for line in open(f, errors="ignore"):
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                dt = local_dt(o.get("timestamp"))
                if not dt or not (since <= dt.date() <= until):
                    continue
                days[dt.date()]["ts"].append(dt)
                if o.get("type") == "user":
                    text = extract_text(o)
                    if text:
                        days[dt.date()]["topics"].append((dt, text))
    return days


def extract_text(obj):
    content = (obj.get("message") or {}).get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = " ".join(
            c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
        )
    else:
        return ""
    text = " ".join(text.split())
    # 跳过工具结果与系统注入（以 < 开头的都是），它们不是"人在干什么"
    if len(text) < 8 or text.startswith("<") or "tool_result" in text:
        return ""
    return text


def windows(timestamps, gap):
    """把时间戳切成若干连续段：相邻间隔 > gap 即切断（切午休/晚餐/离席）。"""
    ts = sorted(set(timestamps))
    if not ts:
        return []
    out, start, prev = [], ts[0], ts[0]
    for t in ts[1:]:
        if t - prev > gap:
            out.append((start, prev))
            start = t
        prev = t
    out.append((start, prev))
    return out


def hours(segs):
    return sum((b - a).total_seconds() for a, b in segs) / 3600.0


def report(days, gap, gap_min, topics, topic_limit):
    total = 0.0
    print(f"{'日期':<12}{'星期':<4}{'有效工时':>9}  会话时段")
    for day in sorted(days):
        info = days[day]
        segs = windows(info["ts"], gap)
        h = hours(segs)
        total += h
        span = " + ".join(f"{a.strftime('%H:%M')}-{b.strftime('%H:%M')}" for a, b in segs) or "—"
        print(f"{day!s:<12}{day.strftime('%a'):<4}{h:>8.1f}h  {span}")
        if topics:
            seen = set()
            shown = 0
            for ts, text in info["topics"]:
                key = text[:40]
                if key in seen:
                    continue
                seen.add(key)
                print(f"{'':>26}{ts.strftime('%H:%M')} | {text[:110]}")
                shown += 1
                if shown >= topic_limit:
                    break
    print(f"\n合计 {total:.1f}h = {total / 8:.2f} 人天（1 人天 = 8h，断点阈值 {gap_min} 分钟）")
    print("⚠️ 这是「在电脑前与 AI 协作」的下限，不含线下会议、读材料、思考 —— 填报需另行补偿")
    return total


def selftest():
    """自检：断点切分与文本过滤。合成数据，不碰真实会话。"""
    t = datetime.datetime(2026, 1, 1)
    mk = lambda m: t + datetime.timedelta(minutes=m)
    # 09:00–10:00 连续；11:00 距上一个 60min —— 阈值 90 不切，算满 2.0h
    assert hours(windows([mk(0), mk(30), mk(60), mk(120)], datetime.timedelta(minutes=90))) == 2.0
    # 阈值降到 60：61min 的间隔被切出去 → 1.0h
    assert hours(windows([mk(0), mk(30), mk(60), mk(121)], datetime.timedelta(minutes=60))) == 1.0
    # 恰好等于阈值不切（> 才切）
    assert len(windows([mk(0), mk(90)], datetime.timedelta(minutes=90))) == 1
    # 空输入
    assert windows([], datetime.timedelta(minutes=90)) == []
    # 重复时间戳只算一次
    assert hours(windows([mk(0), mk(0), mk(30)], datetime.timedelta(minutes=90))) == 0.5
    # 文本过滤：工具结果 / 系统注入 / 过短的不算"人在干什么"
    assert extract_text({"message": {"content": "<system-reminder>x</system-reminder>"}}) == ""
    assert extract_text({"message": {"content": "短"}}) == ""
    assert extract_text({"message": {"content": "这个动作封装成技能吧"}}) == "这个动作封装成技能吧"
    assert extract_text({"message": {"content": [{"type": "text", "text": "多段内容 合并 成一条"}]}}) == "多段内容 合并 成一条"
    # 路径还原：'/' 与中文字符都变 '-'
    assert munge("/Users/me/proj/my-app") == "-Users-me-proj-my-app"
    assert munge("/Users/me/proj/中文目录") == "-Users-me-proj" + "-" * 5
    print("selftest OK")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", default=".", help="工作空间路径（默认当前目录）")
    p.add_argument("--since", help="起始日期 YYYY-MM-DD（默认 30 天前）")
    p.add_argument("--until", help="截止日期 YYYY-MM-DD（默认今天）")
    p.add_argument("--gap", type=int, default=90, help="断点阈值，分钟（默认 90）")
    p.add_argument("--topics", action="store_true", help="附每天的头几条用户消息")
    p.add_argument("--topic-limit", type=int, default=4)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        selftest()
        return

    today = datetime.date.today()
    since = datetime.date.fromisoformat(a.since) if a.since else today - datetime.timedelta(days=30)
    until = datetime.date.fromisoformat(a.until) if a.until else today
    if since > until:
        sys.exit("--since 不能晚于 --until")

    dirs = session_dirs(a.dir)
    if not dirs:
        sys.exit(
            f"没找到会话目录：{PROJECTS}/{munge(a.dir)}*\n"
            f"排查：① 这个工作空间下跑过 Claude Code 吗 ② 路径大小写/软链是否一致（用 pwd -P 看真实路径）"
        )
    print(f"工作空间: {os.path.abspath(a.dir)}")
    print(f"会话目录: {', '.join(os.path.basename(d) for d in dirs)}")
    print(f"区间: {since} ~ {until}\n")

    days = load(dirs, since, until)
    if not days:
        sys.exit("区间内无会话记录")
    report(days, datetime.timedelta(minutes=a.gap), a.gap, a.topics, a.topic_limit)


if __name__ == "__main__":
    main()
