#!/usr/bin/env bash
# 豆包会议文档抓取 —— 包装脚本（自动解决 playwright 依赖路径）
#
# 用法:
#   bash doubao.sh login          # 首次：打开浏览器扫码登录（一次性）
#   bash doubao.sh fetch <URL> [输出目录]   # 抓取逐字稿
#
# 依赖: playwright（任一来源即可，脚本按序自动查找）
#   ① 本目录/上层 node_modules  ② 全局 node_modules  ③ 全局 @playwright/mcp 自带
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find_playwright() {
  # ① 就近
  local d="$HERE"
  for _ in 1 2 3 4; do
    [ -d "$d/node_modules/playwright" ] && { echo "$d/node_modules"; return 0; }
    d="$(dirname "$d")"
  done
  # ② 全局
  local gr; gr="$(npm root -g 2>/dev/null || true)"
  [ -n "$gr" ] && [ -d "$gr/playwright" ] && { echo "$gr"; return 0; }
  # ③ @playwright/mcp 自带
  [ -n "$gr" ] && [ -d "$gr/@playwright/mcp/node_modules/playwright" ] && { echo "$gr/@playwright/mcp/node_modules"; return 0; }
  return 1
}

NP="$(find_playwright)" || {
  cat >&2 <<'EOF'
❌ 未找到 playwright。装一个即可（任选）：
   npm i -g playwright && npx playwright install chromium
   或 npm i -g @playwright/mcp
EOF
  exit 1
}

CMD="${1:-}"; shift || true
case "$CMD" in
  login)
    NODE_PATH="$NP" exec node "$HERE/doubao-login.js" "$@"
    ;;
  fetch)
    [ $# -ge 1 ] || { echo "用法: bash doubao.sh fetch <URL> [输出目录]" >&2; exit 1; }
    NODE_PATH="$NP" exec node "$HERE/doubao-fetch.js" "$@"
    ;;
  *)
    cat >&2 <<'EOF'
用法:
  bash doubao.sh login                    # 首次登录（打开浏览器扫码，一次性）
  bash doubao.sh fetch <URL> [输出目录]    # 抓取逐字稿（复用登录态）
EOF
    exit 1
    ;;
esac
