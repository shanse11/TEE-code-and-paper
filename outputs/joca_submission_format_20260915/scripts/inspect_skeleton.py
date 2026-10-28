#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打印 body 骨架：每个直接子元素一行（含分节符位置），并可导出指定段落原始 XML。"""
import sys, zipfile
from lxml import etree

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
def W(t): return '{%s}%s' % (NS['w'], t)
def R(t): return '{%s}%s' % (NS['r'], t)
def txt(e): return ''.join(e.itertext())

path = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else 'skeleton'
z = zipfile.ZipFile(path)
doc = etree.fromstring(z.read('word/document.xml'))
body = doc.find(W('body'))

if mode == 'skeleton':
    i = 0
    for child in body:
        tag = etree.QName(child).localname
        if tag == 'p':
            ppr = child.find(W('pPr'))
            sect = ppr.find(W('sectPr')) if ppr is not None else None
            ps = ppr.find(W('pStyle')) if ppr is not None else None
            sid = ps.get(W('val')) if ps is not None else '-'
            flags = []
            if sect is not None:
                cols = sect.find(W('cols')); mar = sect.find(W('pgMar'))
                flags.append('SECTPR(cols=%s,L=%s,R=%s)' % (
                    (cols.get(W('num')) if cols is not None and cols.get(W('num')) else '1'),
                    (mar.get(W('left')) if mar is not None else '?'),
                    (mar.get(W('right')) if mar is not None else '?')))
            if child.findall('.//' + W('drawing')): flags.append('DRAW')
            if child.findall('.//' + W('commentRangeStart')): flags.append('CMT')
            if child.findall('.//' + W('commentReference')): flags.append('CMTREF')
            if child.findall('.//' + W('tab')): flags.append('TAB')
            print('[%03d] p <%s> %s | %s' % (i, sid, ' '.join(flags), txt(child)[:70].replace('\n', '\\n')))
            i += 1
        elif tag == 'tbl':
            print('[---] TBL rows=%d | %s' % (len(child.findall(W('tr'))),
                  txt(child.findall(W('tr'))[0]).replace('\n', '\\n')[:60] if child.findall(W('tr')) else ''))
        elif tag == 'sectPr':
            cols = child.find(W('cols')); mar = child.find(W('pgMar'))
            print('[===] FINAL sectPr cols=%s L=%s R=%s' % (
                (cols.get(W('num')) if cols is not None and cols.get(W('num')) else '1'),
                mar.get(W('left')), mar.get(W('right'))))
        else:
            print('[---] %s' % tag)
elif mode == 'xml':
    idxs = [int(x) for x in sys.argv[3].split(',')]
    pi = 0
    for child in body:
        if etree.QName(child).localname == 'p':
            if pi in idxs:
                print('===== paragraph %d =====' % pi)
                print(etree.tostring(child, encoding='unicode', pretty_print=True))
            pi += 1
elif mode == 'sects':
    # 详细列出每个 sectPr（含 headerReference 的真实 r:id）
    for k, s in enumerate(body.iter(W('sectPr'))):
        print('--- sectPr #%d ---' % k)
        print(etree.tostring(s, encoding='unicode', pretty_print=True))
