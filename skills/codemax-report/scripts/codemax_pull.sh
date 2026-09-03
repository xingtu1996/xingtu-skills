#!/bin/bash
# ============================================================================
# codemax_pull.sh — 一键拉取 CodeMax 全维度数据（替代下载 CSV）
# 用法:
#   bash codemax_pull.sh                    # 本期(默认 8/14~今天) + 各期趋势 + 项目级
#   bash codemax_pull.sh -s 2026-08-01 -e 2026-08-28
#   bash codemax_pull.sh -s 2026-08-14 -e 2026-08-28 -o /path/to/dir
# 认证: 复用 settings.local.json env（CODEMAX_ADMIN_TOKEN + CODEMAX_ADMIN_USER）
# 输出: JSON 存 <输出目录>/  + 控制台摘要（直接用于汇报）
# ============================================================================
set -euo pipefail

# --- 参数 ---
START=""; END=""; OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    -s) START="$2"; shift 2;;
    -e) END="$2";   shift 2;;
    -o) OUT="$2";   shift 2;;
    *) echo "❌ 未知参数: $1"; exit 1;;
  esac
done
[ -n "$START" ] || START="$(date -v-14d +%Y-%m-%d)"
[ -n "$END" ]   || END="$(date +%Y-%m-%d)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SELF="$SCRIPT_DIR/codemax_stats.sh"
# 默认输出: 最近工作汇报数字目录（如 828/）
[ -n "$OUT" ] || OUT="$(ls -d /Users/lijiacheng/projects/tfm-ng/.report/工作汇报/[0-9]*/ 2>/dev/null | sort -rn | head -1 | tr -d '/')"
[ -n "$OUT" ] || OUT="."
mkdir -p "$OUT"
TAG="$(echo "$START-$END" | tr -d '-')"

echo "🔌 拉取 CodeMax 数据 [$START ~ $END] → $OUT/"

# --- 本期核心 ---
bash "$SELF" summary -s "$START" -e "$END" > "$OUT/codemax_summary_$TAG.json"
bash "$SELF" users   -s "$START" -e "$END" > "$OUT/codemax_users_$TAG.json"
bash "$SELF" models  -s "$START" -e "$END" > "$OUT/codemax_models_$TAG.json"

# --- 项目级（半年） ---
bash "$SELF" pm-projects --sort-cost -s 2026-03-01 -e "$END" > "$OUT/codemax_projects_$TAG.json"

# --- 趋势各期（对齐四期趋势图；curl 输出无换行，需补 \n） ---
TREND="$OUT/codemax_trend_$TAG.jsonl"
: > "$TREND"
for r in "2026-07-01 2026-07-15" "2026-07-15 2026-07-30" "2026-07-30 2026-08-14" "$START $END"; do
  s=$(echo $r|cut -d' ' -f1); e=$(echo $r|cut -d' ' -f2)
  bash "$SELF" summary -s "$s" -e "$e" >> "$TREND"
  echo >> "$TREND"
done

# --- 摘要 ---
python3 - "$START" "$END" "$OUT" "$TAG" "$SCRIPT_DIR" <<'PY'
import json,sys,os,glob
START,END,OUT,TAG,SCRIPT_DIR=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5]
def load(f):
    try:return json.load(open(f,encoding='utf-8'))
    except:return None
s=load(f"{OUT}/codemax_summary_{TAG}.json") or {}
u=load(f"{OUT}/codemax_users_{TAG}.json") or {}
m=load(f"{OUT}/codemax_models_{TAG}.json") or {}
p=load(f"{OUT}/codemax_projects_{TAG}.json") or {}
d=s.get('data',{})
print("\n========== CodeMax 数据摘要 ==========")
print(f"区间: {START} ~ {END}")
if d:
    print(f"活跃用户: {d.get('total_users')} | 请求: {d.get('total_count'):,} | token: {d.get('total_tokens')/1e8:.1f}亿 | 费用: ¥{d.get('total_cost'):,.0f} | 次均: ¥{d.get('total_cost')/d.get('total_count',1):.4f}")
