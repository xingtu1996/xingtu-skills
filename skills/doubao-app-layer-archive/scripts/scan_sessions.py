#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆包应用层全量落档扫描器（流式，不整读大文件）。

遍历 DoubaoWork 各 Profile 的 .sessions/，对每个会话抽取：
  - 账号/会话元信息（profile、session_id、绝对路径、大小、时间）
  - board.md 任务板（任务ID/标题/Organizer/状态/产物路径）
  - assignment.md 需求流（Created、首条需求摘要当主题、需求条数）
  - agents/*/system/trajectory.jsonl：流式逐行统计 user/assistant/tool 消息数、
    assistant.tool_calls[*].function.name 频次
  - attachments 文件数与大小、memory/MEMORY.md 大小

聚合输出：
  - 账号使用情况（每 Profile 会话数/总大小/时间跨度）
  - 规划周期（按 ISO 周聚合会话数）
  - 全局技能/工具调用 top N
  - 会话清单表（一行一会话）
  - 产物路径索引（board.md 产物路径列 + assignment 里出现的 /Users/ 绝对路径）

用法：
  python3 scan_sessions.py --full --out-md <落档.md> --out-json <原始.json>
  python3 scan_sessions.py --sample 3 --out-md sample.md --out-json sample.json
  python3 scan_sessions.py --profiles "/path/Profile 1" "/path/Profile 2" ...

退出码：0 成功；1 参数/路径错误。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

DEFAULT_PROFILES = [
    "/Users/<user>/Library/Application Support/DoubaoWork/Profile 1",
    "/Users/<user>/Library/Application Support/DoubaoWork/Profile 2",
    "/Users/<user>/Library/Application Support/DoubaoWork/Profile 3",
]

CST = timezone(timedelta(hours=8))


def human(n: int) -> str:
    """字节数转可读字符串。"""
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}GB"


def dir_size(path: Path) -> int:
    """os.walk 累加目录字节数（不跟随符号链接）。"""
    total = 0
    for root, dirs, files in os.walk(path, topdown=True):
        # 不进入 socket/poll-monitors 这类运行时瞬态目录里的大文件？保守：全算
        for f in files:
            fp = Path(root) / f
            try:
                if not fp.is_symlink():
                    total += fp.stat().st_size
            except OSError:
                pass
    return total


def parse_board(board_path: Path) -> list[dict]:
    """解析 board.md 表格，返回任务行 dict 列表。"""
    rows = []
    if not board_path.exists():
        return rows
    try:
        text = board_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return rows
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        if cells[0] in ("任务ID", "---", "---:"):
            continue
        if set(cells[0]) <= set("-: "):
            continue
        rows.append({
            "task_id": cells[0],
            "title": cells[1],
            "organizer": cells[2],
            "status": cells[3],
            "artifact_path": cells[4] if len(cells) > 4 else "",
            "artifact_link": cells[5] if len(cells) > 5 else "",
        })
    return rows


def parse_assignment(asg_path: Path) -> dict:
    """解析 assignment.md：头部元信息 + 按时间戳切块的需求条数 + 首条需求摘要。"""
    info = {"created": "", "agent_id": "", "role": "", "assigned_by": "",
            "request_count": 0, "first_request": "", "request_timestamps": []}
    if not asg_path.exists():
        return info
    try:
        text = asg_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return info
    head, _, body = text.partition("> append-only:")
    for line in head.splitlines():
        m = re.match(r"-\s*Agent ID:\s*(\S+)", line)
        if m:
            info["agent_id"] = m.group(1)
        m = re.match(r"-\s*Role:\s*(\S+)", line)
        if m:
            info["role"] = m.group(1)
        m = re.match(r"-\s*Assigned by:\s*(\S+)", line)
        if m:
            info["assigned_by"] = m.group(1)
        m = re.match(r"-\s*Created:\s*(\S+)", line)
        if m:
            info["created"] = m.group(1)
    # 切块：## [timestamp] 需求
    blocks = re.split(r"\n##\s*\[[^\]]+\]\s*需求", body)
    stamps = re.findall(r"\[(\d{4}-\d{2}-\d{2}T[^\]]+)\]\s*需求", body)
    info["request_timestamps"] = stamps
    info["request_count"] = len(stamps)
    if len(blocks) >= 2:
        first = blocks[1].strip()
        # 截前 120 字当摘要
        first = re.sub(r"\s+", " ", first)
        info["first_request"] = first[:120] + ("…" if len(first) > 120 else "")
    return info


def scan_trajectory(traj_path: Path) -> dict:
    """流式逐行读 trajectory.jsonl，统计消息数与 tool 调用频次。"""
    stats = {"lines": 0, "user": 0, "assistant": 0, "tool": 0,
             "other": 0, "tool_names": Counter(), "has_image": 0}
    try:
        with traj_path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                stats["lines"] += 1
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                role = d.get("role", "")
                if role == "user":
                    stats["user"] += 1
                elif role == "assistant":
                    stats["assistant"] += 1
                elif role == "tool":
                    stats["tool"] += 1
                else:
                    stats["other"] += 1
                if d.get("image_link_list"):
                    stats["has_image"] += 1
                for tc in d.get("tool_calls", []) or []:
                    try:
                        fname = tc.get("function", {}).get("name", "?")
                        stats["tool_names"][fname] += 1
                    except AttributeError:
                        pass
    except OSError:
        pass
    return stats


def scan_session(profile_label: str, session_dir: Path) -> dict:
    session_id = session_dir.name
    board_path = session_dir / "board.md"
    memory_path = session_dir / "memory" / "MEMORY.md"
    attachments_dir = session_dir / "attachments"

    rec = {
        "profile": profile_label,
        "session_id": session_id,
        "path": str(session_dir),
        "size_bytes": dir_size(session_dir),
        "mtime": datetime.fromtimestamp(session_dir.stat().st_mtime, CST).isoformat(),
        "board": parse_board(board_path),
        "agents": [],
        "attachments_count": 0,
        "attachments_size": 0,
        "memory_bytes": memory_path.stat().st_size if memory_path.exists() else 0,
        "assignment_first_request": "",
        "assignment_created": "",
        "assignment_request_count": 0,
    }

    # attachments
    if attachments_dir.exists():
        for root, _, files in os.walk(attachments_dir):
            for f in files:
                fp = Path(root) / f
                try:
                    if not fp.is_symlink():
                        rec["attachments_count"] += 1
                        rec["attachments_size"] += fp.stat().st_size
                except OSError:
                    pass

    # agents
    agents_dir = session_dir / "agents"
    if agents_dir.exists():
        for agent_dir in sorted(agents_dir.iterdir()):
            if not agent_dir.is_dir():
                continue
            asg = parse_assignment(agent_dir / "system" / "assignment.md")
            traj = scan_trajectory(agent_dir / "system" / "trajectory.jsonl")
            rec["agents"].append({
                "agent_id": agent_dir.name,
                "role": asg["role"],
                "created": asg["created"],
                "request_count": asg["request_count"],
                "first_request": asg["first_request"],
                "traj_lines": traj["lines"],
                "msg_user": traj["user"],
                "msg_assistant": traj["assistant"],
                "msg_tool": traj["tool"],
                "has_image_msg": traj["has_image"],
                "tool_names": dict(traj["tool_names"].most_common()),
            })
            # 主 agent（role=main）的首条需求当会话主题
            if asg["role"] == "main" and not rec["assignment_first_request"]:
                rec["assignment_first_request"] = asg["first_request"]
                rec["assignment_created"] = asg["created"]
                rec["assignment_request_count"] = asg["request_count"]

    # 兜底：没有 main agent 就取第一个 agent 的首条需求
    if not rec["assignment_first_request"] and rec["agents"]:
        rec["assignment_first_request"] = rec["agents"][0]["first_request"]
        rec["assignment_created"] = rec["agents"][0]["created"]
        rec["assignment_request_count"] = rec["agents"][0]["request_count"]

    return rec


def iso_week(ts_iso: str) -> str:
    """从 ISO 时间字符串取 ISO 周标签 YYYY-Www。"""
    if not ts_iso:
        return "unknown"
    try:
        dt = datetime.fromisoformat(ts_iso)
    except ValueError:
        return "unknown"
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


def render_md(records: list[dict], top_n: int) -> str:
    lines = []
    lines.append("# 豆包应用层全量落档")
    lines.append("")
    lines.append(f"_生成时间：{datetime.now(CST).isoformat(timespec='seconds')}_")
    lines.append(f"_会话样本数：{len(records)}_")
    lines.append("")

    # 1. 账号使用情况
    lines.append("## 一、账号使用情况")
    lines.append("")
    lines.append("| 账号(Profile) | 会话数 | 总大小 | 最早会话 | 最晚会话 |")
    lines.append("| --- | ---: | ---: | --- | --- |")
    by_profile: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_profile[r["profile"]].append(r)
    for prof, rs in sorted(by_profile.items()):
        sizes = sum(r["size_bytes"] for r in rs)
        mtimes = sorted(r["mtime"] for r in rs if r["mtime"])
        earliest = mtimes[0] if mtimes else "-"
        latest = mtimes[-1] if mtimes else "-"
        lines.append(f"| {prof} | {len(rs)} | {human(sizes)} | {earliest} | {latest} |")
    lines.append("")

    # 2. 规划周期（按 ISO 周）
    lines.append("## 二、规划周期（按 ISO 周聚合会话数）")
    lines.append("")
    week_counter: Counter = Counter()
    for r in records:
        ts = r["assignment_created"] or r["mtime"]
        week_counter[iso_week(ts)] += 1
    lines.append("| ISO 周 | 新会话数 |")
    lines.append("| --- | ---: |")
    for wk in sorted(week_counter.keys()):
        lines.append(f"| {wk} | {week_counter[wk]} |")
    lines.append("")

    # 3. 全局技能/工具调用 top N
    lines.append(f"## 三、全局技能/工具调用 Top {top_n}")
    lines.append("")
    global_tools: Counter = Counter()
    for r in records:
        for a in r["agents"]:
            for name, cnt in a["tool_names"].items():
                global_tools[name] += cnt
    lines.append("| 工具/技能名 | 调用次数 |")
    lines.append("| --- | ---: |")
    for name, cnt in global_tools.most_common(top_n):
        lines.append(f"| `{name}` | {cnt} |")
    lines.append("")

    # 4. 会话清单
    lines.append("## 四、会话清单")
    lines.append("")
    lines.append("| Profile | Session ID | 创建时间 | 大小 | Agent 数 | 需求条数 | 主题摘要 |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | --- |")
    for r in sorted(records, key=lambda x: x["assignment_created"] or x["mtime"]):
        topic = r["assignment_first_request"].replace("|", "\\|")
        lines.append(
            f"| {r['profile'].split()[-1]} | `{r['session_id']}` | "
            f"{r['assignment_created'][:10] or '-'} | {human(r['size_bytes'])} | "
            f"{len(r['agents'])} | {r['assignment_request_count']} | {topic} |"
        )
    lines.append("")

    # 5. 产物路径索引（board.md 产物路径列 + assignment 里出现的绝对路径）
    lines.append("## 五、产物与绝对路径索引")
    lines.append("")
    artifact_paths = []
    for r in records:
        for task in r["board"]:
            p = task["artifact_path"].strip()
            if p:
                artifact_paths.append((r["session_id"], task["title"], p))
    lines.append("### 5.1 board.md 登记的产物路径")
    lines.append("")
    if artifact_paths:
        lines.append("| Session | 任务标题 | 产物路径 |")
        lines.append("| --- | --- | --- |")
        for sid, title, p in artifact_paths:
            lines.append(f"| `{sid}` | {title} | `{p}` |")
    else:
        lines.append("_本批次未从 board.md 提取到产物路径。_")
    lines.append("")

    # 5.2 会话目录绝对路径（全量索引，供后续 session-distill / 内容挖掘跳转）
    lines.append("### 5.2 会话目录绝对路径索引")
    lines.append("")
    for r in sorted(records, key=lambda x: x["profile"]):
        lines.append(f"- `{r['path']}`  <!-- {r['profile']} / {r['session_id']} / {r['assignment_first_request'][:40]} -->")
    lines.append("")

    # 6. 备忘
    lines.append("## 六、备忘与交叉引用")
    lines.append("")
    lines.append("- 本落档只收应用层元数据（账号/会话/工具调用/路径），不做内容挖掘与选稿；内容侧归 `session-distill` skill。")
    lines.append("- xingtu-vault 既有「豆包 166 会话盘点台账」按业务维度交叉引用，本档按技术维度（Profile/trajectory/路径）补充。")
    lines.append("- trajectory.jsonl 是流式逐行扫描，未整读；如需深挖单会话内容，按 §5.2 路径跳过去读对应文件。")
    lines.append("- attachments/ 与 memory/MEMORY.md 可能为空，属正常（临时会话无附件）。")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="豆包应用层全量落档扫描器")
    ap.add_argument("--profiles", nargs="*", default=DEFAULT_PROFILES,
                    help="Profile 根目录列表（默认 3 个 DoubaoWork Profile）")
    ap.add_argument("--full", action="store_true", help="全量扫描所有会话")
    ap.add_argument("--sample", type=int, default=0,
                    help="只抽前 N 个会话（用于示例/冒烟）")
    ap.add_argument("--out-md", required=True, help="输出落档 Markdown 路径")
    ap.add_argument("--out-json", required=True, help="输出原始 JSON 路径")
    ap.add_argument("--top", type=int, default=20, help="全局工具调用 top N")
    args = ap.parse_args()

    if not args.full and args.sample <= 0:
        print("ERROR: 必须指定 --full 或 --sample N", file=sys.stderr)
        return 1

    records: list[dict] = []
    for prof in args.profiles:
        # 短标签：Profile 1 / Profile 2 / Profile 3
        prof_label = Path(prof).name  # e.g. "Profile 2"
        sessions_root = Path(prof) / ".doubaowork" / "agent_mode" / "workspace" / ".sessions"
        if not sessions_root.exists():
            print(f"WARN: 跳过不存在的 Profile 路径 {sessions_root}", file=sys.stderr)
            continue
        session_dirs = sorted([d for d in sessions_root.iterdir() if d.is_dir()])
        if args.sample > 0 and not args.full:
            # sample 模式：从每个 Profile 各抽前 N 个
            session_dirs = session_dirs[:args.sample]
        for sd in session_dirs:
            print(f"扫描 {prof_label} / {sd.name} ...", file=sys.stderr)
            records.append(scan_session(prof_label, sd))

    md = render_md(records, args.top)
    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_md).write_text(md, encoding="utf-8")

    # JSON 序列化（Counter 已转 dict）
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(
        json.dumps(records, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"完成：{len(records)} 会话 -> {args.out_md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
