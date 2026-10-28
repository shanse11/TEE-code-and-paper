#!/usr/bin/env python3

import hashlib
import json
import sys
import zipfile
from pathlib import Path

from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_document(data: bytes, remove_page_borders: bool) -> bytes:
    root = etree.fromstring(data)
    if remove_page_borders:
        for border in root.xpath("//w:sectPr/w:pgBorders", namespaces=NS):
            border.getparent().remove(border)
    return etree.tostring(root, method="c14n")


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: verify_borderless.py ORIGINAL.docx BORDERLESS.docx OUT.json")

    original = Path(sys.argv[1]).resolve()
    borderless = Path(sys.argv[2]).resolve()
    output = Path(sys.argv[3]).resolve()

    with zipfile.ZipFile(original) as old_zip, zipfile.ZipFile(borderless) as new_zip:
        old_names = set(old_zip.namelist())
        new_names = set(new_zip.namelist())
        old_doc = old_zip.read("word/document.xml")
        new_doc = new_zip.read("word/document.xml")
        old_root = etree.fromstring(old_doc)
        new_root = etree.fromstring(new_doc)

        old_borders = len(old_root.xpath("//w:sectPr/w:pgBorders", namespaces=NS))
        new_borders = len(new_root.xpath("//w:sectPr/w:pgBorders", namespaces=NS))
        old_text = old_root.xpath("//w:t/text()", namespaces=NS)
        new_text = new_root.xpath("//w:t/text()", namespaces=NS)

        non_document_differences = []
        for name in sorted(old_names | new_names):
            if name == "word/document.xml":
                continue
            if name not in old_names or name not in new_names:
                non_document_differences.append(name)
                continue
            if digest(old_zip.read(name)) != digest(new_zip.read(name)):
                non_document_differences.append(name)

        result = {
            "original": str(original),
            "borderless": str(borderless),
            "package_entry_names_equal": old_names == new_names,
            "non_document_parts_identical": not non_document_differences,
            "non_document_differences": non_document_differences,
            "document_equal_after_removing_original_page_borders": (
                canonical_document(old_doc, True) == canonical_document(new_doc, False)
            ),
            "visible_text_exact": old_text == new_text,
            "original_page_border_count": old_borders,
            "borderless_page_border_count": new_borders,
            "pass": (
                old_names == new_names
                and not non_document_differences
                and canonical_document(old_doc, True) == canonical_document(new_doc, False)
                and old_text == new_text
                and old_borders > 0
                and new_borders == 0
            ),
        }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
