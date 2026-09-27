#!/usr/bin/env python3
"""公众号发布前收尾脚本（已验证）：封面注入 / 名片插入 / 赞赏开启 / 正文文本无截图编辑 / 保存草稿
用法：编辑 `URL`、`COVER`、`NEW_TEXT_MAP`（正文替换映射：旧子串 → 新文本）后运行。
依赖：Playwright + 常驻 Chrome daemon（CDP http://127.0.0.1:9222，profile ~/.pw_mp_profile）。
"""
import time, json
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
# 编辑器 URL（必须带 token，无 token 会重定向首页）
URL = "https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit&action=edit&reprint_confirm=0&type=77&appmsgid=100000183&token=791582460&lang=zh_CN"
COVER = ""  # 本地封面路径，如 /tmp/cover_top_new.png；空则跳过

# 正文文本替换：旧子串 → 新文本（用 DOM Range 精确选中后删除重输）
TEXT_REPLACE = {
    # "下篇想拆一个真实对话：前司一位同事问我，harness 是不是个装完照着规范干活的东西。这个问题我记到现在——它值得单独聊一篇。":
    #     "下一篇，聊聊那个被问最多的问题：harness 到底是个工具，还是一条规矩？",
    # "一线技术经理，仍在写代码。专注 AI 工具链与工程化落地。":
    #     "一线技术经理，FDE 实践者。技术细节终会过时，工程思想历久弥新。",
}

# 是否操作：封面 / 名片 / 赞赏 / 保存
DO_COVER = False
DO_CARD = False
DO_REWARD = False
DO_SAVE = False


def get_page(p):
    ctx = p.contexts[0]
    page = None
    for pg in ctx.pages:
        if "appmsg" in pg.url:
            page = pg
            break
    if not page:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(URL, timeout=40000)
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        time.sleep(6)
    page.bring_to_front()
    time.sleep(1)
    return page


def body_pm(page):
    return page.evaluate("""() => {
      const pm = Array.from(document.querySelectorAll('.ProseMirror'))
        .find(p => (p.innerText||'').length > 500);
      return pm ? true : false;
    }""")


def upload_cover(page):
    if not COVER:
        return "SKIP"
    try:
        handle = page.query_selector('input[type=file]')
        if not handle:
            return "NO_INPUT"
        handle.set_input_files(COVER)
        time.sleep(4)
        return "OK"
    except Exception as e:
        return f"ERR:{str(e)[:80]}"


def insert_card(page):
    """名片插入：更多 → 账号名片 → 搜索 → 最近使用 → 插入"""
    try:
        more = page.query_selector('#editor_showmore')
        if not more:
            return "NO_SHOWMORE"
        more.click(); time.sleep(1.5)
        prof = page.query_selector('#js_editor_insertProfile')
        if not prof:
            return "NO_PROFILE_ITEM"
        prof.click(); time.sleep(2.5)
        sb = page.evaluate("""() => {
          const el = Array.from(document.querySelectorAll('input'))
            .find(i => (i.placeholder||'').includes('请输入账号名称') && i.offsetParent!==null);
          if(!el) return null;
          const r=el.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2};
        }""")
        if not sb:
            return "NO_SEARCH"
        page.mouse.click(sb['x'], sb['y']); time.sleep(0.8)
        page.keyboard.type("行途", delay=80); time.sleep(2)
        picked = page.evaluate("""() => {
          const el = document.querySelector('li.profile_history_item');
          if(!el || (el.innerText||'').trim()!=='行途') return null;
          const r=el.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2};
        }""")
        if not picked:
            return "NO_RECENT"
        page.mouse.click(picked['x'], picked['y']); time.sleep(1.5)
        sub = page.evaluate("""() => {
          const el = Array.from(document.querySelectorAll('button,div,span')).find(e => {
            const t=(e.innerText||'').trim();
            const r=e.getBoundingClientRect();
            return t==='插入' && r.width>0 && r.height>0 && r.width<200 && e.className.toString().includes('profile_submit');
          });
          if(!el) return null;
          const r=el.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2};
        }""")
        if not sub:
            return "NO_SUBMIT"
        page.mouse.click(sub['x'], sub['y']); time.sleep(3)
        has = page.evaluate("""() => {
          const pm = Array.from(document.querySelectorAll('.ProseMirror'))
            .find(p => (p.innerText||'').length > 500);
          return pm ? !!pm.querySelector('.mp_profile_iframe_wrp, [data-pluginname=mpprofile]') : false;
        }""")
        return "OK" if has else "VERIFY_FAIL"
    except Exception as e:
        return f"ERR:{str(e)[:80]}"


