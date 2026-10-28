# -*- coding: utf-8 -*-
"""按《计算机应用》投稿模板重建稿件 docx。

模板要点：
  - 首页页眉（刊名横幅）与 DOI 行不得删改
  - 有“引言”须从 0 开始编号
  - 样式名与模板一致：文题/作者名/单位/摘要关键词/一、二、三级标题/正文/图表名称/文献列表
  - 图题在图下方、表题在表上方，中英文对照，均用“图表名称”样式
  - 表格由 Word 表格工具绘制，同列精度一致
  - 公式使用 OMML（公式编辑器对象），编号右对齐
"""

from __future__ import annotations

import re
from pathlib import Path

import docx
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor, Emu
from PIL import Image

ROOT = Path("/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup")
SRC = ROOT / "Hybrid_TEE_Rollup修改版.docx"
FIGDIR = ROOT / "paper_outputs" / "figures_vector"
OUT = ROOT / "outputs" / "Hybrid_TEE_Rollup_计算机应用投稿版.docx"

CN_BODY = "宋体"
CN_HEAD = "黑体"
EN = "Times New Roman"
FIG_W = Cm(15.0)

# ---------------------------------------------------------------- 基础工具


def set_run(run, cn=CN_BODY, en=EN, size=9, bold=False, italic=False):
    run.font.name = en
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), en)
    rfonts.set(qn("w:hAnsi"), en)
    rfonts.set(qn("w:eastAsia"), cn)


def add_para(doc, text="", style=None, cn=CN_BODY, en=EN, size=9, bold=False,
             align=None, first_indent=None, space_before=None, space_after=None,
             line=None):
    p = doc.add_paragraph(style=style)
    if text:
        run = p.add_run(text)
        set_run(run, cn=cn, en=en, size=size, bold=bold)
    pf = p.paragraph_format
    if align is not None:
        pf.alignment = align
    if first_indent is not None:
        pf.first_line_indent = Pt(first_indent)
    if space_before is not None:
        pf.space_before = Pt(space_before)
    if space_after is not None:
        pf.space_after = Pt(space_after)
    if line is not None:
        pf.line_spacing = line
    return p


def add_border(p, pos="bottom", sz=6):
    ppr = p._element.get_or_add_pPr()
    pbdr = ppr.find(qn("w:pBdr"))
    if pbdr is None:
        pbdr = OxmlElement("w:pBdr")
        ppr.append(pbdr)
    el = OxmlElement(f"w:{pos}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(sz))
    el.set(qn("w:space"), "1")
    el.set(qn("w:color"), "000000")
    pbdr.append(el)


def set_cell_border(cell, **kwargs):
    tcpr = cell._tc.get_or_add_tcPr()
    borders = tcpr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcpr.append(borders)
    for edge in ("top", "left", "bottom", "right"):
        spec = kwargs.get(edge)
        el = borders.find(qn(f"w:{edge}"))
        if el is None:
            el = OxmlElement(f"w:{edge}")
            borders.append(el)
        if spec is None:
            el.set(qn("w:val"), "nil")
        else:
            sz, val = spec
            el.set(qn("w:val"), val)
            el.set(qn("w:sz"), str(sz))
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), "000000")


# ---------------------------------------------------------------- OMML 公式

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _mr(text, plain=False):
    sty = '<m:rPr><m:sty m:val="p"/></m:rPr>' if plain else ""
    return (f'<m:r>{sty}<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'
            f'<m:t xml:space="preserve">{text}</m:t></m:r>')


def _sub(base, sub):
    return f"<m:sSub><m:e>{base}</m:e><m:sub>{sub}</m:sub></m:sSub>"


def _frac(num, den):
    return f"<m:f><m:num>{num}</m:num><m:den>{den}</m:den></m:f>"


