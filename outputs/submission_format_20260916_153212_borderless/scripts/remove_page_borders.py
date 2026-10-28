#!/usr/bin/env python3

import hashlib
import json
import sys
import zipfile
from pathlib import Path

from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: remove_page_borders.py INPUT.docx OUTPUT.docx AUDIT.json")

    source = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    audit_path = Path(sys.argv[3]).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source, "r") as src:
        document_xml = src.read("word/document.xml")
        root = etree.fromstring(document_xml)
        page_borders = root.xpath("//w:sectPr/w:pgBorders", namespaces=NS)
        removed_count = len(page_borders)
        for border in page_borders:
            border.getparent().remove(border)
        modified_xml = etree.tostring(
            root,
            xml_declaration=True,
            encoding="UTF-8",
            standalone="yes",
        )

        with zipfile.ZipFile(output, "w") as dst:
            for info in src.infolist():
                payload = modified_xml if info.filename == "word/document.xml" else src.read(info.filename)
                dst.writestr(info, payload)

    with zipfile.ZipFile(output, "r") as check:
        check_root = etree.fromstring(check.read("word/document.xml"))
        remaining = check_root.xpath("//w:sectPr/w:pgBorders", namespaces=NS)

    audit = {
        "source": str(source),
        "output": str(output),
        "source_sha256": sha256(source),
        "output_sha256": sha256(output),
        "page_borders_removed": removed_count,
        "page_borders_remaining": len(remaining),
        "scope": "word/document.xml section page borders only; table and paragraph borders unchanged",
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
