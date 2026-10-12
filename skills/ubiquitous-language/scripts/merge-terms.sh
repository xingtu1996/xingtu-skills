#!/usr/bin/env bash
# merge-terms.sh —— 把多个来源的抽取结果并成一份术语表（带冲突检测，绝不静默择一）
#
# 用法:
#   bash merge-terms.sh <抽取结果1> <抽取结果2> [...] [--out <文件>]
#   bash merge-terms.sh -h
#
# 退出码: 0 = 合并完成、无冲突 / 1 = 检出冲突（必须人来裁决）/ 2 = 用法或契约错误
#
# 输入契约（统一格式，缺 术语/定义 列 = 报错，不猜）:
#   | 术语 | 英文/别名 | 定义 | 出处 | 置信度 |
#   |------|-----------|------|------|:--:|
#   | 结算日 | Settlement Date | 资金实际划转的那天 | 《需求 v2》§3 | 🟢 |
#   必填列：术语、定义；可选列：英文/别名、出处、置信度。列序随意——按表头名找列，不按位置。
#
# 为什么这么写（改之前先读）:
#   ① **按表头名找列，不按列序**。表格列序因来源而异，写死列号 = 换一份结果就静默解错，
#      比报错更危险（本技能的红线就是"不静默"）。
#   ② **同一术语定义不一致 → 单列出来，不挑一条**。挑哪条都是替人做业务裁决；
#      两份材料对同一个词理解不同，本身就是这条术语最大的风险信号，藏起来等于埋雷。
#   ③ 解析不出词条 = 报错退出。词条数为 0 时继续"合并成功"必然输出空表，那是假绿。
#   ④ 拆分与比较全走 bash（字节级），awk 只用来"打印行"。
#      macOS 自带 BWK awk 对非 ASCII 的比较是坏的（不同中文被判相等），拿它分组会合并错词条。
#   ⑤ 不用关联数组 —— macOS 自带 bash 3.2 没有 `declare -A`，用了就是换台机器直接崩。
#      分组靠"先排序、再顺序扫描"，线性且可移植。
#   ⑥ 零依赖：只用 sort/cut/sed/grep，不碰 node/python3（CI Shell executor 上可能没有）。

set -euo pipefail

die() { printf '❌ %s\n' "$*" >&2; exit 2; }

trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

# 去掉行尾句读（一个字一个字地摘，用字面量做模式，不用 ${s%?}）
# 为什么不用 *[。.;；、,，] ＋ ${s%?}：
#   ① bash 的 case 模式里**方括号里放多字节字符会直接把语法解析打断**
#      （实测：`*[。.;；、,，])` 报 syntax error near unexpected token `;'），脚本根本起不来
#   ② ${s%?} 删的是"一个字符"，在 LC_ALL=C 下退化成"一个字节"，中文会被削掉半个字
strip_tail() {
  local s="$1"
  case "$s" in
    *"。") printf '%s' "${s%。}"; return 0 ;;
    *".")  printf '%s' "${s%.}";  return 0 ;;
    *"，") printf '%s' "${s%，}"; return 0 ;;
    *",")  printf '%s' "${s%,}";  return 0 ;;
    *"；") printf '%s' "${s%；}"; return 0 ;;
    *";")  printf '%s' "${s%;}";  return 0 ;;
    *"、") printf '%s' "${s%、}"; return 0 ;;
    *)     printf '%s' "$s";      return 1 ;;
  esac
}

# 定义归一化：前后空白 + 行尾句读差异不算"冲突"，否则满屏假冲突把真冲突淹了
norm_def() {
  local s
  s="$(trim "$1")"
  while :; do
    local t
    t="$(strip_tail "$s")"
    [ "$t" = "$s" ] && break
    s="$t"
  done
  printf '%s' "$(trim "$s")"
}

esc_pipe() { printf '%s' "$1" | sed 's/|/\\|/g'; }

usage() {
  awk 'NR>1 && /^#/ { sub(/^# ?/, ""); print; next } NR>1 { exit }' "$0"
  exit 0
}

# ── 参数解析 ───────────────────────────────────────────────
FILES=(); OUT=""
case "${1:-}" in -h|--help) usage ;; esac
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage ;;
    --out) OUT="${2:-}"; [ -n "$OUT" ] || die "--out 后面要跟文件名"; shift ;;
    -*) die "未知参数：$1（-h 看用法）" ;;
    *) FILES+=("$1") ;;
  esac
  shift
done

[ "${#FILES[@]}" -ge 1 ] || { usage; exit 2; }
for f in "${FILES[@]}"; do [ -f "$f" ] || die "抽取结果文件不存在：$f"; done

