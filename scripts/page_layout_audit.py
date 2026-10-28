# -*- coding: utf-8 -*-
"""逐页版面几何验收（v2）。

坐标系：PDF 用户空间，y 自页底向上。
检查项：页面尺寸、页眉/页脚、栏结构（直方图找中缝）、图像对象位置与宽度、
越出版心字符、文本重叠、空白页、每页首末行。
"""
import ctypes
from collections import Counter

import pypdfium2 as pdfium
import pypdfium2.raw as raw

PDF = "outputs/template_alignment/preview/Hybrid_TEE_Rollup_模板对齐版_预览.pdf"

# 版心（twips -> pt，1 twip = 1/20 pt）
ML, MR, MT, MB = 1191 / 20, 907 / 20, 1361 / 20, 680 / 20


def obj_bounds(o):
    l, b, r, t = ctypes.c_float(), ctypes.c_float(), ctypes.c_float(), ctypes.c_float()
    if raw.FPDFPageObj_GetBounds(o, l, b, r, t):
        return l.value, b.value, r.value, t.value
    return None


def audit():
    pdf = pdfium.PdfDocument(PDF)
    print(f"总页数: {len(pdf)}")
    for pi in range(len(pdf)):
        page = pdf[pi]
        w, h = page.get_size()
        tp = page.get_textpage()
        n = tp.count_chars()
        text = tp.get_text_range(0, n)
        chars = []
        for i in range(n):
            try:
                l, btm, r, top = tp.get_charbox(i, loose=False)
            except Exception:
                continue
            ch = text[i] if i < len(text) else "?"
            if ch.strip():
                chars.append((l, btm, r, top, ch))

        print("=" * 78)
        print(f"第 {pi+1} 页  {w/28.35:.1f} x {h/28.35:.1f} cm  字符 {len(chars)}")

        hdr = [c for c in chars if c[3] > h - MT + 6]
        ftr = [c for c in chars if c[1] < MB - 3]
        hdr.sort(key=lambda c: (round(c[1] / 6), c[0]))
        print(f"  页眉: {''.join(c[4] for c in hdr)[:80]!r}")
        print(f"  页脚: {''.join(c[4] for c in ftr)[:40]!r}")

        body = [c for c in chars if MB - 3 <= c[1] and c[3] <= h - MT + 6]
        if not body:
            print("  [!] 正文区无文本（疑似空白页）")
            for o in page.get_objects():
                if o.type == 3:
                    print("     （仅含图像对象）")
            continue

        # ---- 栏结构：x 中点直方图找中缝 ----
        x0, x1 = min(c[0] for c in body), max(c[2] for c in body)
        bins = [0] * int((x1 - x0) // 4 + 2)
        for c in body:
            m = (c[0] + c[2]) / 2
            bins[int((m - x0) // 4)] += 1
        mid_lo, mid_hi = int((x1 - x0) * 0.35 / 4), int((x1 - x0) * 0.65 / 4)
        nz = sorted(b for b in bins if b > 0)
        med = nz[len(nz) // 2] if nz else 0
        thr = max(2, int(med * 0.3))
        valley, best = None, 0
        run = 0
        for k in range(mid_lo, mid_hi):
            if bins[k] < thr:
                run += 1
                if run > best:
                    best, valley = run, k - run + 1
            else:
                run = 0
        if valley is not None and best * 4 >= 12:
            gl, gr = x0 + valley * 4, x0 + (valley + best) * 4
            print(f"  栏结构: 双栏  版心 x[{x0:.0f},{x1:.0f}]  中缝 [{gl:.0f},{gr:.0f}] 宽 {best*4:.0f}pt")
        else:
            print(f"  栏结构: 单栏/通栏  版心 x[{x0:.0f},{x1:.0f}]")

        # ---- 越界 ----
        out = [c for c in body if c[0] < x0 or c[2] > x1 + 0.5]
        L, R = ML, w - MR
        hard = [c for c in body if c[0] < L - 2 or c[2] > R + 2]
        print(f"  越出文本包络: {len(out)}   越出版心(L={L:.0f},R={R:.0f}): {len(hard)}"
              + (f"  例 {hard[:2]}" if hard else ""))

        # ---- 图像 ----
        imgs = []

        def walk(objs):
            for o in objs:
                if o.type == 3:
                    bd = obj_bounds(o.raw)
                    if bd:
                        imgs.append(bd)
                elif o.type == 5:
                    try:
                        walk(o.get_objects())
                    except Exception:
                        pass

        walk(page.get_objects())
        for (l, b, r, t) in imgs:
            iw = r - l
            print(f"  图像: x[{l:.0f},{r:.0f}] y[{b:.0f},{t:.0f}]  宽 {iw/28.35:.1f}cm  "
                  f"{'通栏' if iw > (R - L) * 0.9 else '栏内'}  距版心左 {l - L:.0f}pt")

        # ---- 重叠 ----
        boxes = sorted([(c[0], c[1], c[2], c[3]) for c in body], key=lambda b: (b[1], b[0]))
        ov = 0
        for i in range(len(boxes)):
            for j in range(i + 1, min(i + 8, len(boxes))):
                a, b2 = boxes[i], boxes[j]
                ix = min(a[2], b2[2]) - max(a[0], b2[0])
                iy = min(a[3], b2[3]) - max(a[1], b2[1])
                if ix > 2 and iy > 4:
                    ov += 1
        if ov:
            print(f"  [!] 疑似文本重叠对: {ov}")

        # ---- 行（按列分组后取首末行）----
        def lines_of(sub):
            sub = sorted(sub, key=lambda c: (-c[3], c[0]))
            res, cur, cury = [], [], None
            for c in sub:
                if cury is None or abs(c[3] - cury) < 3.5:
                    cur.append(c)
                    cury = c[3] if cury is None else cury
                else:
                    res.append("".join(x[4] for x in sorted(cur, key=lambda x: x[0])))
                    cur, cury = [c], c[3]
            if cur:
                res.append("".join(x[4] for x in sorted(cur, key=lambda x: x[0])))
            return [s for s in res if s.strip()]

        if valley is not None and best * 4 >= 12:
            left = lines_of([c for c in body if (c[0] + c[2]) / 2 < gl])
            right = lines_of([c for c in body if (c[0] + c[2]) / 2 >= gr])
            print(f"  左栏 {len(left)} 行: 首 {left[0][:40]!r} | 末 {left[-1][:40]!r}")
            print(f"  右栏 {len(right)} 行: 首 {right[0][:40]!r} | 末 {right[-1][:40]!r}")
        else:
            ls = lines_of(body)
            print(f"  {len(ls)} 行: 首 {ls[0][:56]!r} | 末 {ls[-1][:56]!r}")


if __name__ == "__main__":
    audit()
