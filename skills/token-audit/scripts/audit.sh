#!/usr/bin/env bash
# token-audit · 只读审计（量体积 / 查重复加载 / 查安全）
#
# 用法:
#   bash audit.sh                 # 审计当前工作区
#   bash audit.sh <工作区根目录>
#
# **只读**：本脚本不做任何写入。修复由 SKILL.md 第 6 步（可逆操作）负责。
#
# ⚠️ 只统计**真会被加载**的文件（v0.1.1 修正）：
#   Claude Code 加载 **cwd 及其所有祖先目录**的 .claude/，再叠加用户级 ~/.claude/。
#   所以统计范围 = 祖先链上的 .claude/（rules/** + CLAUDE.md）+ 用户级。
#   不统计工作区里散落的其他 CLAUDE.md / AGENTS.md（那是文档，不是常驻配置）。
set -uo pipefail

ROOT="${1:-$PWD}"
cd "$ROOT" || { echo "❌ 目录不存在: $ROOT" >&2; exit 1; }

command -v md5 >/dev/null 2>&1 || command -v md5sum >/dev/null 2>&1 || { echo "❌ 需要 md5 或 md5sum" >&2; exit 1; }
md5of() { if command -v md5 >/dev/null 2>&1; then md5 -q "$1"; else md5sum "$1" | cut -d' ' -f1; fi; }

# ── 收集「会加载」的 .claude 目录：cwd 向上所有祖先 + 用户级 ──
declare -a CDIRS=()
d="$PWD"
while :; do
  [ -d "$d/.claude" ] && CDIRS+=("$d/.claude")
  [ "$d" = "/" ] && break
  d="$(dirname "$d")"
done
# 去重（$HOME 可能已在祖先链里出现）
declare -a UNIQ=()
for x in "${CDIRS[@]}"; do
  dup=0; for y in "${UNIQ[@]:-}"; do [ "$x" = "$y" ] && dup=1; done
  [ "$dup" = 0 ] && UNIQ+=("$x")
done
CDIRS=("${UNIQ[@]}")

echo "════════ ① 体积（标尺：入口 <200 行 / 单文件 <16KB / 常驻 <窗口 5%）════════"
echo "  加载源（cwd 祖先链 + 用户级）: ${#CDIRS[@]} 个 .claude 目录"
TOTAL_B=0
for c in "${CDIRS[@]}"; do
  # 入口文件
  for f in "$c/CLAUDE.md" "$c/AGENTS.md"; do
    [ -f "$f" ] || continue
    L=$(wc -l < "$f" | tr -d ' '); B=$(wc -c < "$f" | tr -d ' ')
    TOTAL_B=$((TOTAL_B + B))
    flag=""; [ "$L" -gt 400 ] && flag="⚠️⚠️ >400 行（开始漏读）"
    [ "$L" -gt 200 ] && [ "$L" -le 400 ] && flag="⚠️ >200 行"
    printf "  %-58s %5s行 %7sB  %s\n" "${f/#$HOME/~}" "$L" "$B" "$flag"
  done
  # rules 下的全部 md（机制：**自动加载**，无 @ 引用也加载）
  [ -d "$c/rules" ] || continue
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    L=$(wc -l < "$f" | tr -d ' '); B=$(wc -c < "$f" | tr -d ' ')
    TOTAL_B=$((TOTAL_B + B))
    flag=""
    [ "$L" -gt 400 ] && flag="⚠️⚠️ >400 行"
    [ "$L" -gt 200 ] && [ "$L" -le 400 ] && flag="⚠️ >200 行"
    [ "$B" -gt 16384 ] && flag="$flag ⚠️ >16KB"
    printf "  %-58s %5s行 %7sB  %s\n" "${f/#$HOME/~}" "$L" "$B" "$flag"
  done < <(find "$c/rules" -name "*.md" 2>/dev/null | sort)
done
TOTAL_K=$((TOTAL_B / 1024))
echo "  ────────────────────────────────────────────────"
# ⚠️ 换算比率：实测 ≈ 4.6 字符/token（混合中英文+代码）。
#    曾按"中文 1.5 字符/token"估，把 173KB 算成 115K tokens，而 /context 实测 37.4k——**差 3 倍**。
printf "  常驻合计 ≈ %s KB ｜ **约 %sK tokens**（按实测 4.6 字符/token 估）\n" \
  "$TOTAL_K" "$((TOTAL_B / 4600))"
echo "  判据：拿 /context 的 Memory files 数字对照，能对上就说明比率适用"

