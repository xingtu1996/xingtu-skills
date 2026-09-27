#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cert_desc_scan.py — 认证描述字数 + 禁词 + 硬命中扫描器（可执行门禁）

用法：
    python3 cert_desc_scan.py "<描述文本>"
    python3 cert_desc_scan.py --file /tmp/desc.txt
    python3 cert_desc_scan.py --file desc.txt --limit 240 --badge "技术主管"
    python3 cert_desc_scan.py --file desc.txt --json  # 机器可读输出

退出码：
    0 = 全绿，可提交
    1 = 命中禁词/硬命中/字数超限/头衔不一致，阻断提交
    2 = 参数错误

设计原则：
    - 与工作区 tools/privacy_scan.py 同源禁词表（SAF-004/010/013）
    - 与 reference.md §二 禁词全表逐字一致
    - 输出人类可读 + 机器可读（--json）双模式
    - 不修改任何文件，纯扫描
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

# ─────────────────────────────────────────────────────────
# 禁词表（与 reference.md §二 同源，改一处必须改两处）
# ─────────────────────────────────────────────────────────

# A. 广告法禁词（🔴 硬命中）
AD_LAW_BANNED = [
    "最", "第一", "国家级", "世界级", "顶级", "顶尖", "极致", "绝对", "唯一",
    "首个", "首选", "独家", "独创", "领先", "领导者", "领袖", "王牌", "金牌",
    "名牌", "保证", "承诺", "担保", "100%", "永久", "万能", "通用", "全能",
    "特价", "低价", "清仓", "抢购", "爆款", "治疗", "治愈", "疗效", "根治",
    "痊愈", "中奖", "抽奖", "免费领", "返现", "返佣",
]

# B. 平台禁修饰词（🔴 硬命中）
PLATFORM_BANNED_MODIFIERS = [
    "资深", "知名", "著名", "有名", "大牌", "大咖", "大牛", "大神",
    "一线", "前沿", "优秀", "卓越", "杰出", "出色",
    "权威", "专家", "导师", "大师", "宗师",
    "优质", "精品", "精选", "精良",
    "深耕", "专注多年", "多年经验", "丰富经验",
    "网红", "火爆", "热门", "实力派", "hardcore", "骨灰级",
]

# C. 真名与英文名（🔴 SAF-010 致命红线）
#    与 tools/privacy_scan.py 同源；工作区专属真名在此维护
REAL_NAMES = [
    "<REALNAME_ZH>", "<EN_NAME_FULL>", "<EN_NAME>", "<PINYIN_FULL>", "<PINYIN>",  # 替换为你自己的红线词
    "J. Li", "j.li", "jiali", "liacheng", "Li Acheng",
]

# D. 公司全称标记（🔴 SAF-004）
COMPANY_SUFFIXES = [
    "有限公司", "股份公司", "股份有限公司", "集团", "控股",
]

# E. 可反推三元组（🟨 组合命中报警）
#    注册资本数字
REGISTERED_CAPITAL_PATTERN = re.compile(r"(\d+\s*(?:万|亿|万元|亿元))")
#    城市/园区
CITIES_AND_PARKS = [
    "北京", "上海", "深圳", "杭州", "广州", "成都", "南京", "武汉", "西安",
    "苏州", "天津", "重庆", "长沙", "青岛", "沈阳", "大连", "厦门", "宁波",
    "中关村", "张江", "科技园", "产业园", "高新区", "开发区", "软件园",
    "创业园", "孵化园", "总部基地",
]
#    精确职务年限
EXACT_YEARS_PATTERN = re.compile(r"(\d+)\s*年(?:经验|以上|工作|从业)?")

# F. 导流词（🔴 平台明文禁）
TRAFFIC_DIVERSION = [
    "加微信", "加V", "加v", "公众号搜索", "扫码关注", "关注领取",
    "知识星球", "小册", "专栏", "付费", "购买", "下单",
    "咨询", "私聊", "私信", "联系我", "加我",
    "官网", "www.", "http://", "https://", ".com", ".cn", ".net",
]

# ─────────────────────────────────────────────────────────
# 扫描逻辑
# ─────────────────────────────────────────────────────────

