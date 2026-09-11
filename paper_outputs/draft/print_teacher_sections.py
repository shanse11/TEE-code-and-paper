from pathlib import Path
from docx import Document

doc = Document(str(Path(__file__).with_name("Hybrid_TEE_Rollup修改版.docx")))
for i, para in enumerate(doc.paragraphs, 1):
    t = para.text.strip()
    if 185 <= i <= 209:
        print(i, t)
