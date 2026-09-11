from __future__ import annotations

import re
import zipfile
from pathlib import Path

P = Path(__file__).resolve().parent / "Hybrid_TEE_Rollup_参考文献排版修订版.docx"

with zipfile.ZipFile(P) as z:
    xml = z.read("word/document.xml").decode("utf-8", errors="replace")

plain = re.sub(r"<[^>]+>", "", xml)
checks = [
    "https://",
    "http://",
    "www.",
    "\u00ad",
    "\ufffe",
    "technical-docu",
    "transac-tions",
    "efficient-Rollup",
    "smart-contracts",
    "Software-Guard",
]
for token in checks:
    print(repr(token), token in plain)

ref_start = plain.find("参考文献：")
tail = plain[ref_start:]
print("reference_section_has_url", bool(re.search(r"https?://|www\\.", tail)))
print("reference_count", len(re.findall(r"\[\d+\]", tail)))
