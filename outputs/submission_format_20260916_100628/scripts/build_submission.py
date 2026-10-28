# -*- coding: utf-8 -*-
"""以《计算机应用》投稿模版.doc（已保真转 docx）为底稿，把原稿内容迁移进去。

原则：
  * 内容（文字、数字、公式、表格、图题）逐字沿用原稿，不做增删改译；
  * 只做版式：样式、字体字号、行距、分栏、页边距、图题位置、表格边框；
  * 公式改为 OMML 可编辑公式对象；
  * 插图改为嵌入型矢量图（由已核实的 SVG 源转换），图题移出表格。
"""
import os
import re
import sys
import zipfile
from datetime import datetime, timezone

import docx
from docx.oxml.ns import qn
from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.dirname(HERE)
WORKSPACE = os.path.dirname(os.path.dirname(RUN))
sys.path.insert(0, HERE)
from img_util import make_drawing, svg_size_emu  # noqa: E402

WNS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
MNS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
W = '{%s}' % WNS
M = '{%s}' % MNS
XMLSPACE = '{http://www.w3.org/XML/1998/namespace}space'

TPL = os.path.join(RUN, 'work', '投稿模版_WPS.docx')
SRC = os.path.join(RUN, 'input_backup', 'Hybrid_TEE_Rollup修改版.docx')
REGISTRY = os.path.join(RUN, 'input_backup', '投稿信息登记表.xlsx')
OUTNAME = 'Hybrid_TEE_Rollup_计算机应用_投稿待确认版.docx'
OUT = os.path.join(RUN, OUTNAME)

SVGDIR = os.path.join(RUN, 'input_backup')

# 模板真实样式 ID
S_TITLE = '16'           # Title / 文题
S_AUTHOR = '56'          # 作者名
S_AFF = '47'             # 单位
S_ABS = '60'             # 固定   = 中文摘要
S_KW = '72'              # 固定2  = 中文关键词
S_CLC = '74'             # 固定3  = 中图分类号
S_ABSEN = '76'           # 固定4  = Abstract
S_KWEN = '78'            # 固定5  = Key words
S_EMPTY = '37'           # 空行用
S_H1 = '64'              # 一级标题
S_H2 = '50'              # 二级标题
S_H3 = '49'              # 三级标题
S_CAP = '84'             # 图表名称
S_DEF = '85'             # 定义定理
S_REF = '88'             # 文献列表
S_REFH = '80'            # 固定6  = 参考文献
S_AUTHOR_BIO = '68'      # 作者简介

FIG_WIDTH_EMU = int(15.0 / 2.54 * 914400)     # 通栏 15 cm
MAX_FIG_H_EMU = int(11.0 / 2.54 * 914400)     # 图高上限 11 cm
COL_WIDTH_TWIPS = 4111                        # 双栏时单栏宽


# ---------------------------------------------------------------- 基础工具
def deep(el):
    return etree.fromstring(etree.tostring(el))


def sub(parent, tag, **attrs):
    e = etree.SubElement(parent, W + tag)
    for k, v in attrs.items():
        e.set(W + k, str(v))
    return e


def new_p(style=None, jc=None, numid=None, ilvl=0, tabs=None):
    p = etree.Element(W + 'p')
    pPr = sub(p, 'pPr')
    if style:
        sub(pPr, 'pStyle', val=style)
    if numid is not None:
        np = sub(pPr, 'numPr')
        sub(np, 'ilvl', val=ilvl)
        sub(np, 'numId', val=numid)
    if jc:
        sub(pPr, 'jc', val=jc)
    if tabs:
        ts = sub(pPr, 'tabs')
        for pos, val in tabs:
            t = sub(ts, 'tab', val=val)
            t.set(W + 'pos', str(pos))
    return p


def runs_of(p, join_breaks=False):
    out = []
    for r in p.findall(W + 'r'):
        rpr = r.find(W + 'rPr')
        b = i = False
        va = None
        if rpr is not None:
            for tag, key in (('b', 'b'), ('i', 'i')):
                e = rpr.find(W + tag)
                if e is not None and e.get(W + 'val') not in ('0', 'false') and key == 'b':
                    b = True
                elif e is not None and e.get(W + 'val') not in ('0', 'false'):
                    i = True
            v = rpr.find(W + 'vertAlign')
            if v is not None and v.get(W + 'val') not in ('0', 'false'):
                va = v.get(W + 'val')
        buf = []
        for node in r.iter():
            if node.tag == W + 't':
                buf.append(node.text or '')
            elif node.tag == W + 'br':
                buf.append(' ' if join_breaks else '\n')
            elif node.tag == W + 'tab':
                buf.append('\t')
        txt = ''.join(buf)
        if txt:
            out.append([txt, b, i, va])
    return out


