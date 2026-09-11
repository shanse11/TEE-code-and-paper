from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from lxml import etree

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
}

EMU_PER_INCH = 914400
DXA_PER_INCH = 1440


def qn(name: str) -> str:
    prefix, local = name.split(":")
    return f"{{{NS[prefix]}}}{local}"


def text_of(el) -> str:
    return "".join(el.xpath(".//w:t/text()", namespaces=NS)).strip()


def font_path() -> str:
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    return ""


FONT_PATH = font_path()


def font(size: int, bold: bool = False):
    if bold:
        bold_candidates = [r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\simhei.ttf"]
        for path in bold_candidates:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
    if FONT_PATH:
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()


def centered_text(draw, xy, text, fnt, fill="#111827"):
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=fnt)
    draw.text((x - (bbox[2] - bbox[0]) / 2, y - (bbox[3] - bbox[1]) / 2), text, font=fnt, fill=fill)


def rounded_box(draw, rect, title, subtitle="", fill="#ffffff", outline="#1f2937", width=8):
    draw.rounded_rectangle(rect, radius=30, fill=fill, outline=outline, width=width)
    x0, y0, x1, y1 = rect
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    if subtitle:
        centered_text(draw, (cx, cy - 34), title, font(68, True))
        centered_text(draw, (cx, cy + 42), subtitle, font(52))
    else:
        centered_text(draw, (cx, cy), title, font(58, True))


def arrow(draw, start, end, fill="#344054", width=10):
    draw.line([start, end], fill=fill, width=width)
    x1, y1 = start
    x2, y2 = end
    import math

    ang = math.atan2(y2 - y1, x2 - x1)
    head = 34
    spread = 0.45
    pts = [
        (x2, y2),
        (x2 - head * math.cos(ang - spread), y2 - head * math.sin(ang - spread)),
        (x2 - head * math.cos(ang + spread), y2 - head * math.sin(ang + spread)),
    ]
    draw.polygon(pts, fill=fill)


def arrow_label(draw, start, end, label, fill="#344054"):
    x = (start[0] + end[0]) / 2
    y = (start[1] + end[1]) / 2 - 36
    centered_text(draw, (x, y), label, font(34, True), fill=fill)


def draw_fig1(path: Path) -> None:
    img = Image.new("RGB", (4800, 1800), "white")
    draw = ImageDraw.Draw(img)
    colors = {
        "request": ("#eef4ff", "#2e5aac"),
        "tee": ("#ecfdf3", "#16803c"),
        "da": ("#fff7e6", "#b45309"),
        "commit": ("#f4f3ff", "#6941c6"),
        "verify": ("#fef3f2", "#b42318"),
    }

    modules = [
        (80, 230, 880, 650, "高频 DApp 请求", "High-frequency DApp", "request"),
        (1030, 230, 1850, 650, "链下执行层", "Simulated TEE", "tee"),
        (2010, 230, 2890, 650, "数据可用性层", "mock-verifiable DA", "da"),
        (3070, 230, 3860, 650, "链上提交层", "compact commit", "commit"),
        (4030, 230, 4720, 650, "验证仲裁层", "challenge / recover", "verify"),
    ]
    for x0, y0, x1, y1, title, subtitle, key in modules:
        fc, ec = colors[key]
        rounded_box(draw, (x0, y0, x1, y1), title, subtitle, fc, ec)

    links = [
        ((880, 440), (1020, 440), "request"),
        ((1850, 440), (2000, 440), "payload + proof"),
        ((2890, 440), (3060, 440), "DA root"),
        ((3860, 440), (4020, 440), "commit"),
    ]
    for s, e, label in links:
        arrow(draw, s, e)
        arrow_label(draw, s, e, label)

    rounded_box(draw, (1120, 1050, 2200, 1430), "正常路径", "low-latency response", "#f9fafb", "#667085", width=7)
    rounded_box(draw, (2820, 1050, 4240, 1430), "异常路径", "DA proof -> replay -> resolve", "#f9fafb", "#667085", width=7)
    arrow(draw, (1440, 660), (1620, 1030), "#16803c", width=10)
    arrow_label(draw, (1440, 660), (1620, 1030), "normal path", "#16803c")
    arrow(draw, (4380, 660), (3500, 1030), "#b42318", width=10)
    arrow_label(draw, (4380, 660), (3500, 1030), "fault path", "#b42318")
    arrow(draw, (3440, 1030), (2460, 660), "#b45309", width=10)
    arrow_label(draw, (3440, 1030), (2460, 660), "fetch evidence", "#b45309")

    centered_text(
        draw,
        (2400, 1660),
        "compact commit binds state root, output hash, proof hash, DA pointer, and DA root",
        font(46),
        fill="#475467",
    )
    img.save(path, dpi=(600, 600))


