#!/usr/bin/env bash
# render-diagrams.sh —— 批量把 .mmd 渲成 .svg（内建 Chrome 兜底，找不到就报错，不静默跳过）
#
# 用法:
#   bash render-diagrams.sh <目录> [--out-dir <目录>]
#   bash render-diagrams.sh -h
#
# 退出码: 0 = 全部成功 / 1 = 有渲染失败 / 2 = 环境或用法错误（缺 mmdc / 缺 Chrome / 路径不对）
#
# 为什么这么写（改之前先读）:
#   ① **内建 Chrome 兜底**。mmdc 默认去找 puppeteer 自己缓存的那份 Chrome，没下过就报
#      `Could not find Chrome (ver. xxx)`，然后它会**提示你去跑 `npx puppeteer browsers install chrome`**——
#      但离线/受限环境下这条命令根本跑不通，且白白多下一个 ~150MB 的浏览器。
#      实测可用解法：指到系统已装的 Chrome。做法是生成临时 puppeteer 配置并 `-p` 传进去。
#   ② **找不到 Chrome 就报错退出（exit 2），绝不静默跳过**。跳过 = 一个图没渲出来却报"完成"，
#      那是最危险的假绿：图是空的，但门禁全绿，没人会去查。
#   ③ **mmdc 返回 0 也要验产物**。渲染"成功"但没落盘/落了个空文件，同样是假绿——
#      所以每个图渲完都检查文件存在且非空。
#   ④ 临时配置写在 mktemp 目录里，trap 清理；不往用户的仓里塞临时文件。
#   ⑤ 零依赖：只用 mktemp/find，不碰 node/python3（CI Shell executor 上可能没有）。
#      mmdc 本身是 node 工具，但它靠 `command -v` 探测，缺了给安装指引而不是崩。

set -euo pipefail

die() { printf '❌ %s\n' "$*" >&2; exit 2; }

usage() {
  awk 'NR>1 && /^#/ { sub(/^# ?/, ""); print; next } NR>1 { exit }' "$0"
  exit 0
}

case "${1:-}" in -h|--help) usage ;; esac
[ $# -ge 1 ] || die "参数不够。用法：bash render-diagrams.sh <目录> [--out-dir <目录>]"

SRC_DIR=""; OUT_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage ;;
    --out-dir) OUT_DIR="${2:-}"; [ -n "$OUT_DIR" ] || die "--out-dir 后面要跟目录"; shift ;;
    -*) die "未知参数：$1（-h 看用法）" ;;
    *) [ -z "$SRC_DIR" ] && SRC_DIR="$1" || die "多给了参数：$1" ;;
  esac
  shift
done

# ⚠️ 变量名带花括号：后面紧跟多字节字符（「（」）时不加花括号，bash 会把它的字节吞进变量名
[ -d "$SRC_DIR" ] || die "目录不存在：${SRC_DIR}（检查路径，别把文件名当目录传进来）"
SRC_DIR="$(cd "$SRC_DIR" && pwd)"
[ -z "$OUT_DIR" ] || mkdir -p "$OUT_DIR"
[ -z "$OUT_DIR" ] || OUT_DIR="$(cd "$OUT_DIR" && pwd)"

# ── 1. mmdc 存在吗 ─────────────────────────────────────────
if ! command -v mmdc >/dev/null 2>&1; then
  cat >&2 <<'EOF'
❌ 没找到 mmdc（mermaid 命令行渲染器）

   装法（任选其一）：
     npm i -g @mermaid-js/mermaid-cli
     npx -y @mermaid-js/mermaid-cli ...     # 不想全局装就用 npx，本脚本暂不代跑

   装完再跑一次。注意 mmdc 是 node 工具，本脚本其余部分零依赖，只这一步需要 node。
EOF
  exit 2
fi

# ── 2. Chrome 兜底 ─────────────────────────────────────────
# 优先用环境变量指路（受限环境里 Chrome 常被装到非标准位置）
find_chrome() {
  if [ -n "${CHROME_PATH:-}" ]; then
    [ -x "$CHROME_PATH" ] && { printf '%s' "$CHROME_PATH"; return 0; }
    printf '⚠️  CHROME_PATH=%s 不存在或不可执行，改走自动探测\n' "$CHROME_PATH" >&2
  fi

  local c
  for c in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta" \
    "/Applications/Chromium.app/Contents/MacOS/Chromium" \
    "$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  do
    [ -x "$c" ] && { printf '%s' "$c"; return 0; }
  done

  for c in google-chrome google-chrome-stable chromium chromium-browser; do
    if command -v "$c" >/dev/null 2>&1; then command -v "$c"; return 0; fi
  done

  return 1
}

CHROME="$(find_chrome || true)"
if [ -z "$CHROME" ]; then
  cat >&2 <<'EOF'
❌ 没找到 Chrome —— mmdc 靠它渲染，没有它一张图也出不来。

   这不是"跳过就行"的问题：静默跳过 = 图没渲出来却报成功，是假绿。

   三种修法：
     1. 装 Chrome（macOS: 官方 dmg 装到 /Applications/；Debian/Ubuntu: apt install chromium）
     2. 已经装在非标准位置 → 显式指路：
          CHROME_PATH=/path/to/chrome bash render-diagrams.sh <目录>
     3. 实在没有浏览器 → 用 npx 让 puppeteer 自己下一份：
          npx puppeteer browsers install chrome && bash render-diagrams.sh <目录>
