from pathlib import Path
from zipfile import ZipFile
from lxml import etree

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}

docx = Path(__file__).with_name("final_fig1_fig2_fixed.docx")
root = etree.fromstring(ZipFile(docx).read("word/document.xml"))
for i, drawing in enumerate(root.xpath("//w:drawing", namespaces=NS), 1):
    print("drawing", i, "srcRect", len(drawing.xpath(".//a:srcRect", namespaces=NS)))
    for sr in drawing.xpath(".//a:srcRect", namespaces=NS):
        print(etree.tostring(sr, encoding="unicode"))
