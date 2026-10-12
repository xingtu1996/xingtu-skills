#!/usr/bin/env bash
# check-terms.sh —— 术语文档门禁自检（定稿/对外前跑一遍）
#
# 用法:
#   bash check-terms.sh <术语文档>
#   bash check-terms.sh -h
#
# 退出码: 0 = 全部通过 / 1 = 有 ❌ / 2 = 用法或环境错误
#
# 检查项（逐项 ✅/❌）:
#   ① 存在术语表本身（没有表 = 没东西可查，不判通过）
#   ② 含版本历史表
#   ③ 含「怎么用」首屏，且在术语表之前（读者先知道怎么用，再读词条）
#   ④ 每条术语行含出处与置信度标记 🟢/🟡/🔴
#   ⑤ 无重复定义（同一术语名只出现一次定义行）
#   ⑥ 无遗留占位符（[待填] / TODO / [一句话说明] …）
#   ⑦ 文档里引用的图文件真实存在
#   ⑧ 🔴 条目不出现在标注为「对外」的章节
#
# 为什么这么写（改之前先读）:
#   ① **"查不了"不等于"没问题"**。解析不出术语表、找不到可查的行，一律判 ❌ 并说明——
#      零可查项时报"全部通过"就是假绿，而门禁一旦假绿，整份表就没人再信了。
#   ② 置信度分级是这份表的价值来源：🟢 可直引 / 🟡 会变，用前复核 / 🔴 仅推断。
#      🔴 混进对外章节 = 拿没核实的东西对外承诺，这是最贵的一类错，所以单列一条检查。
#   ③ 表格解析**按表头名找列**，不按列号——列序会变，写死列号换一份文档就静默解错。
#   ④ 代码围栏内的内容不算文档内容（示例里的 TODO 是示例，不是遗留占位符），
#      否则每次写"怎么用"里的示例都会被误判 → 假红也会让门禁失去信任。
#   ⑤ 全部用字节级匹配（bash case / grep -F），**不用 awk 比较字符串**——
#      macOS 自带 BWK awk 对非 ASCII 的比较是坏的（不同中文会判相等），拿它判断 = 静默漏判。
#   ⑥ 零依赖：只用 grep/sed/find，不碰 node/python3（CI Shell executor 上可能没有，
#      实测踩过用 python3 解析导致假红的坑）。

set -euo pipefail

die() { printf '❌ %s\n' "$*" >&2; exit 2; }

trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

usage() {
  awk 'NR>1 && /^#/ { sub(/^# ?/, ""); print; next } NR>1 { exit }' "$0"
  exit 0
}

