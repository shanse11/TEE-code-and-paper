"""Build a submission-layout copy from the current manuscript and Joca template."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from shutil import copy2
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree

ROOT = Path("/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup")
SOURCE = ROOT / "outputs" / "Hybrid_TEE_Rollup_计算机应用投稿版.docx"
TEMPLATE = Path("/private/tmp/tee_template_review/投稿模版.docx")
OUTPUT = ROOT / "outputs" / "template_alignment" / "Hybrid_TEE_Rollup_计算机应用_模板对齐稿.docx"

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = "{" + NS["w"] + "}"


def name_of(style):
    node = style.find("w:name", NS)
    return node.get(W + "val") if node is not None else None


def style_map(root):
    return {name_of(s): s for s in root.findall("w:style", NS) if name_of(s)}


def replace_child(parent, tag, replacement):
    old = parent.find(tag, NS)
    if old is not None:
        parent.remove(old)
    if replacement is not None:
        parent.append(deepcopy(replacement))


def patch_styles(source_files, template_files):
    source = etree.fromstring(source_files["word/styles.xml"])
    template = etree.fromstring(template_files["word/styles.xml"])
    src_by_name, tpl_by_name = style_map(source), style_map(template)
    # The template uses Word's built-in Heading and Normal styles for its
    # title/body slots, while the current manuscript calls those slots 文题/正文.
    role_map = {
        "文题": "Heading", "作者名": "作者名", "单位": "单位",
        "摘要关键词": "固定", "一级标题": "一级标题", "二级标题": "二级标题",
        "三级标题": "三级标题", "正文": "Normal", "图表名称": "图表名称",
        "文献列表": "文献列表",
    }
    for role, template_role in role_map.items():
        src, tpl = src_by_name.get(role), tpl_by_name.get(template_role)
        if src is None or tpl is None:
            raise RuntimeError(f"Missing required style: {role} / {template_role}")
        # Keep target style IDs, but inherit the template's actual typography.
        for tag in ("w:pPr", "w:rPr"):
            item = tpl.find(tag, NS)
            if tag == "w:pPr" and item is not None:
                item = deepcopy(item)
                # Current headings retain visible manually written numbering.
                # Copying template numPr would render a duplicate number.
                num = item.find("w:numPr", NS)
                if num is not None:
                    item.remove(num)
            replace_child(src, tag, item)
    source_files["word/styles.xml"] = etree.tostring(source, encoding="UTF-8", xml_declaration=True, standalone=True)


def clear_direct_text_formatting(root, style_ids):
    role_ids = set(style_ids.values())
    clear_tags = {W + x for x in ("rFonts", "sz", "szCs", "b", "bCs", "i", "iCs", "color")}
    for p in root.findall(".//w:p", NS):
        pstyle = p.find("w:pPr/w:pStyle", NS)
        if pstyle is None or pstyle.get(W + "val") not in role_ids:
            continue
        ppr = p.find("w:pPr", NS)
        if ppr is not None:
            # The old generated manuscript placed its own line spacing,
            # indentation and alignment directly on almost every paragraph.
            # Retain only the style reference and any section break, so the
            # template's paragraph properties take effect.
            for child in list(ppr):
                if child.tag in {W + x for x in ("spacing", "ind", "jc", "tabs", "keepNext", "keepLines", "widowControl")}:
                    ppr.remove(child)
        # Formula paragraphs use OMML and normal style, so this only affects
        # ordinary text that was overriding the named template style.
        for rpr in p.findall("w:r/w:rPr", NS):
            for child in list(rpr):
                if child.tag in clear_tags:
                    rpr.remove(child)


def make_sect(base, columns, left, right):
    section = deepcopy(base)
    mar = section.find("w:pgMar", NS)
    mar.set(W + "left", str(left))
    mar.set(W + "right", str(right))
    cols = section.find("w:cols", NS)
    if cols is None:
        cols = etree.SubElement(section, W + "cols")
    cols.set(W + "num", str(columns))
    cols.set(W + "space", "448")
    typ = section.find("w:type", NS)
    if typ is None:
        typ = etree.SubElement(section, W + "type")
    typ.set(W + "val", "continuous")
    return section


def put_section_on(paragraph, section):
    ppr = paragraph.find("w:pPr", NS)
    if ppr is None:
        ppr = etree.Element(W + "pPr")
        paragraph.insert(0, ppr)
    old = ppr.find("w:sectPr", NS)
    if old is not None:
        ppr.remove(old)
    ppr.append(section)


def apply_section_layout(root):
    body = root.find("w:body", NS)
    final = body.find("w:sectPr", NS)
    if final is None:
        raise RuntimeError("Document has no final section properties")
    paragraphs = body.findall("w:p", NS)
    text = ["".join(p.xpath(".//w:t/text()", namespaces=NS)).strip() for p in paragraphs]
    intro = text.index("0  引言")
    # Exact template geometry: front matter is one column; the body is two.
    front = make_sect(final, 1, 1191, 907)
    put_section_on(paragraphs[intro - 1], front)
    body.remove(final)
    body.append(make_sect(final, 2, 1902, 1334))

    # Figures and tables are full-width template sections; resume two columns
    # immediately after each visual block.
    visual_starts = [i for i, p in enumerate(paragraphs) if p.xpath(".//w:drawing", namespaces=NS)]
    for start in visual_starts:
        if start == 0:
            continue
        put_section_on(paragraphs[start - 1], make_sect(final, 2, 1902, 1334))
        end = min(start + 2, len(paragraphs) - 1)  # image + Chinese/English captions
        put_section_on(paragraphs[end], make_sect(final, 1, 1191, 907))

    # Tables sit between their bilingual caption paragraphs and the next prose
    # paragraph. Work from body-child order, not Document.paragraphs indexes,
    # so a continuous section contains both caption and table.
    children = list(body)
    for i, child in enumerate(children):
        if child.tag != W + "p":
            continue
        value = "".join(child.xpath(".//w:t/text()", namespaces=NS)).strip()
        if not (value.startswith("表 1 ") or value.startswith("表 2 ")):
            continue
        table_at = next((j for j in range(i + 1, len(children)) if children[j].tag == W + "tbl"), None)
        if table_at is None:
            continue
        previous_p = next((children[j] for j in range(i - 1, -1, -1) if children[j].tag == W + "p"), None)
        next_p = next((children[j] for j in range(table_at + 1, len(children)) if children[j].tag == W + "p"), None)
        if previous_p is not None:
            put_section_on(previous_p, make_sect(final, 2, 1902, 1334))
        if next_p is not None:
            put_section_on(next_p, make_sect(final, 1, 1191, 907))


def main():
    if not SOURCE.is_file() or not TEMPLATE.is_file():
        raise RuntimeError("Source manuscript or converted template is missing")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    copy2(SOURCE, OUTPUT)
    with ZipFile(OUTPUT, "r") as zin, ZipFile(TEMPLATE, "r") as tin:
        files = {item.filename: zin.read(item.filename) for item in zin.infolist()}
        template_files = {item.filename: tin.read(item.filename) for item in tin.infolist()}
    patch_styles(files, template_files)
    root = etree.fromstring(files["word/document.xml"])
    style_root = etree.fromstring(files["word/styles.xml"])
    ids = {name_of(s): s.get(W + "styleId") for s in style_root.findall("w:style", NS) if name_of(s)}
    clear_direct_text_formatting(root, ids)
    apply_section_layout(root)
    files["word/document.xml"] = etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone=True)
    tmp = OUTPUT.with_suffix(".tmp.docx")
    with ZipFile(tmp, "w", ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    tmp.replace(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
