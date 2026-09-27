#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性批量后处理：排版新规（加粗转黑#16181d + 主色橙红F2644F）。
用法: python3 _batch_recolor.py <html1> [html2 ...]
仅做版式层替换，不动正文事实/标题/封面/配图。
"""
import re, sys

def process(path):
    s = open(path, encoding="utf-8").read()
    before = {
        "d71a1b": len(re.findall(r"#d71a1b", s, re.I)),
        "rgba215": len(re.findall(r"rgba\(\s*215\s*,\s*26\s*,\s*27", s)),
        "strongF2644F": len(re.findall(r"<strong[^>]*color:#F2644F", s)),
        "justify": s.count("text-align:justify"),
        "emptyp": len(re.findall(r"<p[^>]*>\s*</p>", s)),
    }
    # 1) 旧大红 hex → 橙红（h2 字+下划线随之变橙红，符合新规）
    s = re.sub(r"#d71a1b", "#F2644F", s, flags=re.I)
    # 2) 旧大红 rgba 背景 → 橙红 rgba（保留 alpha）
    s = re.sub(r"rgba\(\s*215\s*,\s*26\s*,\s*27\s*,", "rgba(242,100,79,", s)
    # 3) 正文加粗 <strong> 内橙红 → 黑 #16181d（只动 strong，禁动 h2/<b>）
    s = re.sub(r"(<strong[^>]*color:)#F2644F", r"\g<1>#16181d", s)
    # 4) justify → left（防短行字间距拉宽病）
    s = s.replace("text-align:justify", "text-align:left")
    # 5) 空 p 清理
    s = re.sub(r"<p[^>]*>\s*</p>", "", s)

    after = {
        "d71a1b": len(re.findall(r"#d71a1b", s, re.I)),
        "rgba215": len(re.findall(r"rgba\(\s*215\s*,\s*26\s*,\s*27", s)),
        "F2644F": s.count("#F2644F"),
        "strongF2644F": len(re.findall(r"<strong[^>]*color:#F2644F", s)),
        "strong16181d": len(re.findall(r"<strong[^>]*color:#16181d", s)),
        "justify": s.count("text-align:justify"),
        "h2橙红": len(re.findall(r"<h2[^>]*color:#F2644F", s)),
    }
    open(path, "w", encoding="utf-8").write(s)
    print(f"  {path.split('/')[-2]}/公众号_发布版.html")
    print(f"    before: d71a1b={before['d71a1b']} rgba215={before['rgba215']} strong#F2644F={before['strongF2644F']} justify={before['justify']} 空p={before['emptyp']}")
    print(f"    after : d71a1b={after['d71a1b']} rgba215={after['rgba215']} F2644F={after['F2644F']} strong#F2644F={after['strongF2644F']} strong#16181d={after['strong16181d']} justify={after['justify']} h2橙红={after['h2橙红']}")

if __name__ == "__main__":
    for p in sys.argv[1:]:
        process(p)
