#!/usr/bin/env python3
"""微信群成员 × 好友交集分析：查指定群里有多少微信好友，辅助判断能不能在该群发公众号。

好友判定口径（v2 修正，2026-09-16）：
  旧口径 local_type=0/1 收录了所有聊过天的人（含群里见过但没加的），误报率高。
  新口径：对群每个成员，检查是否有独立单聊消息表 Msg_<md5(wxid)> 且消息数>0。
  这等价于"加过好友且聊过天"——没加好友的人不会有单聊会话。

数据来源：
  - contact/contact_fts.db : name2id + contact_fts_v5 + chatroom_member_fts_v3
  - message/message_*.db   : 单聊消息表（验证好友身份）

用法：
  python3 group_friend_check.py "PEC"              # 按群名关键词搜
  python3 group_friend_check.py --wxid 49535621631@chatroom
  python3 group_friend_check.py "AI Work" --json    # JSON 输出
"""
import sqlite3, sys, os, json, argparse, re, hashlib, glob

BASE = os.path.expanduser("~/xingtu/data/wechat_decrypted_latest")
DB_PATH = os.path.join(BASE, "contact/contact_fts.db")
MSG_DIR = os.path.join(BASE, "message")

SELF_WXID = "<YOUR_WECHAT_ID>"  # boss 自己的 wxid

LT_CHATROOM = 2
LT_WEWORK = 6


def extract_nickname(search_key: str) -> str:
    """从 search_key 中尽量提取可读昵称，去掉微信号/地区尾巴。"""
    if not search_key:
        return "(未知)"
    s = re.sub(r'[\x00-\x1f\x7f]', '', search_key).strip()
    if not s:
        return "(未知)"
    for _ in range(5):
        old = s
        s = re.sub(
            r'\s*(中国大陆|中国香港|中国澳门|中国台湾|'
            r'北京[\s\u4e00-\u9fff]*|上海[\s\u4e00-\u9fff]*|'
            r'天津|重庆|广东[\s\u4e00-\u9fff]*|广州[\s\u4e00-\u9fff]*|'
            r'深圳[\s\u4e00-\u9fff]*|杭州[\s\u4e00-\u9fff]*|'
            r'成都[\s\u4e00-\u9fff]*|武汉[\s\u4e00-\u9fff]*|'
            r'南京[\s\u4e00-\u9fff]*|西安[\s\u4e00-\u9fff]*|'
            r'苏州[\s\u4e00-\u9fff]*|长沙[\s\u4e00-\u9fff]*|'
            r'厦门[\s\u4e00-\u9fff]*|青岛[\s\u4e00-\u9fff]*|'
            r'大连[\s\u4e00-\u9fff]*|宁波[\s\u4e00-\u9fff]*|'
            r'无锡[\s\u4e00-\u9fff]*|佛山[\s\u4e00-\u9fff]*|'
            r'东莞[\s\u4e00-\u9fff]*|珠海[\s\u4e00-\u9fff]*|'
            r'香港[\s\u4e00-\u9fff]*|台北|高雄|不丹|埃及|百慕大)$', '', s)
        s = re.sub(r'([\u4e00-\u9fff])\s*[A-Za-z][A-Za-z0-9_]{3,}$', r'\1', s)
        if s == old:
            break
    return s.strip()[:30]


def find_room(cur, keyword: str, wxid: str = None):
    """定位群，返回 (room_id, room_name, chatroom_username) 或候选列表。"""
    if wxid:
        cur.execute("SELECT rowid, username FROM name2id WHERE username=?", (wxid,))
        row = cur.fetchone()
        if not row:
            return None
        room_id, username = row
        cur.execute("SELECT search_key FROM contact_fts_v5 WHERE rowid=? AND local_type=?",
                    (room_id, LT_CHATROOM))
        name_row = cur.fetchone()
        room_name = name_row[0] if name_row else username
        return room_id, room_name, username

    like = f"%{keyword}%"
    cur.execute("""
        SELECT f.rowid, f.search_key, n.username
        FROM contact_fts_v5 f
        JOIN name2id n ON f.rowid = n.rowid
        WHERE f.local_type=? AND f.search_key LIKE ?
        ORDER BY length(f.search_key)
    """, (LT_CHATROOM, like))
    rows = cur.fetchall()
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0][0], rows[0][1], rows[0][2]
    return rows


def load_msg_table_index():
    """一次性加载所有 message 库里的 Msg_<hash> 表名集合和对应消息数。"""
    msg_dbs = sorted(glob.glob(os.path.join(MSG_DIR, "message_[0-9]*.db")))
    table_msgs = {}  # table_name -> total messages across all dbs
    for mdb in msg_dbs:
        try:
            mc = sqlite3.connect(mdb)
            mcur = mc.cursor()
            mcur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
            for (tname,) in mcur.fetchall():
                try:
                    mcur.execute(f"SELECT COUNT(*) FROM '{tname}'")
                    table_msgs[tname] = table_msgs.get(tname, 0) + mcur.fetchone()[0]
                except Exception:
                    table_msgs[tname] = table_msgs.get(tname, 0)
            mc.close()
        except Exception:
            pass
    return table_msgs


