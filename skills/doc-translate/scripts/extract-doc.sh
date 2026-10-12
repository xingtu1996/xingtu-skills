#!/usr/bin/env bash
# doc-digest 文本提取 —— 自动探测工具链，缺什么装什么（只装一次）
#
# 用法:
#   bash extract-doc.sh <文件路径>      # 提取文本到 stdout（日志走 stderr）
#   bash extract-doc.sh --check         # 只报环境状态，不提取
#
# 支持的格式: pdf / docx / xlsx / pptx / txt / md / csv / json / xml / log
# 图片不在此处理 —— 直接用 AI 视觉能力读，不要 OCR。
set -uo pipefail

VENV="${DOC_DIGEST_VENV:-$HOME/.cache/doc-digest/venv}"
PY="$VENV/bin/python"

log() { printf '%s\n' "$*" >&2; }
die() { printf '❌ %s\n' "$*" >&2; exit 1; }

# ── 环境自检（--check）──────────────────────────────
check_env() {
  printf 'python3 : '; command -v python3 >/dev/null 2>&1 && echo "✅ $(command -v python3)" || echo "❌ 缺失（必需）"
  printf 'pdftotext: '; command -v pdftotext >/dev/null 2>&1 && echo "✅ 已装（PDF 提取走它，最快最准）" || echo "⚪ 未装（可用，PDF 会退回 pypdf，慢一些）"
  printf 'pypdf    : '; [ -x "$PY" ] && echo "✅ $VENV" || echo "⚪ 未就绪（首次提取 PDF 时自动装，约 20 秒）"
}

# ── PDF ────────────────────────────────────────────
ensure_pypdf() {
  [ -x "$PY" ] && return 0
  command -v python3 >/dev/null 2>&1 || die "系统没有 python3，无法解析 PDF"
  log "首次使用：准备 PDF 解析环境（约 20 秒，只装一次，缓存在 ${VENV}）"
  python3 -m venv "$VENV" >&2 || die "创建 venv 失败"
  "$VENV/bin/pip" install --quiet pypdf >&2 || die "安装 pypdf 失败——检查网络或代理设置"
  log "环境就绪"
}

extract_pdf() {
  local f="$1"
  # ponytail: 优先系统 pdftotext（零安装、排版还原好）；没有才退回 pypdf。
  # 升级路径：若要处理扫描件，需接 OCR（tesseract），当前不做——交给 AI 视觉读图。
  if command -v pdftotext >/dev/null 2>&1; then
    log "用 pdftotext 提取"
    pdftotext -layout "$f" - && return 0
    log "pdftotext 失败，退回 pypdf"
  fi
  ensure_pypdf
  log "用 pypdf 提取"
  "$PY" - "$f" <<'PYEOF'
import sys
from pypdf import PdfReader
r = PdfReader(sys.argv[1])
print(f"页数: {len(r.pages)}")
for i, p in enumerate(r.pages, 1):
    print(f"===== PAGE {i} =====")
    t = (p.extract_text() or "").strip()
    # 空页通常是扫描件——必须显式标出，不允许静默留白（静默留白=AI 会脑补）
    print(t if t else "[本页无文本层——疑似扫描件，请用 AI 视觉能力读图]")
PYEOF
}

# ── OOXML（docx/xlsx/pptx）———————————————
# 三种都是 zip + XML，标准库够用，不引第三方依赖。
extract_ooxml() {
  python3 - "$1" <<'PYEOF'
import sys, zipfile, re, html

path = sys.argv[1]
ext = path.rsplit('.', 1)[-1].lower()

try:
    z = zipfile.ZipFile(path)
except zipfile.BadZipFile:
    sys.exit(f"❌ 不是有效的 Office 文件（zip 解析失败）: {path}")

def strip(xml):
    xml = re.sub(r'<(w:p|a:p)[ >/]', '\n<\\1', xml)   # 段落 → 换行
    xml = re.sub(r'<(w:tab|a:tab)/>', '\t', xml)
    xml = re.sub(r'<[^>]+>', '', xml)
    return html.unescape(xml)

if ext == 'docx':
    print(strip(z.read('word/document.xml').decode('utf-8', 'ignore')))

elif ext == 'xlsx':
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        s = z.read('xl/sharedStrings.xml').decode('utf-8', 'ignore')
        shared = [html.unescape(re.sub(r'<[^>]+>', '', m))
                  for m in re.findall(r'<si>(.*?)</si>', s, re.S)]
    for name in sorted(n for n in z.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml$', n)):
        print(f"\n===== {name} =====")
        sheet = z.read(name).decode('utf-8', 'ignore')
        for row in re.findall(r'<row[^>]*>(.*?)</row>', sheet, re.S):
            cells = []
            for m in re.finditer(r'<c[^>]*?(?:\st="(\w+)")?[^>]*>(?:<v>(.*?)</v>|<is>(.*?)</is>)?</c>', row, re.S):
                t, v, istr = m.group(1), m.group(2), m.group(3)
                if t == 's' and v is not None and v.isdigit() and int(v) < len(shared):
                    cells.append(shared[int(v)])
                elif istr:
                    cells.append(html.unescape(re.sub(r'<[^>]+>', '', istr)))
                else:
                    cells.append(v or '')
            print('\t'.join(cells))

elif ext == 'pptx':
    for name in sorted(n for n in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', n)):
        print(f"\n===== {name} =====")
        print(strip(z.read(name).decode('utf-8', 'ignore')))
PYEOF
}

# ── 主流程 ─────────────────────────────────────────
main() {
  local f="${1:-}"
  [ "$f" = "--check" ] && { check_env; return 0; }
  [ -n "$f" ] || die "用法: bash extract-doc.sh <文件路径>（或 --check 看环境）"
  [ -f "$f" ] || die "文件不存在: $f"

  case "$(printf '%s' "${f##*.}" | tr 'A-Z' 'a-z')" in
    pdf)              extract_pdf "$f" ;;
    docx|xlsx|pptx)   extract_ooxml "$f" ;;
    txt|md|csv|json|xml|log|yml|yaml) cat "$f" ;;
    png|jpg|jpeg|gif|webp|heic|tif|tiff|bmp)
      die "图片不用脚本——直接用 AI 视觉能力（Read 工具）读图，效果比 OCR 好" ;;
    *) die "不支持的类型 .${f##*.} —— 若是 Office/PDF 以外的格式，先转成 PDF 再用" ;;
  esac
}

main "$@"