def enable_reward(page):
    """赞赏开启：点赞赏行 → 弹窗勾协议 → 确定"""
    try:
        pos = page.evaluate("""() => {
          const el = Array.from(document.querySelectorAll('div,span'))
            .find(e => (e.innerText||'').trim()==='不开启' && e.offsetParent!==null);
          if(!el) return null;
          const r=el.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2};
        }""")
        if not pos:
            return "NO_REWARD_ROW"
        page.mouse.click(pos['x'], pos['y']); time.sleep(2)
        cb = page.evaluate("""() => {
          const el = Array.from(document.querySelectorAll('label,div,span')).find(e => {
            const t=(e.innerText||'').trim();
            return t.includes('我已阅读并同意') && e.offsetParent!==null;
          });
          if(!el) return null;
          const r=el.getBoundingClientRect();
          return {x: r.x + 14, y: r.y + r.height/2};  // checkbox 在文字左侧
        }""")
        if not cb:
            return "NO_AGREE"
        page.mouse.click(cb['x'], cb['y']); time.sleep(1)
        ok = page.evaluate("""() => {
          const el = Array.from(document.querySelectorAll('button,div,span')).find(e => {
            const t=(e.innerText||'').trim();
            const r=e.getBoundingClientRect();
            return t==='确定' && r.width>0 && r.height>0 && r.width<120 && e.offsetParent!==null;
          });
          if(!el) return null;
          const r=el.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2};
        }""")
        if not ok:
            return "NO_OK"
        page.mouse.click(ok['x'], ok['y']); time.sleep(2.5)
        t = page.evaluate("() => document.body.innerText||''")
        return "OK" if "账户:行途" in t or "赞赏" in t and "不开启" not in t.split("赞赏")[1][:6] else "VERIFY"
    except Exception as e:
        return f"ERR:{str(e)[:80]}"


def replace_texts(page):
    """正文文本替换：DOM Range 选中旧子串 → Delete → type 新文本"""
    results = {}
    for old, new in TEXT_REPLACE.items():
        sel = page.evaluate("""(old) => {
          const pm = Array.from(document.querySelectorAll('.ProseMirror'))
            .find(p => (p.innerText||'').includes('先聊两句理念') || (p.innerText||'').length > 500);
          if(!pm) return 'NO_PM';
          const walker = document.createTreeWalker(pm, NodeFilter.SHOW_TEXT);
          let node;
          while(node = walker.nextNode()){
            if((node.textContent||'').includes(old)){
              const range = document.createRange();
              range.selectNodeContents(node);
              const sel = window.getSelection();
              sel.removeAllRanges();
              sel.addRange(range);
              return 'SEL:' + sel.toString().length;
            }
          }
          return 'NOT_FOUND';
        }""", old)
        if sel.startswith("SEL:"):
            page.keyboard.press("Delete"); time.sleep(0.3)
            page.keyboard.type(new, delay=30); time.sleep(0.3)
            results[old[:20]] = "OK"
        else:
            results[old[:20]] = sel
    return results


def save_draft(page):
    try:
        btn = page.evaluate("""() => {
          const el = Array.from(document.querySelectorAll('button,a,div,span')).find(e => {
            const t=(e.innerText||'').trim();
            const r=e.getBoundingClientRect();
            return t==='保存为草稿' && r.width>0 && r.height>0;
          });
          if(!el) return null;
          const r=el.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2};
        }""")
        if not btn:
            return "NO_SAVE"
        page.mouse.click(btn['x'], btn['y']); time.sleep(3)
        t = page.evaluate("() => document.body.innerText||''")
        return "OK" if "已保存" in t else "VERIFY"
    except Exception as e:
        return f"ERR:{str(e)[:80]}"


def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        page = get_page(p)
        print("URL:", page.url[:60])
        if DO_COVER:
            print("COVER:", upload_cover(page))
        if DO_CARD:
            print("CARD:", insert_card(page))
        if DO_REWARD:
            print("REWARD:", enable_reward(page))
        if TEXT_REPLACE:
            print("TEXT:", json.dumps(replace_texts(page), ensure_ascii=False))
        if DO_SAVE:
            print("SAVE:", save_draft(page))


if __name__ == "__main__":
    main()
