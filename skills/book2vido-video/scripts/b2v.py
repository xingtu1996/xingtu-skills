#!/usr/bin/env python3
"""book2vido 零依赖驱动客户端（stdlib only）。

为什么自己写而不改 server.py：book2vido 的 GUI 已有完整 HTTP API，
本脚本只做「客户端侧编排」，不动仓库代码，因此不受仓库改动影响。

关键设计：端口在客户端探测后经 --port 传入，绕开 start_server 内
「pkill -9 -f book2vido.gui」的兜底逻辑（占用者若是别的进程它杀不掉，必崩）。

用法:
  b2v.py auto <file> [-o out.mp4] [--repo PATH] [--chapter N] [--voice V]
  b2v.py start  [--repo PATH] [--port N]
  b2v.py upload <file> [--repo PATH]
  b2v.py run <abs_path> [--chapter N] [--voice V]
  b2v.py status <job_id>
  b2v.py fetch <video_name> -o out.mp4
  b2v.py stop
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

STATE_DIR = Path.home() / ".cache" / "book2vido-cli"
PID_FILE = STATE_DIR / "gui.pid"
PORT_FILE = STATE_DIR / "gui.port"

DEFAULT_REPO = os.environ.get("BOOK2VIDO_REPO", "")


# ── 基础 ────────────────────────────────────────────────────────────

def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) != 0


def _pick_port(start: int = 8765, tries: int = 20) -> int:
    """从 start 起找第一个空闲端口。8765 常被本机其他服务占用，必须探测。"""
    for p in range(start, start + tries):
        if _port_free(p):
            return p
    raise RuntimeError(f"no free port in [{start}, {start + tries})")


def _base() -> str:
    if not PORT_FILE.exists():
        raise RuntimeError("GUI 未启动，先跑 `b2v.py start`")
    return f"http://127.0.0.1:{int(PORT_FILE.read_text().strip())}"


def _get(path: str, timeout: float = 15) -> dict:
    req = urllib.request.Request(_base() + path)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _post(path: str, payload: dict, timeout: float = 30) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _base() + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _upload_multipart(path: str, file: Path, timeout: float = 120) -> dict:
    """手写 multipart（stdlib 没有现成的）。server 端自己解析 boundary。"""
    boundary = "----b2vcli" + str(int(time.time() * 1000))
    body = bytearray()
    body += f"--{boundary}\r\n".encode()
    body += (f'Content-Disposition: form-data; name="file"; '
             f'filename="{file.name}"\r\n').encode("utf-8")
    body += b"Content-Type: application/octet-stream\r\n\r\n"
    body += file.read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        _base() + path, data=bytes(body), method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


# ── 服务器生命周期 ──────────────────────────────────────────────────

def _find_python(repo: Path) -> str:
    """优先仓库内 venv，其次环境变量，最后 sys.executable。"""
    for cand in (repo / ".venv" / "bin" / "python3",
                 repo / "venv" / "bin" / "python3"):
        if cand.exists():
            return str(cand)
    return os.environ.get("BOOK2VIDO_PYTHON") or sys.executable


def cmd_start(args) -> int:
    repo = Path(args.repo).expanduser().resolve()
    if not (repo / "src" / "book2vido").exists():
        print(f"❌ 不像 book2vido 仓库: {repo}（找不到 src/book2vido）")
        return 2

    if PID_FILE.exists():
        old = int(PID_FILE.read_text().strip())
        try:
            os.kill(old, 0)
            port = int(PORT_FILE.read_text().strip())
            print(f"✅ GUI 已在运行 http://127.0.0.1:{port} (pid {old})")
            return 0
        except OSError:
            PID_FILE.unlink(missing_ok=True)

    port = args.port or _pick_port()
    py = _find_python(repo)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    log = open(STATE_DIR / "gui.log", "ab", buffering=0)
    proc = subprocess.Popen(
        [py, "-m", "book2vido.gui", "--port", str(port), "--no-browser"],
        cwd=str(repo), stdout=log, stderr=log, start_new_session=True)

    # 等就绪：轮询 /api/check-env
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            with urllib.request.urlopen(base + "/api/check-env", timeout=1) as r:
                json.loads(r.read().decode())
            break
        except Exception:
            if proc.poll() is not None:
                print("❌ GUI 进程已退出，看日志:")
                print((STATE_DIR / "gui.log").read_text()[-2000:])
                return 1
            time.sleep(0.5)
    else:
        print("❌ GUI 启动超时，看日志: " + str(STATE_DIR / "gui.log"))
        return 1

    PID_FILE.write_text(str(proc.pid))
    PORT_FILE.write_text(str(port))
    print(f"✅ GUI ready  http://127.0.0.1:{port}  (pid {proc.pid})")
    return 0


def cmd_stop(args) -> int:
    if not PID_FILE.exists():
        print("GUI 未在运行")
        return 0
    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, 15)
        print(f"🛑 stopped pid {pid}")
    except OSError as e:
        print(f"stop failed: {e}")
    PID_FILE.unlink(missing_ok=True)
    PORT_FILE.unlink(missing_ok=True)
    return 0


# ── 业务动作 ────────────────────────────────────────────────────────

def cmd_upload(args) -> int:
    f = Path(args.file).expanduser().resolve()
    if not f.exists():
        print(f"❌ 文件不存在: {f}")
        return 2
    r = _upload_multipart("/api/upload", f)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r.get("ok") else 1


def cmd_run(args) -> int:
    payload = {"path": args.path, "chapters": [], "voice": args.voice}
    if args.chapter is not None:
        payload["chapters"] = [args.chapter]
    r = _post("/api/run", payload)
    print(json.dumps(r, ensure_ascii=False))
    if not r.get("ok"):
        return 1
    job = r["job_id"]
    print(f"job_id={job}")
    deadline = time.time() + args.timeout
    last = -1
    while time.time() < deadline:
        st = _get(f"/api/status?job_id={job}")
        prog = st.get("progress", 0)
        if prog != last:
            print(f"  [{prog}%] {st.get('message','')}")
            last = prog
        if st.get("done"):
            print("✅ done")
            print(json.dumps(st.get("results", []), ensure_ascii=False, indent=2))
            return 0
        time.sleep(2)
    print("⏱ 超时（任务仍在后台跑，可用 status 继续查）")
    return 1


def cmd_status(args) -> int:
    st = _get(f"/api/status?job_id={args.job_id}")
    print(json.dumps(st, ensure_ascii=False, indent=2))
    return 0


def cmd_fetch(args) -> int:
    url = f"{_base()}/api/video/{args.name}"
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as r, open(out, "wb") as f:
        f.write(r.read())
    print(f"✅ saved {out}  ({out.stat().st_size // 1024} KB)")
    return 0


def cmd_auto(args) -> int:
    """一条龙：确保服务 → 上传 → 跑 → 下载成片。"""
    rc = cmd_start(argparse.Namespace(repo=args.repo, port=args.port))
    if rc != 0:
        return rc

    f = Path(args.file).expanduser().resolve()
    if not f.exists():
        print(f"❌ 文件不存在: {f}")
        return 2
    up = _upload_multipart("/api/upload", f)
    if not up.get("ok"):
        print("❌ upload 失败:", json.dumps(up, ensure_ascii=False))
        return 1
    print("✅ uploaded:", json.dumps(up, ensure_ascii=False)[:300])

    path = up.get("path") or up.get("file") or ""
    if not path:
        print("❌ upload 返回里没有 path 字段，无法继续")
        return 1

    payload = {"path": path, "chapters": [], "voice": args.voice}
    if args.chapter is not None:
        payload["chapters"] = [args.chapter]
    r = _post("/api/run", payload)
    if not r.get("ok"):
        print("❌ run 失败:", json.dumps(r, ensure_ascii=False))
        return 1
    job = r["job_id"]
    print(f"▶ job_id={job}")

    deadline = time.time() + args.timeout
    last = -1
    while time.time() < deadline:
        st = _get(f"/api/status?job_id={job}")
        prog = st.get("progress", 0)
        if prog != last:
            print(f"  [{prog}%] {st.get('message','')}")
            last = prog
        if st.get("done"):
            results = st.get("results", [])
            print("✅ done:", json.dumps(results, ensure_ascii=False)[:500])
            if not results:
                print("⚠️ 无产物")
                return 1
            name = results[0].get("file") or results[0].get("name")
            if not name:
                print("⚠️ results 里没有文件名")
                return 1
            out = args.out or f"./{Path(name).name}"
            return cmd_fetch(argparse.Namespace(name=name, out=out))
        time.sleep(2)
    print("⏱ 超时")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="book2vido CLI driver")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("start"); p.add_argument("--repo", default=DEFAULT_REPO)
    p.add_argument("--port", type=int); p.set_defaults(func=cmd_start)

    p = sub.add_parser("stop"); p.set_defaults(func=cmd_stop)

    p = sub.add_parser("upload"); p.add_argument("file")
    p.add_argument("--repo", default=DEFAULT_REPO); p.set_defaults(func=cmd_upload)

    p = sub.add_parser("run"); p.add_argument("path")
    p.add_argument("--chapter", type=int); p.add_argument("--voice")
    p.add_argument("--timeout", type=int, default=900)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("status"); p.add_argument("job_id")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("fetch"); p.add_argument("name"); p.add_argument("-o", "--out", required=True)
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("auto"); p.add_argument("file")
    p.add_argument("-o", "--out"); p.add_argument("--repo", default=DEFAULT_REPO)
    p.add_argument("--port", type=int); p.add_argument("--chapter", type=int)
    p.add_argument("--voice"); p.add_argument("--timeout", type=int, default=900)
    p.set_defaults(func=cmd_auto)

    args = ap.parse_args()
    if args.cmd in ("start", "auto") and not args.repo:
        print("❌ 需要 --repo（book2vido 仓库路径）或设环境变量 BOOK2VIDO_REPO")
        return 2
    try:
        return args.func(args)
    except urllib.error.URLError as e:
        print(f"❌ 连不上 GUI: {e}（先 `b2v.py start --repo ...`）")
        return 1


if __name__ == "__main__":
    sys.exit(main())
