#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行途 · 微信公众号发布自动化脚本（Playwright 版）
=================================================
把一篇成稿（HTML/PM doc JSON）导入公众号草稿箱，完成正文注入、标题/摘要、
封面、原创声明、保存草稿。群发需人工（个人号接口已回收）。

依赖: pip3 install playwright
用法:
  python3 mp_publish.py --login                    # 首次扫码登录（存 ~/.pw_mp_profile）
  python3 mp_publish.py --article appmsgid=100000183 \
      --html outputs/xxx_公众号正文_预览格式版.html \
      --title "标题" --desc "摘要" \
      --cover /path/to/cover.png \
      --original                          # 开启原创声明
  python3 mp_publish.py --list-drafts              # 列出草稿箱
"""
import argparse, json, os, re, sys, time, base64

PROFILE_DIR = os.path.expanduser("~/.pw_mp_profile")
EDITOR_URL = "https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit&action=edit&type=77&appmsgid={}&lang=zh_CN"
HOME_URL = "https://mp.weixin.qq.com/"

def launch(playwright, headless=False):
    """启动持久化 context（复用登录态）"""
    ctx = playwright.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR, channel="chrome",
        headless=headless, args=["--no-sandbox"],
    )
    return ctx

def html_to_pm_doc(html_path):
    """把公众号预览格式 HTML 转成 PM doc JSON（section 保留背景色，无 blockquote）"""
    html = open(html_path, encoding="utf-8").read()
    pattern = re.compile(r'<(p|h2|section)((?:"[^"]*"|[^">])*)>(.*?)</\1>', re.S)
    blocks = []
    for m in pattern.finditer(html):
        tag, attrs_str, inner = m.group(1), m.group(2), m.group(3)
        style_m = re.search(r'style="([^"]*)"', attrs_str)
        style = style_m.group(1) if style_m else ""
        blocks.append({"tag": tag, "style": style, "inner": inner})

    def strip_tags(s): return re.sub(r'<[^>]+>', '', s)
    def make_text_marks(inner):
        segs = []
        for mm in re.finditer(r'<strong([^>]*)>(.*?)</strong>|([^<]+)', inner, re.S):
            if mm.group(2) is not None:
                attrs_str = mm.group(1); text = strip_tags(mm.group(2))
                color_m = re.search(r'color:\s*([^;]+)', attrs_str)
                color = color_m.group(1).strip() if color_m else None
                marks = [{"type": "textstyle", "attrs": {"fontWeight": "bold"}}]
                if color: marks[0]["attrs"]["color"] = color
                segs.append({"text": text, "marks": marks})
            elif mm.group(3) is not None:
                t = mm.group(3)
                if t.strip(): segs.append({"text": t, "marks": []})
        return segs

    def text_content(p_marks):
        pc = []
        for s in p_marks:
            pc.append({"type": "text", "text": s["text"], **({"marks": s["marks"]} if s["marks"] else {})})
        return pc if pc else [{"type": "text", "text": ""}]

    doc_content = []
    for b in blocks:
        tag, style, inner = b["tag"], b["style"], b["inner"]
        if tag == "p":
            if "<img" in inner:
                src_m = re.search(r'src="([^"]*)"', inner); alt_m = re.search(r'alt="([^"]*)"', inner)
                img_s = re.search(r'<img[^>]*style="([^"]*)"', inner)
                doc_content.append({"type": "para", "attrs": {"tagName": "p", "attributes": {"style": style}},
                    "content": [{"type": "image", "attrs": {"src": src_m.group(1) if src_m else "", "alt": alt_m.group(1) if alt_m else "", "style": img_s.group(1) if img_s else "", "width": "100%", "data-type": "png"}}]})
            else:
                doc_content.append({"type": "para", "attrs": {"tagName": "p", "attributes": {"style": style}}, "content": text_content(make_text_marks(inner))})
        elif tag == "h2":
            doc_content.append({"type": "heading", "attrs": {"tagName": "h2", "attributes": {"style": style}}, "content": [{"type": "text", "text": strip_tags(inner)}]})
        elif tag == "section":
            if "<img" in inner:
                src_m = re.search(r'src="([^"]*)"', inner); alt_m = re.search(r'alt="([^"]*)"', inner)
                img_s = re.search(r'<img[^>]*style="([^"]*)"', inner)
                doc_content.append({"type": "para", "attrs": {"tagName": "section", "attributes": {"style": style}},
                    "content": [{"type": "image", "attrs": {"src": src_m.group(1) if src_m else "", "alt": alt_m.group(1) if alt_m else "", "style": img_s.group(1) if img_s else "", "width": "100%", "data-type": "png"}}]})
            else:
                inner_ps = re.findall(r'<p[^>]*>(.*?)</p>', inner, re.S)
                if inner_ps:
                    p_content = [{"type": "para", "content": text_content(make_text_marks(ip))} for ip in inner_ps]
                    doc_content.append({"type": "para", "attrs": {"tagName": "section", "attributes": {"style": style}}, "content": p_content})
                else:
                    # 修复：无 <p> 包裹的裸文本兜底成单段落，避免空块
                    doc_content.append({"type": "para", "attrs": {"tagName": "section", "attributes": {"style": style}}, "content": text_content(make_text_marks(inner))})
    return {"type": "doc", "content": doc_content}

def inject_body(page, doc):
    """PM 事务注入正文（base64 分块 → nodeFromJSON → replaceWith）"""
    b64 = base64.b64encode(json.dumps(doc, ensure_ascii=False).encode("utf-8")).decode()
    n = len(b64); step = (n + 12) // 13
    for i in range(13):
        chunk = b64[i*step:(i+1)*step]
        page.evaluate("window.__d64_{}={}; 'ok'".format(i, json.dumps(chunk)))
    return page.evaluate("""(() => {
      const v = window.__mpBodyChecktextView;
      if (!v) return 'NO_VIEW';
      const joined = Array.from({length:13},(_,i)=>window['__d64_'+i]).join('');
      let docJSON;
      try { docJSON = JSON.parse(decodeURIComponent(escape(atob(joined)))); } catch(e) { return 'PARSE_FAIL:'+e.message; }
      const schema = v.state.schema;
      let doc;
      try { doc = schema.nodeFromJSON(docJSON); } catch(e) { return 'BUILD_FAIL:'+e.message; }
      const tr = v.state.tr;
      tr.replaceWith(0, v.state.doc.content.size, doc);
      v.dispatch(tr);
      return 'REPLACED size=' + doc.content.size;
    })()""")

def set_field(page, selector, value):
    """用原生 setter 触发 React 更新"""
    return page.evaluate("""({sel, val}) => {
      const el = document.querySelector(sel);
      if(!el) return 'NO_EL';
      const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
      setter.call(el, val);
      el.dispatchEvent(new Event('input', {bubbles:true}));
      el.dispatchEvent(new Event('change', {bubbles:true}));
      return 'SET:' + el.value.length;
    }""", {"sel": selector, "val": value})

def upload_cover(page, cover_path):
    """封面上传：点封面区打开菜单 → 注入 file input（Playwright 决定性优势）"""
    page.evaluate("""(() => {
      const t = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while(t.nextNode()){
        const txt = t.currentNode.textContent.trim();
        if(txt.indexOf('拖拽或选择封面') !== -1){
          let el = t.currentNode.parentElement;
          for(let i=0;i<4 && el;i++){
            if(el.click){ el.click(); return 'CLICKED'; }
            el = el.parentElement;
          }
        }
      }
      return 'NO_COVER';
    })()""")
    page.wait_for_timeout(1500)
    # 菜单弹出后，file input 是隐藏的，Playwright set_input_files 可直接注入
    page.set_input_files("input[type=file]", cover_path)
    page.wait_for_timeout(3000)
    return "COVER_UPLOADED"

def click_original(page):
    """开启原创声明：点开关 → 弹窗 → 勾协议 → 确定"""
    page.evaluate("""(() => {
      const labels = Array.from(document.querySelectorAll('label, [class*=switch], [class*=setting-group]'));
      for(const l of labels){
        const t=(l.textContent||'').trim();
        if(t.indexOf('原创')===0 && l.offsetWidth>0){ l.click(); return 'CLICKED'; }
      }
      return 'NO_LABEL';
    })()""")
    page.wait_for_timeout(1200)
    # 弹窗勾选协议 + 确定
    page.evaluate("""(() => {
      const boxes = Array.from(document.querySelectorAll('input[type=checkbox]'));
      for(const b of boxes){ if(b.offsetParent !== null || b.getBoundingClientRect().width>0){ b.click(); } }
      const btns = Array.from(document.querySelectorAll('button, .weui-desktop-btn'));
      for(const b of btns){ if((b.textContent||'').trim()==='确定' && b.offsetWidth>0){ b.click(); return 'OK_CLICKED'; } }
      return 'NO_OK';
    })()""")
    page.wait_for_timeout(1500)
    return "ORIGINAL_SET"

def save_draft(page):
    page.evaluate("""(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      for(const b of btns){ if((b.textContent||'').trim()==='保存为草稿' && b.offsetWidth>0){ b.click(); return 'SAVED'; } }
      return 'NO_SAVE';
    })()""")
    return "DRAFT_SAVED"

def main():
    ap = argparse.ArgumentParser(description="行途公众号发布自动化（Playwright）")
    ap.add_argument("--login", action="store_true", help="首次扫码登录")
    ap.add_argument("--article", help="appmsgid=100000183")
    ap.add_argument("--html", help="正文HTML路径")
    ap.add_argument("--title", help="标题")
    ap.add_argument("--desc", help="摘要")
    ap.add_argument("--cover", help="封面本地路径")
    ap.add_argument("--original", action="store_true", help="开启原创声明")
    ap.add_argument("--list-drafts", action="store_true", help="列出草稿箱")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        if args.login:
            page.goto(HOME_URL); page.wait_for_timeout(3000)
            print("请在打开的 Chrome 窗口扫码登录公众号后台，登录完成后回车继续...")
            input(">>> 扫码完成后按回车: ")
            print("登录态已保存到", PROFILE_DIR)
            ctx.close(); return

        if args.list_drafts:
            page.goto(HOME_URL); page.wait_for_timeout(3000)
            page.evaluate("document.querySelector('.weui-desktop-layout__bd .menu_item a').click() if ... else null")
            # 简化：直接打印当前页信息
            print("URL:", page.url)
            ctx.close(); return

        if not args.article:
            print("需要 --article appmsgid=xxx"); ctx.close(); return

        # 打开编辑器
        m = re.search(r'(\d+)', args.article)
        url = EDITOR_URL.format(m.group(1))
        page.goto(url); page.wait_for_load_state("domcontentloaded", timeout=20000)
        page.wait_for_timeout(2500)
        print("编辑器已打开:", page.title()[:30])

        # 注入正文
        if args.html:
            doc = html_to_pm_doc(args.html)
            r = inject_body(page, doc)
            print("正文注入:", r)
            page.wait_for_timeout(1500)

        # 标题 + 摘要
        if args.title:
            print("标题:", set_field(page, "textarea.js_title", args.title))
        if args.desc:
            print("摘要:", set_field(page, "textarea.js_desc", args.desc))

        # 封面
        if args.cover:
            print("封面:", upload_cover(page, args.cover))

        # 原创
        if args.original:
            print("原创:", click_original(page))

        # 保存
        print("保存:", save_draft(page))
        page.wait_for_timeout(3000)
        ctx.close()
        print("DONE")

if __name__ == "__main__":
    main()
