# -*- coding: utf-8 -*-
"""
《计算机应用》投稿模板对齐构建脚本

输入：outputs/Hybrid_TEE_Rollup_计算机应用投稿版.docx （上一版稿件，内容已定稿）
输出：outputs/template_alignment/Hybrid_TEE_Rollup_计算机应用模板对齐版.docx

模板依据来源（见 outputs/template_alignment/work/）：
  - 投稿模版.doc 经 Pages/RTF 两条独立路径解析；
  - RTF 逐段抽取真实字号/行距/缩进（work/template_decoded.txt）；
  - Pages docx 抽取分节与分栏（work/template_pages.docx）；
  - 模板批注全文（work/template_textutil.txt 第 377-435 行）。

本脚本不修改原始输入文件。
"""
import copy
import re
import shutil
from pathlib import Path

import docx
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "outputs" / "Hybrid_TEE_Rollup_计算机应用投稿版.docx"
OUTDIR = ROOT / "outputs" / "template_alignment"
OUT = OUTDIR / "Hybrid_TEE_Rollup_计算机应用模板对齐版.docx"

EN = "Times New Roman"
CN = "宋体"
CN_HEI = "黑体"
CN_KAI = "楷体"

ACCESS_DATE = "2026-09-12"   # 实际联网核实日期

# ----------------------------------------------------------------------
# 1. 样式规格（证据见脚本头注释）
#    (字号pt, 粗体, 对齐, 段前pt, 段后pt, 行距pt, 首行/左缩进pt, 中文, 悬挂pt)
# ----------------------------------------------------------------------
STYLES = {
    "文题":       dict(sz=18.0, b=True,  jc="center", before=12, after=12, line=20, ind=0,    cn=CN_HEI, outline=0),
    "作者名":     dict(sz=12.0, b=False, jc="center", before=0,  after=0,  line=20, ind=0,    cn=CN,     outline=0),
    "单位":       dict(sz=7.5,  b=False, jc="center", before=0,  after=0,  line=23, ind=0,    cn=CN,     outline=0),
    "摘要关键词": dict(sz=9.0,  b=False, jc="both",   before=0,  after=0,  line=20, ind=18,   cn=CN,     outline=0),
    "一级标题":   dict(sz=12.0, b=False, jc="left",   before=13.2, after=13.2, line=20, ind=0, cn=CN,    outline=0),
    "二级标题":   dict(sz=9.0,  b=False, jc="left",   before=9.6, after=9.6,  line=20, ind=0, cn=CN,     outline=1),
    "三级标题":   dict(sz=9.0,  b=False, jc="left",   before=6.0, after=6.0,  line=20, ind=0, cn=CN,     outline=2),
    "正文":       dict(sz=9.0,  b=False, jc="both",   before=0,  after=0,  line=20, ind=18,   cn=CN,     outline=None),
    "正文内容":   dict(sz=9.0,  b=False, jc="both",   before=0,  after=0,  line=20, ind=18,   cn=CN,     outline=None),
    "图表名称":   dict(sz=9.0,  b=False, jc="center", before=0,  after=0,  line=20, ind=0,    cn=CN_HEI, outline=None),
    "文献列表":   dict(sz=9.0,  b=False, jc="both",   before=0,  after=0,  line=20, ind=0,    cn=CN,     outline=None, hanging=18),
    "作者简介":   dict(sz=9.0,  b=False, jc="both",   before=0,  after=0,  line=20, ind=0,    cn=CN,     outline=None),
    "定义定理":   dict(sz=9.0,  b=True,  jc="both",   before=0,  after=0,  line=20, ind=18,   cn=CN_HEI, outline=None),
    "结论证明":   dict(sz=9.0,  b=True,  jc="both",   before=0,  after=0,  line=20, ind=18,   cn=CN_KAI, outline=None),
    "公式":       dict(sz=9.0,  b=False, jc="center", before=6,  after=6,  line=20, ind=0,    cn=CN,     outline=None),
}

HEADING_STYLE_OF_LEVEL = {1: "一级标题", 2: "二级标题", 3: "三级标题"}
HEADING_ILVL = {"一级标题": 0, "二级标题": 1, "三级标题": 2}


def half_pt(pt):
    return str(int(round(float(pt) * 2)))


def setnum(pt):
    return str(int(round(float(pt) * 20)))


# ----------------------------------------------------------------------
# XML 小工具
# ----------------------------------------------------------------------
def sub(parent, tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn("w:" + k), v)
    parent.append(e)
    return e


def clear_tag(parent, tag):
    for e in parent.findall(qn(tag)):
        parent.remove(e)


def make_rpr(sz=None, b=None, i=None, cn=None, en=EN, sup=None):
    rPr = OxmlElement("w:rPr")
    if en or cn:
        sub(rPr, "w:rFonts", ascii=en, hAnsi=en, eastAsia=cn or en, cs=en)
    if b:
        sub(rPr, "w:b")
        sub(rPr, "w:bCs")
    if i:
        sub(rPr, "w:i")
        sub(rPr, "w:iCs")
    if sz is not None:
        sub(rPr, "w:sz", val=half_pt(sz))
        sub(rPr, "w:szCs", val=half_pt(sz))
    if sup:
        sub(rPr, "w:vertAlign", val=sup)
    return rPr