EOF
  exit 2
fi

# 临时 puppeteer 配置：把 mmdc 指到系统 Chrome；--no-sandbox 是容器/CI 里跑必需
TMPDIR_RENDER="$(mktemp -d)"
CFG="$TMPDIR_RENDER/puppeteer.json"

# 清理只用 rm -f（点名删已知文件）+ rmdir（只删空目录），**不用 rm -rf**——
# 递归删除一旦路径变量为空就会删到别处，这类脚本要在别人机器上跑，不留这种风险。
cleanup() {
  [ -n "${CFG:-}" ] && rm -f "$CFG"
  [ -n "${TMPDIR_RENDER:-}" ] && rm -f "$TMPDIR_RENDER/last.log"
  [ -n "${TMPDIR_RENDER:-}" ] && rmdir "$TMPDIR_RENDER" 2>/dev/null
  return 0
}
trap cleanup EXIT
cat > "$CFG" <<EOF
{
  "executablePath": "$CHROME",
  "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
}
EOF

echo "渲染器：$(command -v mmdc)"
echo "浏览器：$CHROME"
echo "────────────────────────────────────────"

# ── 3. 逐个渲染 ────────────────────────────────────────────
# find + while read：文件名带空格也不会断（不用 for 遍历未加引号的展开结果）
MMD_LIST="$(find "$SRC_DIR" -type f -name '*.mmd' | LC_ALL=C sort)"
N_TOTAL=0; N_OK=0; N_FAIL=0; FAILED=""

if [ -z "$MMD_LIST" ]; then
  printf '⚠️  %s 下没有 .mmd 文件——先确认路径给对了（这不是成功，是没东西可渲）\n' "$SRC_DIR" >&2
fi

while IFS= read -r mmd; do
  [ -n "$mmd" ] || continue
  N_TOTAL=$((N_TOTAL + 1))

  rel="${mmd#"$SRC_DIR"/}"
  if [ -z "$OUT_DIR" ]; then
    svg="${mmd%.mmd}.svg"
  else
    svg="$OUT_DIR/${rel%.mmd}.svg"
    mkdir -p "$(dirname "$svg")"
  fi

  # 空 .mmd 多半是占位符没填，渲出来是空白图——先拦，别让它混进产物
  if [ ! -s "$mmd" ]; then
    printf '❌ %s：空文件（占位符没填？）\n' "$rel"
    N_FAIL=$((N_FAIL + 1)); FAILED="$FAILED$rel"$'\n'
    continue
  fi

  # 日志只回显前几行：mmdc/puppeteer 的堆栈动辄几十行，真正有用的错误在最上面，
  # 全量刷屏会把"失败的是哪个文件"淹掉
  show_log() {
    sed -n '1,8p' "$TMPDIR_RENDER/last.log" 2>/dev/null | grep -v '^[[:space:]]*$' | sed 's/^/     /'
  }

  if mmdc -p "$CFG" -i "$mmd" -o "$svg" >"$TMPDIR_RENDER/last.log" 2>&1; then
    # 返回 0 不等于画出东西了——产物必须存在且非空，否则就是假绿
    if [ -s "$svg" ]; then
      printf '✅ %s → %s\n' "$rel" "${svg#"$SRC_DIR"/}"
      N_OK=$((N_OK + 1))
    else
      printf '❌ %s：mmdc 返回成功但产物为空/未落盘 → 假绿，按失败处理\n' "$rel"
      show_log
      N_FAIL=$((N_FAIL + 1)); FAILED="$FAILED$rel"$'\n'
    fi
  else
    printf '❌ %s：渲染失败\n' "$rel"
    show_log
    N_FAIL=$((N_FAIL + 1)); FAILED="$FAILED$rel"$'\n'
  fi
done <<< "$MMD_LIST"

# ── 4. 汇总 ────────────────────────────────────────────────
echo "────────────────────────────────────────"
printf '共 %d 个 · 成功 %d · 失败 %d\n' "$N_TOTAL" "$N_OK" "$N_FAIL"

if [ "$N_FAIL" -gt 0 ]; then
  echo ""
  echo "失败的："
  printf '%s' "$FAILED" | sed 's/^/   /'
  echo ""
  cat <<'EOF'
常见修法：
   · Could not find Chrome → 本脚本本该已兜底；若仍报，说明系统 Chrome 不可执行，用 CHROME_PATH 显式指路
   · 语法错误 → 先拿单个文件跑 mmdc -p <cfg> -i x.mmd -o x.svg 看具体行号
   · 中文/emoji 变方块 → 系统缺字体，装一套中文字体（linux: fonts-noto-cjk）
EOF
  exit 1
fi

[ "$N_TOTAL" -gt 0 ] || exit 2      # 一个都没渲 = 没东西可验，不是成功
echo "✅ 全部渲染完成"
exit 0
