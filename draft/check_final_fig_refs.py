from pathlib import Path
from docx import Document
p=Path(__file__).with_name('final_fig1_fig2_fixed.docx')
d=Document(str(p))
for i,para in enumerate(d.paragraphs,1):
 t=para.text.strip()
 if '图 1' in t or '图 2' in t or '表 6' in t:
  print(i,t)
