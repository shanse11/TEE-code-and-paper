from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from lxml import etree

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}

W = f"{{{NS['w']}}}"
WP = f"{{{NS['wp']}}}"
A = f"{{{NS['a']}}}"

EMU_PER_INCH = 914400
DXA_PER_INCH = 1440
COLUMN_IN = 3.10
COLUMN_EMU = int(COLUMN_IN * EMU_PER_INCH)
COLUMN_DXA = int(COLUMN_IN * DXA_PER_INCH)


def qn(name: str) -> str:
    prefix, local = name.split(":")
    return f"{{{NS[prefix]}}}{local}"


def text_of(el) -> str:
    return "".join(el.xpath(".//w:t/text()", namespaces=NS)).strip()


def set_para_text(p, text: str) -> None:
    ppr = p.find("w:pPr", NS)
    for child in list(p):
        if child is not ppr:
            p.remove(child)
    r = etree.SubElement(p, qn("w:r"))
    t = etree.SubElement(r, qn("w:t"))
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text


def set_cell_text(tc, text: str) -> None:
    tcpr = tc.find("w:tcPr", NS)
    for child in list(tc):
        if child is not tcpr:
            tc.remove(child)
    p = etree.SubElement(tc, qn("w:p"))
    r = etree.SubElement(p, qn("w:r"))
    t = etree.SubElement(r, qn("w:t"))
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text


def ensure(parent, tag):
    el = parent.find(tag, NS)
    if el is None:
        el = etree.Element(qn(tag))
        # Word property elements must precede content children; otherwise renderers
        # can ignore direct formatting such as table font sizes.
        first_tags = {"w:pPr", "w:rPr", "w:tcPr", "w:trPr", "w:tblPr"}
        if tag in first_tags:
            parent.insert(0, el)
        else:
            parent.append(el)
    return el


def set_table_width(tbl, widths):
    tblpr = ensure(tbl, "w:tblPr")
    tblw = ensure(tblpr, "w:tblW")
    tblw.set(qn("w:type"), "dxa")
    tblw.set(qn("w:w"), str(COLUMN_DXA))
    jc = tblpr.find("w:jc", NS)
    if jc is None:
        jc = etree.SubElement(tblpr, qn("w:jc"))
    jc.set(qn("w:val"), "center")
    layout = tblpr.find("w:tblLayout", NS)
    if layout is None:
        layout = etree.SubElement(tblpr, qn("w:tblLayout"))
    layout.set(qn("w:type"), "fixed")
    mar = tblpr.find("w:tblCellMar", NS)
    if mar is None:
        mar = etree.SubElement(tblpr, qn("w:tblCellMar"))
    for side in ("top", "left", "bottom", "right"):
        m = mar.find(f"w:{side}", NS)
        if m is None:
            m = etree.SubElement(mar, qn(f"w:{side}"))
        m.set(qn("w:w"), "30")
        m.set(qn("w:type"), "dxa")

    borders = tblpr.find("w:tblBorders", NS)
    if borders is not None:
        tblpr.remove(borders)
    borders = etree.SubElement(tblpr, qn("w:tblBorders"))
    for side in ("top", "bottom"):
        b = etree.SubElement(borders, qn(f"w:{side}"))
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "6")
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), "000000")
    for side in ("left", "right", "insideV"):
        b = etree.SubElement(borders, qn(f"w:{side}"))
        b.set(qn("w:val"), "nil")
    inside = etree.SubElement(borders, qn("w:insideH"))
    inside.set(qn("w:val"), "nil")

    grid = tbl.find("w:tblGrid", NS)
    if grid is not None:
        tbl.remove(grid)
    grid = etree.Element(qn("w:tblGrid"))
    tbl.insert(1 if tblpr is not None else 0, grid)
    for w in widths:
        col = etree.SubElement(grid, qn("w:gridCol"))
        col.set(qn("w:w"), str(w))

    rows = tbl.findall("w:tr", NS)
    for r_idx, tr in enumerate(rows):
        trpr = tr.find("w:trPr", NS)
        if trpr is not None:
            for h in trpr.findall("w:trHeight", NS):
                trpr.remove(h)
        for c_idx, tc in enumerate(tr.findall("w:tc", NS)):
            tcpr = ensure(tc, "w:tcPr")
            tcw = ensure(tcpr, "w:tcW")
            tcw.set(qn("w:type"), "dxa")
            tcw.set(qn("w:w"), str(widths[min(c_idx, len(widths) - 1)]))
            v_align = tcpr.find("w:vAlign", NS)
            if v_align is None:
                v_align = etree.SubElement(tcpr, qn("w:vAlign"))
            v_align.set(qn("w:val"), "center")
            for p in tc.findall(".//w:p", NS):
                ppr = ensure(p, "w:pPr")
                spacing = ppr.find("w:spacing", NS)
                if spacing is None:
                    spacing = etree.SubElement(ppr, qn("w:spacing"))
                spacing.set(qn("w:before"), "0")
                spacing.set(qn("w:after"), "0")
                spacing.set(qn("w:line"), "180")
                spacing.set(qn("w:lineRule"), "auto")
                for r in p.findall("w:r", NS):
                    rpr = ensure(r, "w:rPr")
                    sz = ensure(rpr, "w:sz")
                    szcs = ensure(rpr, "w:szCs")
                    # 7.5 pt, readable but compact for one-column tables.
                    sz.set(qn("w:val"), "15")
                    szcs.set(qn("w:val"), "15")
        if r_idx == 0:
            trpr = ensure(tr, "w:trPr")
            for tc in tr.findall("w:tc", NS):
                tcpr = ensure(tc, "w:tcPr")
                borders = tcpr.find("w:tcBorders", NS)
                if borders is None:
                    borders = etree.SubElement(tcpr, qn("w:tcBorders"))
                bottom = borders.find("w:bottom", NS)
                if bottom is None:
                    bottom = etree.SubElement(borders, qn("w:bottom"))
                bottom.set(qn("w:val"), "single")
                bottom.set(qn("w:sz"), "6")
                bottom.set(qn("w:color"), "000000")