def rebuild_style_element(el, name, spec):
    """按 OOXML schema 顺序重建样式定义：name, basedOn, qFormat, pPr, rPr"""
    for ch in list(el):
        if ch.tag.split("}")[-1] != "styleId":
            el.remove(ch)
    sub(el, "w:name", val=name)
    sub(el, "w:basedOn", val="Normal")
    sub(el, "w:qFormat")
    # ---- pPr（严格按 OOXML schema 顺序）----
    pPr = sub(el, "w:pPr")
    sub(pPr, "w:widowControl")
    if name in HEADING_ILVL:
        np = sub(pPr, "w:numPr")
        sub(np, "w:ilvl", val=str(HEADING_ILVL[name]))
        sub(np, "w:numId", val="10")
    if name == "公式":
        tabs = sub(pPr, "w:tabs")
        sub(tabs, "w:tab", val="center", pos=setnum(110))
        sub(tabs, "w:tab", val="right", pos=setnum(221))
    sp = {"line": setnum(spec["line"]), "lineRule": "exact"}
    if spec["before"]:
        sp["before"] = setnum(spec["before"])
    if spec["after"]:
        sp["after"] = setnum(spec["after"])
    sub(pPr, "w:spacing", **sp)
    if spec.get("hanging"):
        sub(pPr, "w:ind", hanging=setnum(spec["hanging"]))
    elif spec["ind"]:
        sub(pPr, "w:ind", firstLine=setnum(spec["ind"]))
    if name == "一级标题":
        ind = pPr.find(qn("w:ind"))
        if ind is None:
            ind = sub(pPr, "w:ind")
        ind.set(qn("w:right"), setnum(9))
    sub(pPr, "w:jc", val=spec["jc"])
    if spec.get("outline") is not None:
        sub(pPr, "w:outlineLvl", val=str(spec["outline"]))
    # ---- rPr ----
    el.append(make_rpr(sz=spec["sz"], b=spec["b"], cn=spec["cn"], en=EN))


# ----------------------------------------------------------------------
# 2. 样式重建
# ----------------------------------------------------------------------
def rebuild_styles(doc):
    styles_el = doc.styles.element

    # --- docDefaults ---
    dd = styles_el.find(qn("w:docDefaults"))
    if dd is None:
        dd = OxmlElement("w:docDefaults")
        styles_el.insert(0, dd)
    rpd = dd.find(qn("w:rPrDefault"))
    if rpd is None:
        rpd = sub(dd, "w:rPrDefault")
    clear_tag(rpd, "w:rPr")
    rpd.append(make_rpr(sz=9.0, cn=CN, en=EN))
    ppd = dd.find(qn("w:pPrDefault"))
    if ppd is None:
        ppd = sub(dd, "w:pPrDefault")
    clear_tag(ppd, "w:pPr")
    pPr = sub(ppd, "w:pPr")
    sub(pPr, "w:spacing", line=setnum(20), lineRule="exact")
    sub(pPr, "w:widowControl")

    # --- Normal ---
    try:
        st = doc.styles["Normal"]
    except KeyError:
        st = doc.styles.add_style("Normal", 1)
    el = st.element
    for t in ("w:rPr", "w:pPr"):
        clear_tag(el, t)
    pPr = sub(el, "w:pPr")
    sub(pPr, "w:spacing", line=setnum(20), lineRule="exact")
    sub(pPr, "w:jc", val="both")
    sub(pPr, "w:widowControl")
    el.append(make_rpr(sz=9.0, cn=CN, en=EN))

    # --- 模板样式 ---
    for name, spec in STYLES.items():
        try:
            st = doc.styles[name]
        except KeyError:
            st = doc.styles.add_style(name, 1)  # paragraph
        rebuild_style_element(st.element, name, spec)