case "${1:-}" in -h|--help) usage ;; esac
[ $# -ge 1 ] || die "参数不够。用法：bash check-terms.sh <术语文档>"
[ $# -le 1 ] || die "多给了参数（一次查一份）：$2"
DOC="$1"; [ -f "$DOC" ] || die "术语文档不存在：$DOC"
DOC_DIR="$(cd "$(dirname "$DOC")" && pwd)"

NL=$'\n'

# ── 单遍扫描 ───────────────────────────────────────────────
ver_ok=0;        ver_line=0
in_ver=0
usage_line=0
first_term_row=0
cur_head=""
in_fence=0
state=0                      # 0=表外 1=术语表数据区 2=别的表
col_term=-1; col_src=-1
table_no_src=0               # 首个「没有出处列」的表的数据行行号
term_rows=0
seen="${NL}"
dups=""
no_src=""
no_conf=""
red_pub=""
ph_hits=""
lineno=0

while IFS= read -r line || [ -n "$line" ]; do
  lineno=$((lineno + 1))

  # (0) 代码围栏：里面的东西不算文档内容
  case "$line" in
    '```'*|'~~~'*)
      if [ "$in_fence" -eq 0 ]; then in_fence=1; else in_fence=0; fi
      continue ;;
  esac
  if [ "$in_fence" -eq 1 ]; then continue; fi

  # (6) 占位符（在表格之前查，表格里的占位符同样要抓）
  case "$line" in
    *'[待填]'*|*'[一句话说明]'*|*'[待补]'*|*'[待核实]'*|*'<待填>'*|*TODO*|*TBD*|*FIXME*)
      ph_hits="$ph_hits$lineno|$(trim "$line")"$'\n' ;;
  esac

  # (2)(3) 标题
  case "$line" in
    '#'*)
      h="$line"
      while [ "${h#\#}" != "$h" ]; do h="${h#\#}"; done
      cur_head="$(trim "$h")"
      case "$cur_head" in
        *版本历史*) in_ver=1 ;;
        *)          in_ver=0 ;;
      esac
      case "$cur_head" in
        *怎么用*|*用法*|*使用说明*|*如何用*)
          if [ "$usage_line" -eq 0 ]; then usage_line=$lineno; fi ;;
      esac
      state=0
      continue ;;
  esac

  # (2) 版本历史表：标题后出现带「版本号」的表头行即算数
  if [ "$in_ver" -eq 1 ] && [ "$ver_ok" -eq 0 ]; then
    case "$line" in *版本号*) ver_ok=1; ver_line=$lineno ;; esac
  fi

  # (1)(4)(5)(8) 术语表
  case "$line" in
    '|'*'|') ;;
    *) state=0; continue ;;
  esac

  if printf '%s' "$line" | grep -qE '^\|[[:space:]:|-]+\|$'; then continue; fi

  row="${line#|}"; row="${row%|}"
  IFS='|' read -r -a cells <<< "$row"
  for i in "${!cells[@]}"; do cells[$i]="$(trim "${cells[$i]}")"; done

  if [ "$state" -eq 0 ]; then
    col_term=-1; col_src=-1
    for i in "${!cells[@]}"; do
      case "${cells[$i]}" in
        术语)         col_term=$i ;;
        出处|来源|依据) col_src=$i ;;
      esac
    done
    if [ "$col_term" -ge 0 ]; then state=1; else state=2; fi
    continue
  fi
  [ "$state" -eq 1 ] || continue

  term="$(trim "${cells[$col_term]:-}")"
  [ -n "$term" ] || continue
  term_rows=$((term_rows + 1))
  if [ "$first_term_row" -eq 0 ]; then first_term_row=$lineno; fi

  # (4) 置信度标记
  row_conf=""
  case "$line" in
    *🟢*) row_conf="🟢" ;;
    *🟡*) row_conf="🟡" ;;
    *🔴*) row_conf="🔴" ;;
  esac
  if [ -z "$row_conf" ]; then no_conf="$no_conf$lineno:$term"$'\n'; fi

  # (4) 出处
  if [ "$col_src" -ge 0 ]; then
    if [ -z "$(trim "${cells[$col_src]:-}")" ]; then no_src="$no_src$lineno:$term"$'\n'; fi
  else
    if [ "$table_no_src" -eq 0 ]; then table_no_src=$lineno; fi
  fi

  # (5) 重复定义
  case "$seen" in
    *"${NL}${term}${NL}"*) dups="$dups$lineno:$term"$'\n' ;;
    *) seen="$seen$term$NL" ;;
  esac

  # (8) 🔴 不出现在「对外」章节
  if [ "$row_conf" = "🔴" ]; then
    case "$cur_head" in
      # ⚠️ 紧跟着多字节字符的变量名必须带花括号，否则 bash 会把「（」的头几个字节吞进变量名
      *对外*) red_pub="${red_pub}${lineno}:${term}（章节：${cur_head}）"$'\n' ;;
    esac
  fi
done < "$DOC"

