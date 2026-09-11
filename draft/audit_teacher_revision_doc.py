from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from lxml import etree

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def text_of(el):
    return "".join(el.xpath(".//w:t/text()", namespaces=NS)).strip()


def main(path: str):
    with zipfile.ZipFile(path) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    body = root.find("w:body", NS)
    print("SECTIONS")
    for i, sect in enumerate(root.xpath("//w:sectPr", namespaces=NS), 1):
        cols = sect.find("w:cols", NS)
        num = cols.get(f"{{{NS['w']}}}num") if cols is not None else None
        typ = sect.find("w:type", NS)
        print(i, "cols", num or "1/default", "type", typ.get(f"{{{NS['w']}}}val") if typ is not None else "default")

    print("\nFIRST 35 PARAS")
    pno = 0
    for child in body:
        if child.tag == f"{{{NS['w']}}}p":
            pno += 1
            t = text_of(child)
            if t or child.find("w:pPr/w:sectPr", NS) is not None:
                print(f"P{pno:03d}", "SECT" if child.find("w:pPr/w:sectPr", NS) is not None else "", t[:180])
            if pno >= 35:
                break
        elif child.tag == f"{{{NS['w']}}}tbl":
            pno += 1
            print(f"T{pno:03d}", text_of(child)[:180])

    print("\nHEADINGS")
    for i, p in enumerate(root.xpath("//w:p", namespaces=NS), 1):
        t = text_of(p)
        if re.match(r"^\d+(?:\.\d+)*\s", t) or t in {"参考文献"}:
            print(i, t[:200])

    print("\nREFERENCES")
    for i, p in enumerate(root.xpath("//w:p", namespaces=NS), 1):
        t = text_of(p)
        if re.match(r"^\[\d+\]", t):
            print(i, t[:220])

    print("\nCITATION PARAS")
    for i, p in enumerate(root.xpath("//w:p", namespaces=NS), 1):
        t = text_of(p)
        if re.search(r"\[\d+\]", t) and not re.match(r"^\[\d+\]", t):
            print(i, re.findall(r"\[(\d+)\]", t), t[:220])


if __name__ == "__main__":
    main(sys.argv[1])
