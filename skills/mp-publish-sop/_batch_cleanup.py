#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按标题回收旧稿：删除目标标题下除 keep 列表外的所有草稿。"""
import re, json, urllib.request

API = "https://api.weixin.qq.com/cgi-bin"
APPID = "${WECHAT_APPID}"
SECRET_FILE = "github/xingtu-vault/09_个人台账/04_凭据备忘/公众号AppSecret_2026-09-02_明文.txt"

TARGETS = {
    "我在 AI 落地现场，发现技术从来不是卡点",
    "窄门难入，宽门难出：我为什么选了那条慢路",
    "专家做内容没人看？因为你在自嗨",
}
KEEP = {
    "EnzxjcHKb7JLLj5CpkCQJWDNxAErXLoYqchdBmXfpKlZ0lV5LeJByeV7s9vOFS3U",  # FDE-13 新
    "EnzxjcHKb7JLLj5CpkCQJTb6Qrnfl41tWfvk1NVeck2OYA2A4jlN881DlvLv3uto",  # GROW-08 新
    "EnzxjcHKb7JLLj5CpkCQJcpq9j0LxAzP93EXB1H0fAeNklDo-zQHxhlwbuFQTBoB",  # T-936 新
}

def tok():
    secret = [t for t in re.findall(r"[A-Za-z0-9]{32}", open(SECRET_FILE, encoding="utf-8").read())][-1]
    u = f"{API}/token?grant_type=client_credential&appid={APPID}&secret={secret}"
    return json.load(urllib.request.urlopen(u, timeout=30))["access_token"]

def post(t, path, payload):
    r = urllib.request.urlopen(urllib.request.Request(
        f"{API}/{path}?access_token={t}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}), timeout=30)
    return json.load(r)

t = tok()
# 全量拉取（分页）
items = []
off = 0
while True:
    r = post(t, "draft/batchget", {"offset": off, "count": 20, "no_content": 1})
    batch = r.get("item", [])
    items.extend(batch)
    off += len(batch)
    if len(batch) < 20 or off >= r.get("total_count", 0):
        break

print(f"草稿箱总数拉取: {len(items)}")
to_del = []
for it in items:
    mid = it.get("media_id", "")
    art = (it.get("content", {}).get("news_item") or [{}])[0]
    title = art.get("title", "")
    if title in TARGETS and mid not in KEEP:
        to_del.append((mid, title))

print(f"待删除旧稿 {len(to_del)} 篇:")
for mid, title in to_del:
    r = post(t, "draft/delete", {"media_id": mid})
    print(f"  delete {mid[-12:]}  [{title[:20]}] → errcode={r.get('errcode',0)} {r.get('errmsg','')}")

# 复核：剩余目标标题草稿
print("\n=== 复核：剩余目标标题草稿（应只剩3个新稿）===")
off = 0
while True:
    r = post(t, "draft/batchget", {"offset": off, "count": 20, "no_content": 1})
    for it in r.get("item", []):
        art = (it.get("content", {}).get("news_item") or [{}])[0]
        if art.get("title", "") in TARGETS:
            mid = it.get("media_id", "")
            tag = "✅新稿保留" if mid in KEEP else "🔴未删净"
            print(f"  {mid[-12:]}  [{art.get('title','')[:24]}]  {tag}")
    off += 20
    if off >= r.get("total_count", 0):
        break
