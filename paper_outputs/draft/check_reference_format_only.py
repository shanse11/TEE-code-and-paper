from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

BASE = Path(__file__).resolve().parent
import sys

DOCX = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "Hybrid_TEE_Rollup_参考文献格式修订版.docx"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = NS["w"]


def qn(tag: str) -> str:
    return f"{{{W}}}{tag}"


def text_of(p: ET.Element) -> str:
    return "".join(t.text or "" for t in p.findall(".//w:t", NS))


def main() -> None:
    with zipfile.ZipFile(DOCX, "r") as zf:
        names = zf.namelist()
        print("zip_bad", zf.testzip())
        print("duplicate_parts", sorted(n for n in set(names) if names.count(n) > 1))
        root = ET.fromstring(zf.read("word/document.xml"))
        raw_xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
    paras = root.findall(".//w:body/w:p", NS)
    ref_idx = next(i for i, p in enumerate(paras) if text_of(p).strip() == "参考文献：")
    ref_numbers = []
    for p in paras[ref_idx + 1 :]:
        m = re.match(r"^\[(\d+)\]", text_of(p).strip())
        if m:
            ref_numbers.append(int(m.group(1)))
    bad_runs = []
    body_cites = []
    forbidden = []
    for i, p in enumerate(paras[:ref_idx], 1):
        txt = text_of(p)
        if not re.search(r"\[\d+\]", txt):
            continue
        body_cites.extend(int(x) for x in re.findall(r"\[(\d+)\]", txt))
        stripped = txt.strip()
        if re.match(r"^(摘|关键词|Abstract|Key words|图\s*\d+|Fig\.\d+|表\s*\d+|Table\s*\d+|\d+(\.\d+)*\s)", stripped):
            forbidden.append((i, stripped[:80]))
        for r in p.findall("w:r", NS):
            rtxt = text_of(r)
            if re.fullmatch(r"\[\d+\]", rtxt or ""):
                va = r.find("w:rPr/w:vertAlign", NS)
                if va is None or va.get(qn("val")) != "superscript":
                    bad_runs.append((i, rtxt))
    print("ref_heading", text_of(paras[ref_idx]).strip())
    print("ref_numbers", ref_numbers)
    print("body_citations", body_cites)
    print("bad_superscript_runs", bad_runs)
    print("forbidden_citation_locations", forbidden)
    print("missing_refs", sorted(set(body_cites) - set(ref_numbers)))
    print("unreferenced_refs", sorted(set(ref_numbers) - set(body_cites)))
    print("has_abnormal_soft_hyphen", "\u00ad" in raw_xml or "\ufffe" in raw_xml)


if __name__ == "__main__":
    main()
