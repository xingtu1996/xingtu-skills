#!/usr/bin/env bash
# meeting-archive 归档脚手架
#
# 用法:
#   bash archive.sh <会议日期> <主题> <文档仓根目录> <文件> [文件...]
#
# 例:
#   bash archive.sh 20260916 kickoff ~/projects/<文档仓> ~/Downloads/纪要.md ~/Downloads/Kickoff.docx
#
# 做三件机械事（判断类的事交给 AI，脚本不做）:
#   ① 建目录 meeting/<日期>-<主题>/ 与 附件/
#   ② .docx → 原件进 附件/，同时 pandoc 转 Markdown 放目录根
#      .md/.txt → 直接放目录根
#   ③ 每个文件报 md5 与「是否与目录内已有文件重复」——入库前查重是这个技能的铁律
#
# 不做: 重命名成「纪要_日期.md」/「逐字稿_日期.md」（AI 按内容判断后自己改）
#       提炼要点、写文件头（AI 做）
set -euo pipefail

DATE="${1:-}"; TOPIC="${2:-}"; REPO="${3:-}"; shift 3 2>/dev/null || true

if [ -z "$DATE" ] || [ -z "$TOPIC" ] || [ -z "$REPO" ] || [ $# -eq 0 ]; then
  cat >&2 <<'EOF'
用法: bash archive.sh <会议日期> <主题> <文档仓根目录> <文件> [文件...]

  <会议日期>   YYYYMMDD，例 20260916
  <主题>       简短 slug，例 kickoff / avd-review
  <文档仓根> 文档仓的本地路径
  <文件>       一个或多个：.docx（原件+转换）或 .md/.txt（直接归档）

例:
  bash archive.sh 20260916 kickoff ~/projects/<文档仓> ~/Downloads/纪要.md ~/Downloads/Kickoff.docx
EOF
  exit 1
fi

DIR="$REPO/meeting/${DATE}-${TOPIC}"
ATT="$DIR/附件"
mkdir -p "$ATT"

echo "📁 归档目录: $DIR"
echo

md5of() { md5 -q "$1" 2>/dev/null || shasum -a 256 "$1" | cut -c1-32; }

# 收集目录内已有文件的 md5（用于查重）
declare -a EXISTING_HASH
for f in "$DIR"/*.md "$ATT"/*; do
  [ -f "$f" ] || continue
  EXISTING_HASH+=("$(md5of "$f")|$f")
done

for SRC in "$@"; do
  [ -f "$SRC" ] || { echo "⚠️  跳过（不存在）: $SRC"; continue; }
  BASE="$(basename "$SRC")"
  EXT="$(printf '%s' "${BASE##*.}" | tr '[:upper:]' '[:lower:]')"
  H="$(md5of "$SRC")"

  # 查重
  DUP=""
  for e in "${EXISTING_HASH[@]:-}"; do
    [ -z "$e" ] && continue
    [ "${e%%|*}" = "$H" ] && DUP="${e#*|}"
  done

  if [ -n "$DUP" ]; then
    echo "🔁 重复（内容与已有文件一致，不建议再入库）:"
    echo "     新: $BASE"
    echo "     旧: $DUP"
    echo "     md5: $H"
    echo
    continue
  fi

  case "$EXT" in
    docx|doc)
      cp "$SRC" "$ATT/"
      echo "📎 原件 → 附件/$BASE"
      if command -v pandoc >/dev/null 2>&1; then
        OUT="$DIR/${BASE%.*}.md"
        pandoc "$SRC" -t gfm --wrap=none -o "$OUT" 2>/dev/null \
          && echo "📝 转换 → $(basename "$OUT")" \
          || echo "⚠️  pandoc 转换失败，原件已保留在 附件/"
      else
        echo "⚠️  未安装 pandoc，跳过 Markdown 转换。装法: brew install pandoc"
      fi
      ;;
    md|txt)
      cp "$SRC" "$DIR/"
      echo "📄 归档 → $BASE"
      ;;
    *)
      cp "$SRC" "$ATT/"
      echo "📎 未识别类型，作附件 → 附件/$BASE"
      ;;
  esac

  echo "     md5: $H"
  EXISTING_HASH+=("$H|$DIR/$BASE")
  echo
done

echo "── 下一步（AI 做）──"
echo "  1. 按内容判断类型，重命名:  纪要_${DATE}.md / 逐字稿_${DATE}.md"
echo "  2. 提炼「决策 / 待办 / 风险」，写进文件头的要点区"
echo "  3. 写文件头（归档时间 / 会议日期 / 来源 / 原始文件）"
echo "  4. 更新 CHANGELOG"
