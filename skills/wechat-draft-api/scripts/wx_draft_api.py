#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wechat-draft-api.py — 微信公众号「官方 API 建稿到草稿箱」工具（通用参数化版）

行途开源矩阵 wechat-draft-api skill 携带脚本。从 tools/wx_draft_api.py 抽离参数化：
  - appid / appsecret 不再硬编码，改由参数或环境变量注入（凭据不落代码）
  - 公众号名片卡改为可选注入（--profile-card-file / WX_PROFILE_CARD），不传则不插
  - 群发永不自动化：终点 = 草稿箱（draft/add），绝不调用 masssend

流程：access_token → 配图 uploadimg 换 mmbiz 链接 → 正文占位替换为 <img> →
      封面 add_material 拿 thumb_media_id → draft/add 建稿。

用法（环境变量）:
  export WX_APPID="你的appid"
  export WX_SECRET_FILE="/path/to/appsecret.txt"   # 文件内容=32位secret
  python3 wechat-draft-api.py --pkg <发布包> --title <标题> --desc <摘要> [--profile-card-file 名片.html] [--dry-run]

用法（直接传参）:
  python3 wechat-draft-api.py --appid xxx --secret-file yyy.txt --pkg ... --title ... --desc ...

发布包需含：02_排版HTML/公众号_发布版.html、04_配图/（与正文占位对应）、01_正文/正文_vN.md（含 【配图：x.png】 占位）。
"""
import argparse, json, os, re, sys, urllib.request, urllib.parse, uuid

API = "https://api.weixin.qq.com/cgi-bin"


def load_profile_card(path_or_text):
    """加载官方名片卡：若参数是存在的文件则读文件，否则当字面量返回；空则返回 None。"""
    if not path_or_text:
        return None
    if os.path.isfile(path_or_text):
        return open(path_or_text, encoding="utf-8").read().strip()
    return path_or_text.strip() or None


def inject_profile_card(body, card):
    """把名片卡插入正文开头（首个 <section> 之后）与文末（最后一个 </section> 之后），幂等。"""
    if not card:
        return body
    m = re.search(r"<section[^>]*>", body)
    if m:
        j = m.end()
        body = body[:j] + "\n" + card + "\n" + body[j:]
    end = body.rfind("</section>")
    if end >= 0:
        e = end + len("</section>")
        body = body[:e] + "\n" + card + "\n" + body[e:]
    return body


def post_json(url, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def post_multipart(url, filepath, field="media"):
    boundary = uuid.uuid4().hex
    name = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        data = f.read()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"{name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def get_token(appid, secret):
    url = f"{API}/token?grant_type=client_credential&appid={appid}&secret={secret}"
    with urllib.request.urlopen(url, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    if "access_token" not in d:
        sys.exit(f"🔴 token 获取失败: {d}")
    return d["access_token"]


def extract_body(pkg):
    p = os.path.join(pkg, "02_排版HTML", "公众号_发布版.html")
    s = open(p, encoding="utf-8").read()
    i = s.find('id="content"')
    start = s.find("<section", i)
    end = s.rfind("</section>") + len("</section>")
    return s[start:end]


def figs_of(pkg):
    """01_正文 下按占位引用的图（正文_vN.md 中的 【配图：x.png】）"""
    body_md = None
    d = os.path.join(pkg, "01_正文")
    if not os.path.isdir(d):
        return []
    for f in sorted(os.listdir(d)):
        if re.match(r"正文_v\d+\.md", f):
            body_md = os.path.join(d, f)
    if not body_md:
        return []
    s = open(body_md, encoding="utf-8").read()
    return re.findall(r"【配图：([^】]+)】", s)


def main():
    ap = argparse.ArgumentParser(description="微信公众号官方 API 建稿到草稿箱（群发不自动化）")
    ap.add_argument("--pkg", required=True, help="发布包目录")
    ap.add_argument("--title", required=True)
    ap.add_argument("--desc", required=True)
    ap.add_argument("--author", default="行途")
    ap.add_argument("--appid", default=os.environ.get("WX_APPID", ""), help="公众号 AppID（或从 WX_APPID 读）")
    ap.add_argument("--secret-file", default=os.environ.get("WX_SECRET_FILE", ""), help="存 appsecret 的本地文件（或从 WX_SECRET_FILE 读）")
    ap.add_argument("--profile-card-file", default=os.environ.get("WX_PROFILE_CARD", ""), help="官方名片卡 HTML 片段路径/字面量；不传则不插名片")
    ap.add_argument("--cover-file", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not a.appid:
        sys.exit("🔴 缺少 appid：传 --appid 或设环境变量 WX_APPID")
    if not a.secret_file or not os.path.isfile(a.secret_file):
        sys.exit("🔴 缺少 secret 文件：传 --secret-file 或设环境变量 WX_SECRET_FILE（文件内容=32位 appsecret）")
    secret = ""
    for tok in re.findall(r"[A-Za-z0-9]{32}", open(a.secret_file, encoding="utf-8").read()):
        secret = tok
        break
    if not secret:
        sys.exit("🔴 未能从 secret 文件解析出 32 位 appsecret")

    token = get_token(a.appid, secret)
    print("① access_token OK")

    body = extract_body(a.pkg)
    figs = figs_of(a.pkg)
    fig_dir = os.path.join(a.pkg, "04_配图")

    url_map = {}
    for fig in figs:
        src = os.path.join(fig_dir, fig)
        if not os.path.exists(src):
            print(f"  ⚠️ 配图缺失跳过：{fig}")
            continue
        if fig.lower().endswith(".webp") and sys.platform == "darwin":
            png = os.path.join(fig_dir, fig.replace(".webp", ".png"))
            if not os.path.exists(png):
                os.system(f'sips -s format png "{src}" --out "{png}" >/dev/null 2>&1')
            src = png
        r = post_multipart(f"{API}/media/uploadimg?access_token={token}", src)
        if "url" not in r:
            print(f"  🔴 uploadimg 失败 {fig}: {r}")
            continue
        url_map[fig] = r["url"]
        print(f"  🖼 {fig} → {r['url'][:60]}...")
    for fig, u in url_map.items():
        body = body.replace(f"【配图：{fig}】", f'<img src="{u}" style="width:100%;display:block;margin:18px 0;">')
    body = re.sub(r"<p[^>]*>【配图：[^<]*</p>", "", body)  # 未上传成功的不留占位

    card = load_profile_card(a.profile_card_file)
    body = inject_profile_card(body, card)
    print(f"② 正文构建：{len(body)} chars（嵌图 {len(url_map)}/{len(figs)}，名片 {'已插' if card else '未插'}）")

    cover = a.cover_file or os.path.join(a.pkg, "03_封面", sorted(
        f for f in os.listdir(os.path.join(a.pkg, "03_封面")) if f.endswith(".png")
        and "真人" not in f and "旧" not in f)[-1])
    r = post_multipart(f"{API}/material/add_material?access_token={token}&type=image", cover)
    if "media_id" not in r:
        sys.exit(f"🔴 封面上传失败: {r}")
    thumb = r["media_id"]
    print(f"③ 封面素材 OK：{cover}")

    payload = {"articles": [{"title": a.title, "author": a.author, "digest": a.desc,
                             "content": body, "thumb_media_id": thumb,
                             "need_open_comment": 1, "only_fans_can_comment": 0}]}
    if a.dry_run:
        print("④ 干跑结束（不加 --dry-run 则真正建稿到草稿箱）")
        return
    r = post_json(f"{API}/draft/add?access_token={token}", payload)
    if "media_id" in r:
        print(f"⑤ ✅ 草稿已建：draft media_id = {r['media_id']}（在草稿箱设原创/合集/定时即可，群发不自动化）")
    else:
        sys.exit(f"🔴 draft/add 失败: {r}")


if __name__ == "__main__":
    main()
