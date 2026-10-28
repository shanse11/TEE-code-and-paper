"""Create a manuscript by inserting the current paper into a copied Joca template."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from shutil import copy2
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree

ROOT = Path("/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup")
SOURCE = ROOT / "outputs" / "Hybrid_TEE_Rollup_计算机应用投稿版.docx"
TEMPLATE = Path("/private/tmp/tee_template_review/投稿模版.docx")
OUTPUT = ROOT / "outputs" / "template_alignment" / "Hybrid_TEE_Rollup_计算机应用_模板原文粘贴版.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W_NS, "r": R_NS}
W, R = "{" + W_NS + "}", "{" + R_NS + "}"


def text_of(node):
    return "".join(node.xpath(".//w:t/text()", namespaces=NS)).strip()


def styles_by_name(root):
    result = {}
    for style in root.findall("w:style", NS):
        name = style.find("w:name", NS)
        if name is not None:
            result[name.get(W + "val")] = style.get(W + "styleId")
    return result


def target_style(source_style, value, target):
    if source_style == "文题":
        return target["Heading"]
    if source_style == "作者名":
        return target["作者名"]
    if source_style == "单位":
        return target["单位"]
    if source_style == "摘要关键词":
        if value.startswith("摘  要"):
            return target["固定"]
        if value.startswith("关键词"):
            return target["固定2"]
        if value.startswith("中图分类号"):
            return target["固定3"]
        if value.startswith("Abstract"):
            return target["固定4"]
        if value.startswith("Key words"):
            return target["固定5"]
        return target["文献列表"]
    if source_style in {"一级标题", "二级标题", "三级标题", "图表名称", "文献列表"}:
        return target[source_style]
    return target["Normal"]


def clear_source_overrides(paragraph, is_formula=False, is_figure=False):
    ppr = paragraph.find("w:pPr", NS)
    if ppr is not None and not is_formula and not is_figure:
        for child in list(ppr):
            if child.tag in {W + x for x in ("spacing", "ind", "jc", "tabs", "keepNext", "keepLines", "widowControl")}:
                ppr.remove(child)
    if is_formula:
        return
    clear = {W + x for x in ("rFonts", "sz", "szCs", "b", "bCs", "i", "iCs", "color")}
    for rpr in paragraph.findall("w:r/w:rPr", NS):
        for child in list(rpr):
            if child.tag in clear:
                rpr.remove(child)


def set_pstyle(paragraph, style_id):
    ppr = paragraph.find("w:pPr", NS)
    if ppr is None:
        ppr = etree.Element(W + "pPr")
        paragraph.insert(0, ppr)
    pstyle = ppr.find("w:pStyle", NS)
    if pstyle is None:
        pstyle = etree.Element(W + "pStyle")
        ppr.insert(0, pstyle)
    pstyle.set(W + "val", style_id)


def rel_id_number(rel_id):
    return int(rel_id[3:]) if rel_id.startswith("rId") and rel_id[3:].isdigit() else 0


def copy_image_relationships(src_files, out_files, body_blocks):
    rel_tag = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
    rel_root = etree.fromstring(src_files["word/_rels/document.xml.rels"])
    out_rel_root = etree.fromstring(out_files["word/_rels/document.xml.rels"])
    image_rels = {r.get("Id"): r for r in rel_root.findall(rel_tag) if r.get("Type", "").endswith("/image")}
    highest = max((rel_id_number(r.get("Id", "")) for r in out_rel_root.findall(rel_tag)), default=0)
    mapping = {}
    for old_id, old_rel in image_rels.items():
        if not any(block.xpath(f".//*[@r:embed='{old_id}']", namespaces=NS) for block in body_blocks):
            continue
        highest += 1
        new_id = f"rId{highest}"
        old_target = old_rel.get("Target")
        media_name = Path(old_target).name
        new_target = f"media/paper_{media_name}"
        source_media = "word/" + old_target
        target_media = "word/" + new_target
        out_files[target_media] = src_files[source_media]
        new_rel = deepcopy(old_rel)
        new_rel.set("Id", new_id)
        new_rel.set("Target", new_target)
        out_rel_root.append(new_rel)
        mapping[old_id] = new_id
    for block in body_blocks:
        for node in block.xpath(".//*[@r:embed]", namespaces=NS):
            if node.get(R + "embed") in mapping:
                node.set(R + "embed", mapping[node.get(R + "embed")])
    out_files["word/_rels/document.xml.rels"] = etree.tostring(out_rel_root, encoding="UTF-8", xml_declaration=True, standalone=True)


def clone_section(section, columns):
    result = deepcopy(section)
    cols = result.find("w:cols", NS)
    if cols is None:
        cols = etree.SubElement(result, W + "cols")
    cols.set(W + "num", str(columns))
    cols.set(W + "space", "448")
    typ = result.find("w:type", NS)
    if typ is None:
        typ = etree.SubElement(result, W + "type")
    typ.set(W + "val", "continuous")
    return result


def apply_section(paragraph, section):
    ppr = paragraph.find("w:pPr", NS)
    if ppr is None:
        ppr = etree.Element(W + "pPr")
        paragraph.insert(0, ppr)
    existing = ppr.find("w:sectPr", NS)
    if existing is not None:
        ppr.remove(existing)
    ppr.append(section)


def keep_with_next(paragraph):
    ppr = paragraph.find("w:pPr", NS)
    if ppr is None:
        ppr = etree.Element(W + "pPr")
        paragraph.insert(0, ppr)
    if ppr.find("w:keepNext", NS) is None:
        ppr.append(etree.Element(W + "keepNext"))


def page_break_before(paragraph):
    ppr = paragraph.find("w:pPr", NS)
    if ppr is None:
        ppr = etree.Element(W + "pPr")
        paragraph.insert(0, ppr)
    if ppr.find("w:pageBreakBefore", NS) is None:
        ppr.append(etree.Element(W + "pageBreakBefore"))


def layout_sections(body, front, two_col):
    children = list(body)
    paragraphs = [c for c in children if c.tag == W + "p"]
    intro = next(p for p in paragraphs if text_of(p) == "0  引言")
    apply_section(paragraphs[paragraphs.index(intro) - 1], clone_section(front, 1))
    final = body.find("w:sectPr", NS)
    body.remove(final)
    body.append(clone_section(two_col, 2))
    # Wide figures and tables have a surrounding continuous one-column section.
    children = list(body)
    for i, child in enumerate(children):
        if child.tag == W + "p" and child.xpath(".//w:drawing", namespaces=NS):
            prev_p = next((children[j] for j in range(i - 1, -1, -1) if children[j].tag == W + "p"), None)
            if prev_p is not None:
                apply_section(prev_p, clone_section(two_col, 2))
            captions = [children[j] for j in range(i + 1, min(i + 4, len(children))) if children[j].tag == W + "p"]
            if captions:
                apply_section(captions[-1], clone_section(front, 1))
    children = list(body)
    for i, child in enumerate(children):
        if child.tag != W + "p" or not text_of(child).startswith(("表 1 ", "表 2 ")):
            continue
        table_at = next((j for j in range(i + 1, len(children)) if children[j].tag == W + "tbl"), None)
        if table_at is None:
            continue
        prev_p = next((children[j] for j in range(i - 1, -1, -1) if children[j].tag == W + "p"), None)
        next_p = next((children[j] for j in range(table_at + 1, len(children)) if children[j].tag == W + "p"), None)
        if prev_p is not None:
            apply_section(prev_p, clone_section(two_col, 2))
        # Keep each short full-width table as one readable unit. This avoids
        # a caption and header row stranded at the foot of the prior page.
        page_break_before(child)
        keep_with_next(child)
        english_caption = next((children[j] for j in range(i + 1, table_at) if children[j].tag == W + "p"), None)
        if english_caption is not None:
            keep_with_next(english_caption)
        if next_p is not None:
            apply_section(next_p, clone_section(front, 1))


def remove_template_comments(out_files):
    out_files.pop("word/comments.xml", None)
    out_files.pop("word/commentsExtended.xml", None)
    rel_tag = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
    rel_root = etree.fromstring(out_files["word/_rels/document.xml.rels"])
    for rel in list(rel_root.findall(rel_tag)):
        if "/comments" in rel.get("Type", ""):
            rel_root.remove(rel)
    out_files["word/_rels/document.xml.rels"] = etree.tostring(rel_root, encoding="UTF-8", xml_declaration=True, standalone=True)
    content = etree.fromstring(out_files["[Content_Types].xml"])
    ct = "{http://schemas.openxmlformats.org/package/2006/content-types}"
    for item in list(content):
        if item.get("PartName", "").startswith("/word/comments"):
            content.remove(item)
    out_files["[Content_Types].xml"] = etree.tostring(content, encoding="UTF-8", xml_declaration=True, standalone=True)


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    copy2(TEMPLATE, OUTPUT)
    with ZipFile(SOURCE) as src, ZipFile(TEMPLATE) as template:
        src_files = {n: src.read(n) for n in src.namelist()}
        out_files = {n: template.read(n) for n in template.namelist()}
    source_doc = etree.fromstring(src_files["word/document.xml"])
    source_body = source_doc.find("w:body", NS)
    target_doc = etree.fromstring(out_files["word/document.xml"])
    target_body = target_doc.find("w:body", NS)
    target_styles = styles_by_name(etree.fromstring(out_files["word/styles.xml"]))
    source_styles = styles_by_name(etree.fromstring(src_files["word/styles.xml"]))
    source_names = {v: k for k, v in source_styles.items()}
    blocks = [deepcopy(b) for b in source_body if b.tag != W + "sectPr"]
    copy_image_relationships(src_files, out_files, blocks)
    final_section = target_body.find("w:sectPr", NS)
    section_nodes = target_doc.xpath(".//w:sectPr", namespaces=NS)
    front = section_nodes[0]
    two_col = next(s for s in section_nodes if (s.find("w:cols", NS) is not None and s.find("w:cols", NS).get(W + "num") == "2"))
    for child in list(target_body):
        if child is not final_section:
            target_body.remove(child)
    for block in blocks:
        if block.tag == W + "p":
            pstyle = block.find("w:pPr/w:pStyle", NS)
            source_name = source_names.get(pstyle.get(W + "val") if pstyle is not None else "", "Normal")
            formula = bool(block.xpath(".//m:oMath", namespaces={**NS, "m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}))
            figure = bool(block.xpath(".//w:drawing", namespaces=NS))
            clear_source_overrides(block, formula, figure)
            set_pstyle(block, target_style(source_name, text_of(block), target_styles))
        target_body.insert(len(target_body) - 1, block)
    layout_sections(target_body, front, two_col)
    out_files["word/document.xml"] = etree.tostring(target_doc, encoding="UTF-8", xml_declaration=True, standalone=True)
    remove_template_comments(out_files)
    temp = OUTPUT.with_suffix(".tmp.docx")
    with ZipFile(temp, "w", ZIP_DEFLATED) as zout:
        for name, data in out_files.items():
            zout.writestr(name, data)
    temp.replace(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
