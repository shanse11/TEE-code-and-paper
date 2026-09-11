from zipfile import ZipFile
from lxml import etree
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
root=etree.fromstring(ZipFile(r'E:\项目\project_code\paper_outputs\draft\final_layout_fixed_only.docx').read('word/document.xml'))
tbl=root.xpath('//w:tbl',namespaces=NS)[1]
print(etree.tostring(tbl.xpath('.//w:r',namespaces=NS)[0],encoding='unicode'))
print(etree.tostring(tbl.xpath('.//w:tcPr',namespaces=NS)[0],encoding='unicode')[:1000])