def is_real_friend(wxid: str, table_msgs: dict) -> int:
    """检查 wxid 是否有独立单聊消息表，返回消息数（0=非好友）。"""
    # 群/企微号不是好友
    if wxid.endswith('@chatroom') or wxid.endswith('@openim') or wxid.endswith('@im.chatroom'):
        return 0
    if wxid == SELF_WXID:
        return 0
    h = hashlib.md5(wxid.encode()).hexdigest()
    tname = f"Msg_{h}"
    return table_msgs.get(tname, 0)


def run(keyword: str = None, wxid: str = None, as_json: bool = False):
    db = os.path.expanduser(DB_PATH)
    if not os.path.exists(db):
        print(f"错误：数据库不存在 {db}", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(db)
    cur = con.cursor()

    result = find_room(cur, keyword, wxid)
    if result is None:
        msg = f"未找到匹配的群：{keyword or wxid}"
        if as_json:
            print(json.dumps({"error": msg}, ensure_ascii=False))
        else:
            print(msg)
        sys.exit(1)

    if isinstance(result, list):
        if as_json:
            print(json.dumps({"error": "多个群匹配", "candidates": [
                {"room_id": r[0], "name": r[1], "username": r[2]} for r in result
            ]}, ensure_ascii=False, indent=2))
        else:
            print(f"「{keyword}」匹配到多个群，请用 --wxid 指定：")
            for r in result:
                print(f"  {r[2]:40s}  {r[1]}")
        sys.exit(1)

    room_id, room_name, chatroom_wxid = result

    # 群成员总数
    cur.execute("SELECT COUNT(DISTINCT member_id) FROM chatroom_member_fts_v3 WHERE room_id=?", (room_id,))
    total = cur.fetchone()[0]

    # 拿群所有成员的 wxid + 显示名
    cur.execute("""
        SELECT n.username, f.search_key, f.local_type
        FROM chatroom_member_fts_v3 g
        JOIN name2id n ON g.member_id = n.rowid
        LEFT JOIN contact_fts_v5 f ON g.member_id = f.rowid
        WHERE g.room_id = ?
    """, (room_id,))
    all_members = cur.fetchall()
    con.close()

    # 加载消息表索引，判定真好友
    table_msgs = load_msg_table_index()

    friends = []
    wework = []
    for wxid, search_key, ltype in all_members:
        if wxid == SELF_WXID:
            continue
        # 企微联系人单列
        if ltype == LT_WEWORK or wxid.endswith('@openim'):
            wework.append({"wxid": wxid, "display": extract_nickname(search_key)})
            continue
        # 检查是否有单聊消息
        dm_count = is_real_friend(wxid, table_msgs)
        if dm_count > 0:
            friends.append({
                "wxid": wxid,
                "display": extract_nickname(search_key),
                "dm_messages": dm_count,
            })

    # 按单聊消息数降序（聊得越多越熟）
    friends.sort(key=lambda x: -x["dm_messages"])

    friend_count = len(friends)
    density = friend_count / total * 100 if total else 0

    if density < 2:
        verdict = "🟢 可推"
        advice = "熟人密度低，公开推公众号问题不大"
    elif density <= 5:
        verdict = "🟡 谨慎"
        advice = "有少量熟人，建议用轻量话术/不点名"
    else:
        verdict = "🔴 不推"
        advice = "熟人密度高，容易被认出来，建议换群或私域转化"

    output = {
        "room_name": room_name,
        "room_wxid": chatroom_wxid,
        "total_members": total,
        "friend_count": friend_count,
        "wework_count": len(wework),
        "density_pct": round(density, 1),
        "verdict": verdict,
        "advice": advice,
        "friends": friends,
        "wework": wework,
    }

    if as_json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"群：{room_name}（{chatroom_wxid}）")
        print(f"总人数：{total}  |  真好友：{friend_count}  |  企微联系人：{len(wework)}")
        print(f"熟人密度：{density:.1f}%  {verdict}")
        print(f"建议：{advice}")
        print()
        if friends:
            print(f"—— 真好友（{len(friends)}人，按单聊活跃度排序）——")
            for f in friends:
                print(f"  • {f['display']}  ({f['dm_messages']}条单聊)")
            print()
        if wework:
            print(f"—— 企业微信联系人（{len(wework)}人）——")
            for w in wework:
                print(f"  • {w['display']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="微信群好友交集分析（v2：单聊表验证真好友）")
    ap.add_argument("keyword", nargs="?", help="群名关键词")
    ap.add_argument("--wxid", help="群 wxid（xxx@chatroom）")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args()

    if not args.keyword and not args.wxid:
        ap.print_help()
        sys.exit(1)

    run(keyword=args.keyword, wxid=args.wxid, as_json=args.json)