# ----------------------------------------------------------------------
# 3. numbering.xml：标题多级列表 + 参考文献自动编号
# ----------------------------------------------------------------------
NUMBERING_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:abstractNum w:abstractNumId="10">
    <w:multiLevelType w:val="multilevel"/>
    <w:lvl w:ilvl="0">
      <w:start w:val="0"/>
      <w:numFmt w:val="decimal"/>
      <w:lvlText w:val="%1"/>
      <w:lvlJc w:val="left"/>
      <w:pPr><w:ind w:left="0" w:firstLine="0"/></w:pPr>
    </w:lvl>
    <w:lvl w:ilvl="1">
      <w:start w:val="1"/>
      <w:numFmt w:val="decimal"/>
      <w:lvlText w:val="%1.%2"/>
      <w:lvlJc w:val="left"/>
      <w:pPr><w:ind w:left="0" w:firstLine="0"/></w:pPr>
    </w:lvl>
    <w:lvl w:ilvl="2">
      <w:start w:val="1"/>
      <w:numFmt w:val="decimal"/>
      <w:lvlText w:val="%1.%2.%3"/>
      <w:lvlJc w:val="left"/>
      <w:pPr><w:ind w:left="0" w:firstLine="0"/></w:pPr>
    </w:lvl>
  </w:abstractNum>
  <w:num w:numId="10"><w:abstractNumId w:val="10"/></w:num>
  <w:abstractNum w:abstractNumId="20">
    <w:multiLevelType w:val="singleLevel"/>
    <w:lvl w:ilvl="0">
      <w:start w:val="1"/>
      <w:numFmt w:val="decimal"/>
      <w:lvlText w:val="[%1]"/>
      <w:lvlJc w:val="left"/>
      <w:pPr><w:ind w:left="360" w:hanging="360"/></w:pPr>
      <w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/></w:rPr>
    </w:lvl>
  </w:abstractNum>
  <w:num w:numId="20"><w:abstractNumId w:val="20"/></w:num>