echo
echo "════════ ② 重复加载（**跨所有加载源**比同名同内容）════════"
# ⚠️ 不用关联数组 —— macOS 自带 bash 3.2 不支持 `declare -A`
TMPD=$(mktemp); trap 'rm -f "$TMPD"' EXIT
DUPS=0
for c in "${CDIRS[@]}"; do
  [ -d "$c/rules" ] || continue
  while IFS= read -r rel; do
    h="$(md5of "$c/rules/$rel")"
    prev="$(grep -F -m1 "	$rel	" "$TMPD" 2>/dev/null || true)"
    if [ -n "$prev" ]; then
      ph="$(printf '%s' "$prev" | cut -f1)"
      pp="$(printf '%s' "$prev" | cut -f3)"
      if [ "$h" = "$ph" ]; then
        printf "  ⚠️ 完全重复（纯浪费）: %s\n     %s\n     %s\n" "$rel" "${pp/#$HOME/~}" "${c}/rules/$rel" | sed "s|$HOME|~|g"
      else
        printf "  ⚠️ 同名不同内容（需人裁）: %s\n     %s (%sB)\n     %s (%sB)\n" \
          "$rel" "${pp/#$HOME/~}" "$(wc -c < "$pp" | tr -d ' ')" \
          "${c}/rules/$rel" "$(wc -c < "$c/rules/$rel" | tr -d ' ')" | sed "s|$HOME|~|g"
      fi
      DUPS=$((DUPS + 1))
    else
      printf '%s\t%s\t%s\n' "$h" "$rel" "$c/rules/$rel" >> "$TMPD"
    fi
  done < <(cd "$c/rules" 2>/dev/null && find . -name "*.md" | sed 's|^\./||')
done
[ "$DUPS" = 0 ] && echo "  ✅ 未发现重复" || echo "  → 共 $DUPS 处；md5 相同可移走子级那份（父级提供同内容）"

echo
echo "════════ ③ 安全自检 ════════"
echo "--- 权限（allow 列表，排除 settings 自身误报）---"
FOUND_PERM=0
for c in "${CDIRS[@]}"; do
  for s in "$c/settings.json" "$c/settings.local.json"; do
    [ -f "$s" ] || continue
    wide=$(grep -oE '"Bash\([^)]*\)"' "$s" 2>/dev/null | grep -E '\*\)|rm |sudo |chmod ' | head -6)
    if [ -n "$wide" ]; then
      echo "  ⚠️ ${s/#$HOME/~} 有过宽条目:"; echo "$wide" | sed 's/^/     /'
      FOUND_PERM=1
    fi
  done
done
[ "$FOUND_PERM" = 0 ] && echo "  ✅ 未见明显过宽条目"

echo "--- 凭据残留（**排除 settings 类**，只看脚本/配置）---"
CRED=$(find "${CDIRS[@]}" -type f \( -name "*.sh" -o -name "*.js" -o -name "*.yml" -o -name "*.yaml" -o -name "*.env*" \) 2>/dev/null \
  | xargs grep -lEi '(password|passwd|secret|token|api[_-]?key)[^a-z]{0,3}[:=][^$][^"'"'"']{7,}' 2>/dev/null | head -8)
[ -n "$CRED" ] && { echo "  ⚠️ 疑似明文凭据（需人工看）:"; echo "$CRED" | sed "s|$HOME|~|g; s/^/     /"; } \
              || echo "  ✅ 未见明文凭据"

echo "--- hook 有效性（指向的脚本是否存在且可执行）---"
FOUND_HOOK=0
for c in "${CDIRS[@]}"; do
  for s in "$c/settings.json" "$c/settings.local.json"; do
    [ -f "$s" ] || continue
    while IFS= read -r p; do
      [ -z "$p" ] && continue
      p="${p/#\~/$HOME}"
      case "$p" in
        /*) if [ -x "$p" ]; then echo "  ✅ ${p/#$HOME/~}"; else echo "  ⚠️ hook 脚本不存在或不可执行: ${p/#$HOME/~}（**静默失效**）"; fi ;;
      esac
      FOUND_HOOK=1
    done < <(grep -oE '(~|/)[^ "]+\.(sh|js|py)' "$s" 2>/dev/null | sort -u)
  done
done
[ "$FOUND_HOOK" = 0 ] && echo "  （未发现 hook 配置）"

echo
echo "════════ 完成（本脚本只读，未做任何修改）════════"
echo "下一步：SKILL.md 第 2 步分「机制 vs 配置」→ 第 3 步算 Multi-Agent 乘数 → 第 5 步出报告 → 人审后才执行"