def draw_fig2(path: Path) -> None:
    img = Image.new("RGB", (4800, 1500), "white")
    draw = ImageDraw.Draw(img)
    states = [
        ("PENDING", 70, 230),
        ("OPEN", 730, 230),
        ("RESPONDED", 1390, 230),
        ("NARROWING", 2180, 230),
        ("READY", 3000, 230),
        ("REPLAYED", 3660, 230),
        ("RESOLVED", 4320, 230),
    ]
    w, h = 430, 270
    for name, x, y in states:
        rounded_box(draw, (x, y, x + w, y + h), name, "", "#eef4ff", "#2e5aac", width=8)
    for i in range(len(states) - 1):
        x1, y1 = states[i][1] + w, states[i][2] + h // 2
        x2, y2 = states[i + 1][1] - 10, states[i + 1][2] + h // 2
        arrow(draw, (x1, y1), (x2, y2), width=9)

    rounded_box(draw, (2180, 950, 2610, 1220), "TIMEOUT", "", "#fff7e6", "#b45309", width=8)
    rounded_box(draw, (3000, 950, 3430, 1220), "RECOVERED", "", "#ecfdf3", "#16803c", width=8)
    arrow(draw, (2395, 510), (2395, 930), "#b45309", width=9)
    arrow_label(draw, (2395, 510), (2395, 930), "timeout", "#b45309")
    arrow(draw, (2620, 1085), (2980, 1085), "#16803c", width=9)
    arrow_label(draw, (2620, 1085), (2980, 1085), "recover", "#16803c")
    arrow(draw, (3215, 930), (3215, 525), "#16803c", width=9)
    arrow_label(draw, (3215, 930), (3215, 525), "resume", "#16803c")
    centered_text(
        draw,
        (2400, 1390),
        "Recovery changes liveness state only; challenge facts and evidence remain unchanged.",
        font(46),
        fill="#475467",
    )
    img.save(path, dpi=(600, 600))


def next_rid(rels_root) -> str:
    max_id = 0
    for rel in rels_root:
        rid = rel.get("Id", "")
        if rid.startswith("rId") and rid[3:].isdigit():
            max_id = max(max_id, int(rid[3:]))
    return f"rId{max_id + 1}"


def add_image_relationship(rels_root, target_name: str) -> str:
    rid = next_rid(rels_root)
    rel = etree.SubElement(rels_root, "Relationship")
    rel.set("Id", rid)
    rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image")
    rel.set("Target", f"media/{target_name}")
    return rid


def set_table_width(tbl, width_dxa: int) -> None:
    tblpr = tbl.find("w:tblPr", NS)
    if tblpr is None:
        tblpr = etree.Element(qn("w:tblPr"))
        tbl.insert(0, tblpr)
    tblw = tblpr.find("w:tblW", NS)
    if tblw is None:
        tblw = etree.SubElement(tblpr, qn("w:tblW"))
    tblw.set(qn("w:type"), "dxa")
    tblw.set(qn("w:w"), str(width_dxa))
    jc = tblpr.find("w:jc", NS)
    if jc is None:
        jc = etree.SubElement(tblpr, qn("w:jc"))
    jc.set(qn("w:val"), "center")
    grid = tbl.find("w:tblGrid", NS)
    if grid is not None:
        tbl.remove(grid)
    grid = etree.Element(qn("w:tblGrid"))
    tbl.insert(1, grid)
    col = etree.SubElement(grid, qn("w:gridCol"))
    col.set(qn("w:w"), str(width_dxa))
    for tc in tbl.xpath(".//w:tc", namespaces=NS):
        tcpr = tc.find("w:tcPr", NS)
        if tcpr is None:
            tcpr = etree.Element(qn("w:tcPr"))
            tc.insert(0, tcpr)
        tcw = tcpr.find("w:tcW", NS)
        if tcw is None:
            tcw = etree.SubElement(tcpr, qn("w:tcW"))
        tcw.set(qn("w:type"), "dxa")
        tcw.set(qn("w:w"), str(width_dxa))
    for tr in tbl.findall("w:tr", NS):
        trpr = tr.find("w:trPr", NS)
        if trpr is not None:
            for h in trpr.findall("w:trHeight", NS):
                trpr.remove(h)


def set_drawing_image(tbl, rid: str, width_in: float, height_in: float) -> None:
    cx = int(width_in * EMU_PER_INCH)
    cy = int(height_in * EMU_PER_INCH)
    drawing = tbl.find(".//w:drawing", NS)
    if drawing is None:
        raise RuntimeError("Figure table does not contain a drawing.")
    for blip in drawing.xpath(".//a:blip", namespaces=NS):
        blip.set(qn("r:embed"), rid)
    for extent in drawing.xpath(".//wp:extent", namespaces=NS):
        extent.set("cx", str(cx))
        extent.set("cy", str(cy))
    for ext in drawing.xpath(".//a:xfrm/a:ext", namespaces=NS):
        ext.set("cx", str(cx))
        ext.set("cy", str(cy))
    for p in tbl.xpath(".//w:p", namespaces=NS):
        ppr = p.find("w:pPr", NS)
        if ppr is None:
            ppr = etree.Element(qn("w:pPr"))
            p.insert(0, ppr)
        spacing = ppr.find("w:spacing", NS)
        if spacing is None:
            spacing = etree.SubElement(ppr, qn("w:spacing"))
        spacing.set(qn("w:before"), "0")
        spacing.set(qn("w:after"), "0")
        spacing.set(qn("w:line"), "240")
        spacing.set(qn("w:lineRule"), "auto")
        jc = ppr.find("w:jc", NS)
        if jc is None:
            jc = etree.SubElement(ppr, qn("w:jc"))
        jc.set(qn("w:val"), "center")