</w:numbering>"""


def install_numbering(doc):
    from docx.opc.part import XmlPart
    from docx.opc.packuri import PackURI
    from docx.oxml import parse_xml
    element = parse_xml(NUMBERING_XML.encode("utf-8"))
    for rid, rel in list(doc.part.rels.items()):
        if rel.reltype.endswith("/numbering"):
            try:
                doc.part.drop_rel(rid)
            except Exception:
                pass
    target = None
    for p in doc.part.package.iter_parts():
        if str(p.partname) == "/word/numbering.xml":
            target = p
            break
    if target is not None:
        old = target.element
        for ch in list(old):
            old.remove(ch)
        for ch in list(element):
            old.append(ch)
        part = target
    else:
        part = XmlPart(PackURI("/word/numbering.xml"),
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml",
                       element, doc.part.package)
    doc.part.relate_to(part, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering")


# ----------------------------------------------------------------------
# 4. 清理覆盖样式的直接格式
# ----------------------------------------------------------------------
KEEP_RPR = {"w:vertAlign", "w:rStyle"}


def strip_direct_format(doc):
    n = 0
    for p in doc.paragraphs:
        for r in p.runs:
            rPr = r._element.find(qn("w:rPr"))
            if rPr is None:
                continue
            changed = False
            for ch in list(rPr):
                if ch.tag.split("}")[-1] in ("sz", "szCs", "rFonts", "b", "bCs", "i", "iCs",
                                             "caps", "smallCaps", "color", "spacing", "kern"):
                    if ch.tag.split("}")[-1] in ("i",):
                        continue  # 保留语义斜体
                    rPr.remove(ch)
                    changed = True
            if changed:
                n += 1
            if len(rPr) == 0:
                r._element.remove(rPr)
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for r in p.runs:
                        rPr = r._element.find(qn("w:rPr"))
                        if rPr is None:
                            continue
                        for ch in list(rPr):
                            if ch.tag.split("}")[-1] in ("sz", "szCs", "rFonts", "b", "bCs", "color"):
                                rPr.remove(ch)
                        if len(rPr) == 0:
                            r._element.remove(rPr)
    return n


# ----------------------------------------------------------------------
# 5. 分节 / 分栏
# ----------------------------------------------------------------------
# 页面参数取自模板 .doc 实测值（单位 twips：1 twip = 1/1440 in；A4 = 11900 x 16840）
# 注意：不可用 setnum()（pt->twip，x20）换算厘米值，否则页面尺寸会缩小约 28 倍。
PAGE_W, PAGE_H = "11900", "16840"
MARGIN = dict(top="1361", right="907", bottom="680", left="1191",
              header="737", footer="737", gutter="0")
COL_SPACE = "448"


def make_sect(cols=1, title_pg=False, last=False):
    """按 OOXML schema 顺序构造 sectPr（type, pgSz, pgMar, cols, titlePg, docGrid）。"""
    s = OxmlElement("w:sectPr")
    if not last:
        sub(s, "w:type", val="continuous")
    sub(s, "w:pgSz", w=PAGE_W, h=PAGE_H, orient="portrait")
    sub(s, "w:pgMar", **MARGIN)
    if cols == 1:
        sub(s, "w:cols", num="1")
    else:
        sub(s, "w:cols", num="2", space=COL_SPACE, equalWidth="1")
    if title_pg:
        sub(s, "w:titlePg")
    # 行网格 pitch = 20pt(400 twips)，与正文/标题行距一致，避免网格吸附改变行距
    sub(s, "w:docGrid", type="lines", linePitch="400")
    return s


PPR_ORDER_NUM = 6   # numPr 在 pPr 中的大致位置（widowControl 之后）


def ensure_numPr(pPr, ilvl, numid):
    """按 schema 顺序插入/替换 w:numPr。"""
    np = pPr.find(qn("w:numPr"))
    if np is None:
        np = OxmlElement("w:numPr")
        anchor = pPr.find(qn("w:widowControl"))
        if anchor is not None:
            anchor.addnext(np)
        else:
            pPr.insert(0, np)
    else:
        clear_tag(np, "w:ilvl")
        clear_tag(np, "w:numId")
    sub(np, "w:ilvl", val=ilvl)
    sub(np, "w:numId", val=numid)


def attach_sect(para, sect):
    pPr = para._p.get_or_add_pPr()
    clear_tag(pPr, "w:sectPr")
    pPr.append(sect)


# ----------------------------------------------------------------------
# 6. 页眉 / 页脚
# ----------------------------------------------------------------------
def build_header_footer(doc):
    from docx.opc.part import XmlPart
    from docx.opc.packuri import PackURI
    from docx.oxml import parse_xml

    def part_xml(inner, body_text):
        return ('<w:%s xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '%s</w:%s>' % (inner, body_text, inner))

    def para(text, sz, jc, cn=CN, b=False):
        rpr = ('<w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s"/>'
               '<w:sz w:val="%s"/><w:szCs w:val="%s"/>%s</w:rPr>') % (
            EN, EN, cn, half_pt(sz), half_pt(sz), "<w:b/>" if b else "")
        p = ('<w:p><w:pPr><w:spacing w:line="240" w:lineRule="exact"/>'
             '<w:jc w:val="%s"/></w:pPr><w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>') % (
            jc, rpr, text)
        return p

    hdr = (para("Journal of Computer Applications", 7.5, "center") +
           para("ISSN 1001-9081", 7.5, "center") +
           para("计算机应用   CODEN JYIIDU   http://www.joca.cn", 7.5, "center"))
    ftr = ('<w:p><w:pPr><w:spacing w:line="240" w:lineRule="exact"/><w:jc w:val="center"/></w:pPr>'
           '<w:r><w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s"/>'
           '<w:sz w:val="%s"/><w:szCs w:val="%s"/></w:rPr>'
           '<w:fldChar w:fldCharType="begin"/></w:r>'
           '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
           '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>') % (
        EN, EN, CN, half_pt(7.5), half_pt(7.5))

    def get_or_replace(partname, content_type, element):
        """若同名部件已存在则替换其内容，避免 zip 中出现重复部件名。"""
        for p in doc.part.package.iter_parts():
            if str(p.partname) == partname:
                old = p.element
                for k in list(old.attrib):
                    if k not in element.attrib:
                        del old.attrib[k]
                for k, v in element.attrib.items():
                    old.set(k, v)
                for ch in list(old):
                    old.remove(ch)
                for ch in list(element):
                    old.append(ch)
                return p
        return XmlPart(PackURI(partname), content_type, element, doc.part.package)

    hpart = get_or_replace("/word/header1.xml",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml",
                           parse_xml(part_xml("hdr", hdr)))
    fpart = get_or_replace("/word/footer1.xml",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml",
                           parse_xml(part_xml("ftr", ftr)))
    for rid, rel in list(doc.part.rels.items()):
        if rel.reltype.endswith("/header") or rel.reltype.endswith("/footer"):
            try:
                doc.part.drop_rel(rid)
            except Exception:
                pass
    hrid = doc.part.relate_to(hpart, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header")
    frid = doc.part.relate_to(fpart, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer")
    return hrid, frid


def add_hf_to_sect(sect, hrid, frid):
    """写入页眉/页脚引用。

    注意两点：
    1) 关系 ID 必须用 r:id（命名空间 r），写成 w:rid 会导致 Word/LibreOffice 无法解析；
    2) headerReference/footerReference 必须排在 sectPr 最前面（schema 顺序先于 type/pgSz）。
    """
    for t in ("w:headerReference", "w:footerReference"):
        clear_tag(sect, t)
    # 同时提供 default 与 first 引用：模板启用了 titlePg（首页不同），
    # 若只给 default 引用，Word/LibreOffice 会在首页显示空白页眉页脚。
    refs = [("w:headerReference", hrid), ("w:headerReference", hrid),
            ("w:footerReference", frid), ("w:footerReference", frid)]
    kinds = ["default", "first", "default", "first"]
    for (tag, rid), kind in zip(refs, kinds):
        el = OxmlElement(tag)
        el.set(qn("w:type"), kind)
        el.set(qn("r:id"), rid)
        sect.insert(0, el)


def add_hf_refs(body, hrid, frid):
    for sect in body.findall(qn("w:sectPr")):
        add_hf_to_sect(sect, hrid, frid)
    # 段落级 sectPr
    for p in body.findall(".//" + qn("w:p")):
        pPr = p.find(qn("w:pPr"))
        if pPr is None:
            continue
        sect = pPr.find(qn("w:sectPr"))
        if sect is None:
            continue
        add_hf_to_sect(sect, hrid, frid)


# ----------------------------------------------------------------------
# 7. 内容修正
# ----------------------------------------------------------------------
HEADING_RENAME = {
    "4.1  紧凑提交能否降低链上提交规模": "紧凑提交的规模隔离效果",
    "4.2  批大小如何影响 DA 感知摊销成本": "批大小对摊销成本的影响",
    "4.3  恢复机制能否改善超时场景下的挑战活性": "恢复机制对挑战活性的作用",
    "4.4  不同故障场景能否被检测、恢复或惩罚": "故障场景的检测与处置",
    "4.5  Solidity、本地 EVM 与 Sepolia 证据能否支撑链上对应物": "链上对应物的证据支撑",
    "3.1.4  协议性质": "挑战事实不变性与活性分离",
}

TYPO_FIX = [
    ("仲裁连续性。。", "仲裁连续性。"),
    ("其基本状态包括协议状态覆盖", "其基本状态覆盖"),
    ("可恢复仲裁路\t径", "可恢复仲裁路径"),
    ("构建DA 感知成本摊销模型", "构建 DA 感知成本摊销模型"),
]

# 参考文献：新顺序（按正文首次出现顺序）
REFERENCES = [
    ("Wen Xiaoqing, Feng Quanbi, Lyu Hanzheng, et al. TeeRollup: efficient Rollup design "
     "using heterogeneous TEE[PP/OL]. V3. arXiv (2025-11-30) [%s]. https://arxiv.org/abs/2409.14647. "
     "DOI:10.48550/arXiv.2409.14647." % ACCESS_DATE),
    ("Conway K D, So C, Yu X, et al. opML: optimistic machine learning on blockchain[PP/OL]. "
     "V2. arXiv (2024-02-05) [%s]. https://arxiv.org/abs/2401.17555. DOI:10.48550/arXiv.2401.17555." % ACCESS_DATE),
    ("Picco G, Fortugno A. Dynamic fraud proof[PP/OL]. arXiv (2025-02-14) [%s]. "
     "https://arxiv.org/abs/2502.10321. DOI:10.48550/arXiv.2502.10321." % ACCESS_DATE),
    ("Al-Bassam M. LazyLedger: a distributed data availability ledger with client-side smart "
     "contracts[PP/OL]. V4. arXiv (2019-06-08) [%s]. https://arxiv.org/abs/1905.09274. "
     "DOI:10.48550/arXiv.1905.09274." % ACCESS_DATE),
    ("Buterin V. An incomplete guide to Rollups[EB/OL]. (2021-01-05) [%s]. "
     "https://vitalik.eth.limo/general/2021/01/05/rollup.html." % ACCESS_DATE),
    ("ETHEREUM FOUNDATION. Optimistic Rollups[EB/OL]. (2024) [%s]. "
     "https://ethereum.org/en/developers/docs/scaling/optimistic-rollups/." % ACCESS_DATE),
    ("ARBITRUM FOUNDATION. Arbitrum Nitro technical documentation[EB/OL]. (2024) [%s]. "
     "https://docs.arbitrum.io/." % ACCESS_DATE),
    ("OP LABS. Optimism documentation: fault proofs and dispute games[EB/OL]. (2024) [%s]. "
     "https://docs.optimism.io/stack/fault-proofs/." % ACCESS_DATE),
    ("Tas E N, Tse D, Yang L, et al. Light clients for lazy blockchains[PP/OL]. V3. arXiv "
     "(2024-05-04) [%s]. https://arxiv.org/abs/2203.15968. DOI:10.48550/arXiv.2203.15968." % ACCESS_DATE),
    ("EIGENLABS. EigenDA documentation[EB/OL]. (2024) [%s]. https://docs.eigenda.xyz/." % ACCESS_DATE),
    ("CELESTIA. Celestia: modular blockchain network[EB/OL]. (2024) [%s]. https://docs.celestia.org/." % ACCESS_DATE),
    ("INTEL CORPORATION. Intel Software Guard Extensions developer guide[EB/OL]. (2024) [%s]. "
     "https://www.intel.com/content/www/us/en/developer/tools/software-guard-extensions.html." % ACCESS_DATE),
    ("ETHEREUM FOUNDATION. EIP-4844: shard blob transactions[EB/OL]. (2024) [%s]. "
     "https://eips.ethereum.org/EIPS/eip-4844." % ACCESS_DATE),
]

# 旧编号 -> 新编号
REF_MAP = {1: 1, 6: 3, 7: 4, 2: 5, 3: 6, 4: 7, 5: 8, 8: 9, 9: 10, 10: 11, 11: 12, 12: 13}

ADDED_CITATION = {
    23: ("TEEROLLUP", "[1]"),
    24: ("opML", "[2]"),
    25: ("Dynamic Fraud Proof", "[3]"),
    26: ("LazyLedger", "[4]"),
}


def para_text(p):
    return "".join(n.text or "" for n in p._p.iter(qn("w:t")))


def set_para_text(p, text, keep_math=True):
    """替换段落文本，保留 oMath 等内嵌对象（仅在无内嵌对象时使用）。"""
    for r in list(p._p.findall(qn("w:r"))):
        p._p.remove(r)


def replace_run_text(el, old, new):
    """在段落的所有 w:t 上做纯文本替换（跨 run 时退化为逐 run 替换）。"""
    ts = [n for n in el.iter(qn("w:t"))]
    if not ts:
        return False
    joined = "".join(t.text or "" for t in ts)
    if old not in joined:
        return False
    newjoined = joined.replace(old, new, 1)
    # 把结果写回第一个 w:t，其余清空
    ts[0].text = newjoined
    ts[0].set(qn("xml:space"), "preserve")
    for t in ts[1:]:
        t.text = ""
    return True


# ----------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------
def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, OUT)          # 在副本上工作，原文件只读
    doc = docx.Document(str(OUT))
    body = doc.element.body

    log = []

    # ---- 7.1 标题文本去手工编号 + 重命名 ----
    for p in doc.paragraphs:
        st = p.style.name
        if st not in ("一级标题", "二级标题", "三级标题"):
            continue
        txt = para_text(p)
        if txt in HEADING_RENAME:
            replace_run_text(p._p, txt, HEADING_RENAME[txt])
            log.append("重命名标题: %s -> %s" % (txt, HEADING_RENAME[txt]))
            txt = HEADING_RENAME[txt]
        m = re.match(r"^\s*(\d+(?:\.\d+)*)\s+(.*)$", txt)
        if m:
            replace_run_text(p._p, txt, m.group(2).strip())
            log.append("去除手工编号: %s -> %s" % (txt, m.group(2).strip()))

    # ---- 7.2 正文笔误 ----
    for p in doc.paragraphs:
        t = para_text(p)
        for a, bb in TYPO_FIX:
            if a in t:
                replace_run_text(p._p, a, bb)
                log.append("笔误修正: %r -> %r" % (a, bb))
                t = t.replace(a, bb)

    # ---- 7.3 引用编号重映射（必须先于补引，否则新增的引用号会被误重映射）----
    def remap(m):
        nums = [int(x) for x in re.findall(r"\d+", m.group(0))]
        new = "[%s]" % ",".join(str(REF_MAP.get(n, n)) for n in nums)
        return new

    for p in doc.paragraphs:
        if p.style.name == "文献列表":
            continue
        t = para_text(p)
        if not re.search(r"\[\d", t):
            continue
        newt = re.sub(r"\[\d+(?:\s*,\s*\d+)*\]", remap, t)
        if newt != t:
            # 重建文本（这些段落无内嵌数学对象）
            if p._p.find(".//" + qn("m:oMath")) is None:
                replace_run_text(p._p, t, newt)
                log.append("引用重编号: %s" % (re.findall(r"\[\d+(?:\s*,\s*\d+)*\]", t)[:4]))

    # ---- 7.4 新增引用（相关工作首现处；在重映射之后插入，编号不会被改写）----
    for idx, (anchor, cit) in ADDED_CITATION.items():
        if idx >= len(doc.paragraphs):
            continue
        p = doc.paragraphs[idx]
        t = para_text(p)
        if cit in t:
            continue
        if anchor in t:
            replace_run_text(p._p, anchor, anchor + cit)
            log.append("补引 %s 于段落 %d: %s…" % (cit, idx, t[:24]))

    # ---- 7.5 参考文献重写（去手工编号，改自动编号）----
    ref_ps = [p for p in doc.paragraphs if p.style.name == "文献列表" and para_text(p).strip()]
    for i, p in enumerate(ref_ps):
        t = para_text(p)
        t = re.sub(r"^\s*\[\d+\]\s*", "", t)
        if i < len(REFERENCES):
            t = REFERENCES[i]
        replace_run_text(p._p, para_text(p), t)
        pPr = p._p.get_or_add_pPr()
        np = pPr.find(qn("w:numPr"))
        if np is None:
            np = sub(pPr, "w:numPr")
        else:
            clear_tag(np, "w:ilvl")
            clear_tag(np, "w:numId")
        sub(np, "w:ilvl", val="0")
        sub(np, "w:numId", val="20")
    # 条目数不足时补齐（新增文献）
    while len(ref_ps) < len(REFERENCES) and ref_ps:
        newp = copy.deepcopy(ref_ps[-1]._p)
        ref_ps[-1]._p.addnext(newp)
        from docx.text.paragraph import Paragraph
        ref_ps.append(Paragraph(newp, None))
    for i, p in enumerate(ref_ps):
        if i >= len(REFERENCES):
            break
        t = re.sub(r"^\s*\[\d+\]\s*", "", para_text(p))
        if t.strip() != REFERENCES[i]:
            replace_run_text(p._p, para_text(p), REFERENCES[i])
    for p in ref_ps:
        ensure_numPr(p._p.get_or_add_pPr(), "0", "20")
    log.append("参考文献重写 %d 条（自动编号）" % len(ref_ps))

    # ---- 7.6 成本公式归并到 3.3 ----
    move_equations(doc, log)

    # （公式样式在样式重建后统一处理，见 §8 之后）

    # ---- 7.8 “参考文献”“随稿附件”标题不参与编号 ----
    for p in doc.paragraphs:
        if p.style.name in ("一级标题", "二级标题") and (
                para_text(p).strip() in ("参考文献",) or para_text(p).startswith("附：")):
            ensure_numPr(p._p.get_or_add_pPr(), "0", "0")
            log.append("标题取消自动编号: %s" % para_text(p)[:20])

    # ---- 7.9 随稿附件二级标题同样取消编号 ----
    for p in doc.paragraphs:
        if p.style.name == "二级标题" and re.match(r"^\d+\.\s", para_text(p)):
            ensure_numPr(p._p.get_or_add_pPr(), "0", "0")

    # ---- 8. 样式 / 编号 ----
    rebuild_styles(doc)
    install_numbering(doc)

    # ---- 8.1 编号公式段落套用“公式”样式 ----
    for p in doc.paragraphs:
        if p._p.find(".//" + qn("m:oMath")) is not None and p.style.name in ("Normal", "正文"):
            t = para_text(p)
            if re.search(r"\(\d\)", t.strip()) and len(t.strip()) <= 6:
                pPr = p._p.get_or_add_pPr()
                clear_tag(pPr, "w:pStyle")
                sub(pPr, "w:pStyle", val=doc.styles["公式"].style_id)

    # ---- 9. 三线表 + 表头重复 ----
    for t in doc.tables:
        make_three_line(t)

    # ---- 10. 分节与分栏 ----
    layout_sections(doc, log)

    # ---- 11. 页眉页脚 ----
    hrid, frid = build_header_footer(doc)
    add_hf_refs(doc.element.body, hrid, frid)

    # ---- 12. 清理直接格式 ----
    n = strip_direct_format(doc)
    log.append("清除直接格式 run 数: %d" % n)

    # ---- 13. 保留语义加粗：定义/性质/定理 ----
    for p in doc.paragraphs:
        t = para_text(p)
        if re.match(r"^(定义\s*\d|性质[一二三四五六七八九十]|定理\s*\d|推论\s*\d|引理\s*\d)", t):
            for r in p.runs[:1]:
                rPr = r._element.get_or_add_rPr()
                sub(rPr, "w:b")

    doc.save(str(OUT))
    print("\n".join(log))
    print("\n已保存:", OUT)


# ----------------------------------------------------------------------
def move_equations(doc, log):
    """把 §4 中的式(1)(2) 与变量说明前移到 §3.3 成本模型处，删除重复定义。"""
    ps = doc.paragraphs
    idx_33 = idx_e1 = idx_e2 = idx_var = None
    for i, p in enumerate(ps):
        t = para_text(p)
        if t.startswith("模型表达为") and "C_total" in t:
            idx_33 = i
        if p._p.find(".//" + qn("m:oMath")) is not None:
            tt = t.strip()
            if tt.endswith("(1)") and idx_e1 is None:
                idx_e1 = i
            elif tt.endswith("(2)") and idx_e2 is None:
                idx_e2 = i
    if idx_e1 is not None and idx_e1 + 2 < len(ps):
        idx_var = idx_e1 + 2
    if None in (idx_33, idx_e1, idx_e2, idx_var):
        log.append("公式归并跳过（定位失败）：33=%s e1=%s e2=%s var=%s" % (idx_33, idx_e1, idx_e2, idx_var))
        return

    p33 = ps[idx_33]._p
    e1 = ps[idx_e1]._p
    e2 = ps[idx_e2]._p
    var = ps[idx_var]._p

    # 3.3 原句改为引导语 + 变量说明；公式插到其后
    old33 = para_text(ps[idx_33])
    new33 = ("成本模型表达为式(1)、式(2)。其中，总成本由提交成本、数据可用性成本与争议处置成本构成，"
             "批处理后单笔摊销成本为总成本与批处理规模之比。")
    replace_run_text(p33, old33, new33)
    p33.addnext(e1)
    e1.addnext(e2)
    e2.addnext(var)
    log.append("成本公式(1)(2) 由第4节前移至 3.3 节，第 3.3 节改为引用式编号")


# ----------------------------------------------------------------------
def make_three_line(table):
    """三线表：顶线、栏目线下、底线；其余边框取消；首行重复表头。"""
    tblPr = table._tbl.tblPr
    clear_tag(tblPr, "w:tblBorders")
    borders = sub(tblPr, "w:tblBorders")
    for tag, val in (("top", "single"), ("bottom", "single"),
                     ("left", "nil"), ("right", "nil"),
                     ("insideH", "nil"), ("insideV", "nil")):
        e = sub(borders, "w:" + tag)
        if val == "nil":
            e.set(qn("w:val"), "nil")
        else:
            e.set(qn("w:val"), "single")
            e.set(qn("w:sz"), "6")
            e.set(qn("w:space"), "0")
            e.set(qn("w:color"), "000000")
    # 栏目线（表头行下边框）
    hdr = table.rows[0]._tr
    trPr = hdr.get_or_add_trPr()
    sub(trPr, "w:tblHeader")
    for c in hdr.tc_lst:
        tcPr = c.get_or_add_tcPr()
        clear_tag(tcPr, "w:tcBorders")
        tb = sub(tcPr, "w:tcBorders")
        b = sub(tb, "w:bottom")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "6")
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), "000000")


# ----------------------------------------------------------------------
def layout_sections(doc, log):
    """前置部分通栏；正文双栏；宽图/宽表通栏；随稿材料通栏。"""
    body = doc.element.body
    children = [c for c in body.iterchildren()
                if c.tag in (qn("w:p"), qn("w:tbl"))]

    # 定位宽块（图片段 / 表格）
    wide = []          # (首元素, 末元素)
    for i, c in enumerate(children):
        if c.tag == qn("w:p") and c.find(".//" + qn("w:drawing")) is not None:
            last = children[i]
            j = i + 1
            while j < len(children) and children[j].tag == qn("w:p") and \
                    children[j].find(qn("w:pPr")) is not None and \
                    children[j].find(qn("w:pPr")).find(qn("w:pStyle")) is not None and \
                    children[j].find(qn("w:pPr")).find(qn("w:pStyle")).get(qn("w:val")) in ("图表名称",):
                last = children[j]
                j += 1
            wide.append((children[i], last))
        elif c.tag == qn("w:tbl"):
            prev = children[i - 1]
            wide.append((children[i - 2] if i >= 2 and children[i - 2].tag == qn("w:p") else prev,
                         c))
    # 去重（表格与其前一标题可能重叠）
    seen = set()
    uniq = []
    for a, b in wide:
        if id(a) in seen:
            continue
        seen.add(id(a))
        seen.add(id(b))
        uniq.append((a, b))
    wide = uniq

    # 最后一个正文一级标题“附：随稿附件”的起点
    attach_start = None
    for c in children:
        pPr = c.find(qn("w:pPr")) if c.tag == qn("w:p") else None
        if pPr is None:
            continue
        ps_ = pPr.find(qn("w:pStyle"))
        if ps_ is not None and ps_.get(qn("w:val")) == "一级标题":
            t = "".join(n.text or "" for n in c.iter(qn("w:t")))
            if t.startswith("附："):
                attach_start = c
    front_end = None
    # 前置部分：正文第一个一级标题（引言）之前的最后一个“摘要关键词”段落（英文关键词）。
    # 注意：随稿材料里的基金项目/作者简介/联系方式也使用“摘要关键词”样式，
    # 不能简单取全文最后一个，否则前置区分节会落到随稿材料里。
    first_h1 = None
    for i, c in enumerate(children):
        pPr = c.find(qn("w:pPr")) if c.tag == qn("w:p") else None
        if pPr is None:
            continue
        ps_ = pPr.find(qn("w:pStyle"))
        if ps_ is not None and ps_.get(qn("w:val")) == "一级标题":
            first_h1 = i
            break
    for i in range(first_h1 if first_h1 is not None else len(children)):
        c = children[i]
        pPr = c.find(qn("w:pPr")) if c.tag == qn("w:p") else None
        if pPr is None:
            continue
        ps_ = pPr.find(qn("w:pStyle"))
        if ps_ is not None and ps_.get(qn("w:val")) == "摘要关键词":
            front_end = c

    allc = children
    attach_to = None

    def attach_to(el, sect):
        """el 为 body 直接子元素（w:p 或 w:tbl）"""
        if el.tag == qn("w:p"):
            from docx.text.paragraph import Paragraph
            attach_sect(Paragraph(el, None), sect)
        else:
            lp = el.findall(".//" + qn("w:p"))[-1]
            from docx.text.paragraph import Paragraph
            attach_sect(Paragraph(lp, None), sect)

    # 前置部分结束：1 栏 + 首页不同
    if front_end is not None:
        attach_to(front_end, make_sect(cols=1, title_pg=True))
    # 随稿材料起点前一段：结束双栏
    if attach_start is not None:
        idx = allc.index(attach_start)
        for k in range(idx - 1, -1, -1):
            if allc[k].tag == qn("w:p"):
                attach_to(allc[k], make_sect(cols=1))
                break
    # 宽块：前一段结束双栏，块末结束通栏（仅处理正文区；随稿材料本身通栏，不参与）
    limit = allc.index(attach_start) if attach_start is not None else len(allc)
    for first, last in wide:
        if allc.index(first) >= limit:
            continue
        fi = allc.index(first)
        for k in range(fi - 1, -1, -1):
            if allc[k].tag == qn("w:p"):
                attach_to(allc[k], make_sect(cols=2))
                break
        attach_to(last, make_sect(cols=1))

    # 文末 sectPr
    body_sect = body.find(qn("w:sectPr"))
    if body_sect is not None:
        body.remove(body_sect)
    body.append(make_sect(cols=1, last=True))
    log.append("分节：前置通栏 + 正文双栏 + %d 处通栏图表/表格 + 随稿材料通栏" % len(wide))


if __name__ == "__main__":
    main()
