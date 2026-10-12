#!/usr/bin/env bash
# scan-refs.sh —— 术语文档影响面扫描：谁引用了它 / 旧写法还残留在哪
#
# 用法:
#   bash scan-refs.sh <术语文档> <仓库根>              # 谁引用了这份术语表
#   bash scan-refs.sh <术语文档> <仓库根> <旧写法>     # 追加：全仓扫旧写法残留（收尾复扫）
#   bash scan-refs.sh -h
#
# 退出码: 0 = 无命中 / 1 = 有命中（要逐条处理）/ 2 = 用法或环境错误
#
# 为什么这么写（改之前先读）:
#   ① 术语改名的代价不在术语表本身，在**引用它的那些文件**。漏一个 = 留下一条指向旧名的死链。
#      所以先跑一次拿清单，再决定动哪些。命中格式：文件:行号 | 引用形式 | 命中行原文
#   ② 第三个参数（旧写法）是**收尾复扫**用的。同一份表，改之前跑是找目标，改之后跑才是证据——
#      必须回到 0 命中才算收口；改完不复扫 = 隐患潜伏，等于没改完。
#   ③ 只报不改。命中里可能有历史归档 / 逐字稿 / 会议记录——那是「记录」不是「产出」，
#      自动改会把当时说的原话抹掉。判据：这份文件是记录还是产出？记录只登记，产出才动手。
#   ④ 引用形式只分「markdown 链接 / 文件名提及」两种，不做语义推断——
#      推断换一份文档就失效，而静默漏报比报错危险。
#   ⑤ 匹配一律字节级：grep -F 找候选，分类走 bash case / grep -E。
#      **不用 awk 比字符串**——macOS 自带 BWK awk 对非 ASCII 的比较是坏的（不同中文被判相等），
#      拿它做判断 = 静默漏掉一整类命中。本机无 gawk，换实现绕不过去。
#   ⑥ 零依赖：只用 grep/find/sed，不碰 node/python3（CI Shell executor 上可能没有）。

set -euo pipefail

die() { printf '❌ %s\n' "$*" >&2; exit 2; }

# trim：bash 参数扩展，不调 sed/awk（理由见设计要点 ⑤）
trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

# 转义 ERE 元字符——文件名里的 . + ( ) 会改变正则含义
esc_ere() { printf '%s' "$1" | sed 's/[.[\*^$()+?{}|]/\\&/g'; }

usage() {
  awk 'NR>1 && /^#/ { sub(/^# ?/, ""); print; next } NR>1 { exit }' "$0"
  exit 0
}

case "${1:-}" in -h|--help) usage ;; esac
[ $# -ge 2 ] || die "参数不够。用法：bash scan-refs.sh <术语文档> <仓库根> [旧写法]"
DOC="$1"; REPO="$2"; OLD="${3:-}"

[ -f "$DOC" ]  || die "术语文档不存在：$DOC"
[ -d "$REPO" ] || die "仓库根不是目录：$REPO"

REPO_ABS="$(cd "$REPO" && pwd)"
DOC_ABS="$(cd "$(dirname "$DOC")" && pwd)/$(basename "$DOC")"
BASE="$(basename "$DOC_ABS")"
ESC="$(esc_ere "$BASE")"

# 文件名太通用时命中会淹没真实引用——先说清楚，别让人误读清单
case "$BASE" in
  README.md|readme.md|index.md|Index.md)
    printf '⚠️  文件名「%s」过于通用，命中里会混入无关文件——考虑给术语表一个专名（如 TERMS.md）。\n\n' "$BASE" >&2 ;;
esac

EXCLUDES=(--exclude-dir=.git --exclude-dir=node_modules --exclude-dir=dist
          --exclude-dir=build --exclude-dir=.venv --exclude-dir=.idea --exclude-dir=target)

# ── 1. 引用扫描 ────────────────────────────────────────────
# -I（--binary-files=without-match）：图片/压缩包字节巧合会匹配上，那是假命中，不是引用
HITS="$(grep -rnFI "${EXCLUDES[@]}" -F -- "$BASE" "$REPO_ABS" 2>/dev/null || true)"

REPORT=""; N=0
if [ -n "$HITS" ]; then
  while IFS= read -r hit; do
    [ -n "$hit" ] || continue
    f="${hit%%:*}"; rest="${hit#*:}"; ln="${rest%%:*}"; text="${rest#*:}"
    [ "$f" = "$DOC_ABS" ] && continue          # 自己是真相源，不是引用方
    rel="${f#"$REPO_ABS"/}"
    if printf '%s' "$text" | grep -qE "\]\([^)]*${ESC}[^)]*\)"; then
      form="markdown 链接"
    else
      form="文件名提及"                         # 正文/代码块里点名，同样会随改名变成死引用
    fi
    REPORT="$REPORT$rel:$ln | $form | $text"$'\n'
    N=$((N + 1))
  done <<< "$HITS"
fi

# ── 2. 旧写法残留（收尾复扫）───────────────────────────────
# 排除术语文档自身：表里常常要**登记**旧写法（"旧写法 → 规范名"），那是应有的内容，不是残留
OREPORT=""; ON=0
if [ -n "$OLD" ]; then
  OHITS="$(grep -rnFI "${EXCLUDES[@]}" --exclude="$BASE" -F -- "$OLD" "$REPO_ABS" 2>/dev/null || true)"
  if [ -n "$OHITS" ]; then
    while IFS= read -r hit; do
      [ -n "$hit" ] || continue
      f="${hit%%:*}"; rest="${hit#*:}"; ln="${rest%%:*}"; text="${rest#*:}"
      rel="${f#"$REPO_ABS"/}"
      OREPORT="$OREPORT$rel:$ln | 旧写法残留 | $text"$'\n'
      ON=$((ON + 1))
    done <<< "$OHITS"
  fi
fi

# ── 输出 ───────────────────────────────────────────────────
echo "术语文档：$DOC_ABS"
echo "扫描范围：$REPO_ABS"
echo "────────────────────────────────────────"

if [ "$N" -gt 0 ]; then
  echo "📌 引用方（$N 处，改名前先看这份清单）："
  printf '%s' "$REPORT"
  echo ""
else
  echo "📌 引用方：无（没有别的文件按文件名指向这份表）"
  echo ""
fi

if [ -n "$OLD" ]; then
  if [ "$ON" -gt 0 ]; then
    # ⚠️ 变量名带花括号：紧跟多字节字符（「」（））时不加花括号，bash 会把它的字节吞进变量名
    echo "🧹 旧写法「${OLD}」残留（${ON} 处，全部清掉才算收口）："
    printf '%s' "$OREPORT"
    echo ""
  else
    echo "🧹 旧写法「${OLD}」残留：无 ✅（已排除术语文档自身——表里登记旧写法是应有的）"
    echo ""
  fi
fi

if [ $((N + ON)) -gt 0 ]; then
  cat <<'EOF'
⚠️ 动手前先分类（判据：这份文件是「记录」还是「产出」？）：
   · 记录（逐字稿 / 会议纪要归档 / 历史邮件 / 变更日志）→ 原文照旧，只在清单里登记
   · 产出（需求 / 设计 / README / 代码注释 / 模板）→ 改
EOF
  exit 1
fi

echo "✅ 无命中"
exit 0