def add_runs(p, runs):
    for txt, b, i, va in runs:
        r = sub(p, 'r')
        if b or i or va:
            rPr = sub(r, 'rPr')
            if b:
                sub(rPr, 'b')
            if i:
                sub(rPr, 'i')
            if va:
                sub(rPr, 'vertAlign', val=va)
        t = sub(r, 't')
        t.set(XMLSPACE, 'preserve')
        t.text = txt
    return p


def flatten(runs):
    return [(ch, b, i, va) for txt, b, i, va in runs for ch in txt]


def unflatten(chars):
    out = []
    for ch, b, i, va in chars:
        if out and (out[-1][1], out[-1][2], out[-1][3]) == (b, i, va):
            out[-1][0] += ch
        else:
            out.append([ch, b, i, va])
    return out


def strip_leading(runs, n):
    while n > 0 and runs:
        if len(runs[0][0]) <= n:
            n -= len(runs[0][0])
            runs.pop(0)
        else:
            runs[0][0] = runs[0][0][n:]
            n = 0
    return runs


# ---------------------------------------------------------------- OMML
def mr(parent, text, nor=False):
    r = etree.SubElement(parent, M + 'r')
    if nor:
        rPr = etree.SubElement(r, M + 'rPr')
        etree.SubElement(rPr, M + 'nor')
    wrPr = etree.SubElement(r, W + 'rPr')
    rf = etree.SubElement(wrPr, W + 'rFonts')
    rf.set(W + 'ascii', 'Cambria Math')
    rf.set(W + 'hAnsi', 'Cambria Math')
    t = etree.SubElement(r, M + 't')
    t.set(XMLSPACE, 'preserve')
    t.text = text
    return r


def _sSubSup(parent, kind, base, tail):
    s = etree.SubElement(parent, M + kind)
    e = etree.SubElement(s, M + 'e')
    mr(e, base)
    b = etree.SubElement(s, M + ('sub' if kind == 'sSub' else 'sup'))
    mr(b, tail, nor=(kind == 'sSub'))
    return s


def new_omath():
    return etree.fromstring('<m:oMath xmlns:m="%s" xmlns:w="%s"/>' % (MNS, WNS))


def omath_plain(parts):
    om = new_omath()
    for p in parts:
        if p[0] == 'r':
            mr(om, p[1])
        elif p[0] == 'sub':
            _sSubSup(om, 'sSub', p[1], p[2])
    return om


def omath_recover():
    om = new_omath()
    mr(om, 'Recover', nor=True)
    mr(om, '(cs) ')
    mr(om, '= ')
    _sSubSup(om, 'sSup', 'cs', "'")
    return om


EQ1 = [('r', 'cs '), ('r', '= '), ('r', '('), ('r', 'id'), ('r', ', '), ('r', 's'),
       ('r', ', '), ('r', 'F'), ('r', ', '), ('r', 'T'), ('r', ')')]
EQ2 = [('r', 'M '), ('r', '= '), ('r', '('), ('r', 'S'), ('r', ', '), ('r', 'E'),
       ('r', ', '), ('r', 'δ'), ('r', ')')]
EQ4 = [('r', 'F'), ('r', '(cs) '), ('r', '= '), ('r', 'F'), ('r', '('),
       ('r', 'Recover', 'nor'), ('r', '(cs))')]
EQ5 = [('sub', 'C', 'total'), ('r', ' = '), ('sub', 'C', 'commit'), ('r', ' + '),
       ('sub', 'C', 'DA'), ('r', ' + '), ('sub', 'p', 'challenge'), ('r', ' × '),
       ('sub', 'C', 'challenge')]
EQ6 = [('sub', 'C', 'amortized'), ('r', ' = ')]


def omath_delta():
    om = new_omath()
    for t in ('δ', ': ', 'S', ' × ', 'E', ' → ', 'S'):
        mr(om, t)
    return om


def omath_eq4():
    om = new_omath()
    mr(om, 'F')
    mr(om, '(cs) ')
    mr(om, '= ')
    mr(om, 'F')
    mr(om, '( ')
    mr(om, 'Recover', nor=True)
    mr(om, '(cs) )')
    return om


