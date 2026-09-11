from __future__ import annotations

import re
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path
from lxml import etree

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def qn(name: str) -> str:
    prefix, local = name.split(":")
    return f"{{{NS[prefix]}}}{local}"


def text_of(el) -> str:
    return "".join(el.xpath(".//w:t/text()", namespaces=NS)).strip()


def ensure(parent, tag):
    el = parent.find(tag, NS)
    if el is None:
        el = etree.Element(qn(tag))
        if tag in {"w:pPr", "w:rPr"}:
            parent.insert(0, el)
        else:
            parent.append(el)
    return el


def set_text(p, text: str) -> None:
    ppr = p.find("w:pPr", NS)
    old_rpr = p.find("w:r/w:rPr", NS)
    for child in list(p):
        if child is not ppr:
            p.remove(child)
    r = etree.SubElement(p, qn("w:r"))
    if old_rpr is not None:
        r.append(deepcopy(old_rpr))
    t = etree.SubElement(r, qn("w:t"))
    t.set(XML_SPACE, "preserve")
    t.text = text


def set_run_font(r, east_asia: str | None = None, ascii_font: str | None = None, size_half_pt: int | None = None, bold: bool | None = None):
    rpr = ensure(r, "w:rPr")
    fonts = rpr.find("w:rFonts", NS)
    if fonts is None:
        fonts = etree.Element(qn("w:rFonts"))
        rpr.insert(0, fonts)
    if east_asia:
        fonts.set(qn("w:eastAsia"), east_asia)
    if ascii_font:
        fonts.set(qn("w:ascii"), ascii_font)
        fonts.set(qn("w:hAnsi"), ascii_font)
        fonts.set(qn("w:cs"), ascii_font)
    if size_half_pt is not None:
        sz = rpr.find("w:sz", NS)
        if sz is None:
            sz = etree.SubElement(rpr, qn("w:sz"))
        sz.set(qn("w:val"), str(size_half_pt))
        szcs = rpr.find("w:szCs", NS)
        if szcs is None:
            szcs = etree.SubElement(rpr, qn("w:szCs"))
        szcs.set(qn("w:val"), str(size_half_pt))
    if bold is not None:
        b = rpr.find("w:b", NS)
        if bold and b is None:
            etree.SubElement(rpr, qn("w:b"))
        elif not bold and b is not None:
            rpr.remove(b)
        bcs = rpr.find("w:bCs", NS)
        if bold and bcs is None:
            etree.SubElement(rpr, qn("w:bCs"))
        elif not bold and bcs is not None:
            rpr.remove(bcs)


def format_para(p, align: str | None = None, before: int | None = None, after: int | None = None, line: int | None = None):
    ppr = ensure(p, "w:pPr")
    if align:
        jc = ppr.find("w:jc", NS)
        if jc is None:
            jc = etree.SubElement(ppr, qn("w:jc"))
        jc.set(qn("w:val"), align)
    if before is not None or after is not None or line is not None:
        spacing = ppr.find("w:spacing", NS)
        if spacing is None:
            spacing = etree.SubElement(ppr, qn("w:spacing"))
        if before is not None:
            spacing.set(qn("w:before"), str(before))
        if after is not None:
            spacing.set(qn("w:after"), str(after))
        if line is not None:
            spacing.set(qn("w:line"), str(line))
            spacing.set(qn("w:lineRule"), "auto")


def apply_font_to_para(p, east_asia=None, ascii_font=None, size_half_pt=None, bold=None):
    for r in p.findall("w:r", NS):
        set_run_font(r, east_asia=east_asia, ascii_font=ascii_font, size_half_pt=size_half_pt, bold=bold)


def make_para_like(template, text: str):
    p = etree.fromstring(etree.tostring(template))
    set_text(p, text)
    return p


def clone_section_with_cols(final_sect, cols_num: int):
    sect = deepcopy(final_sect)
    cols = sect.find("w:cols", NS)
    if cols is None:
        cols = etree.SubElement(sect, qn("w:cols"))
    if cols_num == 1:
        cols.attrib.pop(qn("w:num"), None)
    else:
        cols.set(qn("w:num"), str(cols_num))
        cols.set(qn("w:space"), "420")
    typ = sect.find("w:type", NS)
    if typ is None:
        typ = etree.SubElement(sect, qn("w:type"))
    typ.set(qn("w:val"), "continuous")
    return sect


def insert_section_on_para(p, sect):
    ppr = ensure(p, "w:pPr")
    old = ppr.find("w:sectPr", NS)
    if old is not None:
        ppr.remove(old)
    ppr.append(sect)


