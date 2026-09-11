from docx import Document
from pathlib import Path
p=Path('E:/项目/project_code/paper_outputs/draft/final_layout_fixed_only.docx')
d=Document(str(p))
for i,t in enumerate(d.tables,1):
 print('\nTABLE',i, len(t.rows), len(t.columns))
 for r in t.rows:
  print(' | '.join(c.text.replace('\n',' / ') for c in r.cells))
