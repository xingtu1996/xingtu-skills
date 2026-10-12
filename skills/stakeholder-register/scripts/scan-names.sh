#!/usr/bin/env bash
# scan-names.sh —— 拿干系人清单去核材料里的人名
#
# 用法:
#   bash scan-names.sh <清单文件> [目录...]                 # 扫目录（默认当前目录）
#   bash scan-names.sh <清单文件> --check <材料文件>        # 只核一份材料
#   bash scan-names.sh <清单文件> [目录] --alias <误写>     # 只查某个误写扩散到哪
#   bash scan-names.sh <清单文件> [目录] --count-only       # 只看规模，不打明细
#   bash scan-names.sh <清单文件> --self-test               # 只验清单格式，不扫文件
#
# 退出码: 0 = 干净 / 1 = 有命中 / 2 = 用法或格式错误
#
# 设计要点（改之前先读）:
#   ① 只认「## 别名索引」一节，不从主表猜列序 —— 表格列序因项目而异，
#      解析表格换项目就静默失效，比报错更危险。
#   ② 解析不出词条 = 报错退出，不静默跳过 —— 空词表扫全仓必然"全绿"，那是假绿。
#   ③ 只输出「命中原文」，不自动改 —— 同一个词可能是普通词汇或另一个人的名字。
#   ④ ⚠️ **awk 只用来拆行，绝不做字符串比较** —— macOS 自带 BWK awk 的比较
#      对非 ASCII 是坏的（实测 "老张" == "张伟" 返回真），会把中文误判成相等，
#      静默漏掉一整列别名。trim 与比较一律用 bash（字节级，可靠）。
#      本机无 gawk，不能靠换实现绕过。

set -uo pipefail

die() { printf '❌ %s\n' "$*" >&2; exit 2; }

# trim：bash 参数扩展，不调 sed/awk（理由见设计要点 ④）
trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

# ── 参数解析 ──────────────────────────────────────────────
REGISTER=""
MODE="scan"          # scan | check | count | alias | self-test
TARGET=""            # --check 的文件 / --alias 的词
SCAN_PATHS=()

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage ;;
    --self-test) MODE="self-test" ;;
    --count-only) MODE="count" ;;
    --check) MODE="check"; TARGET="${2:-}"; [ -n "$TARGET" ] || die "--check 后面要跟材料文件"; shift ;;
    --alias) MODE="alias"; TARGET="${2:-}"; [ -n "$TARGET" ] || die "--alias 后面要跟误写词"; shift ;;
    -*) die "未知参数：$1（-h 看用法）" ;;
    *)
      if [ -z "$REGISTER" ]; then REGISTER="$1"; else SCAN_PATHS+=("$1"); fi
      ;;
  esac
  shift
done

[ -n "$REGISTER" ] || { usage; exit 2; }
[ -f "$REGISTER" ] || die "清单文件不存在：$REGISTER"

# ── 解析别名索引 ──────────────────────────────────────────
# 格式（见 templates/干系人清单.md）：
#   ## 别名索引（…）
#   - 规范名 = 别名1, 别名2
# awk 在这里只负责「圈出这一节」和「按行输出」，不碰字段内容。
SECTION="$(awk '
  /^##[[:space:]]*别名索引/ { in_sec = 1; next }
  in_sec && /^##[[:space:]]/ { exit }
  in_sec { print }
' "$REGISTER")"

if [ -z "$(printf '%s' "$SECTION" | tr -d '[:space:]')" ]; then
  cat >&2 <<EOF
❌ 在 $REGISTER 里找不到别名索引

   期望格式（标题必须含「别名索引」四个字）：
     ## 别名索引（供脚本扫描用，勿改格式）
     - 张伟 = Wei Zhang, 老张

   没有这一节，扫描无从下手 —— 直接报错，不返回"全绿"。
EOF
  exit 2
fi

CANON_LIST=""
PAIRS=""          # 每行 "规范名<TAB>别名"

