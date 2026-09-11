from lxml import etree
from pathlib import Path
import zipfile
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def text(el): return ''.join(el.xpath('.//w:t/text()',namespaces=NS)).strip()
p=Path('E:/项目/project_code/paper_outputs/draft/final_layout_fixed_only.docx')
root=etree.fromstring(zipfile.ZipFile(p).read('word/document.xml'))
body=root.find('w:body',NS)
no=0
for child in body:
 no+=1
 if 130<=no<=180:
  tag='T' if child.tag.endswith('tbl') else 'P'
  sect=' sect' if tag=='P' and child.find('w:pPr/w:sectPr',NS) is not None else ''
  print(f'{tag}{no:03d}{sect}: {text(child)[:180]}')