def omath_facts():
    om = new_omath()
    mr(om, 'Facts', nor=True)
    mr(om, '(')
    _sSubSup(om, 'sSub', 'cs', 'before')
    mr(om, ') = ')
    mr(om, 'Facts', nor=True)
    mr(om, '(')
    _sSubSup(om, 'sSub', 'cs', 'after')
    mr(om, ')')
    return om


def omath_cost_amortized():
    om = new_omath()
    _sSubSup(om, 'sSub', 'C', 'amortized')
    mr(om, ' = ')
    frac = etree.SubElement(om, M + 'f')
    num = etree.SubElement(frac, M + 'num')
    _sSubSup(num, 'sSub', 'C', 'total')
    den = etree.SubElement(frac, M + 'den')
    _sSubSup(den, 'sSub', 'batch', 'size')
    return om


def omath_subscript(base, tail):
    om = new_omath()
    _sSubSup(om, 'sSub', base, tail)
    return om


def registry_values():
    from openpyxl import load_workbook
    wb = load_workbook(REGISTRY, data_only=False, read_only=True)
    ws = wb['投稿信息登记表']
    out = {}
    for row in ws.iter_rows(min_row=6, values_only=True):
        if len(row) >= 4 and row[2]:
            out[str(row[2]).strip()] = '' if row[3] is None else str(row[3]).strip()
    return out


