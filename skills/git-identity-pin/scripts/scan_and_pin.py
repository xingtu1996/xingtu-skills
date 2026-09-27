#!/usr/bin/env python3
"""git-identity-pin: 扫描目录树下 git 仓库，按业务域钉死 local 提交身份。

只改 .git/config 的 local user.name/email，不动 commit 历史、不 push。
local 优先于 global：写 local 即固定，不受全局改动影响。

两种目标解析模式：
  A. 无 --mapfile：目标 = 全局 user.name/email（或 --name/--email），--skip 前缀跳过
  B. 有 --mapfile：按 JSON 规则匹配仓库相对路径前缀，命中取该规则身份；都不中取 default
"""
import os, subprocess, json, argparse, sys

def git(d, args, timeout=20):
    try:
        r = subprocess.run(["git", "-C", d] + args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return 1, "", str(e)

def find_git_roots(top):
    roots = []
    for dp, dn, fn in os.walk(top):
        if ".git" in dn:
            roots.append(dp)
            dn.remove(".git")
            dn[:] = [x for x in dn if not x.startswith(".git")]
    return roots

def load_map(path):
    with open(path) as f:
        m = json.load(f)
    assert "default" in m and "rules" in m, "mapfile 需含 default + rules"
    return m

def match_pat(rel, pat):
    """pat 既可作路径前缀(crv-local/)，也可作仓库名/basename 前缀(crv-)。"""
    pat = pat.rstrip("/")
    if rel == pat or rel.startswith(pat + "/"):
        return True
    base = os.path.basename(rel)
    if base == pat or base.startswith(pat):
        return True
    return False

def resolve_via_map(rel, m):
    for rule in m["rules"]:
        for pat in rule.get("match", []):
            if match_pat(rel, pat):
                return rule
    return m["default"]

def main():
    ap = argparse.ArgumentParser(description="扫描并钉死 git 仓库 local 提交身份")
    ap.add_argument("--root", required=True, help="扫描根目录")
    ap.add_argument("--audit", action="store_true", help="只读审计（默认）")
    ap.add_argument("--pin", action="store_true", help="钉死模式")
    ap.add_argument("--name", help="模式A 目标 name；省略读全局")
    ap.add_argument("--email", help="模式A 目标 email；省略读全局")
    ap.add_argument("--skip", nargs="*", default=[], help="模式A 跳过前缀")
    ap.add_argument("--mapfile", help="模式B 业务域映射 JSON（default+rules）")
    ap.add_argument("--dry-run", action="store_true", help="只报告不改写")
    ap.add_argument("--report", help="JSON 报告输出路径")
    args = ap.parse_args()

    use_map = bool(args.mapfile)
    if use_map:
        m = load_map(args.mapfile)
        def target_of(rel):
            r = resolve_via_map(rel, m)
            return r.get("name", ""), r.get("email", ""), bool(r.get("skip", False))
    else:
        if args.name and args.email:
            tgt_name, tgt_email = args.name, args.email
        else:
            _, gn, _ = git(os.path.expanduser("~"), ["config", "--global", "user.name"])
            _, ge, _ = git(os.path.expanduser("~"), ["config", "--global", "user.email"])
            tgt_name, tgt_email = gn or "", ge or ""
        if not tgt_email:
            print("ERROR: 目标 email 缺失（需 --email 或全局已配置 user.email）", file=sys.stderr)
            sys.exit(2)
        def target_of(rel):
            skip = any(rel == s or rel.startswith(s + os.sep) for s in args.skip)
            return tgt_name, tgt_email, skip

    roots = find_git_roots(args.root)
    rootset = set(roots)
    top_roots = [r for r in roots if os.path.dirname(r) not in rootset]

    repos = []
    for r in top_roots:
        rel = os.path.relpath(r, args.root)
        tname, temail, tskip = target_of(rel)
        _, le, _ = git(r, ["config", "--get", "user.email"])
        _, ln, _ = git(r, ["config", "--get", "user.name"])
        hist = git(r, ["log", "--all", "--format=%ae|%an"])[1]
        emails, names = set(), set()
        for line in hist.splitlines():
            if "|" in line:
                ae, an = line.split("|", 1)
                emails.add(ae.strip()); names.add(an.strip())
        repos.append({
            "path": rel, "local_email": le, "local_name": ln,
            "target_email": temail, "target_name": tname, "skip": tskip,
            "hist_emails": sorted(emails), "hist_names": sorted(names),
        })

    if args.audit or not args.pin:
        for r in repos:
            flag = " [SKIP]" if r["skip"] else ""
            matched = "OK " if r["local_email"] == r["target_email"] else "MIS"
            print(f"{matched} {r['path']}{flag}")
            print(f"    local: {r['local_name']!r} <{r['local_email']}>  target={r['target_email']}")
            if r["hist_emails"]:
                print(f"    hist:  {r['hist_emails']}")
        mismatch = sum(1 for r in repos if not r["skip"] and r["local_email"] != r["target_email"])
        print(f"\n审计完毕：{len(repos)} 仓，非 skip 中身份不符目标 = {mismatch}")
    else:
        done, skipped, failed = [], [], []
        for r in repos:
            if r["skip"]:
                skipped.append(r["path"]); continue
            if r["local_email"] == r["target_email"]:
                skipped.append(r["path"]); continue
            if args.dry_run:
                done.append((r["path"], r["local_email"], r["target_email"])); continue
            rc1, _, e1 = git(r, ["config", "user.name", r["target_name"]])
            rc2, _, e2 = git(r, ["config", "user.email", r["target_email"]])
            if rc1 == 0 and rc2 == 0:
                done.append((r["path"], r["local_email"], r["target_email"]))
            else:
                failed.append((r["path"], e1 or e2))
        tag = "（dry-run）" if args.dry_run else ""
        print(f"钉死{tag}成功: {len(done)}")
        for p, old, new in done:
            print(f"  {p}  ({old} -> {new})")
        print(f"跳过(已是目标或 skip): {len(skipped)}")
        print(f"失败: {len(failed)}")
        for p, e in failed:
            print(f"  {p}: {e}")

    if args.report:
        with open(args.report, "w") as f:
            json.dump({"repos": repos}, f, ensure_ascii=False, indent=2)
        print(f"\n报告已写 {args.report}")

if __name__ == "__main__":
    main()
