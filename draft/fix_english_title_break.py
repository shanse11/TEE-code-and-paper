from pathlib import Path
import zipfile
from lxml import etree

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def qn(name):
    prefix, local = name.split(":")
    return f"{{{NS[prefix]}}}{local}"


def text_of(el):
    return "".join(el.xpath(".//w:t/text()", namespaces=NS)).strip()


docx = Path(__file__).with_name("Hybrid_TEE_Rollup_导师意见修订版.docx")
with zipfile.ZipFile(docx, "r") as zin:
    files = {name: zin.read(name) for name in zin.namelist()}

root = etree.fromstring(files["word/document.xml"])
target = "Recoverable Challenge Protocol and Lightweight DA Cost Evaluation for Hybrid TEE-Rollup in High-Frequency DApps"
for p in root.xpath("//w:p", namespaces=NS):
    if text_of(p) == target:
        ppr = p.find("w:pPr", NS)
        rpr = p.find("w:r/w:rPr", NS)
        for child in list(p):
            if child is not ppr:
                p.remove(child)
        r = etree.SubElement(p, qn("w:r"))
        if rpr is not None:
            r.append(etree.fromstring(etree.tostring(rpr)))
        t1 = etree.SubElement(r, qn("w:t"))
        t1.set(XML_SPACE, "preserve")
        t1.text = "Recoverable Challenge Protocol and Lightweight DA Cost Evaluation for"
        etree.SubElement(r, qn("w:br"))
        t2 = etree.SubElement(r, qn("w:t"))
        t2.set(XML_SPACE, "preserve")
        t2.text = "Hybrid TEE-Rollup in High-Frequency DApps"
        break

files["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes")
with zipfile.ZipFile(docx, "w", zipfile.ZIP_DEFLATED) as zout:
    for name, data in files.items():
        zout.writestr(name, data)