# ── 解析：逐文件抽记录，格式 term<SEP>def<SEP>origin<SEP>conf<SEP>en<SEP>src ──
#
# ⚠️ 分隔符用「单元分隔符」$'\x1f'，**不能用 tab**。tab 属于 IFS 空白字符，
#    `IFS=$'\t' read` 会把连续的分隔符当"一个"，中间的空列被整列吃掉、后面的列集体左移
#    （实测：a\tb\t\t\tc 读成 o=c 而不是 o= 空）。来源文件少一个可选列时就静默串列，
#    而串列后的输出看起来完全正常 —— 典型的静默错误。
#    $'\x1f' 是非空白控制字符，每个出现都严格切一刀，空列原样保留。
SEP=$'\x1f'
RECORDS=""

parse_file() {
  local file="$1" src; src="$(basename "$file")"
  local line="" row="" i=0 c=""
  local -a cells=()
  local state=0            # 0=表外 1=术语表数据区 2=别的表（跳过）
  local col_term=-1 col_def=-1 col_org=-1 col_conf=-1 col_en=-1
  local rows=0 lineno=0

  while IFS= read -r line || [ -n "$line" ]; do
    lineno=$((lineno + 1))

    case "$line" in
      '|'*'|') ;;
      *) state=0; continue ;;
    esac

    # 分隔行 |---|---|：只是排版，不是数据
    if printf '%s' "$line" | grep -qE '^\|[[:space:]:|-]+\|$'; then continue; fi

    row="${line#|}"; row="${row%|}"
    IFS='|' read -r -a cells <<< "$row"
    for i in "${!cells[@]}"; do cells[$i]="$(trim "${cells[$i]}")"; done

    if [ "$state" -eq 0 ]; then
      # 每张表的第一行当表头；找不到「术语」列 = 这张表不是术语表，整张跳过
      col_term=-1; col_def=-1; col_org=-1; col_conf=-1; col_en=-1
      for i in "${!cells[@]}"; do
        c="${cells[$i]}"
        case "$c" in
          术语)        col_term=$i ;;
          定义|说明|含义) col_def=$i ;;
          出处|来源)    col_org=$i ;;
          置信度|置信)  col_conf=$i ;;
          英文|英文名|别名|英文/别名) col_en=$i ;;
        esac
      done
      if [ "$col_term" -ge 0 ] && [ "$col_def" -ge 0 ]; then state=1
      elif [ "$col_term" -ge 0 ]; then
        die "$file:$lineno 术语表缺少「定义」列——没有定义就无从检测冲突。
   期望表头（列序随意）：
     | 术语 | 英文/别名 | 定义 | 出处 | 置信度 |"
      else
        state=2
      fi
      continue
    fi

    [ "$state" -eq 1 ] || continue

    local term def org conf en
    term="$(trim "${cells[$col_term]:-}")"
    def="$(norm_def "${cells[$col_def]:-}")"
    org="";  [ "$col_org"  -ge 0 ] && org="$(trim "${cells[$col_org]:-}")"
    conf=""; [ "$col_conf" -ge 0 ] && conf="$(trim "${cells[$col_conf]:-}")"
    en="";   [ "$col_en"   -ge 0 ] && en="$(trim "${cells[$col_en]:-}")"

    [ -n "$term" ] || continue
    if [ -z "$def" ]; then
      printf '⚠️  %s:%s 「%s」没有定义——已保留，但冲突检测对它无效\n' "$file" "$lineno" "$term" >&2
    fi

    RECORDS="$RECORDS$term$SEP$def$SEP$org$SEP$conf$SEP$en$SEP$src"$'\n'
    rows=$((rows + 1))
  done < "$file"

  printf '    %-40s %d 条\n' "$src" "$rows" >&2
  [ "$rows" -gt 0 ] || printf '⚠️  %s 解析出 0 条——这份抽取结果是不是没按契约出表？\n' "$src" >&2
}

printf '解析输入：\n' >&2
for f in "${FILES[@]}"; do parse_file "$f"; done

TOTAL="$(printf '%s' "$RECORDS" | grep -c . || true)"
[ "$TOTAL" -gt 0 ] || die "所有输入加起来 0 条词条——拒绝输出空表当成功（空表合并完必然\"无冲突\"，那是假绿）"

# ── 分组：先排序（术语→定义），再顺序扫描合并来源 ──────────
# 排序用 LC_ALL=C：分组只看"相同串是否相邻"，与语序无关，但固定成字节序可避免换 locale 后行为漂移
SORTED="$(printf '%s' "$RECORDS" | LC_ALL=C sort -t"$SEP" -k1,1 -k2,2)"