def scan(text: str, limit: int = 240, badge: str | None = None) -> dict:
    """扫描认证描述，返回命中报告。

    Args:
        text: 认证描述全文
        limit: 字数上限（公众号默认 240）
        badge: 头衔字面（钉钉名片原文），用于逐字一致校验；None = 跳过该校验

    Returns:
        {
            "char_count": int,
            "limit": int,
            "over_limit": bool,
            "hits": {
                "ad_law_banned": [str],
                "platform_banned_modifiers": [str],
                "real_names": [str],
                "company_suffixes": [str],
                "registered_capital": [str],
                "cities_and_parks": [str],
                "exact_years": [str],
                "traffic_diversion": [str],
            },
            "badge_check": {
                "badge": str | None,
                "present_in_text": bool | None,
                "passed": bool | None,
            },
            "triad_risk": bool,  # 三元组同时命中
            "passed": bool,
            "blocking_reasons": [str],
        }
    """
    char_count = len(text)
    over_limit = char_count > limit

    hits: dict[str, list[str]] = {
        "ad_law_banned": [],
        "platform_banned_modifiers": [],
        "real_names": [],
        "company_suffixes": [],
        "registered_capital": [],
        "cities_and_parks": [],
        "exact_years": [],
        "traffic_diversion": [],
    }

    # 简单子串命中（大小写不敏感用于英文名）
    text_lower = text.lower()
    for w in AD_LAW_BANNED:
        if w in text:
            hits["ad_law_banned"].append(w)
    for w in PLATFORM_BANNED_MODIFIERS:
        if w.lower() in text_lower:
            hits["platform_banned_modifiers"].append(w)
    for w in REAL_NAMES:
        if w.lower() in text_lower:
            hits["real_names"].append(w)
    for w in COMPANY_SUFFIXES:
        if w in text:
            hits["company_suffixes"].append(w)
    for w in TRAFFIC_DIVERSION:
        if w.lower() in text_lower:
            hits["traffic_diversion"].append(w)
    for w in CITIES_AND_PARKS:
        if w in text:
            hits["cities_and_parks"].append(w)

    # 正则命中
    hits["registered_capital"] = [m.group(0) for m in REGISTERED_CAPITAL_PATTERN.finditer(text)]
    hits["exact_years"] = [m.group(0) for m in EXACT_YEARS_PATTERN.finditer(text) if int(m.group(1)) >= 3]

    # 三元组风险：行业类目 + 精确注册资本 + 管理职位
    #   简化判定：注册资本数字 + 城市/园区 同时命中 → 高风险
    #   完整判定需要行业类目词表，此处给保守报警
    triad_risk = bool(hits["registered_capital"] and (hits["cities_and_parks"] or hits["company_suffixes"]))

    # 头衔字面校验
    badge_check: dict = {"badge": badge, "present_in_text": None, "passed": None}
    if badge is not None:
        present = badge in text
        badge_check["present_in_text"] = present
        badge_check["passed"] = present

    # 阻断原因
    blocking_reasons: list[str] = []
    if over_limit:
        blocking_reasons.append(f"字数超限：{char_count}/{limit}")
    if hits["ad_law_banned"]:
        blocking_reasons.append(f"广告法禁词命中：{', '.join(hits['ad_law_banned'])}")
    if hits["platform_banned_modifiers"]:
        blocking_reasons.append(f"平台禁修饰词命中：{', '.join(hits['platform_banned_modifiers'])}")
    if hits["real_names"]:
        blocking_reasons.append(f"真名/英文名命中（SAF-010 🔴）：{', '.join(hits['real_names'])}")
    if hits["company_suffixes"]:
        blocking_reasons.append(f"公司全称标记命中（SAF-004）：{', '.join(hits['company_suffixes'])}")
    if hits["traffic_diversion"]:
        blocking_reasons.append(f"导流词命中：{', '.join(hits['traffic_diversion'])}")
    if triad_risk:
        blocking_reasons.append(
            f"可反推三元组风险（SAF-013）：注册资本 {hits['registered_capital']} + "
            f"城市/园区 {hits['cities_and_parks']} + 公司标记 {hits['company_suffixes']}"
        )
    if badge is not None and badge_check["passed"] is False:
        blocking_reasons.append(f"头衔字面不一致：描述未包含「{badge}」（与名片逐字一致铁律）")

    passed = not blocking_reasons

    return {
        "char_count": char_count,
        "limit": limit,
        "over_limit": over_limit,
        "hits": hits,
        "badge_check": badge_check,
        "triad_risk": triad_risk,
        "passed": passed,
        "blocking_reasons": blocking_reasons,
    }


# ─────────────────────────────────────────────────────────
# 输出格式化
# ─────────────────────────────────────────────────────────

def format_human(report: dict, text: str) -> str:
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("认证描述扫描报告")
    lines.append("=" * 60)
    lines.append(f"文本：{text}")
    lines.append(f"字数：{report['char_count']}/{report['limit']}")
    lines.append("")

    if report["passed"]:
        lines.append("✅ 全绿，可提交")
    else:
        lines.append("🔴 阻断，不可提交")
        lines.append("")
        lines.append("阻断原因：")
        for reason in report["blocking_reasons"]:
            lines.append(f"  - {reason}")
        lines.append("")

    # 命中详情（无论是否阻断都输出，便于诊断）
    lines.append("命中详情：")
    for category, words in report["hits"].items():
        if words:
            lines.append(f"  {category}: {', '.join(words)}")
    if not any(report["hits"].values()):
        lines.append("  （无命中）")

    if report["badge_check"]["badge"] is not None:
        lines.append("")
        badge = report["badge_check"]["badge"]
        present = report["badge_check"]["present_in_text"]
        lines.append(f"头衔字面校验：「{badge}」 {'✅ 出现在描述中' if present else '🔴 未出现'}")

    if report["triad_risk"]:
        lines.append("")
        lines.append("⚠️  三元组风险：建议模糊注册资本或城市/园区中至少一项")

    lines.append("=" * 60)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────

def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="认证描述字数 + 禁词 + 硬命中扫描器（可执行门禁）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("text", nargs="?", help="认证描述文本（位置参数）")
    parser.add_argument("--file", "-f", type=Path, help="从文件读取描述文本")
    parser.add_argument("--limit", "-l", type=int, default=240, help="字数上限（默认 240，公众号口径）")
    parser.add_argument("--badge", "-b", type=str, default=None, help="头衔字面（钉钉名片原文），校验逐字一致")
    parser.add_argument("--json", action="store_true", help="输出 JSON（机器可读）")
    args = parser.parse_args(list(argv) if argv is not None else None)

    # 读取文本
    if args.file:
        if not args.file.exists():
            print(f"错误：文件不存在 {args.file}", file=sys.stderr)
            return 2
        text = args.file.read_text(encoding="utf-8").strip()
    elif args.text:
        text = args.text.strip()
    else:
        print("错误：必须提供描述文本（位置参数或 --file）", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 2

    if not text:
        print("错误：描述文本为空", file=sys.stderr)
        return 2

    # 扫描
    report = scan(text, limit=args.limit, badge=args.badge)

    # 输出
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_human(report, text))

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