def remove_block(body, block) -> None:
    if block is not None and block.getparent() is body:
        body.remove(block)


def main() -> None:
    base = Path(__file__).with_name("final_reference_structure_fixed.docx")
    out = Path(__file__).with_name("final_layout_fixed_only.docx")
    shutil.copyfile(base, out)

    with zipfile.ZipFile(out, "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    root = etree.fromstring(files["word/document.xml"])
    body = root.find("w:body", NS)

    # Remove all continuous section breaks embedded in paragraphs; keep one final two-column section.
    for sect in root.xpath("//w:pPr/w:sectPr", namespaces=NS):
        sect.getparent().remove(sect)
    final_sect = body.find("w:sectPr", NS)
    if final_sect is None:
        final_sect = etree.SubElement(body, qn("w:sectPr"))
    cols = final_sect.find("w:cols", NS)
    if cols is None:
        cols = etree.SubElement(final_sect, qn("w:cols"))
    cols.set(qn("w:num"), "2")
    cols.set(qn("w:space"), "420")
    typ = final_sect.find("w:type", NS)
    if typ is None:
        typ = etree.SubElement(final_sect, qn("w:type"))
    typ.set(qn("w:val"), "continuous")

    # Remove manual page breaks and empty section-only paragraphs left by prior layout surgery.
    for br in root.xpath("//w:br[@w:type='page']", namespaces=NS):
        br.getparent().remove(br)

    # Inline figures: scale to a single column and preserve aspect ratio.
    for drawing in root.xpath("//w:drawing", namespaces=NS):
        inline = drawing.find("wp:inline", NS)
        anchor = drawing.find("wp:anchor", NS)
        obj = inline if inline is not None else anchor
        if obj is None:
            continue
        extent = obj.find("wp:extent", NS)
        if extent is None:
            continue
        cx = int(extent.get("cx", "0"))
        cy = int(extent.get("cy", "0"))
        if cx <= 0 or cy <= 0:
            continue
        if anchor is not None:
            # Convert anchored/floating drawings to inline to avoid clipping and text overlap.
            anchor.tag = qn("wp:inline")
            obj = anchor
        new_cx = min(cx, COLUMN_EMU)
        new_cy = round(cy * new_cx / cx)
        extent.set("cx", str(new_cx))
        extent.set("cy", str(new_cy))
        for xfrm in drawing.xpath(".//a:xfrm", namespaces=NS):
            ext = xfrm.find("a:ext", NS)
            if ext is not None:
                ext.set("cx", str(new_cx))
                ext.set("cy", str(new_cy))

    # Compact Table 2 wording as requested.
    tables = body.findall("w:tbl", NS)
    table2 = tables[1]
    table2_data = [
        ["系统", "挑战", "恢复", "DA", "成本"],
        ["OP", "欺诈证明", "窗口", "非重点", "未建模"],
        ["Arb", "交互争议", "推进", "非重点", "未建模"],
        ["OTR", "TEE 乐观", "有限", "部分关联", "未建模"],
        ["TEE-R", "TEE 快速", "机制", "架构", "未摊销"],
        ["本文", "可恢复", "活性转移", "字段证明", "负载/批/路径"],
    ]
    for tr, row in zip(table2.findall("w:tr", NS), table2_data):
        for tc, val in zip(tr.findall("w:tc", NS), row):
            set_cell_text(tc, val)

    # Gas table: use requested header wording.
    gas_table = tables[10]
    header = gas_table.find("w:tr", NS)
    for tc, val in zip(header.findall("w:tc", NS), ["操作", "gasUsed", "含义"]):
        set_cell_text(tc, val)
    for tr in gas_table.findall("w:tr", NS)[1:]:
        cells = tr.findall("w:tc", NS)
        if len(cells) >= 2:
            txt = text_of(cells[1]).replace(".00", "")
            set_cell_text(cells[1], txt)

    # Update prose references for the removed deployment-address table.
    for p in body.findall("w:p", NS):
        t = text_of(p)
        if "同一套合约已部署到 Sepolia 测试网，见表 6" in t:
            set_para_text(
                p,
                "RQ5 评估链上合约对应物。当前项目已将核心路径映射为 Solidity 合约，并在 Hardhat 本地 EVM 测试链上得到 gas 用量基线，见表 5。同一套合约已部署至 Sepolia 测试网，Chain ID 为 11155111，部署区块为 10825904。这些结果说明原型路径具有合约对应物和公开测试网可部署性，不应被解释为生产可用性。",
            )
        elif t.startswith("上述 RQ1 至 RQ5 已经包含了部分对比分析"):
            set_para_text(
                p,
                "上述 RQ1 至 RQ5 已经包含了部分对比分析。总体来看，可恢复路径使超时场景从检测停滞推进到可重放与结算；紧凑提交将链上提交稳定在约 406 字节；DA 感知成本模型说明批处理和数据可用性路径共同决定摊销成本；故障分类则区分检测、拒绝、重放与罚没等不同协议能力。",
            )
        elif t.startswith("从对照可以看出"):
            set_para_text(
                p,
                "从相关工作梳理可以看出，已有工作已经提供 TEE-Rollup、乐观欺诈证明和模块化数据可用性等主要路线；本文将可恢复挑战路径、数据可用性绑定紧凑提交和轻量成本模型放入同一个可运行研究原型中，并分别用 Python、Hardhat 与 Sepolia 证据说明机制可行性、链上对应物和可部署性边界。",
            )

    # Remove Table 6 (deployment addresses), Table 7, and Table 8 with their captions.
    delete_text_starts = {
        "表 6  Sepolia 部署信息",
        "Table 6  Sepolia deployment information",
        "表 7  对比实验小结",
        "Table 7  Summary of comparison experiments",
        "表 8  相关工作与本文工作的对照",
        "Table 8  Comparison with related work",
    }
    blocks = list(body)
    for block in blocks:
        if block.tag == qn("w:p") and text_of(block) in delete_text_starts:
            remove_block(body, block)
    for tbl in list(body.findall("w:tbl", NS)):
        first = text_of(tbl)
        if (
            first.startswith("项目数值Network / Chain ID")
            or first.startswith("对比维度对应研究问题")
            or first.startswith("方向 / 工作核心关注")
        ):
            remove_block(body, tbl)

    # Remove blank paragraphs created only for old section toggles.
    for p in list(body.findall("w:p", NS)):
        if not text_of(p) and not p.xpath(".//w:drawing", namespaces=NS):
            ppr = p.find("w:pPr", NS)
            if ppr is None or len(ppr) == 0:
                body.remove(p)

    # Table geometry after deletions.
    tables = body.findall("w:tbl", NS)
    for tbl in tables:
        rows = tbl.findall("w:tr", NS)
        cols_count = len(rows[0].findall("w:tc", NS)) if rows else 1
        if cols_count == 1:
            widths = [COLUMN_DXA]
        elif cols_count == 2:
            widths = [int(COLUMN_DXA * 0.34), COLUMN_DXA - int(COLUMN_DXA * 0.34)]
        elif cols_count == 3:
            widths = [int(COLUMN_DXA * 0.25), int(COLUMN_DXA * 0.25), COLUMN_DXA - int(COLUMN_DXA * 0.50)]
        elif cols_count == 4:
            widths = [int(COLUMN_DXA * 0.20), int(COLUMN_DXA * 0.25), int(COLUMN_DXA * 0.25), COLUMN_DXA - int(COLUMN_DXA * 0.70)]
        else:
            widths = [int(COLUMN_DXA * 0.22), int(COLUMN_DXA * 0.19), int(COLUMN_DXA * 0.17), int(COLUMN_DXA * 0.14)]
            widths.append(COLUMN_DXA - sum(widths))
        set_table_width(tbl, widths)

    # Five-column semantic table needs extra compact text to avoid vertical wrapping in one column.
    tables = body.findall("w:tbl", NS)
    if len(tables) >= 2:
        for r in tables[1].xpath(".//w:r", namespaces=NS):
            rpr = ensure(r, "w:rPr")
            sz = ensure(rpr, "w:sz")
            szcs = ensure(rpr, "w:szCs")
            sz.set(qn("w:val"), "11")
            szcs.set(qn("w:val"), "11")

    files["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)


if __name__ == "__main__":
    main()
