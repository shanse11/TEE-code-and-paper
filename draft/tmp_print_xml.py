from pathlib import Path
from zipfile import ZipFile
from lxml import etree
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def text(el): return ''.join(el.xpath('.//w:t/text()',namespaces=NS)).strip()
root=etree.fromstring(ZipFile(Path('E:/项目/project_code/paper_outputs/draft/Hybrid_TEE_Rollup修改版.docx')).read('word/document.xml'))
for i,p in enumerate(root.xpath('//w:p',namespaces=NS),1):
 t=text(p)
 if 180 <= i <= 210 or t.startswith('6'):
  print(i,t)
