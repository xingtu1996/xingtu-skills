#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行途 · 公众号新建草稿并导入（mp_publish.py 的补位驱动）
流程：登录检测 → 草稿箱新建图文（拿 appmsgid）→ 正文注入 → 标题/摘要/封面/原创 → 保存
用法:
  python3 mp_new_draft.py --html xxx.html --title "标题" --desc "摘要" \
      --cover cover.png --original
"""
import argparse, os, re, sys

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)
from mp_publish import (PROFILE_DIR, HOME_URL, launch, html_to_pm_doc,
                        inject_body, set_field, upload_cover, click_original, save_draft)

def get_token(page):
    m = re.search(r'token=(\d+)', page.url)
    if m: return m.group(1)
    tok = page.evaluate("(()=>{const a=document.querySelector('a[href*=\"token=\"]');return a?a.href.match(/token=(\\d+)/)?.[1]:null})()")
    return tok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--desc", required=True)
    ap.add_argument("--cover", required=True)
    ap.add_argument("--original", action="store_true")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(HOME_URL); page.wait_for_timeout(4000)

        token = get_token(page)
        if not token:
            print("LOGIN_NEEDED: 登录态失效，请先跑 --login 扫码"); ctx.close(); return

        # 进草稿箱 UI → 新建图文
        page.goto(f"https://mp.weixin.qq.com/cgi-bin/appmsg?begin=0&count=10&type=77&action=list_card&token={token}&lang=zh_CN")
        page.wait_for_timeout(4000)
        clicked = page.evaluate("""(() => {
          const els = Array.from(document.querySelectorAll('button, a, .weui-desktop-btn, .weui-desktop-btn_primary'));
          for(const el of els){
            const t=(el.textContent||'').replace(/\\s/g,'');
            if((t.includes('写新的图文')||t.includes('新的图文')||t==='新建') && el.offsetWidth>0){ el.click(); return 'CLICKED:'+t; }
          }
          return 'NO_NEW_BTN';
        })()""")
        print("新建按钮:", clicked)
        page.wait_for_timeout(3500)
        m = re.search(r'appmsgid=(\d+)', page.url)
        if not m:
            print("NO_APPMSGID, URL:", page.url[:120]); ctx.close(); return
        appmsgid = m.group(1)
        print("新草稿 appmsgid =", appmsgid)
        page.wait_for_timeout(2000)

        doc = html_to_pm_doc(args.html)
        print("正文注入:", inject_body(page, doc))
        page.wait_for_timeout(1500)
        print("标题:", set_field(page, "textarea.js_title", args.title))
        print("摘要:", set_field(page, "textarea.js_desc", args.desc))
        print("封面:", upload_cover(page, args.cover))
        if args.original:
            print("原创:", click_original(page))
        print("保存:", save_draft(page))
        page.wait_for_timeout(3500)
        ctx.close()
        print("DONE appmsgid=" + appmsgid)

if __name__ == "__main__":
    main()
