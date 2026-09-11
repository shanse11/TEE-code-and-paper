from pathlib import Path
from docx import Document

doc = Document(str(Path(__file__).with_name("final_layout_fixed_only.docx")))
for i, p in enumerate(doc.paragraphs, 1):
    t = p.text.strip()
    if "表 " in t or "图 " in t or "表" in t and "所示" in t:
        print(i, t[:180])