uds=sorted(u.get('data',[]),key=lambda x:-x.get('count',0))
if uds:
    print("\n用户 TOP10:")
    for i,x in enumerate(uds[:10],1):
        print(f"  {i:2}. {x.get('username','?'):14} {x.get('count',0):7,}次  ¥{x.get('total_cost',0):7.0f}")
md=sorted(m.get('data',[]),key=lambda x:-x.get('count',0))
if md:
    tot=sum(x.get('count',0) for x in md)
    print("\n模型:")
    for x in md[:5]:
        print(f"  {x.get('model_name','?'):22} {x.get('count',0):7,}次({x.get('count',0)/tot*100:.0f}%) ¥{x.get('total_cost',0):6.0f}")
pi=p.get('data',{}).get('items',[])
if pi:
    print("\n项目 TOP5 (半年):")
    for x in pi[:5]:
        print(f"  {x.get('project_name','?')[:28]:28} {x.get('total_tokens',0)/1e6:6.0f}M tok  ¥{x.get('total_cost',0):7.0f}")

# --- 广分维度（较上次对比，维护在用/渗透/请求变化） ---
try:
    roster=[]
    for line in open(f"{SCRIPT_DIR}/gz_roster.txt",encoding="utf-8"):
        line=line.rstrip()
        if line and not line.startswith("#") and "|" in line:
            p=line.split("|")
            if len(p)>=2: roster.append(p[1].strip())
    uu=u.get('data',[])
    unames={x.get("username") for x in uu}
    gz=[r for r in roster if r in unames]
    gz_req=sum(x.get("count",0) for x in uu if x.get("username") in set(gz))
    rate=round(len(gz)/len(roster)*100)
    try:
        base=json.load(open(f"{SCRIPT_DIR}/gz_baseline.json",encoding="utf-8"))
        d_req=(gz_req/base.get('requests',1)-1)*100
        delta=f"较上次({base.get('date','?')}): 在用 {base.get('active')}→{len(gz)} | 渗透 {base.get('rate')}%→{rate}% | 请求 {base.get('requests')/10000:.1f}万→{gz_req/10000:.1f}万 {d_req:+.0f}%"
    except: delta="暂无上次基准"
    print(f"\n广分维度: 在用 {len(gz)}/{len(roster)} ({rate}%) | 请求 {gz_req:,} | {delta}")
except Exception as e:
    pass

# --- 四期趋势（从 trend JSONL 解析，API 维护，不写死） ---
tf=f"{OUT}/codemax_trend_{TAG}.jsonl"
labels=["7/15 一期(7/1~7/15)","7/30 二期","8/14 三期",f"{START}~{END} 四期"]
if os.path.exists(tf):
    print("\n四期趋势（API 取数）:")
    print(f"{'期':22} {'在用':>4} {'请求':>10} {'token':>8} {'费用':>8} {'次均':>7}")
    for i,line in enumerate(open(tf,encoding='utf-8')):
        try: d=json.loads(line)['data']
        except: continue
        lbl=labels[i] if i<len(labels) else f"区间{i}"
        print(f"{lbl:22} {d.get('total_users',0):>4} {d.get('total_count',0):>10,} {d.get('total_tokens',0)/1e8:>6.1f}亿 ¥{d.get('total_cost',0):>6,.0f} ¥{d.get('total_cost',0)/d.get('total_count',1):>6.4f}")
print("\nJSON 已存:", [f for f in ['codemax_summary','codemax_users','codemax_models','codemax_projects','codemax_trend'] if os.path.exists(f"{OUT}/{f}_{TAG}.json") or os.path.exists(f"{OUT}/{f}_{TAG}.jsonl")])
print("========== 完 ==========")
PY
