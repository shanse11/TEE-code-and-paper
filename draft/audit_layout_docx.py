from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from lxml import etree

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
}


def text_of(el):
    return "".join(el.xpath(".//w:t/text()", namespaces=NS)).strip()


def main(path: str) -> None:
    docx = Path(path)
    with zipfile.ZipFile(docx) as zf:
        xml = zf.read("word/document.xml")
    root = etree.fromstring(xml)
    body = root.find("w:body", NS)
    paras = body.findall("w:p", NS)
    tables = body.findall("w:tbl", NS)

    print(f"paragraphs={len(paras)} tables={len(tables)}")
    print("sections:")
    sects = root.xpath("//w:sectPr", namespaces=NS)
    for i, sect in enumerate(sects, 1):
        cols = sect.find("w:cols", NS)
        num = cols.get(f"{{{NS['w']}}}num") if cols is not None else None
        sep = cols.get(f"{{{NS['w']}}}sep") if cols is not None else None
        typ = sect.find("w:type", NS)
        print(f"  {i}: cols={num or '1/default'} sep={sep} type={typ.get(f'{{{NS['w']}}}val') if typ is not None else 'default'}")

    print("first 80 blocks:")
    block_no = 0
    for child in body:
        if child.tag == f"{{{NS['w']}}}p":
            block_no += 1
            t = text_of(child)
            if t or child.xpath(".//w:drawing", namespaces=NS) or child.find("w:pPr/w:sectPr", NS) is not None:
                sect = " sectPr" if child.find("w:pPr/w:sectPr", NS) is not None else ""
                drawings = len(child.xpath(".//w:drawing", namespaces=NS))
                brs = child.xpath(".//w:br", namespaces=NS)
                breaks = ",".join([b.get(f"{{{NS['w']}}}type", "line") for b in brs])
                print(f"  P{block_no:03d}{sect} draw={drawings} br={breaks}: {t[:110]}")
        elif child.tag == f"{{{NS['w']}}}tbl":
            block_no += 1
            rows = child.findall("w:tr", NS)
            row_text = text_of(rows[0]) if rows else ""
            tblw = child.find("w:tblPr/w:tblW", NS)
            w = tblw.get(f"{{{NS['w']}}}w") if tblw is not None else ""
            typ = tblw.get(f"{{{NS['w']}}}type") if tblw is not None else ""
            print(f"  T{block_no:03d} rows={len(rows)} w={w} type={typ}: {row_text[:110]}")
        if block_no >= 80:
            break

    print("drawings:")
    for i, drawing in enumerate(root.xpath("//w:drawing", namespaces=NS), 1):
        inline = drawing.find("wp:inline", NS)
        anchor = drawing.find("wp:anchor", NS)
        kind = "inline" if inline is not None else "anchor" if anchor is not None else "unknown"
        obj = inline if inline is not None else anchor
        extent = obj.find("wp:extent", NS) if obj is not None else None
        cx = int(extent.get("cx")) if extent is not None else 0
        cy = int(extent.get("cy")) if extent is not None else 0
        prev_p = drawing.getparent()
        while prev_p is not None and prev_p.tag != f"{{{NS['w']}}}p":
            prev_p = prev_p.getparent()
        print(f"  fig{i}: {kind} {cx/914400:.2f}x{cy/914400:.2f} in near='{text_of(prev_p)[:80] if prev_p is not None else ''}'")


if __name__ == "__main__":
    main(sys.argv[1])
