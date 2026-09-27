#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量重渲：@@PH 标记法防灰框卡 → review 主题 → 还原字面【配图：】段落。
用法: python3 _batch_render.py <pkg1> [pkg2 ...]
"""
import re, subprocess, sys, os

ROOT = "${WORKSPACE}"
MD2W = os.path.join(ROOT, "md2wechat/bin/md2wechat.js")

def latest_md(pkg):
    d = os.path.join(pkg, "01_正文")
    cands = [f for f in os.listdir(d) if re.match(r"正文_v\d+\.md", f)]
    cands.sort()
    return os.path.join(d, cands[-1])

def render(pkg):
    md = latest_md(pkg)
    html = os.path.join(pkg, "02_排版HTML", "公众号_发布版.html")
    s = open(md, encoding="utf-8").read()
    # 1) 【配图：x】 → @@PH:x@@（防 md2wechat 渲灰框卡）
    tmp = os.path.join(ROOT, ".agents/skills/mp-publish-sop/_render_input.md")
    open(tmp, "w", encoding="utf-8").write(re.sub(r"【配图：(.+?)】", r"@@PH:\1@@", s))
    # 2) 渲
    r = subprocess.run(["node", MD2W, tmp, "--theme", "review", "--links", "keep",
                        "--no-signature", "-o", html], capture_output=True, text=True)
    if not os.path.exists(html):
        print(f"  🔴 渲失败 {pkg}: {r.stdout} {r.stderr}")
        return
    # 3) 还原 @@PH:x@@ → 字面 <p ...>【配图：x】</p>
    h = open(html, encoding="utf-8").read()
    h = re.sub(r"<p[^>]*>\s*@@PH:(.+?)@@\s*</p>",
               r'<p style="margin:18px 0;text-align:center;">【配图：\1】</p>', h)
    open(html, "w", encoding="utf-8").write(h)
    n_ph = h.count("@@PH")
    n_fig = len(re.findall(r"【配图：", h))
    print(f"  {os.path.basename(pkg)}: MD={os.path.basename(md)} 残留@@PH={n_ph} 字面【配图：】={n_fig}")

if __name__ == "__main__":
    for p in sys.argv[1:]:
        render(p)