def sect_para(cols: int) -> etree._Element:
    p = etree.Element(qn("w:p"))
    ppr = etree.SubElement(p, qn("w:pPr"))
    sect = etree.SubElement(ppr, qn("w:sectPr"))
    typ = etree.SubElement(sect, qn("w:type"))
    typ.set(qn("w:val"), "continuous")
    col = etree.SubElement(sect, qn("w:cols"))
    col.set(qn("w:num"), str(cols))
    if cols == 2:
        col.set(qn("w:space"), "420")
    return p


def find_figure_tables(body):
    found = {}
    for tbl in body.findall("w:tbl", NS):
        t = text_of(tbl)
        if "图 1" in t and "Hybrid TEE-Rollup 原型系统架构" in t:
            found[1] = tbl
        elif "图 2" in t and "可恢复挑战协议流程" in t:
            found[2] = tbl
    return found


def main() -> None:
    draft = Path(__file__).resolve().parent
    base = draft / "final_layout_fixed_only.docx"
    out = draft / "final_fig1_fig2_fixed.docx"
    assets = draft / "fig1_fig2_fixed_assets"
    assets.mkdir(exist_ok=True)

    fig1 = assets / "fig1_architecture_600dpi.png"
    fig2 = assets / "fig2_recoverable_flow_600dpi.png"
    draw_fig1(fig1)
    draw_fig2(fig2)

    shutil.copyfile(base, out)
    with zipfile.ZipFile(out, "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    root = etree.fromstring(files["word/document.xml"])
    rels_root = etree.fromstring(files["word/_rels/document.xml.rels"])
    body = root.find("w:body", NS)

    rid1 = add_image_relationship(rels_root, "fig1_architecture_600dpi.png")
    rid2 = add_image_relationship(rels_root, "fig2_recoverable_flow_600dpi.png")
    files["word/media/fig1_architecture_600dpi.png"] = fig1.read_bytes()
    files["word/media/fig2_recoverable_flow_600dpi.png"] = fig2.read_bytes()

    section = body.find("w:sectPr", NS)
    page_w = int(section.find("w:pgSz", NS).get(qn("w:w")))
    margin = section.find("w:pgMar", NS)
    usable_dxa = page_w - int(margin.get(qn("w:left"))) - int(margin.get(qn("w:right")))
    usable_in = usable_dxa / DXA_PER_INCH
    fig_width_in = usable_in * 0.96

    tables = find_figure_tables(body)
    if 1 not in tables or 2 not in tables:
        raise RuntimeError("Could not locate both Figure 1 and Figure 2 tables.")

    # Full-width figure tables. The image aspect ratios come from the generated figures.
    set_table_width(tables[1], int(usable_dxa * 0.96))
    set_drawing_image(tables[1], rid1, fig_width_in, fig_width_in * (1800 / 4800))
    set_table_width(tables[2], int(usable_dxa * 0.96))
    set_drawing_image(tables[2], rid2, fig_width_in, fig_width_in * (1500 / 4800))

    # Add continuous section switches only around Figure 1 and Figure 2:
    # previous section = two columns, figure section = one column, following text = two columns.
    for fig_no in (2, 1):
        tbl = tables[fig_no]
        idx = body.index(tbl)
        body.insert(idx, sect_para(2))
        body.insert(idx + 2, sect_para(1))

    files["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes")
    files["word/_rels/document.xml.rels"] = etree.tostring(rels_root, xml_declaration=True, encoding="UTF-8", standalone="yes")

    settings = etree.fromstring(files["word/settings.xml"])
    if settings.find("w:doNotAutoCompressPictures", NS) is None:
        settings.append(etree.Element(qn("w:doNotAutoCompressPictures")))
    default_dpi = settings.find("w14:defaultImageDpi", NS)
    if default_dpi is None:
        default_dpi = etree.Element(qn("w14:defaultImageDpi"))
        settings.append(default_dpi)
    default_dpi.set(qn("w14:val"), "300")
    files["word/settings.xml"] = etree.tostring(settings, xml_declaration=True, encoding="UTF-8", standalone="yes")

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)


if __name__ == "__main__":
    main()