def main():
    draft = Path(__file__).resolve().parent
    src = draft / "Hybrid_TEE_Rollup修改版.docx"
    out = draft / "Hybrid_TEE_Rollup_导师意见修订版.docx"
    shutil.copyfile(src, out)

    with zipfile.ZipFile(out, "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    root = etree.fromstring(files["word/document.xml"])
    body = root.find("w:body", NS)
    final_sect = body.find("w:sectPr", NS)
    if final_sect is None:
        raise RuntimeError("No final section properties found.")
    final_cols = final_sect.find("w:cols", NS)
    if final_cols is None:
        final_cols = etree.SubElement(final_sect, qn("w:cols"))
    final_cols.set(qn("w:num"), "2")
    final_cols.set(qn("w:space"), "420")

    # Replace and format front matter.
    front_replacements = {
        "摘  要：": "摘  要：高频去中心化应用（DApp）要求低延迟、低链上开销与公开可验证仲裁并存。本文面向 Hybrid TEE-Rollup 场景，提出可恢复挑战机制、携带证据的紧凑提交机制和数据可用性感知成本模型。可恢复挑战机制将超时会话恢复为可重放、可结算状态；紧凑提交绑定状态根、输出哈希、证明哈希、DA 指针与 DA 根；成本模型用于分析负载规模、批处理摊销与 DA 路径选择。基于 Python 原型、本地 EVM gas 测量与 Sepolia 部署记录，实验显示紧凑提交平均约 406 字节，在给定配置下模块化 DA 采样路径可降低约 96.33% 摊销成本，可恢复路径改善超时场景下的挑战完成能力。上述结论基于模拟 TEE、可验证 DA 注册表和配置化成本模型。",
        "关键词：": "关键词：Hybrid TEE-Rollup；交互式挑战；数据可用性；高频 DApp；成本摊销；故障恢复",
        "中图分类号：": "文献标志码：A    中图分类号：TP311",
        "Recoverable Challenge Protocol": "Recoverable Challenge Protocol and Lightweight DA Cost Evaluation for Hybrid TEE-Rollup in High-Frequency DApps",
        "Abstract:": "Abstract: High-frequency decentralized applications (DApps) require low latency, low on-chain overhead, and publicly verifiable arbitration. This paper proposes a recoverable challenge mechanism, an evidence-carrying compact commitment mechanism, and a data-availability-aware cost model for Hybrid TEE-Rollup. The recoverable challenge mechanism restores timeout sessions to replayable and settleable states; the compact commitment binds the state root, output hash, proof hash, DA pointer, and DA root; and the cost model analyzes payload size, batching amortization, and DA path selection. Based on a Python prototype, local EVM gas measurements, and Sepolia deployment records, the compact commitment averages about 406 bytes, the modular DA sampling path reduces amortized cost by about 96.33% under the given configuration, and the recovery path improves challenge completion under timeout scenarios. The conclusions are based on a simulated TEE, a verifiable DA registry, and a configurable cost model.",
        "Key words:": "Key words: Hybrid TEE-Rollup; interactive challenge; data availability; high-frequency DApp; cost amortization; fault recovery",
    }
    for p in body.findall("w:p", NS):
        t = text_of(p)
        for prefix, new_text in front_replacements.items():
            if t.startswith(prefix):
                set_text(p, new_text)
                break

    paras = body.findall("w:p", NS)
    if len(paras) >= 9:
        # first nine visible paragraphs are title through Key words.
        for idx, p in enumerate(paras[:9], 1):
            if idx == 1:
                format_para(p, align="center", before=0, after=120, line=300)
                apply_font_to_para(p, east_asia="黑体", ascii_font="Times New Roman", size_half_pt=36, bold=True)
            elif idx == 2:
                format_para(p, align="center", after=80, line=240)
                apply_font_to_para(p, east_asia="楷体", ascii_font="Times New Roman", size_half_pt=24, bold=False)
            elif idx in {3, 4, 5}:
                format_para(p, align="left", after=60, line=240)
                apply_font_to_para(p, east_asia="楷体", ascii_font="Times New Roman", size_half_pt=20, bold=False)
            elif idx == 6:
                format_para(p, align="center", before=80, after=60, line=260)
                apply_font_to_para(p, east_asia="Times New Roman", ascii_font="Times New Roman", size_half_pt=28, bold=True)
            elif idx == 7:
                format_para(p, align="center", after=40, line=240)
                apply_font_to_para(p, east_asia="Times New Roman", ascii_font="Times New Roman", size_half_pt=24, bold=False)
            elif idx in {8, 9}:
                format_para(p, align="left", after=60, line=240)
                apply_font_to_para(p, east_asia="Times New Roman", ascii_font="Times New Roman", size_half_pt=20, bold=False)
        insert_section_on_para(paras[8], clone_section_with_cols(final_sect, 1))

    # Move and compress related work.
    blocks = list(body)
    p_by_text = {text_of(el): el for el in body.findall("w:p", NS)}
    section2 = p_by_text.get("2  背景与威胁模型")
    old21 = p_by_text.get("2.1  Rollup、可信执行环境与数据可用性")
    old22 = p_by_text.get("2.2  问题范围与对抗假设")
    rel_heading = p_by_text.get("6.5  相关工作")
    if not all([section2, old21, old22, rel_heading]):
        raise RuntimeError("Required headings not found.")

    set_text(section2, "2  相关工作与背景")
    set_text(old21, "2.2  Rollup、可信执行环境与数据可用性")
    set_text(old22, "2.3  问题范围与对抗假设")

    related_texts = [
        "2.1  相关工作",
        "TEEROLLUP 提出了利用异构 TEE 降低 Rollup 验证成本的系统设计。本文受其思路启发，但聚焦异常场景下的挑战恢复和紧凑提交的证据绑定。",
        "opML 与 optimistic fraud proof 等工作研究如何通过乐观证明支持复杂计算，通常包含二分定位、单步仲裁和链上验证。本文借鉴交互式争议定位思想，但不实现完整 FPVM 或真实 ML 执行证明，而将二分重放用于 Hybrid TEE-Rollup 原型中的异常仲裁。",
        "Dynamic Fraud Proof 关注无争议场景下的最终性压缩，并在发现争议时动态延迟结算。该方向强调挑战窗口和验证者参与机制的动态调整；本文聚焦更窄的超时后挑战会话恢复问题。",
        "LazyLedger、模块化 DA 以及轻客户端相关工作强调数据可用性与执行验证解耦。本文使用可验证 DA 注册表和配置化建模分析紧凑提交加数据可用性验证的成本趋势。",
    ]
    heading_template = rel_heading
    body_template = p_by_text.get("TEEROLLUP 提出了利用异构 TEE 降低 Rollup 验证成本的系统设计。本文受其思路启发，但聚焦异常场景下的挑战恢复和紧凑提交的证据绑定。")
    insert_at = body.index(section2) + 1
    for i, t in enumerate(related_texts):
        p = make_para_like(heading_template if i == 0 else body_template, t)
        body.insert(insert_at, p)
        insert_at += 1

    # Replace Section 6 with the requested short conclusion.
    blocks = list(body)
    start6 = next(i for i, el in enumerate(blocks) if el.tag == qn("w:p") and text_of(el) == "6  讨论与局限性")
    ref_i = next(i for i, el in enumerate(blocks) if el.tag == qn("w:p") and text_of(el) == "参考文献")
    conclusion_heading = blocks[start6]
    set_text(conclusion_heading, "6  结论")
    para_template = blocks[start6 + 1]
    conclusion1 = "本文面向高频去中心化应用中的低延迟、低链上开销与公开可验证仲裁需求，提出了面向 Hybrid TEE-Rollup 的可恢复挑战机制、携带证据的紧凑提交机制以及数据可用性感知成本模型。可恢复挑战机制将超时会话恢复为可重放、可结算状态，强调恢复操作只恢复协议活性而不改变争议事实；紧凑提交机制绑定状态根、输出哈希、证明哈希、DA 指针与 DA 根，为异常路径提供最小证据入口；成本模型则用于分析负载规模、批处理摊销与 DA 路径选择之间的关系。"
    conclusion2 = "基于 Python 原型、本地 EVM gas 测量与 Sepolia 部署记录，实验结果表明，紧凑提交能够隔离链上提交规模与完整负载增长，在给定配置下模块化 DA 采样路径具有明显的摊销成本优势，恢复路径也能改善超时场景下的挑战完成能力。需要说明的是，当前结果基于模拟 TEE、可验证 DA 注册表和配置化成本模型，尚不代表真实主网或生产环境表现。后续工作将进一步接入真实 TEE 与数据可用性网络，并完善并发挑战、恢复频率限制和故障到罚没的统一处理机制。"
    p1 = make_para_like(para_template, conclusion1)
    p2 = make_para_like(para_template, conclusion2)
    # Remove everything between old section-6 heading and references.
    for el in blocks[start6 + 1 : ref_i]:
        body.remove(el)
    body.insert(body.index(conclusion_heading) + 1, p1)
    body.insert(body.index(conclusion_heading) + 2, p2)

    # Format headings after all text mutations.
    for p in body.findall("w:p", NS):
        t = text_of(p)
        if re.match(r"^\d+\s", t):
            format_para(p, before=120, after=60, line=240)
            apply_font_to_para(p, east_asia="黑体", ascii_font="Times New Roman", size_half_pt=23, bold=True)
        elif re.match(r"^\d+\.\d+\s", t):
            format_para(p, before=80, after=40, line=240)
            apply_font_to_para(p, east_asia="黑体", ascii_font="Times New Roman", size_half_pt=23, bold=True)
        elif re.match(r"^\d+\.\d+\.\d+", t):
            format_para(p, before=60, after=30, line=240)
            apply_font_to_para(p, east_asia="黑体", ascii_font="Times New Roman", size_half_pt=21, bold=True)

    files["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)

    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
