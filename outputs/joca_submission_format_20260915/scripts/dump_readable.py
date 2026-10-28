#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 audit_docx 输出渲染成人类可读的清单（正文元素序列 + 样式 + 批注锚点）。"""
import json, sys, zipfile, re
from lxml import etree

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def W(t): return '{%s}%s' % (NS['w'], t)
def txt(e): return ''.join(e.itertext())

audit_path, docx_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
rep = json.load(open(audit_path, encoding='utf-8'))
z = zipfile.ZipFile(docx_path)
doc = etree.fromstring(z.read('word/document.xml'))
body = doc.find(W('body'))

lines = []
lines.append('=' * 100)
lines.append(f"DOCX: {docx_path}")
lines.append('=' * 100)
lines.append('')
lines.append('--- 样式清单 (styles.xml) ---')
for s in rep['styles']:
    if s.get('default') == '1' or s['styleId'] in ('Normal',):
        pass
    lines.append(json.dumps(s, ensure_ascii=False))
lines.append('')
lines.append('--- docDefaults ---')
lines.append(json.dumps({'rPr': rep.get('docDefaults'), 'pPr': rep.get('docDefaults_pPr')}, ensure_ascii=False, indent=1))
lines.append('')
lines.append('--- 分节 ---')
for i, s in enumerate(rep['sections']):
    lines.append(f'[{i}] ' + json.dumps(s, ensure_ascii=False))
lines.append('')
lines.append('--- 页眉页脚 ---')
for k, v in rep['headers_footers'].items():
    lines.append(f'{k}: text={v["text"]!r}')
    for p in v['paras']:
        lines.append(f'    style={p["style"]} text={p["text"]!r} drawing={p["hasDrawing"]} fld={p["hasFld"]}')
lines.append('')
lines.append('--- 编号定义 ---')
lines.append(json.dumps(rep.get('numbering', {}), ensure_ascii=False, indent=1))
lines.append('')
lines.append('--- 批注 (%d) ---' % len(rep['comments']))
for c in rep['comments']:
    lines.append(f"  id={c['id']} author={c['author']} :: {c['text']}")
lines.append('')
lines.append('--- 正文元素序列（按文档顺序，含表格） ---')

# 重建顺序：使用 audit 的 body_sequence 不好定位表格内容，这里直接遍历 XML
p_i = 0
t_i = 0
for child in body:
    tag = etree.QName(child).localname
    if tag == 'p':
        ppr = child.find(W('pPr'))
        ps = ppr.find(W('pStyle')) if ppr is not None else None
        sid = ps.get(W('val')) if ps is not None else '(none)'
        t = txt(child)
        marks = []
        if child.findall('.//' + W('commentRangeStart')) or child.findall('.//' + W('commentReference')):
            marks.append('COMMENT')
        if child.findall('.//' + W('drawing')):
            marks.append('DRAWING')
        if child.findall('.//' + W('ins')): marks.append('INS')
        if child.findall('.//' + W('del')): marks.append('DEL')
        if child.findall('.//' + W('tab')): marks.append('TAB')
        if child.findall('.//' + {'w': NS['w']}[ 'w'] if False else W('footnoteReference')): marks.append('FN')
        # 批注锚点 id
        cids = [c.get(W('id')) for c in child.findall('.//' + W('commentRangeStart'))]
        cids += [c.get(W('id')) for c in child.findall('.//' + W('commentReference'))]
        lines.append(f"[p{p_i:03d}] <{sid}> {'|'.join(marks)} {t!r}")
        if sid in ('(none)',) and ppr is not None:
            lines.append(f"        pPr={etree.tostring(ppr, encoding='unicode')[:500]}")
    elif tag == 'tbl':
        rows = child.findall(W('tr'))
        lines.append(f"[TBL{t_i}] rows={len(rows)}")
        for r_i, tr in enumerate(rows):
            cells = []
            for tc in tr.findall(W('tc')):
                cells.append(txt(tc).replace('\n', '⏎'))
            lines.append(f"    r{r_i}: " + ' || '.join(repr(c) for c in cells))
        t_i += 1
    elif tag == 'sectPr':
        lines.append('[SECTPR 段末节属性]')
    else:
        lines.append(f'[{tag}]')

lines.append('')
lines.append('--- 媒体 ---')
for m in rep['media']:
    lines.append('  ' + m)

open(out_path, 'w', encoding='utf-8').write('\n'.join(lines))
print('written', out_path, len(lines), 'lines')
