#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最后一轮结构探查：图片环绕方式、示例表格边框、原稿图表容器结构、页眉页脚关系、原稿分节位置。"""
import zipfile, json
from lxml import etree
NW = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
RW = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
MW = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
def W(t): return '{%s}%s' % (NW, t)
def R(t): return '{%s}%s' % (RW, t)
def M(t): return '{%s}%s' % (MW, t)
def tag(e): return etree.QName(e).localname
def compact(el):
    if el is None: return None
    out = []
    for c in el:
        attrs = {etree.QName(k).localname: v for k, v in c.attrib.items()}
        kids = compact(c)
        d = {tag(c): (attrs or None)}
        if kids: d['kids'] = kids
        out.append(d)
    return out

TPL = '02_template_docx/模板_投稿模版.docx'
SRC = '00_input_backup/原稿_Hybrid_TEE_Rollup修改版.docx'

print('#' * 30, '模板：document.xml.rels（页眉页脚映射）')
zt = zipfile.ZipFile(TPL)
rels = etree.fromstring(zt.read('word/_rels/document.xml.rels'))
for r in rels:
    t = r.get('Type').rsplit('/', 1)[-1]
    if t in ('header', 'footer', 'image', 'comments', 'numbering', 'styles', 'settings', 'fontTable', 'theme'):
        print('  %-10s %-8s -> %s' % (t, r.get('Id'), r.get('Target')))

print()
print('#' * 30, '模板：正文中的 sectPr 引用的 r:id')
tplbody = etree.fromstring(zt.read('word/document.xml')).find(W('body'))
for i, s in enumerate(tplbody.iter(W('sectPr'))):
    refs = [(tag(x), x.get(W('type')), x.get(R('id'))) for x in list(s) if tag(x) in ('headerReference', 'footerReference')]
    print('  sect#%d %s' % (i, refs))

print()
print('#' * 30, '模板：示例表格 TBL2（UCI 数据集）边框')
ti = 0
for tbl in tplbody.findall(W('tbl')):
    if ti == 2:
        print('  tblPr:', json.dumps(compact(tbl.find(W('tblPr'))), ensure_ascii=False))
        tr = tbl.findall(W('tr'))
        for ri, r in enumerate(tr[:2]):
            for ci, tc in enumerate(r.findall(W('tc'))):
                print('  r%d c%d tcPr:' % (ri, ci), json.dumps(compact(tc.find(W('tcPr'))), ensure_ascii=False))
        break
    ti += 1

print()
print('#' * 30, '原稿：图片容器与环绕方式')
zs = zipfile.ZipFile(SRC)
sbody = etree.fromstring(zs.read('word/document.xml')).find(W('body'))
for di, d in enumerate(sbody.iter(W('drawing'))):
    parent = d.getparent()
    chain = []
    p = d
    while p is not None and tag(p) != 'body':
        chain.append(tag(p)); p = p.getparent()
    kind = None
    for ch in d.iter():
        if tag(ch) in ('inline', 'anchor'):
            kind = tag(ch)
            ext = ch.find('{%s}extent' % 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing')
            print('  drawing#%d kind=%s extent=%s' % (di, kind, (ext.attrib if ext is not None else None)))
            break
    print('      链:', ' < '.join(chain))
    for blip in d.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}blip'):
        print('      blip r:embed =', blip.get(R('embed')))

print()
print('#' * 30, '原稿：四个 1×1 图片表格的内部结构（第 1 个）')
tbls = sbody.findall(W('tbl'))
for i, tbl in enumerate(tbls[:4]):
    print('  表格#%d 行数=%d' % (i, len(tbl.findall(W('tr')))))
    for ri, r in enumerate(tbl.findall(W('tr'))):
        for ci, tc in enumerate(r.findall(W('tc'))):
            print('    r%d c%d:' % (ri, ci))
            for pi, p in enumerate(tc.findall(W('p'))):
                ppr = p.find(W('pPr'))
                print('       p%d pPr=%s text=%r hasDraw=%s' % (
                    pi, json.dumps(compact(ppr), ensure_ascii=False),
                    ''.join(p.itertext()), p.find('.//' + W('drawing')) is not None))
    if i >= 1:
        break

print()
print('#' * 30, '原稿：真实表格 tblPr 与首行 tcPr（表4）')
for i, tbl in enumerate(tbls):
    trs = tbl.findall(W('tr'))
    if len(trs) > 1:
        print('  表格#%d rows=%d cols=%d' % (i, len(trs), len(trs[0].findall(W('tc')))))
        print('    tblPr:', json.dumps(compact(tbl.find(W('tblPr'))), ensure_ascii=False))
        for ci, tc in enumerate(trs[0].findall(W('tc'))):
            print('    r0c%d tcPr:' % ci, json.dumps(compact(tc.find(W('tcPr'))), ensure_ascii=False))
        break

print()
print('#' * 30, '原稿：分节位置')
pi = 0
for ch in sbody:
    if tag(ch) == 'p':
        ppr = ch.find(W('pPr'))
        s = ppr.find(W('sectPr')) if ppr is not None else None
        if s is not None:
            print('  p%d 带 sectPr: %s | %r' % (pi, json.dumps(compact(s), ensure_ascii=False)[:400], ''.join(ch.itertext())[:40]))
        pi += 1
    elif tag(ch) == 'sectPr':
        print('  末尾 sectPr:', json.dumps(compact(ch), ensure_ascii=False)[:400])

print()
print('#' * 30, '原稿：run 级直接格式统计（前 30 段）')
pi = 0
for ch in sbody:
    if tag(ch) == 'p' and pi < 30:
        rs = []
        for r in ch.findall(W('r')):
            rp = r.find(W('rPr'))
            if rp is not None:
                rs.append({tag(x): ({etree.QName(k).localname: v for k, v in x.attrib.items()} or 'on') for x in rp})
        print('  p%-3d %r  rPr=%s' % (pi, ''.join(ch.itertext())[:30], json.dumps(rs, ensure_ascii=False)[:260]))
        pi += 1
