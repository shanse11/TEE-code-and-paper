#!/usr/bin/env python3
"""Replace the final Chinese contact block with the template-style English author bio."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree


SOURCE = Path(
    "/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup/outputs/"
    "submission_format_20260916_153212_borderless/"
    "Hybrid_TEE_Rollup_计算机应用_投稿待确认版_无页面边框.docx"
)
OUTPUT = Path(
    "/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup/outputs/"
    "submission_format_20260916_163153_english_bio/"
    "Hybrid_TEE_Rollup_计算机应用_投稿待确认版_英文作者简介.docx"
)
AUDIT = OUTPUT.parent / "qa" / "author_bio_edit_audit.json"

CONTACT_LINES = [
    "联系人：杨帆",
    "通信地址：上海市普陀区中山北路3663号华东师范大学数据科学与工程学院，200062",
    "电子信箱：2991777340@qq.com",
    "电话：13319693336",
]
NAME = "YANG Fan"
BIO_REMAINDER = (
    ", born in 2003, M. S. candidate. His research interests include "
    "blockchain systems and interoperability, TEE-based privacy computing, "
    "Layer 2/Rollup scaling and security, and decentralized finance and "
    "transaction fairness."
)
BIO = NAME + BIO_REMAINDER

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def qn(local: str) -> str:
    return f"{{{W_NS}}}{local}"


def paragraph_text(p: etree._Element) -> str:
    return "".join(p.xpath(".//w:t/text()", namespaces=NS))


def make_rpr(*, bold: bool = False) -> etree._Element:
    rpr = etree.Element(qn("rPr"))
    if bold:
        etree.SubElement(rpr, qn("b"))
    etree.SubElement(rpr, qn("sz")).set(qn("val"), "18")
    etree.SubElement(rpr, qn("szCs")).set(qn("val"), "18")
    return rpr


def add_run(p: etree._Element, text: str, *, bold: bool = False) -> None:
    run = etree.SubElement(p, qn("r"))
    run.append(make_rpr(bold=bold))
    t = etree.SubElement(run, qn("t"))
    t.text = text


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    with ZipFile(SOURCE, "r") as zin:
        infos = zin.infolist()
        package = {info.filename: zin.read(info.filename) for info in infos}

    original_document = package["word/document.xml"]
    root = etree.fromstring(original_document)
    original_body_texts = [paragraph_text(p) for p in root.xpath("//w:body/w:p", namespaces=NS)]
    original_sectprs = [
        etree.tostring(node)
        for node in root.xpath("//w:sectPr", namespaces=NS)
    ]
    body = root.find("w:body", NS)
    if body is None:
        raise RuntimeError("word/document.xml has no w:body")

    children = list(body)
    positions = []
    for line in CONTACT_LINES:
        matches = [i for i, child in enumerate(children) if child.tag == qn("p") and paragraph_text(child) == line]
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly one paragraph for {line!r}; found {matches}")
        positions.append(matches[0])
    if positions != list(range(positions[0], positions[0] + len(CONTACT_LINES))):
        raise RuntimeError(f"Contact paragraphs are not consecutive: {positions}")

    last_contact = children[positions[-1]]
    final_sectpr = last_contact.find("w:pPr/w:sectPr", NS)
    if final_sectpr is None:
        raise RuntimeError("Final contact paragraph does not contain the expected two-column section properties")
    for child in list(last_contact):
        if child.tag != qn("pPr"):
            last_contact.remove(child)

    ppr = last_contact.find("w:pPr", NS)
    if ppr is None:
        raise RuntimeError("Final contact paragraph is missing w:pPr")
    pstyle = etree.Element(qn("pStyle"))
    pstyle.set(qn("val"), "88")
    ppr.insert(0, pstyle)
    ppr_rpr = etree.Element(qn("rPr"))
    etree.SubElement(ppr_rpr, qn("sz")).set(qn("val"), "18")
    etree.SubElement(ppr_rpr, qn("szCs")).set(qn("val"), "18")
    ppr.insert(1, ppr_rpr)
    add_run(last_contact, NAME, bold=True)
    add_run(last_contact, BIO_REMAINDER)

    for idx in reversed(positions[:-1]):
        body.remove(children[idx])

    package["word/document.xml"] = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone="yes"
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as zout:
        for info in infos:
            zout.writestr(info, package[info.filename])

    with ZipFile(OUTPUT, "r") as z:
        out_package = {name: z.read(name) for name in z.namelist()}
    out_root = etree.fromstring(out_package["word/document.xml"])
    out_texts = [paragraph_text(p) for p in out_root.xpath("//w:body/w:p", namespaces=NS)]
    expected_texts = [
        BIO if text == CONTACT_LINES[-1] else text
        for text in original_body_texts
        if text not in CONTACT_LINES[:-1]
    ]
    out_sectprs = [
        etree.tostring(node)
        for node in out_root.xpath("//w:sectPr", namespaces=NS)
    ]
    non_document_differences = [
        name
        for name, data in package.items()
        if name != "word/document.xml" and out_package.get(name) != data
    ]

    audit = {
        "source": str(SOURCE),
        "output": str(OUTPUT),
        "source_sha256": sha256(SOURCE.read_bytes()),
        "output_sha256": sha256(OUTPUT.read_bytes()),
        "english_bio": BIO,
        "english_bio_count": out_texts.count(BIO),
        "remaining_contact_lines": [line for line in CONTACT_LINES if line in out_texts],
        "body_paragraph_sequence_exact_except_author_block": out_texts == expected_texts,
        "section_properties_identical": out_sectprs == original_sectprs,
        "non_document_parts_identical": not non_document_differences,
        "non_document_differences": non_document_differences,
        "page_border_count": len(out_root.xpath("//w:sectPr/w:pgBorders", namespaces=NS)),
    }
    audit["pass"] = (
        audit["english_bio_count"] == 1
        and not audit["remaining_contact_lines"]
        and audit["body_paragraph_sequence_exact_except_author_block"]
        and audit["section_properties_identical"]
        and audit["non_document_parts_identical"]
        and audit["page_border_count"] == 0
    )
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not audit["pass"]:
        raise RuntimeError(json.dumps(audit, ensure_ascii=False, indent=2))
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
