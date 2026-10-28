#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用 DOCX 结构审计：样式 / 编号 / 分节 / 页眉页脚 / 批注 / 表格 / 图片 / 公式 / 正文元素序列。"""
import sys, json, zipfile, re
from collections import Counter, OrderedDict
from lxml import etree

NS = {
    'w':  'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r':  'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a':  'http://schemas.openxmlformats.org/drawingml/2006/main',
    'm':  'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'ct': 'http://schemas.openxmlformats.org/package/2006/content-types',
    'pr': 'http://schemas.openxmlformats.org/package/2006/relationships',
}
def q(t):
    p, l = t.split(':')
    return '{%s}%s' % (NS[p], l)

def W(t): return q('w:' + t)

def txt_of(el):
    return ''.join(el.itertext())

def style_name_map(styles_root):
    m = {}
    for s in styles_root.findall(W('style')):
        sid = s.get(W('styleId'))
        nm = s.find(W('name'))
        m[sid] = nm.get(W('val')) if nm is not None else sid
    return m

def rpr_summary(el):
    """从 rPr / pPr/rPr 提取字体字号等要点"""
    if el is None:
        return None
    out = {}
    rf = el.find(W('rFonts'))
    if rf is not None:
        f = {}
        for k in ('ascii', 'eastAsia', 'hAnsi', 'cs', 'hint'):
            v = rf.get(W(k))
            if v: f[k] = v
        if f: out['rFonts'] = f
    for tag, key in (('sz', 'sz'), ('szCs', 'szCs')):
        e = el.find(W(tag))
        if e is not None: out[key] = e.get(W('val'))
    for tag in ('b', 'i', 'u', 'strike', 'dstrike', 'smallCaps', 'caps', 'vanish'):
        e = el.find(W(tag))
        if e is not None:
            out[tag] = e.get(W('val')) or 'on'
    e = el.find(W('vertAlign'))
    if e is not None: out['vertAlign'] = e.get(W('val'))
    e = el.find(W('spacing'))
    if e is not None: out['charSpacing'] = e.get(W('val'))
    e = el.find(W('color'))
    if e is not None: out['color'] = e.get(W('val'))
    e = el.find(W('position'))
    if e is not None: out['position'] = e.get(W('val'))
    return out or None

def ppr_summary(ppr):
    if ppr is None:
        return None
    out = {}
    ps = ppr.find(W('pStyle'))
    if ps is not None: out['pStyle'] = ps.get(W('val'))
    for tag, key in (('jc', 'jc'), ('outlineLvl', 'outlineLvl'), ('textAlignment', 'textAlignment')):
        e = ppr.find(W(tag))
        if e is not None: out[key] = e.get(W('val'))
    e = ppr.find(W('numPr'))
    if e is not None:
        ilvl = e.find(W('ilvl')); nid = e.find(W('numId'))
        out['numPr'] = {'ilvl': ilvl.get(W('val')) if ilvl is not None else None,
                        'numId': nid.get(W('val')) if nid is not None else None}
    e = ppr.find(W('spacing'))
    if e is not None:
        out['spacing'] = {k: e.get(W(k)) for k in ('before', 'after', 'line', 'lineRule', 'beforeLines', 'afterLines') if e.get(W(k))}
    e = ppr.find(W('ind'))
    if e is not None:
        out['ind'] = {k: e.get(W(k)) for k in ('firstLine', 'left', 'right', 'hanging', 'firstLineChars', 'leftChars') if e.get(W(k))}
    tabs = ppr.find(W('tabs'))
    if tabs is not None:
        out['tabs'] = [{k: t.get(W(k)) for k in ('val', 'pos', 'leader')} for t in tabs.findall(W('tab'))]
    r = rpr_summary(ppr.find(W('rPr')))
    if r: out['rPr'] = r
    return out or None

def run_summary(r):
    out = {'t': r.text if r.text else ''}
    rp = rpr_summary(r.find(W('rPr')))
    if rp: out['rPr'] = rp
    if r.find(W('tab')) is not None: out['hasTab'] = True
    if r.find(W('drawing')) is not None: out['hasDrawing'] = True
    if r.find(W('object')) is not None: out['hasObject'] = True
    if r.find(W('commentReference')) is not None: out['hasCommentRef'] = True
    if r.find(W('footnoteReference')) is not None: out['hasFootnoteRef'] = True
    if r.find(W('br')) is not None: out['hasBr'] = True
    return out

