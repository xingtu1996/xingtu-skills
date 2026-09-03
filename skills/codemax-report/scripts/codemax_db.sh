#!/bin/bash
# ============================================================================
# codemax_db.sh — CodeMax 平台数据库（newapi）只读查询封装
# 用法:
#   bash codemax_db.sh "SELECT ..."                        # 自定义 SQL
#   bash codemax_db.sh users                               # 快捷: 全部用户清单
#   bash codemax_db.sh user <name>                         # 快捷: 按用户名/昵称查身份
#   bash codemax_db.sh tables                              # 快捷: 全部表
#   bash codemax_db.sh -prod "SQL"                         # prod 只读护栏（仅 SELECT/SHOW/...）
# 连接: ${CODEX_DB_DSN}（settings.local.json env），默认 newapi 库
#   DSN 格式: user:pass@tcp(host:port)/db，密码可含 @（从 @tcp( 反向定位）
# 安全: ① prod 只读护栏 ② 密码走 MYSQL_PWD 不进 ps
# ============================================================================
set -euo pipefail

DSN="${CODEX_DB_DSN:-}"
[ -n "$DSN" ] || { echo "❌ 未配置 CODEX_DB_DSN（settings.local.json env，格式 user:pass@tcp(host:port)/db）"; exit 1; }

# --- 解析 DSN: user:pass@tcp(host:port)/db（密码含 @ 也正确） ---
DB_USER="${DSN%%:*}"
REST="${DSN#*:}"
DB_PASS="${REST%%@tcp(*}"          # 到 @tcp( 前即密码（含内部 @）
HP="${REST#*@tcp(}"; HP="${HP%%)*}" # host:port
DB_HOST="${HP%%:*}"
DB_PORT="${HP##*:}"
DB_NAME="${REST##*/}"

# --- 参数 ---
PROD=0
[ "${1:-}" = "-prod" ] && { PROD=1; shift; }
ARG="${1:-}"

# --- prod 只读护栏 ---
if [ "$PROD" = "1" ]; then
  if echo "$ARG" | grep -qiE '(insert|update|delete|drop|alter|truncate|replace|create|grant|set\s)'; then
    echo "❌ prod 只读护栏: 检测到写操作关键词"; exit 1
  fi
  if ! echo "$ARG" | grep -qiE '^\s*(select|show|desc|explain|with)\b'; then
    echo "❌ prod 只读护栏: 首词非只读语句"; exit 1
  fi
fi

run() { echo "🔌 [$([ $PROD = 1 ] && echo prod || echo default)] $DB_NAME @ $DB_HOST:$DB_PORT"; MYSQL_PWD="$DB_PASS" mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" "$DB_NAME" -e "$1"; }

case "$ARG" in
  users)   run "SELECT id, username, display_name, email, role, status, FROM_UNIXTIME(created_at) AS created FROM users ORDER BY id" ;;
  user)    NAME="${2:-}"; [ -n "$NAME" ] || { echo "用法: bash codemax_db.sh user <用户名/昵称>"; exit 1; }
           run "SELECT id, username, display_name, email, role, status, request_count, FROM_UNIXTIME(created_at) AS created FROM users WHERE username LIKE '%$NAME%' OR display_name LIKE '%$NAME%' OR email LIKE '%$NAME%'" ;;
  tables)  run "SHOW TABLES" ;;
  "")      echo "用法: bash codemax_db.sh [-prod] \"<SQL>\" | users | user <name> | tables"; exit 1 ;;
  *)       run "$ARG" ;;
esac