# ── (7) 引用的图文件是否存在 ──────────────────────────────
REFS="$(grep -oE '\]\([^)]+\)' "$DOC" 2>/dev/null | sed 's/^](//; s/)$//' | LC_ALL=C sort -u || true)"
N_REF=0; missing=""
while IFS= read -r p; do
  [ -n "$p" ] || continue
  case "$p" in http://*|https://*|mailto:*|'#'*) continue ;; esac
  p="${p%%#*}"
  case "$p" in *.svg|*.png|*.jpg|*.jpeg|*.webp|*.gif|*.mmd|*.drawio) ;; *) continue ;; esac
  N_REF=$((N_REF + 1))
  case "$p" in /*) target="$p" ;; *) target="$DOC_DIR/$p" ;; esac
  if [ ! -e "$target" ]; then missing="$missing$p"$'\n'; fi
done <<< "$REFS"

# ── 报告 ───────────────────────────────────────────────────
FAIL=0
echo "术语文档：$DOC"
echo "────────────────────────────────────────"

if [ "$term_rows" -gt 0 ]; then
  printf '✅ ① 术语表存在            数据行 %d 条\n' "$term_rows"
else
  printf '❌ ① 没解析出术语表        —— 没有表就没东西可查，不判通过。\n'
  printf '                          期望表头含「术语」列：| 术语 | 定义 | 出处 | 置信度 |\n'
  FAIL=1
fi

if [ "$ver_ok" -eq 1 ]; then
  printf '✅ ② 版本历史表            第 %d 行\n' "$ver_line"
else
  printf '❌ ② 缺版本历史表          —— 术语文档每次变更都要留痕（改了什么 + 为什么），\n'
  printf '                          否则下次没人知道某个定义是什么时候、因何改的\n'
  FAIL=1
fi

if [ "$usage_line" -eq 0 ]; then
  printf '❌ ③ 缺「怎么用」首屏      —— 开头要说清楚：谁在什么时候、怎么查这份表\n'
  FAIL=1
elif [ "$first_term_row" -gt 0 ] && [ "$usage_line" -gt "$first_term_row" ]; then
  printf '❌ ③ 「怎么用」不在首屏    第 %d 行，在术语表（第 %d 行）之后\n' "$usage_line" "$first_term_row"
  printf '                          读者一上来就看词条，不知道这份表怎么用、什么时候查\n'
  FAIL=1
elif [ "$first_term_row" -eq 0 ]; then
  printf '✅ ③ 首屏「怎么用」        第 %d 行（本文档没解析出术语表，位置无从比较）\n' "$usage_line"
else
  printf '✅ ③ 首屏「怎么用」        第 %d 行（术语表从第 %d 行才开始）\n' "$usage_line" "$first_term_row"
fi

# ④ 拆成三条独立判定，**只有全部通过才打一个 ✅**——
#    否则会出现「✅ 出处 + 置信度」和「❌ 没有出处列」同时挂着的自相矛盾报告
if [ "$term_rows" -eq 0 ]; then
  printf '⏭ ④ 出处 + 置信度         无术语表，本项无从检查（**不算通过**）\n'
elif [ "$no_conf" = "" ] && [ "$table_no_src" -eq 0 ] && [ "$no_src" = "" ]; then
  printf '✅ ④ 出处 + 置信度         每条术语行都带 🟢/🟡/🔴 与出处\n'
else
  if [ "$no_conf" != "" ]; then
    printf '❌ ④ 缺置信度标记 %d 条     —— 没标 = 读的人不知道能不能直接引用\n' "$(printf '%s' "$no_conf" | grep -c . || true)"
    printf '%s' "$no_conf" | sed 's/^/                          行 /'
  fi
  if [ "$table_no_src" -gt 0 ]; then
    printf '❌ ④ 术语表没有「出处」列  第 %d 行起\n' "$table_no_src"
    printf '                          —— 每个定义都要能追溯到谁说的/哪份文件，否则无法复核\n'
  elif [ "$no_src" != "" ]; then
    printf '❌ ④ 有 %d 条出处为空       —— 无出处的定义等于"我说的"，不能进知识库\n' "$(printf '%s' "$no_src" | grep -c . || true)"
    printf '%s' "$no_src" | sed 's/^/                          行 /'
  fi
  FAIL=1
fi

if [ "$term_rows" -eq 0 ]; then
  printf '⏭ ⑤ 无重复定义            无术语表，本项无从检查（**不算通过**）\n'
elif [ "$dups" = "" ]; then
  printf '✅ ⑤ 无重复定义\n'
else
  printf '❌ ⑤ 同一术语出现多次定义  —— 一个词两个定义，写材料时各取所需就乱了\n'
  printf '%s' "$dups" | sed 's/^/                          行 /'
  FAIL=1
fi

if [ "$ph_hits" = "" ]; then
  printf '✅ ⑥ 无遗留占位符\n'
else
  printf '❌ ⑥ 有遗留占位符 %d 处\n' "$(printf '%s' "$ph_hits" | grep -c . || true)"
  printf '%s' "$ph_hits" | sed 's/^/                          /'
  FAIL=1
fi

if [ "$missing" = "" ]; then
  printf '✅ ⑦ 引用的图文件存在      （本地图片/图形引用 %d 处）\n' "$N_REF"
else
  printf '❌ ⑦ 引用的图文件不存在    —— 断链的图，读者看到的是空白\n'
  printf '%s' "$missing" | sed 's/^/                          /'
  FAIL=1
fi

if [ "$term_rows" -eq 0 ]; then
  printf '⏭ ⑧ 🔴 未出现在对外章节    无术语表，本项无从检查（**不算通过**）\n'
elif [ "$red_pub" = "" ]; then
  printf '✅ ⑧ 🔴 未出现在对外章节\n'
else
  printf '❌ ⑧ 🔴 条目进了「对外」章节 —— 🔴 = 仅推断、未核实，对外承诺最贵的一类错\n'
  printf '%s' "$red_pub" | sed 's/^/                          /'
  FAIL=1
fi

echo "────────────────────────────────────────"
if [ "$FAIL" -eq 0 ]; then
  echo "✅ 全部通过"
  exit 0
fi
echo "❌ 未通过——修完再定稿/对外"
exit 1
