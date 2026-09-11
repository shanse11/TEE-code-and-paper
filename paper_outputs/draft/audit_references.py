from __future__ import annotations

import re
from pathlib import Path
from docx import Document


DOCX = Path(__file__).with_name("final_layout_fixed_only.docx")
doc = Document(str(DOCX))

paras = [p.text.strip() for p in doc.paragraphs]
try:
    ref_start = next(i for i, t in enumerate(paras) if t == "参考文献")
except StopIteration:
    raise SystemExit("No reference heading found")

print("REFERENCE LIST")
for i, t in enumerate(paras[ref_start + 1 :], ref_start + 2):
    if re.match(r"^\[\d+\]", t):
        print(f"P{i}: {t}")

print("\nCITATIONS BEFORE REFERENCES")
pat = re.compile(r"\[(\d+(?:\]\[\d+)*)\]")
for i, t in enumerate(paras[:ref_start], 1):
    cites = re.findall(r"\[(\d+)\]", t)
    if cites:
        print(f"P{i}: {','.join(cites)} :: {t[:220]}")
