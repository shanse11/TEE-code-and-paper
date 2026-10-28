#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF -> 逐页 PNG + 拼版总览图（依赖 pypdfium2 / PIL）"""
import sys, os, math
import pypdfium2 as pdfium
from PIL import Image, ImageDraw

def render(pdf_path, outdir, dpi=110, prefix='page'):
    os.makedirs(outdir, exist_ok=True)
    doc = pdfium.PdfDocument(pdf_path)
    scale = dpi / 72.0
    paths = []
    for i in range(len(doc)):
        page = doc[i]
        img = page.render(scale=scale).to_pil()
        p = os.path.join(outdir, f'{prefix}-{i+1:02d}.png')
        img.save(p)
        paths.append(p)
        page.close()
    doc.close()
    return paths

def contact_sheet(paths, out_path, cols=4, cell_w=460, label=True):
    if not paths:
        return None
    thumbs = []
    for p in paths:
        im = Image.open(p).convert('RGB')
        r = cell_w / im.width
        thumbs.append((os.path.basename(p), im.resize((cell_w, max(1, int(im.height * r))), Image.LANCZOS)))
    rows = math.ceil(len(thumbs) / cols)
    row_h = [0] * rows
    for i, (_, t) in enumerate(thumbs):
        row_h[i // cols] = max(row_h[i // cols], t.height)
    pad, top = 10, (22 if label else 0)
    W = cols * cell_w + (cols + 1) * pad
    H = sum(h + top + pad for h in row_h) + pad
    sheet = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(sheet)
    y = pad
    for r_i in range(rows):
        x = pad
        for c_i in range(cols):
            i = r_i * cols + c_i
            if i >= len(thumbs):
                break
            name, t = thumbs[i]
            if label:
                d.text((x, y + 4), name, fill='black')
            sheet.paste(t, (x, y + top))
            x += cell_w + pad
        y += row_h[r_i] + top + pad
    sheet.save(out_path)
    return out_path

if __name__ == '__main__':
    pdf = sys.argv[1]
    outdir = sys.argv[2]
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 110
    prefix = sys.argv[4] if len(sys.argv) > 4 else 'page'
    sheet = sys.argv[5] if len(sys.argv) > 5 else None
    paths = render(pdf, outdir, dpi, prefix)
    print(f'rendered {len(paths)} pages -> {outdir}')
    if sheet:
        contact_sheet(paths, sheet)
        print('contact sheet ->', sheet)
