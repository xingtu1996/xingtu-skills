#!/usr/bin/env python3
"""裁掉 HTML 全页截图尾部的空白（默认背景 #f7f8fa）。

用法:
    python3 crop_tail.py <input.png> <output.png> [--bg 247,248,250] [--tol 4] [--pad 40]

原理: 从图片底部逐行往上扫描，找到第一个「与背景色差异超过 tol」的行，
      在其下方保留 pad 像素作为留白，裁掉其余部分。
"""
import argparse
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow:  pip install pillow")


def crop_tail(src, dst, bg=(247, 248, 250), tol=4, pad=40, step_y=2, step_x=5):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    px = im.load()
    last = h - 1
    for y in range(h - 1, -1, -step_y):
        row_has_content = False
        for x in range(0, w, step_x):
            r, g, b = px[x, y]
            if abs(r - bg[0]) > tol or abs(g - bg[1]) > tol or abs(b - bg[2]) > tol:
                row_has_content = True
                break
        if row_has_content:
            last = y
            break
    new_h = min(h, last + pad)
    im.crop((0, 0, w, new_h)).save(dst)
    print(f"{src} -> {dst}  {w}x{new_h}  (raw {w}x{h})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--bg", default="247,248,250", help="背景色 R,G,B")
    ap.add_argument("--tol", type=int, default=4)
    ap.add_argument("--pad", type=int, default=40, help="底部保留留白像素")
    a = ap.parse_args()
    crop_tail(a.src, a.dst, bg=tuple(int(v) for v in a.bg.split(",")),
              tol=a.tol, pad=a.pad)