# ---------------------------------------------------------------- 主流程
def main():
    tpl = docx.Document(TPL)
    src = docx.Document(SRC)
    reg = registry_values()

    # 首页脚注区：删除模板示例日期、基金占位和教学文本，仅填入已登记的作者事实。
    footer = tpl.sections[0].first_page_footer
    footer_paras = list(footer.paragraphs)
    for p in footer_paras[1:3]:
        p._element.getparent().remove(p._element)
    footer_paras[3].clear()
    footer_paras[3].add_run(
        '作者简介：{name}（{year}—），{gender}，{native}人，{identity}，主要研究方向：{research}。'.format(
            name=reg['第 1 作者姓名'], year=reg['出生年'], gender=reg['性别'],
            native=reg['籍贯（省 + 市）'], identity=reg['职称 / 身份'],
            research=reg['主要研究方向']))

    sect_list = []
    for child in tpl.element.body:
        if child.tag == W + 'p':
            pPr = child.find(W + 'pPr')
            if pPr is not None:
                sp = pPr.find(W + 'sectPr')
                if sp is not None:
                    sect_list.append(deep(sp))
    SECT_TITLE, SECT_2COL, SECT_1COL = sect_list[0], sect_list[1], sect_list[2]

    # 模板 DOI 段（保留原文，去掉批注锚点）
    doi_p = None
    for child in tpl.element.body:
        if child.tag == W + 'p':
            doi_p = deep(child)
            break
    for tag in ('commentRangeStart', 'commentRangeEnd', 'commentReference',
                'bookmarkStart', 'bookmarkEnd'):
        for e in doi_p.iter(W + tag):
            e.getparent().remove(e)
    # 去掉随 DOI 行浮动的模板说明文本框（"您的稿件编号…"等），保留 DOI 行原文
    MC = '{http://schemas.openxmlformats.org/markup-compatibility/2006}'
    for ac in doi_p.iter(MC + 'AlternateContent'):
        ac.getparent().remove(ac)
    for r in list(doi_p.findall(W + 'r')):
        if r.find(W + 'drawing') is None and r.find(W + 'pict') is None \
                and r.find(W + 't') is None and r.find(W + 'tab') is None:
            doi_p.remove(r)

    src_children = list(src.element.body)
    src_tbls = [deep(c) for c in src_children if c.tag == W + 'tbl']
    src_paras = [deep(c) for c in src_children if c.tag == W + 'p']
    assert len(src_tbls) == 6 and len(src_paras) == 147, (len(src_tbls), len(src_paras))

    draw_tmpl = None
    for t in src_tbls:
        d = t.find('.//' + W + 'drawing')
        if d is not None:
            draw_tmpl = d

    body = tpl.element.body
    for ch in list(body):
        body.remove(ch)
    final = deep(SECT_1COL)
    body.append(final)
    last = {'p': None}

    def emit(p_el):
        body.insert(len(body) - 1, p_el)
        last['p'] = p_el
        return p_el

    def emit_tbl(t_el):
        body.insert(len(body) - 1, t_el)
        last['p'] = None

    def close_with(sect):
        if last['p'] is None:
            return
        pPr = last['p'].find(W + 'pPr')
        if pPr is None:
            pPr = etree.Element(W + 'pPr')
            last['p'].insert(0, pPr)
        old = pPr.find(W + 'sectPr')
        if old is not None:
            pPr.remove(old)
        pPr.append(deep(sect))

    def para_runs(idx, style=None, jc=None, numid=None, ilvl=0, strip=0,
                  join_breaks=False):
        runs = runs_of(src_paras[idx], join_breaks=join_breaks)
        if strip:
            runs = strip_leading(runs, strip)
        p = new_p(style=style, jc=jc, numid=numid, ilvl=ilvl)
        return emit(add_runs(p, runs))

    def para_text(text, style=None, jc=None, numid=None, ilvl=0):
        p = new_p(style=style, jc=jc, numid=numid, ilvl=ilvl)
        return emit(add_runs(p, [[text, False, False, None]]))

    def force_black(p):
        for r in p.findall(W + 'r'):
            rpr = r.find(W + 'rPr')
            if rpr is None:
                rpr = etree.Element(W + 'rPr')
                r.insert(0, rpr)
            color = rpr.find(W + 'color')
            if color is None:
                color = etree.SubElement(rpr, W + 'color')
            color.set(W + 'val', '000000')
            color.attrib.pop(W + 'themeColor', None)

    def add_text_with_math_vars(p, text):
        """把含义明确的成本变量转换为行内 OMML；其他字符逐字保留。"""
        pattern = re.compile(r'(?<![A-Za-z])([Cp]|batch)_(total|commit|DA|challenge|amortized|size)')
        pos = 0
        for m in pattern.finditer(text):
            if m.start() > pos:
                add_runs(p, [[text[pos:m.start()], False, False, None]])
            p.append(omath_subscript(m.group(1), m.group(2)))
            pos = m.end()
        if pos < len(text):
            add_runs(p, [[text[pos:], False, False, None]])
        return p

    FIGNAMES = ['fig1_architecture', 'fig2_challenge_flow',
                'fig3_byte_size', 'fig4_da_cost']
    # 通栏表格列宽（dxa，合计 8670 = 15.29 cm 版心宽）
    TBL_WIDTHS = {4: [1900, 2150, 2150, 2470], 5: [2200, 1700, 4770]}

    def figure_block(tbl_idx):
        cell = src_tbls[tbl_idx].find('.//' + W + 'tc')
        caps = [''.join(t.text or '' for t in p.iter(W + 't'))
                for p in cell.findall(W + 'p')]
        cn = caps[1] if len(caps) > 1 else ''
        en = caps[2] if len(caps) > 2 else ''
        close_with(SECT_2COL)
        name = FIGNAMES[tbl_idx]
        # 直接嵌入登记表指定且已核实的 SVG 矢量源。
        svg = os.path.join(SVGDIR, name + '.svg')
        if not os.path.exists(svg):
            raise FileNotFoundError(svg)
        img_path = svg
        cx0, cy0 = svg_size_emu(svg)
        w_emu = FIG_WIDTH_EMU
        if w_emu * cy0 / float(cx0) > MAX_FIG_H_EMU:
            w_emu = int(MAX_FIG_H_EMU * cx0 / float(cy0))
        p = new_p(style=None, jc='center')
        r = sub(p, 'r')
        r.append(make_drawing(tpl, img_path, w_emu, draw_tmpl, name=name))
        emit(p)
        pcn = para_text(cn, style=S_CAP)
        pen = para_text(en, style=S_CAP)
        force_black(pcn)
        force_black(pen)
        close_with(SECT_1COL)

    def set_tbl_width(tbl, widths):
        """表格通栏排放：整体宽度放大到版心宽，避免英文标识符在窄列内被折断。"""
        pr = tbl.find(W + 'tblPr')
        if pr is None:
            pr = etree.Element(W + 'tblPr')
            tbl.insert(0, pr)
        for tag in ('tblW', 'tblLayout'):
            old = pr.find(W + tag)
            if old is not None:
                pr.remove(old)
        tw = etree.Element(W + 'tblW')
        tw.set(W + 'w', str(sum(widths)))
        tw.set(W + 'type', 'dxa')
        lay = etree.Element(W + 'tblLayout')
        lay.set(W + 'type', 'fixed')
        # tblPr 中顺序：tblW 应位于 tblBorders 之后、tblLayout 之前
        pr.insert(0, tw)
        anchors = ('tblStyle', 'tblpPr', 'tblOverlap', 'bidiVisual', 'tblStyleRowBandSize',
                   'tblStyleColBandSize', 'tblW', 'jc', 'tblCellSpacing', 'tblInd',
                   'tblBorders', 'shd', 'tblLayout', 'tblCellMar', 'tblLook')
        pr.remove(tw)
        pos = 0
        for a in anchors:
            idxs = [i for i, c in enumerate(pr) if c.tag == W + a]
            if idxs:
                pos = max(pos, idxs[-1] + 1)
        pr.insert(pos, tw)
        lay_pos = [i for i, c in enumerate(pr) if c.tag == W + 'tblLayout']
        if lay_pos:
            pr[lay_pos[0]].set(W + 'type', 'fixed')
        else:
            pr.insert(pos + 1, lay)
        grid = tbl.find(W + 'tblGrid')
        if grid is not None:
            for gc, wv in zip(grid.findall(W + 'gridCol'), widths):
                gc.set(W + 'w', str(wv))
        for tr in tbl.findall(W + 'tr'):
            tcs = tr.findall(W + 'tc')
            ci = 0
            for tc in tcs:
                tcpr = tc.find(W + 'tcPr')
                if tcpr is None:
                    continue
                gs = tcpr.find(W + 'gridSpan')
                span = int(gs.get(W + 'val')) if gs is not None else 1
                cw = tcpr.find(W + 'tcW')
                if cw is None:
                    cw = etree.SubElement(tcpr, W + 'tcW')
                cw.set(W + 'w', str(sum(widths[ci:ci + span])))
                cw.set(W + 'type', 'dxa')
                ci += span

    def border(parent, edge, val='single', sz='4'):
        e = etree.SubElement(parent, W + edge)
        e.set(W + 'val', val)
        e.set(W + 'sz', sz)
        e.set(W + 'space', '0')
        e.set(W + 'color', '000000')

    def style_three_line_table(tbl, tbl_idx):
        """按参考论文可见打印线：顶线、表头下线、底线；表4各类别间加细分组线。"""
        pr = tbl.find(W + 'tblPr')
        old = pr.find(W + 'tblBorders')
        if old is not None:
            pr.remove(old)
        borders = etree.SubElement(pr, W + 'tblBorders')
        border(borders, 'top', sz='8')
        border(borders, 'left', val='nil', sz='0')
        border(borders, 'bottom', sz='8')
        border(borders, 'right', val='nil', sz='0')
        border(borders, 'insideH', val='nil', sz='0')
        border(borders, 'insideV', val='nil', sz='0')
        rows = tbl.findall(W + 'tr')
        for ri, tr in enumerate(rows):
            trpr = tr.find(W + 'trPr')
            if trpr is None:
                trpr = etree.Element(W + 'trPr')
                tr.insert(0, trpr)
            if ri == 0:
                etree.SubElement(trpr, W + 'tblHeader')
            etree.SubElement(trpr, W + 'cantSplit')
            for tc in tr.findall(W + 'tc'):
                tcpr = tc.find(W + 'tcPr')
                if tcpr is None:
                    tcpr = etree.Element(W + 'tcPr')
                    tc.insert(0, tcpr)
                old_tc = tcpr.find(W + 'tcBorders')
                if old_tc is not None:
                    tcpr.remove(old_tc)
                if ri == 0 or (tbl_idx == 4 and 0 < ri < len(rows) - 1):
                    tb = etree.SubElement(tcpr, W + 'tcBorders')
                    border(tb, 'bottom', sz='4')
                for p in tc.findall(W + 'p'):
                    ppr = p.find(W + 'pPr')
                    if ppr is None:
                        ppr = etree.Element(W + 'pPr')
                        p.insert(0, ppr)
                    jc = ppr.find(W + 'jc')
                    if jc is None:
                        jc = etree.SubElement(ppr, W + 'jc')
                    jc.set(W + 'val', 'center')
                    for r in p.findall(W + 'r'):
                        rpr = r.find(W + 'rPr')
                        if rpr is None:
                            rpr = etree.Element(W + 'rPr')
                            r.insert(0, rpr)
                        for tag in ('color', 'sz', 'szCs'):
                            old_fmt = rpr.find(W + tag)
                            if old_fmt is not None:
                                rpr.remove(old_fmt)
                        color = etree.SubElement(rpr, W + 'color')
                        color.set(W + 'val', '000000')
                        for tag in ('sz', 'szCs'):
                            szel = etree.SubElement(rpr, W + tag)
                            szel.set(W + 'val', '18')

    def real_table_block(tbl_idx, cap_cn, cap_en):
        close_with(SECT_2COL)
        pcn = para_text(cap_cn, style=S_CAP)
        pen = para_text(cap_en, style=S_CAP)
        force_black(pcn)
        force_black(pen)
        t = deep(src_tbls[tbl_idx])
        set_tbl_width(t, TBL_WIDTHS[tbl_idx])
        style_three_line_table(t, tbl_idx)
        emit_tbl(t)
        emit(new_p(style=S_EMPTY))
        close_with(SECT_1COL)

    # ---------------- 首页（单栏） ----------------
    emit(doi_p)
    para_runs(0, style=S_TITLE)
    para_text(reg['第 1 作者姓名'] + '1*', style=S_AUTHOR)
    para_runs(2, style=S_AFF)
    para_text('(*通信作者电子邮箱' + reg['通信作者邮箱'] + ')', style=S_AFF)
    para_runs(3, style=S_ABS, numid=3, ilvl=0, strip=len('摘  要：'))
    zh_kw = ''.join(t.text or '' for t in src_paras[4].iter(W + 't'))
    zh_kw = zh_kw.replace('关键词：', '', 1).replace('Hybrid TEE-Rollup；', '', 1)
    para_text(zh_kw, style=S_KW, numid=3, ilvl=1)
    para_text(reg['中图分类号'] + '\u3000\u3000文献标志码：' + reg['文献标志码'],
              style=S_CLC, numid=3, ilvl=2)
    en_title = src.paragraphs[6].text.replace('\n', ' ')
    para_text(en_title, style=S_TITLE)
    para_text(reg['姓名拼音 / 英文名'] + '1*', style=S_AUTHOR)
    para_runs(8, style=S_AFF)
    para_runs(9, style=S_ABSEN, numid=3, ilvl=3, strip=len('Abstract: '))
    en_kw = ''.join(t.text or '' for t in src_paras[10].iter(W + 't'))
    en_kw = en_kw.replace('Key words: ', '', 1).replace('Hybrid TEE-Rollup; ', '', 1)
    para_text(en_kw, style=S_KWEN, numid=3, ilvl=4)
    close_with(SECT_TITLE)
    emit(new_p(style=S_EMPTY))

    # ---------------- 正文 ----------------
    HEAD_RE = re.compile(r'^(\d+(?:\.\d+)*)\s+(.+)$')
    INLINE_F = {48: ('挑战会话定义为：', '。', EQ1),
                51: ('挑战状态机定义为：', '。', EQ2),
                54: ('恢复函数定义为：', '。', 'rec'),
                55: ('恢复仅改变活性相关状态，不改变挑战事实，即满足：', '。', 'eq4')}
    # 正文行内出现、且与显示公式同形的表达式，一并用公式编辑器表示
    INLINE_SPLIT = {
        52: [('E 为事件集合；', ' 为状态转移函数。', omath_delta)],
        77: [('则恢复操作满足 ', '，即恢复不向', omath_facts)],
        94: [('模型表达为 ', '。其中', EQ5),
             ('批处理后单笔摊销成本记为 ', '。', omath_cost_amortized)],
    }
    DISPLAY = {98: (EQ5, '（1）'), 99: (omath_cost_amortized, '（2）')}
    SUBHEAD = {69, 79, 83}
    DEFS = {47, 50, 53}

    def text_of(idx):
        return ''.join(t.text or '' for t in src_paras[idx].iter(W + 't'))

    i = 11
    while i < len(src_paras):
        idx = i
        if idx == 32:
            figure_block(0)
        elif idx == 59:
            figure_block(1)
        elif idx == 104:
            figure_block(2)
        elif idx == 107:
            figure_block(3)
        elif idx == 115:
            real_table_block(4, text_of(115), text_of(116))
            i = 118
            continue
        elif idx == 120:
            real_table_block(5, text_of(120), text_of(121))
            i = 123
            continue

        if idx in DISPLAY:
            eq, num = DISPLAY[idx]
            p = new_p(style=None, tabs=[(COL_WIDTH_TWIPS // 2, 'center'),
                                        (COL_WIDTH_TWIPS, 'right')])
            r = sub(p, 'r')
            r.append(etree.Element(W + 'tab'))
            p.append(eq() if callable(eq) else omath_plain(eq))
            r2 = sub(p, 'r')
            r2.append(etree.Element(W + 'tab'))
            t = sub(r2, 't')
            t.set(XMLSPACE, 'preserve')
            t.text = num
            emit(p)
            i += 1
            continue

        if idx in INLINE_SPLIT:
            chars = flatten(runs_of(src_paras[idx]))
            text = ''.join(c[0] for c in chars)
            segs, pos = [], 0
            for sm, em, eq in INLINE_SPLIT[idx]:
                a = text.index(sm, pos) + len(sm)
                b = text.index(em, a)
                segs.append(('t', unflatten(chars[pos:a])))
                segs.append(('m', eq))
                pos = b
            segs.append(('t', unflatten(chars[pos:])))
            p = new_p(style=None)
            for kind, v in segs:
                if kind == 't':
                    if idx == 94:
                        add_text_with_math_vars(p, ''.join(x[0] for x in v))
                    else:
                        add_runs(p, v)
                else:
                    p.append(v() if callable(v) else omath_plain(v))
            emit(p)
            i += 1
            continue

        if idx in INLINE_F:
            pre, post, eq = INLINE_F[idx]
            p = new_p(style=None)
            add_runs(p, [[pre, False, False, None]])
            p.append(omath_recover() if eq == 'rec' else
                     (omath_eq4() if eq == 'eq4' else omath_plain(eq)))
            add_runs(p, [[post, False, False, None]])
            emit(p)
            i += 1
            continue

        if idx == 108:
            para_text(text_of(idx).replace('第 4.1.4 节', '第 3.1.4 节'))
        elif idx == 100:
            p = new_p(style=None)
            add_text_with_math_vars(p, text_of(idx))
            emit(p)
        elif idx == 130:
            para_runs(idx, style=S_REFH, numid=0)
        elif 131 <= idx <= 142:
            para_runs(idx, style=S_REF)
        elif idx in DEFS:
            para_runs(idx, style=S_DEF)
        elif idx in SUBHEAD:
            para_runs(idx, style=None)
        else:
            m = HEAD_RE.match(text_of(idx))
            if m:
                lvl = len(m.group(1).split('.'))
                style = {1: S_H1, 2: S_H2, 3: S_H3}.get(lvl, S_H1)
                para_runs(idx, style=style, numid=2, ilvl=lvl - 1,
                          strip=len(m.group(0)) - len(m.group(2)))
            else:
                para_runs(idx, style=None)
        i += 1

    # 结论、参考文献和原稿联系信息继续采用模板正文双栏；其后不再追加非模板内容。
    close_with(SECT_2COL)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tpl.save(OUT)
    print('saved:', OUT, os.path.getsize(OUT))
    postprocess(OUT)
    return OUT


# ---------------------------------------------------------------- 后处理
def postprocess(path):
    tmp = path + '.tmp'
    zin = zipfile.ZipFile(path)
    docxml = zin.read('word/document.xml')
    if b'xmlns:m=' not in docxml[:4000]:
        docxml = docxml.replace(
            b'<w:document ',
            b'<w:document xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" ',
            1)

    used = set(m.decode('ascii')
               for m in re.findall(rb'r:(?:embed|id|link)="(rId\d+)"', docxml))
    rels = zin.read('word/_rels/document.xml.rels')
    rel_root = etree.fromstring(rels)
    drop_media, kept = [], []
    for rel in list(rel_root):
        rid, target = rel.get('Id'), rel.get('Target', '')
        if rid in used or rel.get('TargetMode') == 'External':
            kept.append(rel)
        elif ('comments' in target.lower() or target.startswith('media/')
              or target.startswith('embeddings/')):
            drop_media.append((rid, target))
        else:
            kept.append(rel)
    for rel in list(rel_root):
        rel_root.remove(rel)
    for rel in kept:
        rel_root.append(rel)
    new_rels = etree.tostring(rel_root, xml_declaration=True, encoding='UTF-8',
                              standalone=True)

    drop_parts = {'word/' + t.lstrip('/') for _, t in drop_media}
    for nm in zin.namelist():
        if 'comments' in nm and nm.startswith('word/'):
            drop_parts.add(nm)
    # 删除模板示例遗留的自定义文档属性；保留论文所需的正文、样式与页面部件。
    drop_parts.add('docProps/custom.xml')

    ct_root = etree.fromstring(zin.read('[Content_Types].xml'))
    for ov in list(ct_root):
        pn = (ov.get('PartName') or '').lstrip('/')
        if pn in drop_parts:
            ct_root.remove(ov)
    new_ct = etree.tostring(ct_root, xml_declaration=True, encoding='UTF-8',
                            standalone=True)

    pkg_rels_root = etree.fromstring(zin.read('_rels/.rels'))
    for rel in list(pkg_rels_root):
        if (rel.get('Target') or '').lstrip('/') == 'docProps/custom.xml':
            pkg_rels_root.remove(rel)
    new_pkg_rels = etree.tostring(pkg_rels_root, xml_declaration=True, encoding='UTF-8',
                                  standalone=True)

    core_root = etree.fromstring(zin.read('docProps/core.xml'))
    ns = {
        'dc': 'http://purl.org/dc/elements/1.1/',
        'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
    }
    for xp, value in (
        ('dc:title', '面向高频 DApp 的 Hybrid TEE-Rollup 可恢复挑战协议与轻量 DA 成本评估'),
        ('dc:creator', '杨帆'),
        ('cp:lastModifiedBy', '杨帆'),
    ):
        el = core_root.find(xp, namespaces=ns)
        if el is None:
            prefix, local = xp.split(':')
            el = etree.SubElement(core_root, '{%s}%s' % (ns[prefix], local))
        el.text = value
    # 清除模板示例遗留的打印时间和修订号；创建、修改时间写入本次实际生成时间。
    for old in core_root.findall('{%s}lastPrinted' % ns['cp']):
        core_root.remove(old)
    revision = core_root.find('cp:revision', namespaces=ns)
    if revision is None:
        revision = etree.SubElement(core_root, '{%s}revision' % ns['cp'])
    revision.text = '1'
    dcterms_ns = 'http://purl.org/dc/terms/'
    xsi_ns = 'http://www.w3.org/2001/XMLSchema-instance'
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    for local in ('created', 'modified'):
        el = core_root.find('{%s}%s' % (dcterms_ns, local))
        if el is None:
            el = etree.SubElement(core_root, '{%s}%s' % (dcterms_ns, local))
        el.set('{%s}type' % xsi_ns, 'dcterms:W3CDTF')
        el.text = now
    new_core = etree.tostring(core_root, xml_declaration=True, encoding='UTF-8',
                              standalone=True)

    settings_root = etree.fromstring(zin.read('word/settings.xml'))
    for track in settings_root.findall(W + 'trackRevisions'):
        settings_root.remove(track)
    update = settings_root.find(W + 'updateFields')
    if update is None:
        update = etree.SubElement(settings_root, W + 'updateFields')
    update.set(W + 'val', 'true')
    mathpr = settings_root.find(M + 'mathPr')
    if mathpr is None:
        mathpr = etree.SubElement(settings_root, M + 'mathPr')
    mathfont = mathpr.find(M + 'mathFont')
    if mathfont is None:
        mathfont = etree.SubElement(mathpr, M + 'mathFont')
    mathfont.set(M + 'val', 'Times New Roman')
    new_settings = etree.tostring(settings_root, xml_declaration=True, encoding='UTF-8',
                                  standalone=True)

    # 将旧 Windows 中文字体别名映射到本机实际字体，仅用于跨平台渲染兼容。
    styles_xml = zin.read('word/styles.xml')
    styles_xml = styles_xml.replace(b'Liberation Serif', b'Times New Roman')
    for old in ('宋体', '华文宋体', '仿宋_GB2312', '楷体', '楷体_GB2312', '等线', 'zh-CN'):
        styles_xml = styles_xml.replace(('w:eastAsia="' + old + '"').encode('utf-8'),
                                        b'w:eastAsia="Songti SC"')
    styles_xml = styles_xml.replace('w:eastAsia="黑体"'.encode('utf-8'),
                                    b'w:eastAsia="STHeiti"')
    for attr in ('ascii', 'hAnsi', 'cs'):
        for old in ('宋体', '华文宋体', '仿宋_GB2312', '楷体', '楷体_GB2312', '等线', '黑体'):
            styles_xml = styles_xml.replace(
                ('w:%s="%s"' % (attr, old)).encode('utf-8'),
                ('w:%s="Times New Roman"' % attr).encode('utf-8'))

    zout = zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED)
    for item in zin.infolist():
        fn = item.filename
        if fn in drop_parts:
            continue
        data = zin.read(fn)
        if fn == 'word/document.xml':
            data = docxml
        elif fn == 'word/_rels/document.xml.rels':
            data = new_rels
        elif fn == '[Content_Types].xml':
            data = new_ct
        elif fn == '_rels/.rels':
            data = new_pkg_rels
        elif fn == 'docProps/core.xml':
            data = new_core
        elif fn == 'word/settings.xml':
            data = new_settings
        elif fn == 'word/styles.xml':
            data = styles_xml
        zout.writestr(item, data)
    zin.close()
    zout.close()
    os.replace(tmp, path)
    print('post-processed; dropped parts:', sorted(drop_parts))


if __name__ == '__main__':
    main()