while IFS= read -r line; do
  [ -n "$line" ] || continue
  case "$line" in -*) ;; *) continue ;; esac          # 只认列表项
  case "$line" in *=*) ;; *) continue ;; esac         # 必须有 =

  canon="$(trim "${line%%=*}")"
  canon="${canon#-}"                                  # 去掉行首的 -
  canon="$(trim "$canon")"
  [ -n "$canon" ] || continue

  # 一个人只记一次规范名
  case "$CANON_LIST" in
    *$'\n'"$canon"$'\n'*|"$canon"$'\n'*) ;;
    *) CANON_LIST="$CANON_LIST$canon"$'\n' ;;
  esac

  # 拆别名——用 tr 断行，再逐个 trim；比较交给 bash
  while IFS= read -r raw; do
    alias="$(trim "$raw")"
    [ -n "$alias" ] || continue
    [ "$alias" = "$canon" ] && continue               # bash 比较：字节级，可靠
    PAIRS="$PAIRS$canon"$'\t'"$alias"$'\n'
  # ⚠️ 必须用 '%s\n' —— read 读到「没有尾随换行的最后一行」时返回非零，
  #    while 会当场终止，**把每行的最后一个别名整条吞掉**（本行踩过）
  done < <(printf '%s\n' "${line#*=}" | tr ',' '\n')
done <<< "$SECTION"

N_CANON="$(printf '%s' "$CANON_LIST" | grep -c .)"
N_ALIAS="$(printf '%s' "$PAIRS" | grep -c .)"

if [ "$MODE" = "self-test" ]; then
  echo "✅ 清单格式 OK：$REGISTER"
  echo "   规范名 $N_CANON 个 · 别名 $N_ALIAS 条"
  echo "   规范名：$(printf '%s' "$CANON_LIST" | tr '\n' ' ')"
  exit 0
fi

if [ "$N_CANON" -eq 0 ] || [ "$N_ALIAS" -eq 0 ]; then
  die "解析出 规范名 $N_CANON 个 / 别名 $N_ALIAS 条 —— 拒绝给出扫描结论（空词表扫完必然\"全绿\"）"
fi

# ── 扫描目标 ──────────────────────────────────────────────
EXCLUDES=(--exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv
          --exclude-dir=dist --exclude-dir=build --exclude-dir=.harness
          --exclude="$(basename "$REGISTER")")
# ↑ 排除清单自己：清单里写着 "张伟 = Wei Zhang, 老张"，不排除的话每次扫描
#   都把自己的别名索引当命中报出来，全是噪音。

if [ "$MODE" = "check" ]; then
  [ -f "$TARGET" ] || die "材料文件不存在：$TARGET"
  SCAN_TARGETS=("$TARGET")
else
  SCAN_PATHS=("${SCAN_PATHS[@]:-.}")
  SCAN_TARGETS=("${SCAN_PATHS[@]}")
fi

# 只查一个具体误写（bash 过滤，不用 awk 比较）
if [ "$MODE" = "alias" ]; then
  FILTERED="$(while IFS=$'\t' read -r c a; do
    [ -n "$a" ] || continue
    [ "$a" = "$TARGET" ] && printf '%s\t%s\n' "$c" "$a"
  done <<< "$PAIRS")"
  [ -n "$FILTERED" ] || die "清单的别名里没有「${TARGET}」——先把它补进常见误写列再扫"
  PAIRS="$FILTERED"
fi

# ── 逐条扫描 ──────────────────────────────────────────────
# 🔴 = 该文件里只出现别名（直接改）
# 🟡 = 该文件里别名与规范名混用（文件内部就不统一）
RED=0; YELLOW=0
RED_FILES=""; YELLOW_FILES=""
REPORT=""