def build_math(xml_inner):
    xml = (f'<m:oMath xmlns:m="{M_NS}" '
           f'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f"{xml_inner}</m:oMath>")
    from docx.oxml import parse_xml
    return parse_xml(xml)


def C(name):
    """带下标的成本变量，如 C_total"""
    base, _, idx = name.partition("_")
    return _sub(_mr(base), _mr(idx, plain=True))


def add_equation(doc, inner, number):
    """公式 + 右对齐编号：制表位居中 + 制表位右对齐"""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(4)
    pf.space_after = Pt(4)
    ppr = p._element.get_or_add_pPr()
    tabs = OxmlElement("w:tabs")
    usable = int(15.0 / 2.54 * 1440)
    for pos, val in ((usable // 2, "center"), (usable, "right")):
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), val)
        tab.set(qn("w:pos"), str(pos))
        tabs.append(tab)
    ppr.append(tabs)
    r = p.add_run()
    r._element.append(OxmlElement("w:tab"))
    p._element.append(build_math(inner))
    r2 = p.add_run()
    r2._element.append(OxmlElement("w:tab"))
    set_run(p.add_run(f"({number})"), size=9)
    return p


def add_inline_math(p, inner):
    p._element.append(build_math(inner))


# ---------------------------------------------------------------- 样式


def define_styles(doc):
    styles = doc.styles

    def mk(name, base="Normal"):
        try:
            return styles.add_style(name, docx.enum.style.WD_STYLE_TYPE.PARAGRAPH)
        except Exception:
            return styles[name]

    def cfg(st, cn, size, bold=False, align=None, before=0, after=0,
            indent=None, hanging=None, line=1.15):
        st.font.name = EN
        st.font.size = Pt(size)
        st.font.bold = bold
        rpr = st.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            rpr.append(rf)
        rf.set(qn("w:ascii"), EN)
        rf.set(qn("w:hAnsi"), EN)
        rf.set(qn("w:eastAsia"), cn)
        pf = st.paragraph_format
        if align is not None:
            pf.alignment = align
        pf.space_before = Pt(before)
        pf.space_after = Pt(after)
        pf.line_spacing = line
        if indent is not None:
            pf.first_line_indent = Pt(indent)
        if hanging is not None:
            pf.left_indent = Pt(hanging)
            pf.first_line_indent = Pt(-hanging)

    s = mk("文题");            cfg(s, CN_HEAD, 18, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=10, line=1.3)
    s = mk("作者名");          cfg(s, CN_BODY, 12, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
    s = mk("单位");            cfg(s, CN_BODY, 7.5, align=WD_ALIGN_PARAGRAPH.CENTER, after=2, line=1.1)
    s = mk("摘要关键词");      cfg(s, CN_BODY, 9, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=2, line=1.2)
    s = mk("一级标题");        cfg(s, CN_HEAD, 12, bold=True, before=10, after=5)
    s = mk("二级标题");        cfg(s, CN_HEAD, 10.5, bold=True, before=8, after=4)
    s = mk("三级标题");        cfg(s, CN_HEAD, 9, bold=True, before=6, after=3)
    s = mk("正文");            cfg(s, CN_BODY, 9, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=18, after=1)
    s = mk("图表名称");        cfg(s, CN_HEAD, 9, align=WD_ALIGN_PARAGRAPH.CENTER, before=3, after=3, line=1.1)
    s = mk("文献列表");        cfg(s, CN_BODY, 9, align=WD_ALIGN_PARAGRAPH.JUSTIFY, hanging=21, after=1, line=1.15)


# ---------------------------------------------------------------- 页面与页眉


def setup_page(doc):
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.left_margin = Cm(3.0)
    sec.right_margin = Cm(3.0)
    sec.top_margin = Cm(2.8)
    sec.bottom_margin = Cm(2.5)
    sec.header_distance = Cm(1.5)
    sec.footer_distance = Cm(1.4)
    sec.different_first_page_header_footer = True

    # 正文页页眉：计算机应用 + 页码
    hp = sec.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = hp.add_run("计算机应用")
    set_run(r, cn=CN_HEAD, size=7.5)
    add_border(hp, "bottom", sz=6)

    fpr = sec.footer.paragraphs[0]
    fpr.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 首页页眉：刊名横幅 + DOI 行（不得修改）
    fh = sec.first_page_header.paragraphs[0]
    fh.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fh.add_run("Journal of Computer Applications　　ISSN 1001-9081")
    set_run(r, size=7.5)
    p2 = sec.first_page_header.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p2.add_run("计算机应用　　CODEN JYIIDU　　http://www.joca.cn")
    set_run(r, cn=CN_HEAD, size=7.5)
    add_border(p2, "bottom", sz=6)

    # 首页页脚页码
    fp = sec.first_page_footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER


# ---------------------------------------------------------------- 表格


def add_three_line_table(doc, rows, widths_cm=None, size=8.5):
    """三线表：顶线/底线 1.5pt，栏目线 0.75pt，其余框线细线以便审阅。"""
    tbl = doc.add_table(rows=len(rows), cols=len(rows[0]))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = True
    n = len(rows)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER if ri == 0 or ci != len(row) - 1 \
                else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            run = p.add_run(str(val))
            set_run(run, cn=CN_HEAD if ri == 0 else CN_BODY, size=size, bold=(ri == 0))
            if ri == 0:
                set_cell_border(cell, top=(12, "single"), bottom=(6, "single"),
                                left=(4, "single"), right=(4, "single"))
            elif ri == n - 1:
                set_cell_border(cell, top=(4, "single"), bottom=(12, "single"),
                                left=(4, "single"), right=(4, "single"))
            else:
                set_cell_border(cell, top=(4, "single"), bottom=(4, "single"),
                                left=(4, "single"), right=(4, "single"))
    if widths_cm:
        for ci, w in enumerate(widths_cm):
            for ri in range(n):
                tbl.cell(ri, ci).width = Cm(w)
    return tbl


def add_figure(doc, png_name, caption_cn, caption_en, width=FIG_W):
    path = FIGDIR / png_name
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    run = p.add_run()
    with Image.open(path) as im:
        w, h = im.size
    run.add_picture(str(path), width=width, height=Emu(int(width * h / w)))
    add_para(doc, caption_cn, style="图表名称")
    add_para(doc, caption_en, style="图表名称")


# ---------------------------------------------------------------- 主流程


def main():
    src = Document(str(SRC))
    sp = [p.text for p in src.paragraphs]

    doc = Document()
    define_styles(doc)
    setup_page(doc)

    # DOI 行（保留模板原文，不得修改）
    p = add_para(doc, "doi:10.11772/j.issn.1001-9081.yyyymmnnnn", size=9)
    p.paragraph_format.space_after = Pt(6)

    # ---- 中文题名 / 作者 / 单位
    add_para(doc, sp[0].strip(), style="文题")
    add_para(doc, "杨帆*", style="作者名")
    add_para(doc, "（华东师范大学 数据科学与工程学院，上海 200062）", style="单位")
    add_para(doc, "(*通信作者电子邮箱 2991777340@qq.com)", style="单位", space_after=6)

    # ---- 中文摘要 / 关键词 / 分类号
    add_para(doc, sp[3].strip(), style="摘要关键词")
    add_para(doc, "关键词：交互式挑战；数据可用性；高频 DApp；成本摊销；故障恢复", style="摘要关键词")
    add_para(doc, "中图分类号 TP311　　文献标志码: A", style="摘要关键词", space_after=8)

    # ---- 英文题名 / 作者 / 单位
    add_para(doc, re.sub(r"\s+", " ", sp[6].strip()), style="文题")
    add_para(doc, "YANG Fan", style="作者名")
    add_para(doc, "(School of Data Science and Engineering, East China Normal University, "
                  "Shanghai 200062, China)", style="单位")
    add_para(doc, sp[9].strip(), style="摘要关键词")
    add_para(doc, "Key words: interactive challenge; data availability; "
                  "high-frequency decentralized application (DApp); cost amortization; fault recovery",
             style="摘要关键词", space_after=8)

    # ---- 正文
    HEADINGS = {
        11: "0  引言",
        20: "1  相关工作",
        30: "2  系统概览",
        33: "2.1  执行层与正常路径",
        36: "2.2  数据可用性接口",
        39: "2.3  验证层与恢复触发",
        43: "3  核心机制与成本评估",
        44: "3.1  可恢复挑战协议",
        45: "3.1.1  协议模型与形式化定义",
        57: "3.1.2  超时、恢复、重放与仲裁结算",
        63: "3.1.3  正确性边界与协议性质",
        67: "3.1.4  协议性质",
        87: "3.2  携带证据的紧凑提交机制",
        91: "3.3  数据可用性感知成本评估",
        96: "4  实验评估",
        101: "4.1  紧凑提交能否降低链上提交规模",
        104: "4.2  批大小如何影响 DA 感知摊销成本",
        107: "4.3  恢复机制能否改善超时场景下的挑战活性",
        112: "4.4  不同故障场景能否被检测、恢复或惩罚",
        118: "4.5  Solidity、本地 EVM 与 Sepolia 证据能否支撑链上对应物",
        124: "4.6  实验小结",
        127: "5  结语",
    }
    FIG_AFTER = {32: "fig1_architecture.png", 58: "fig2_challenge_flow.png",
                 103: "fig3_byte_size.png", 106: "fig4_da_cost.png"}
    CAPTIONS = {
        "fig1_architecture.png": ("图 1  Hybrid TEE-Rollup 原型系统架构",
                                  "Fig. 1  Prototype architecture of Hybrid TEE-Rollup"),
        "fig2_challenge_flow.png": ("图 2  可恢复挑战协议流程",
                                    "Fig. 2  Workflow of the recoverable challenge protocol"),
        "fig3_byte_size.png": ("图 3  完整负载与紧凑提交的字节规模对比",
                               "Fig. 3  Byte-size comparison between full payloads and compact commits"),
        "fig4_da_cost.png": ("图 4  不同数据可用性配置下的摊销 gas 用量趋势",
                             "Fig. 4  Amortized gas trends under different DA configurations"),
    }
    SKIP = {130}
    REF_START, REF_END = 131, 142

    def fix(text):
        t = text
        t = t.replace("第 4.1.4 节", "第 3.1.4 节")
        t = t.replace("表 5", "表 2").replace("表 4", "表 1")
        return t

    def emit_table(src_table, caption_cn, caption_en, widths_cm):
        add_para(doc, caption_cn, style="图表名称", space_before=8)
        add_para(doc, caption_en, style="图表名称")
        rows = [[c.strip() for c in [cell.text for cell in row.cells]] for row in src_table.rows]
        add_three_line_table(doc, rows, widths_cm=widths_cm)

    for idx in range(11, 130):
        if idx in SKIP:
            continue
        if idx == 115:   # 表 1 题名与表体（随文）
            emit_table(src.tables[4], "表 1  失败场景分类与当前证据边界",
                       "Table 1  Failure scenarios and evidence boundaries",
                       [2.6, 4.4, 4.2, 3.8])
            continue
        if idx in (116, 117):
            continue
        if idx == 120:   # 表 2 题名与表体（随文）
            rows = [[c.strip() for c in [cell.text for cell in row.cells]]
                    for row in src.tables[5].rows]
            for ri in range(1, len(rows)):     # 同列精度统一为 2 位小数
                rows[ri][1] = f"{float(rows[ri][1]):.2f}"
            add_para(doc, "表 2  本地 EVM 关键路径平均 gasUsed", style="图表名称", space_before=8)
            add_para(doc, "Table 2  Average gasUsed of local EVM key paths", style="图表名称")
            add_three_line_table(doc, rows, widths_cm=[4.6, 3.4, 7.0])
            continue
        if idx in (121, 122):
            continue
        text = sp[idx].strip()
        if not text:
            continue
        if idx in HEADINGS:
            level = HEADINGS[idx].count("  ") and len(HEADINGS[idx].split("  ")[0].split("."))
            style = "一级标题" if "." not in HEADINGS[idx].split("  ")[0] else (
                "二级标题" if HEADINGS[idx].split("  ")[0].count(".") == 1 else "三级标题")
            add_para(doc, HEADINGS[idx], style=style)
            continue
        if idx == 98:   # 公式 (1)
            inner = (C("C_total") + _mr("=") + C("C_commit") + _mr("+") + C("C_DA")
                     + _mr("+") + _sub(_mr("p"), _mr("challenge", plain=True))
                     + _mr("×") + C("C_challenge"))
            add_equation(doc, inner, 1)
            continue
        if idx == 99:   # 公式 (2)
            inner = (_sub(_mr("C"), _mr("amortized", plain=True))
                     + _mr("=") + _frac(C("C_total"), _sub(_mr("batch"), _mr("size", plain=True))))
            add_equation(doc, inner, 2)
            continue
        if idx == 100:
            text = ("其中，C_commit 表示链上紧凑提交或完整负载提交成本，C_DA 表示不同 DA 路径下的数据成本，"
                    "C_challenge 表示争议发生时挑战、恢复、重放和结算成本，p_challenge 表示争议发生概率。")
            p = add_para(doc, "", style="正文")
            add_inline_math(p, C("C_commit"))
            p.add_run(" 表示链上紧凑提交或完整负载提交成本，")
            add_inline_math(p, C("C_DA"))
            p.add_run(" 表示不同 DA 路径下的数据成本，")
            add_inline_math(p, C("C_challenge"))
            p.add_run(" 表示争议发生时挑战、恢复、重放和结算成本，")
            add_inline_math(p, _sub(_mr("p"), _mr("challenge", plain=True)))
            p.add_run(" 表示争议发生概率。")
            for r in p.runs:
                set_run(r, size=9)
            continue

        if idx == 48:
            p = add_para(doc, "挑战会话定义为：", style="正文")
            add_inline_math(p, _mr("cs") + _mr("=") + _mr("(") + _mr("id") + _mr(",")
                            + _mr("s") + _mr(",") + _mr("F") + _mr(",") + _mr("T") + _mr(")"))
            set_run(p.add_run("。"), size=9)
            continue
        if idx == 51:
            p = add_para(doc, "挑战状态机定义为：", style="正文")
            add_inline_math(p, _mr("M") + _mr("=") + _mr("(") + _mr("S") + _mr(",")
                            + _mr("E") + _mr(",") + _mr("δ") + _mr(")"))
            set_run(p.add_run("。"), size=9)
            continue
        if idx == 54:
            p = add_para(doc, "恢复函数定义为：", style="正文")
            add_inline_math(p, _mr("Recover", plain=True) + _mr("(") + _mr("cs") + _mr(")")
                            + _mr("=") + _sub(_mr("cs"), _mr("′")))
            set_run(p.add_run("。"), size=9)
            continue
        if idx == 55:
            p = add_para(doc, "恢复仅改变活性相关状态，不改变挑战事实，即满足：", style="正文")
            add_inline_math(p, _mr("F") + _mr("(") + _mr("cs") + _mr(")") + _mr("=")
                            + _mr("F") + _mr("(") + _mr("Recover", plain=True) + _mr("(")
                            + _mr("cs") + _mr(")") + _mr(")"))
            set_run(p.add_run("。"), size=9)
            continue

        p = add_para(doc, fix(text), style="正文")
        # 定义与性质小标题行加粗；未编号的第四级小标题同样加粗
        if re.match(r"^(定义\s*\d|性质[一二三四五])", text) or text in (
                "挑战事实不变性", "安全性与活性分离", "仲裁连续性"):
            for r in p.runs:
                r.font.bold = True
                rf = r._element.rPr.find(qn("w:rFonts"))
                rf.set(qn("w:eastAsia"), CN_HEAD)

        if idx in FIG_AFTER:
            name = FIG_AFTER[idx]
            cn, en = CAPTIONS[name]
            add_figure(doc, name, cn, en)

    # ---- 参考文献
    add_para(doc, "参考文献", style="一级标题", space_before=12)
    for i in range(REF_START, REF_END + 1):
        txt = re.sub(r"^\[\d+\]\s*", "", sp[i].strip())
        add_para(doc, f"[{i - REF_START + 1}] {txt}", style="文献列表")

    # ---- 基金与作者简介
    add_para(doc, "基金项目：无", style="摘要关键词", space_before=8)
    add_para(doc, "作者简介：杨帆（2003—），男，湖南邵阳人，硕士研究生，"
                  "主要研究方向：区块链系统与跨链互操作、可信执行环境与隐私计算、"
                  "Layer 2/Rollup 扩容与安全、去中心化金融与交易公平性。", style="摘要关键词")
    add_para(doc, "本文有任何疑问请联系作者：杨帆，手机号是：13319693336，"
                  "邮箱是 2991777340@qq.com。", style="摘要关键词")
    add_para(doc, "YANG Fan, born in 2003, M. S. candidate. His research interests include "
                  "blockchain systems and cross-chain interoperability, trusted execution "
                  "environment and privacy computing, Layer 2/Rollup scaling and security, "
                  "and decentralized finance and trading fairness.", style="摘要关键词")

    # ---- 随稿附件（编辑部要求，正式排版前删除本页）
    doc.add_page_break()
    add_para(doc, "附：随稿附件（供编辑部审稿使用，正式排版前删除本节）", style="一级标题")
    add_para(doc, "1. 作者工作量说明", style="二级标题")
    add_para(doc, "杨帆：独立完成本文全部工作，包括选题与研究问题界定、可恢复挑战协议与紧凑提交机制设计、"
                  "Python 原型与 Solidity 合约实现、本地 EVM 与 Sepolia 实验、"
                  "DA 感知成本模型构建与实验分析、论文撰写与修改。", style="正文")
    add_para(doc, "2. 变量符号说明", style="二级标题")
    add_para(doc, "本文无矩阵、矢量变量；其余变量均采用常规斜体，说明如下：", style="正文")
    sym_rows = [
        ["变量符号", "含义", "备注"],
        ["C_total", "单笔交易总成本", "常规斜体"],
        ["C_commit", "链上紧凑提交或完整负载提交成本", "常规斜体"],
        ["C_DA", "不同 DA 路径下的数据成本", "常规斜体"],
        ["C_challenge", "争议发生时挑战、恢复、重放与结算成本", "常规斜体"],
        ["C_amortized", "批处理后单笔摊销成本", "常规斜体"],
        ["p_challenge", "争议发生概率", "常规斜体"],
        ["batch_size", "批处理规模", "常规斜体"],
        ["cs = (id, s, F, T)", "挑战会话：标识、状态、挑战事实集合、超时参数", "常规斜体"],
        ["M = (S, E, δ)", "挑战状态机：状态集合、事件集合、状态转移函数", "常规斜体"],
        ["n", "执行轨迹长度", "常规斜体"],
    ]
    add_three_line_table(doc, sym_rows, widths_cm=[4.2, 7.4, 3.4], size=8.5)
    add_para(doc, "3. 研究背景与基金项目介绍", style="二级标题")
    add_para(doc, "本文无基金项目支持。研究背景：高频去中心化应用（如链上 AI 推理服务）要求低延迟、"
                  "低链上开销与公开可验证仲裁并存；现有 Rollup 路线在异常路径上缺乏超时后的恢复与仲裁连续性保障，"
                  "链上提交也难以在保留证据关联的前提下与完整负载解耦。本文据此提出可恢复挑战协议、"
                  "携带证据的紧凑提交机制与数据可用性感知成本模型，并以 Python 原型、"
                  "本地 EVM gas 实测与 Sepolia 部署记录加以验证。", style="正文")

    doc.save(str(OUT))
    print("SAVED:", OUT)


if __name__ == "__main__":
    main()
