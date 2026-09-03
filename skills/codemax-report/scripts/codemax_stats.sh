#!/bin/bash
# ============================================================================
# codemax_stats.sh — CodeMax 平台（NewAPI）统计 API 封装
# 用法:
#   bash codemax_stats.sh summary    [-s 2026-08-01] [-e 2026-08-28]
#   bash codemax_stats.sh users      [-s ...] [-e ...]
#   bash codemax_stats.sh models     [-s ...] [-e ...]
#   bash codemax_stats.sh pm-options
#   bash codemax_stats.sh pm-projects [--sort-cost] [-s ...] [-e ...]
#   bash codemax_stats.sh log-stat   [-s 2026-08-01] [-e ...] [-t 0]   # NewAPI 日志统计
#   bash codemax_stats.sh api-models                                   # NewAPI 模型清单
# 认证（二选一）:
#   A. CODEMAX_TOKEN + CODEMAX_USER  → Bearer 令牌（系统访问令牌 + 用户 ID）
#   B. CODEMAX_COOKIE                → 浏览器会话 Cookie
#   存 settings.local.json env（CODEMAX_TOKEN=... CODEMAX_USER=... CODEMAX_COOKIE=...）
# 安全: 凭证走环境变量不进 ps；URL 为内网只读统计接口
# ============================================================================
set -euo pipefail

BASE="https://codemax.co-mall.com"
# 认证优先级: CODEMAX_ADMIN_TOKEN（admin, user=1）> CODEMAX_TOKEN+CODEMAX_USER（个人）> CODEMAX_COOKIE
ADMIN_TOKEN="${CODEMAX_ADMIN_TOKEN:-}"; TOKEN="${CODEMAX_TOKEN:-}"; USER_ID="${CODEMAX_USER:-}"; COOKIE="${CODEMAX_COOKIE:-}"
[ -n "$ADMIN_TOKEN" ] && { TOKEN="$ADMIN_TOKEN"; USER_ID="${CODEMAX_ADMIN_USER:-1}"; }
[ -n "$TOKEN$COOKIE" ] || { echo "❌ 未配置认证：CODEMAX_ADMIN_TOKEN 或 CODEMAX_TOKEN+CODEMAX_USER 或 CODEMAX_COOKIE（settings.local.json env）"; exit 1; }

UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/151.0.0.0 Safari/537.36'
if [ -n "$TOKEN" ]; then
  [ -n "$USER_ID" ] || { echo "❌ Bearer 模式需 CODEMAX_USER（用户 ID）"; exit 1; }
  AUTH=(-H "Authorization: Bearer $TOKEN" -H "New-API-User: $USER_ID")
else
  AUTH=(-H "Cookie: $COOKIE")
fi
CURL=(curl -s "${AUTH[@]}" -H 'Cache-Control: no-store' -H "User-Agent: $UA" -H 'Accept: application/json')

# --- 参数解析 ---
CMD="${1:-}"; shift || true
START=""; END=""; SORT=""; TYPE="0"; PID=""
while [ $# -gt 0 ]; do
  case "$1" in
    -s) START="$2"; shift 2;;
    -e) END="$2";   shift 2;;
    -t) TYPE="$2";  shift 2;;
    -p) PID="$2";   shift 2;;
    --sort-cost) SORT="total_cost"; shift;;
    *) echo "❌ 未知参数: $1"; exit 1;;
  esac
done
[ -n "$START" ] || START="$(date +%Y-%m-01)"
[ -n "$END" ]   || END="$(date +%Y-%m-%d)"
# 日期 → Unix 秒（macOS）
TS_S="$(date -j -f '%Y-%m-%d' "$START" +%s 2>/dev/null || echo "$START")"
TS_E="$(date -j -f '%Y-%m-%d' "$END" +%s 2>/dev/null || echo "$END")"

case "$CMD" in
  summary)     "${CURL[@]}" "$BASE/api/data/admin/stats/summary?start_date=$START&end_date=$END";;
  users)       "${CURL[@]}" "$BASE/api/data/admin/stats/users?start_date=$START&end_date=$END";;
  models)      "${CURL[@]}" "$BASE/api/data/admin/stats/models?start_date=$START&end_date=$END";;
  pm-options)  "${CURL[@]}" "$BASE/api/pm_work_stats/projects/options";;
  pm-projects) "${CURL[@]}" "$BASE/api/pm_work_stats/projects?p=1&page_size=100&sort_field=${SORT:-total_cost}&sort_order=desc&start_date=$START&end_date=$END";;
  log-stat)    "${CURL[@]}" "$BASE/api/log/self/stat?type=$TYPE&token_name=&model_name=&start_timestamp=$TS_S&end_timestamp=$TS_E&group=";;
  api-models)  "${CURL[@]}" "$BASE/api/models";;
  pm-staffs)   [ -n "$PID" ] || { echo "❌ 需 -p <project_id>"; exit 1; }
               "${CURL[@]}" "$BASE/api/pm_work_stats/projects/$PID/staffs?p=1&page_size=100&start_date=$START&end_date=$END";;
  *)
    echo "用法: bash codemax_stats.sh {summary|users|models|pm-options|pm-projects|pm-staffs|log-stat|api-models} [-s 起] [-e 止] [-t 0|1|2] [-p <项目id>] [--sort-cost]"
    echo "示例: bash codemax_stats.sh log-stat -s 2026-08-01 -e 2026-08-28"
    exit 1;;
esac