while IFS=$'\t' read -r canon alias; do
  [ -n "$canon" ] || continue
  # ⚠️ -I（--binary-files=without-match）：图片/文档/压缩包里**字节巧合**会匹配上，
  #    实测在真实仓里刷出 29 条假阳性（png/docx/xlsx）——二进制不是人写的文字，不该报
  HITS="$(grep -rnFI "${EXCLUDES[@]}" -- "$alias" "${SCAN_TARGETS[@]}" 2>/dev/null)"
  [ -n "$HITS" ] || continue

  FILES="$(printf '%s\n' "$HITS" | cut -d: -f1 | sort -u)"
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    # ⚠️ 不能写 "|| echo 0"——grep -c 无命中时**自己就输出 0**，再 echo 一个会变成两行
    n_alias="$(grep -cF -- "$alias" "$f" 2>/dev/null)"; n_alias="${n_alias:-0}"
    n_canon="$(grep -cF -- "$canon" "$f" 2>/dev/null)"; n_canon="${n_canon:-0}"
    if [ "$n_canon" -gt 0 ]; then
      YELLOW=$((YELLOW + n_alias)); YELLOW_FILES="$YELLOW_FILES$f"$'\n'
      mark="🟡"; note="同一文件里「${canon}」与「${alias}」混用"
    else
      RED=$((RED + n_alias)); RED_FILES="$RED_FILES$f"$'\n'
      mark="🔴"; note="应改为「${canon}」"
    fi
    if [ "$MODE" != "count" ]; then
      REPORT="$REPORT
$mark $f  —— $alias → ${canon}（${note}）
$(printf '%s\n' "$HITS" | grep -F "$f:" | head -5 | sed 's/^/     /')"
    fi
  done <<< "$FILES"
done <<< "$PAIRS"

# sort -u：同一文件可能因多个别名多次入列，不去重会把「文件数」报虚
NF_RED="$(printf '%s' "$RED_FILES" | grep . | sort -u | grep -c . || true)"
NF_YEL="$(printf '%s' "$YELLOW_FILES" | grep . | sort -u | grep -c . || true)"

# ── 未登记人名的疑似项（仅 --check，单词文件噪声可控）────
UNKNOWN=""
if [ "$MODE" = "check" ]; then
  KNOWN="$(printf '%s\n%s' "$CANON_LIST" "$(printf '%s' "$PAIRS" | cut -f2)")"
  UNKNOWN="$(grep -ohIE '[A-Z][a-z]+ [A-Z][a-z]+' "$TARGET" 2>/dev/null | sort -u | while IFS= read -r n; do
    printf '%s\n' "$KNOWN" | grep -qxF -- "$n" || printf '%s\n' "$n"
  done)"
fi

# ── 输出 ──────────────────────────────────────────────────
echo "清单：${REGISTER}（规范名 $N_CANON 个 · 别名 $N_ALIAS 条）"
[ "$MODE" = "check" ] && echo "材料：$TARGET"
echo "────────────────────────────────────────"

if [ "$MODE" != "count" ] && [ -n "$REPORT" ]; then printf '%s\n\n' "$REPORT"; fi

if [ -n "$UNKNOWN" ]; then
  echo "⚪ 清单里没有的疑似人名（查来源，查不到标 [待核实]，别猜）："
  printf '%s\n' "$UNKNOWN" | sed 's/^/     /'
  echo ""
fi

printf '🔴 确定误写 %d 处（%d 个文件）\n' "$RED" "$NF_RED"
printf '🟡 混用     %d 处（%d 个文件）\n' "$YELLOW" "$NF_YEL"

if [ "$MODE" = "count" ]; then
  echo ""
  echo "（--count-only：未列明细。去掉该参数看具体位置）"
fi

if [ $((RED + YELLOW)) -gt 0 ]; then
  cat <<'EOF'

⚠️ 改之前确认两类文件不要动（原文照旧，只在清单里登记）：
   · 逐字稿 / 会议截图 / 原始邮件 / 历史归档
   判据：这份文件是「记录」还是「产出」？记录不动，产出才改。
EOF
  exit 1
fi

echo "✅ 未发现误写"
exit 0