ROWS=""
cur_key=""; ct=""; cd=""; co=""; cc=""; ce=""; cs=""
flush_row() {
  [ -n "$ct" ] || return 0
  ROWS="$ROWS$ct$SEP$cd$SEP$co$SEP$cc$SEP$ce$SEP$cs"$'\n'
}

while IFS="$SEP" read -r t d o c e s; do
  [ -n "$t" ] || continue
  key="$t$SEP$d"
  if [ "$key" != "$cur_key" ]; then
    flush_row
    ct="$t"; cd="$d"; co="$o"; cc="$c"; ce="$e"; cs="$s"; cur_key="$key"
  else
    case ",$cs," in *",$s,"*) ;; *) cs="$cs,$s" ;; esac    # 同一 (术语,定义) 的来源合并，不重复列
  fi
done <<< "$SORTED"
flush_row

# 同一术语出现 ≥2 行 = 有 ≥2 种定义 = 冲突
CONFLICT_TERMS="$(printf '%s' "$ROWS" | LC_ALL=C cut -d"$SEP" -f1 | LC_ALL=C uniq -d)"
NL=$'\n'
CONFLICT_INDEX="${NL}${CONFLICT_TERMS}${NL}"

# ── 渲染 ───────────────────────────────────────────────────
TABLE=""; CONFLICTS=""; last_conf_term=""; n_conf=0

# 空单元格统一补 —：留白会被读成"漏解析"，而"没这项"和"解析失败"是两回事
cell() { if [ -n "$1" ]; then printf '%s' "$1"; else printf '—'; fi; }

while IFS="$SEP" read -r t d o c e s; do
  [ -n "$t" ] || continue

  is_conf=0
  case "$CONFLICT_INDEX" in *"${NL}${t}${NL}"*) is_conf=1 ;; esac

  state_cell="✅"
  if [ "$is_conf" -eq 1 ]; then
    state_cell="⚠️ 冲突"
    if [ "$t" != "$last_conf_term" ]; then
      CONFLICTS="$CONFLICTS"$'\n'"### ⚔ $t"$'\n'
      last_conf_term="$t"; n_conf=$((n_conf + 1))
    fi
    CONFLICTS="$CONFLICTS- 定义：「$(esc_pipe "$d")」 ← 来源：$s"$'\n'
  fi

  TABLE="$TABLE| $(esc_pipe "$t") | $(esc_pipe "$(cell "$e")") | $(esc_pipe "$(cell "$d")") | $(esc_pipe "$(cell "$o")") | $(esc_pipe "$(cell "$c")") | $s | $state_cell |"$'\n'
done <<< "$ROWS"

N_TERM="$(printf '%s' "$ROWS" | LC_ALL=C cut -d"$SEP" -f1 | LC_ALL=C uniq | grep -c . || true)"

DOC_TXT="$(cat <<EOF
# 合并后的术语表

> 由 merge-terms.sh 生成 · 术语 $N_TERM 个 · 定义行 $TOTAL 条 · 来源 ${#FILES[@]} 份
> 状态列 ⚠️ 冲突 = 同一术语在不同来源里定义不一致，**必须人工裁决后再定稿**。

| 术语 | 英文/别名 | 定义 | 出处 | 置信度 | 来源 | 状态 |
|------|-----------|------|------|:--:|------|:--:|
$TABLE
EOF
)"

if [ "$n_conf" -gt 0 ]; then
  # 命令替换会吃掉结尾换行，这里补两个——表格与下面的标题之间必须空行，否则 markdown 渲染不出标题
  DOC_TXT="$DOC_TXT"$'\n\n'"## ⚔️ 冲突清单（$n_conf 个术语，定义不一致）

> **不静默择一**——两份材料对同一个词理解不同，本身就是这条术语最大的风险信号。
> 处理方式：① 找双方对齐口径 ② 若确实是两个概念，拆成两个术语 ③ 拿不准标 \`[待裁决]\`，别猜。
$CONFLICTS"
fi

if [ -n "$OUT" ]; then
  printf '%s\n' "$DOC_TXT" > "$OUT"
  # ⚠️ 变量名**必须带花括号**：紧跟着写多字节字符（这里是「（」）时，
  #    bash 会把该字符的头几个字节吞进变量名，报 `OUT?: unbound variable`（本行实测踩过）
  echo "✅ 已写出：${OUT}（术语 ${N_TERM} 个 · 定义行 ${TOTAL} 条 · 冲突 ${n_conf} 个）"
else
  printf '%s\n' "$DOC_TXT"
fi

if [ "$n_conf" -gt 0 ]; then
  printf '\n❌ 检出 %d 个术语定义冲突——裁决完再定稿\n' "$n_conf" >&2
  exit 1
fi
printf '\n✅ 无冲突（每个术语在所有来源里定义一致）\n' >&2
exit 0