def audit(path, out_json):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    rep = OrderedDict()
    rep['file'] = path
    rep['zip_entries'] = sorted(names)

    doc = etree.fromstring(z.read('word/document.xml'))
    body = doc.find(W('body'))

    # --- styles ---
    styles_root = etree.fromstring(z.read('word/styles.xml')) if 'word/styles.xml' in names else None
    smap = {}
    if styles_root is not None:
        smap = style_name_map(styles_root)
        styles = []
        for s in styles_root.findall(W('style')):
            e = OrderedDict()
            e['styleId'] = s.get(W('styleId'))
            e['type'] = s.get(W('type'))
            e['default'] = s.get(W('default'))
            nm = s.find(W('name')); e['name'] = nm.get(W('val')) if nm is not None else None
            bo = s.find(W('basedOn')); e['basedOn'] = bo.get(W('val')) if bo is not None else None
            no = s.find(W('next')); e['next'] = no.get(W('val')) if no is not None else None
            lnk = s.find(W('link')); e['link'] = lnk.get(W('val')) if lnk is not None else None
            lip = s.find(W('locked')); e['locked'] = lip.get(W('val')) if lip is not None else None
            sp = s.find(W('semiHidden')); e['semiHidden'] = True if sp is not None else None
            cu = s.find(W('customStyle')); e['customStyle'] = True if cu is not None else None
            ppr = ppr_summary(s.find(W('pPr')))
            if ppr: e['pPr'] = ppr
            rp = rpr_summary(s.find(W('rPr')))
            if rp: e['rPr'] = rp
            tbl = s.find(W('tblPr'))
            if tbl is not None: e['tblPr'] = True
            styles.append(e)
        rep['styles'] = styles
        rep['docDefaults'] = rpr_summary(
            styles_root.find(q('w:docDefaults')).find(q('w:rPrDefault')).find(W('rPr'))
        ) if styles_root.find(q('w:docDefaults')) is not None else None
        pdd = styles_root.find(q('w:docDefaults'))
        if pdd is not None:
            prd = pdd.find(q('w:pPrDefault'))
            rep['docDefaults_pPr'] = ppr_summary(prd.find(W('pPr'))) if prd is not None else None
        lat = styles_root.find(q('w:latentStyles'))
        if lat is not None:
            rep['latentStyles_count'] = len(lat.findall(W('lsdException')))
            rep['latentStyles_def'] = {k: lat.get(W(k)) for k in ('defLockedState','defUIPriority','defSemiHidden','defUnhideWhenUsed','defQFormat','count') if lat.get(W(k))}

    # --- numbering ---
    if 'word/numbering.xml' in names:
        nroot = etree.fromstring(z.read('word/numbering.xml'))
        abstract = {}
        for a in nroot.findall(W('abstractNum')):
            aid = a.get(W('abstractNumId'))
            lv = []
            for l in a.findall(W('lvl')):
                ilvl = l.get(W('ilvl'))
                fmt = l.find(W('numFmt')); txt = l.find(W('lvlText')); st = l.find(W('start'))
                jc = l.find(W('lvlJc')); pst = l.find(W('pStyle'))
                lv.append({'ilvl': ilvl,
                           'numFmt': fmt.get(W('val')) if fmt is not None else None,
                           'lvlText': txt.get(W('val')) if txt is not None else None,
                           'start': st.get(W('val')) if st is not None else None,
                           'lvlJc': jc.get(W('val')) if jc is not None else None,
                           'pStyle': pst.get(W('val')) if pst is not None else None})
            abstract[aid] = {'abstractNumId': aid, 'levels': lv,
                             'numStyleLink': (a.find(W('numStyleLink')).get(W('val')) if a.find(W('numStyleLink')) is not None else None)}
        nums = []
        for n in nroot.findall(W('num')):
            nums.append({'numId': n.get(W('numId')),
                         'abstractNumId': n.find(W('abstractNumId')).get(W('val'))})
        rep['numbering'] = {'abstract': abstract, 'num': nums}

    # --- sections ---
    secs = []
    for s in body.iter(W('sectPr')):
        e = OrderedDict()
        pg = s.find(W('pgSz')); mar = s.find(W('pgMar'))
        if pg is not None: e['pgSz'] = {k: pg.get(W(k)) for k in ('w','h','orient','code') if pg.get(W(k))}
        if mar is not None: e['pgMar'] = {k: mar.get(W(k)) for k in ('top','right','bottom','left','header','footer','gutter','topLines','bottomLines') if mar.get(W(k))}
        cols = s.find(W('cols'))
        if cols is not None: e['cols'] = {k: cols.get(W(k)) for k in ('num','space','sep','equalWidth') if cols.get(W(k))}
        e['titlePg'] = s.find(W('titlePg')) is not None
        e['type'] = (s.find(W('type')).get(W('val')) if s.find(W('type')) is not None else None)
        for tag in ('headerReference', 'footerReference'):
            refs = [{k: r.get(W(k)) for k in ('type', 'id')} for r in s.findall(W(tag))]
            if refs: e[tag] = refs
        secs.append(e)
    rep['sections'] = secs

    # --- headers / footers ---
    hf = OrderedDict()
    for n in sorted(names):
        if re.match(r'word/(header|footer)\d*\.xml', n):
            root = etree.fromstring(z.read(n))
            hf[n] = {'text': txt_of(root),
                     'paras': [{'style': (p.find(W('pPr')).find(W('pStyle')).get(W('val'))
                                          if p.find(W('pPr')) is not None and p.find(W('pPr')).find(W('pStyle')) is not None else None),
                                'text': txt_of(p),
                                'hasDrawing': p.find('.//' + q('w:drawing')) is not None,
                                'hasFld': len(p.findall('.//' + W('fldSimple'))) + len(p.findall('.//' + W('instrText')))} for p in root.findall(W('p'))]}
    rep['headers_footers'] = hf

    # --- comments ---
    if 'word/comments.xml' in names:
        croot = etree.fromstring(z.read('word/comments.xml'))
        rep['comments'] = [{'id': c.get(W('id')), 'author': c.get(W('author')), 'date': c.get(W('date')),
                            'text': txt_of(c)} for c in croot.findall(W('comment'))]
    else:
        rep['comments'] = []

    # --- doc-level flags ---
    settings = etree.fromstring(z.read('word/settings.xml')) if 'word/settings.xml' in names else None
    if settings is not None:
        rep['settings_flags'] = {
            'trackChanges': settings.find(W('trackChanges')) is not None,
            'evenAndOddHeaders': settings.find(W('evenAndOddHeaders')) is not None,
            'defaultTabStop': (settings.find(W('defaultTabStop')).get(W('val')) if settings.find(W('defaultTabStop')) is not None else None),
            'compat': len(settings.findall(q('w:compat'))),
            'rsid_count': len(settings.findall(W('rsid'))),
        }
        rep['mathPr_present'] = settings.find(q('m:mathPr')) is not None

    # --- body walk ---
    paras, tables, drawings, math = [], [], [], []
    body_seq = []
    p_idx = 0
    for child in body:
        tag = etree.QName(child).localname
        if tag == 'p':
            ppr = child.find(W('pPr'))
            ps = ppr.find(W('pStyle')) if ppr is not None else None
            sid = ps.get(W('val')) if ps is not None else None
            runs = [run_summary(r) for r in child.findall(W('r'))]
            paras.append({'i': p_idx, 'styleId': sid, 'styleName': smap.get(sid, sid),
                          'pPr': ppr_summary(ppr), 'text': txt_of(child), 'runs': runs,
                          'n_math': len(child.findall('.//' + q('m:oMath'))),
                          'has_comment': child.find(W('commentRangeStart')) is not None or './/' not in '',
                          'has_ins': child.find(W('ins')) is not None or len(child.findall('.//' + W('ins'))) > 0,
                          'has_del': len(child.findall('.//' + W('del'))) > 0,
                          'has_drawing': len(child.findall('.//' + q('w:drawing'))) > 0})
            body_seq.append({'type': 'p', 'i': p_idx, 'style': smap.get(sid, sid), 'preview': txt_of(child)[:60]})
            p_idx += 1
        elif tag == 'tbl':
            tbls = []
            for tr in child.findall(W('tr')):
                row = []
                for tc in tr.findall(W('tc')):
                    tcpr = tc.find(W('tcPr'))
                    gs = tcpr.find(W('gridSpan')) if tcpr is not None else None
                    vm = tcpr.find(W('vMerge')) if tcpr is not None else None
                    row.append({'text': txt_of(tc),
                                'gridSpan': gs.get(W('val')) if gs is not None else None,
                                'vMerge': (vm.get(W('val')) or 'continue') if vm is not None else None,
                                'has_drawing': tc.find('.//' + q('w:drawing')) is not None})
                tbls.append(row)
            tables.append({'rows': len(tbls), 'cols': len(tbls[0]) if tbls else 0, 'cells': tbls,
                           'tblPr': etree.tostring(child.find(W('tblPr')), encoding='unicode')[:1200] if child.find(W('tblPr')) is not None else None})
            body_seq.append({'type': 'tbl', 'rows': len(tbls), 'preview': (tbls[0][0]['text'][:40] if tbls and tbls[0] else '')})
        else:
            body_seq.append({'type': tag})

    for m in body.iter(q('m:oMath')):
        math.append(etree.tostring(m, encoding='unicode'))
    for d in body.iter(q('w:drawing')):
        drawings.append(etree.tostring(d, encoding='unicode')[:400])

    rep['paragraphs'] = paras
    rep['paragraph_count'] = len(paras)
    rep['style_usage'] = dict(Counter(p['styleName'] for p in paras))
    rep['tables'] = tables
    rep['body_sequence'] = body_seq
    rep['math_count'] = len(math)
    rep['math_samples'] = math[:5]
    rep['drawing_count'] = len(drawings)
    rep['drawing_samples'] = drawings[:3]
    rep['media'] = sorted(n for n in names if n.startswith('word/media/'))
    rep['rels_document'] = z.read('word/_rels/document.xml.rels').decode('utf-8')[:6000] if 'word/_rels/document.xml.rels' in names else None

    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    return rep

if __name__ == '__main__':
    r = audit(sys.argv[1], sys.argv[2])
    print('paragraphs:', r['paragraph_count'])
    print('style_usage:', json.dumps(r['style_usage'], ensure_ascii=False))
    print('tables:', [(t['rows'], t['cols']) for t in r['tables']])
    print('math_count:', r['math_count'], 'drawings:', r['drawing_count'])
    print('media:', len(r['media']))
    print('comments:', len(r['comments']))
    print('sections:', len(r['sections']))
    print('headers_footers:', {k: v['text'][:60] for k, v in r['headers_footers'].items()})
