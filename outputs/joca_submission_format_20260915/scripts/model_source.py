#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""建立原稿内容模型：逐块分类 + 记录局部格式（加粗/上下标/斜体/字体）。"""
import zipfile, json, re, sys
from lxml import etree
NW = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
RW = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
DW = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
AW = 'http://schemas.openxmlformats.org/drawingml/2006/main'
def W(t): return '{%s}%s' % (NW, t)
def R(t): return '{%s}%s' % (RW, t)
def tag(e): return etree.QName(e).localname
def text_of(e): return ''.join(e.itertext())

SRC = '00_input_backup/原稿_Hybrid_TEE_Rollup修改版.docx'
z = zipfile.ZipFile(SRC)
doc = etree.fromstring(z.read('word/document.xml'))
body = doc.find(W('body'))

blocks = []
pi = 0
ti = 0
for ch in body:
    t = tag(ch)
    if t == 'p':
        runs = []
        for r in ch.findall(W('r')):
            rp = r.find(W('rPr'))
            info = {'t': ''.join(r.itertext())}
            if rp is not None:
                for x in rp:
                    n = tag(x)
                    if n == 'vertAlign': info['va'] = x.get(W('val'))
                    elif n in ('b', 'bCs') and (x.get(W('val')) not in ('0', 'false')): info['b'] = 1
                    elif n == 'i' and (x.get(W('val')) not in ('0', 'false')): info['i'] = 1
                    elif n == 'rFonts':
                        ea = x.get(W('eastAsia')); asc = x.get(W('ascii'))
                        if ea: info['ea'] = ea
                        if asc: info['asc'] = asc
                    elif n == 'sz': info['sz'] = x.get(W('val'))
                    elif n == 'color': info['color'] = x.get(W('val'))
                    elif n == 'rStyle': info['rStyle'] = x.get(W('val'))
                    elif n == 'highlight': info['hl'] = x.get(W('val'))
                    elif n == 'u': info['u'] = x.get(W('val')) or 'on'
            if r.find(W('drawing')) is not None: info['drawing'] = True
            if r.find(W('tab')) is not None: info['tab'] = True
            if r.find(W('br')) is not None: info['br'] = True
            runs.append(info)
        blocks.append({'kind': 'p', 'i': pi, 'text': text_of(ch), 'runs': runs,
                       'has_sect': (ch.find(W('pPr')) is not None and ch.find(W('pPr')).find(W('sectPr')) is not None)})
        pi += 1
    elif t == 'tbl':
        trs = ch.findall(W('tr'))
        cells = []
        for tr in trs:
            row = []
            for tc in tr.findall(W('tc')):
                cellp = []
                for p in tc.findall(W('p')):
                    cellp.append({'text': text_of(p), 'drawing': p.find('.//' + W('drawing')) is not None})
                tcpr = tc.find(W('tcPr'))
                tcw = tcpr.find(W('tcW')) if tcpr is not None else None
                span = tcpr.find(W('gridSpan')) if tcpr is not None else None
                row.append({'paras': cellp, 'w': tcw.get(W('w')) if tcw is not None else None,
                            'span': span.get(W('val')) if span is not None else None})
            cells.append(row)
        tblw = ch.find(W('tblPr')).find(W('tblW')) if ch.find(W('tblPr')) is not None else None
        blocks.append({'kind': 'tbl', 'i': ti, 'rows': len(trs),
                       'cols': len(trs[0].findall(W('tc'))) if trs else 0,
                       'tblW': (tblw.get(W('w')), tblw.get(W('type'))) if tblw is not None else None,
                       'cells': cells})
        ti += 1
    else:
        blocks.append({'kind': t})

json.dump(blocks, open(sys.argv[1] if len(sys.argv) > 1 else '03_models/source_blocks.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# 打印摘要视图
print('块总数:', len(blocks), '| 段落:', pi, '| 表格:', ti)
print()
print('===== 非默认局部格式的段落 =====')
for b in blocks:
    if b['kind'] != 'p':
        continue
    odd = [r for r in b['runs'] if any(k in r for k in ('b', 'i', 'va', 'rStyle', 'hl', 'u', 'color'))]
    if odd:
        print('p%-3d %r' % (b['i'], b['text'][:44]))
        for r in b['runs'][:8]:
            if any(k in r for k in ('b', 'i', 'va', 'rStyle', 'hl', 'u', 'color', 'drawing')):
                print('      ', json.dumps(r, ensure_ascii=False))
print()
print('===== 表格概览 =====')
for b in blocks:
    if b['kind'] == 'tbl':
        print('TBL%d rows=%d cols=%d tblW=%s | 首行: %s' % (
            b['i'], b['rows'], b['cols'], b['tblW'],
            ' || '.join('/'.join(p['text'] for p in c['paras'])[:26] for c in b['cells'][0])))
