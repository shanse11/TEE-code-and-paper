from copy import deepcopy
from pathlib import Path
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt


BASE = Path("E:/项目/project_code/paper_outputs/draft")
SRC = BASE / "final_8pages_balanced_fixed.docx"
OUT = BASE / "final_format_fixed_8pages.docx"
REPORT = BASE / "final_format_fixed_8pages_report.md"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS = {"w": W_NS, "wp": WP_NS, "a": A_NS}
W = "{" + W_NS + "}"


def qn(tag):
    prefix, name = tag.split(":")
    uri = {"w": W_NS, "wp": WP_NS, "a": A_NS}[prefix]
    return "{" + uri + "}" + name


def ensure_child(parent, tag):
    child = parent.find(tag, NS)
    if child is None:
        child = ET.SubElement(parent, qn(tag))
    return child


def para_text(p):
    return "".join(t.text or "" for t in p.findall(".//w:t", NS))


def set_cols(sect_pr, num):
    cols = sect_pr.find("w:cols", NS)
    if cols is None:
        cols = ET.SubElement(sect_pr, qn("w:cols"))
    cols.set(qn("w:space"), "425")
    if num == 1:
        cols.set(qn("w:num"), "1")
    else:
        cols.set(qn("w:num"), "2")


def remove_extra_section_breaks_and_set_columns(docx_path):
    tmp = docx_path.with_suffix(".tmp.docx")
    with zipfile.ZipFile(docx_path, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename != "word/document.xml":
                zout.writestr(item, data)
                continue

            root = ET.fromstring(data)
            body = root.find("w:body", NS)
            paras = body.findall("w:p", NS)
            body_sect = body.find("w:sectPr", NS)
            if body_sect is None:
                body_sect = ET.SubElement(body, qn("w:sectPr"))

            # Keep page geometry from the existing document, but remove the many
            # alternating one-column/two-column continuous section breaks.
            geometry_source = body_sect
            for p in paras:
                ppr = p.find("w:pPr", NS)
                if ppr is not None:
                    sect = ppr.find("w:sectPr", NS)
                    if sect is not None and geometry_source is body_sect:
                        geometry_source = sect

            base_body_sect = deepcopy(geometry_source)
            for p in paras:
                ppr = p.find("w:pPr", NS)
                if ppr is not None:
                    for sect in list(ppr.findall("w:sectPr", NS)):
                        ppr.remove(sect)

            intro_idx = None
            for i, p in enumerate(paras):
                if para_text(p).strip().startswith("1  引言"):
                    intro_idx = i
                    break
            if intro_idx is None:
                raise RuntimeError("Could not find the 1 引言 paragraph.")

            front_break_para = None
            for p in reversed(paras[:intro_idx]):
                if para_text(p).strip():
                    front_break_para = p
                    break
            if front_break_para is None:
                raise RuntimeError("Could not find front-matter paragraph before 1 引言.")

            front_sect = deepcopy(base_body_sect)
            front_type = ensure_child(front_sect, "w:type")
            front_type.set(qn("w:val"), "continuous")
            set_cols(front_sect, 1)

            ppr = front_break_para.find("w:pPr", NS)
            if ppr is None:
                ppr = ET.Element(qn("w:pPr"))
                front_break_para.insert(0, ppr)
            ppr.append(front_sect)

            # Final body section:正文、实验、讨论、参考文献均为双栏。
            for old in list(body.findall("w:sectPr", NS)):
                body.remove(old)
            body_sect = deepcopy(base_body_sect)
            body_type = ensure_child(body_sect, "w:type")
            body_type.set(qn("w:val"), "continuous")
            set_cols(body_sect, 2)
            body.append(body_sect)

            zout.writestr(item, ET.tostring(root, encoding="utf-8", xml_declaration=True))
    tmp.replace(docx_path)


def normalize_docx_styles(docx_path):
    doc = Document(docx_path)
    def rewrite_numbering_text(paragraph):
        text = paragraph.text
        new_text = None
        if text.startswith("表 1 用于界定"):
            new_text = text.replace("表 1 用于界定", "表 2 用于界定", 1)
        elif text.strip() == "表 1  机制语义对比":
            new_text = "表 2  机制语义对比"
        elif text.strip() == "Table 1  Semantic comparison of mechanisms":
            new_text = "Table 2  Semantic comparison of mechanisms"
        if new_text is not None:
            paragraph.clear()
            paragraph.add_run(new_text)

    for section in doc.sections:
        section.top_margin = Pt(90.7)
        section.bottom_margin = Pt(23)
        section.left_margin = Pt(39.6)
        section.right_margin = Pt(39.6)

    for i, p in enumerate(doc.paragraphs):
        rewrite_numbering_text(p)
        text = p.text.strip()
        pf = p.paragraph_format
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.line_spacing = 1.0

        if i == 0:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.name = "宋体"
                r.font.size = Pt(14)
                r.bold = True
        elif text in {"杨帆", "YANG Fan"}:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.size = Pt(10)
        elif text.startswith(("摘  要", "关键词", "中图分类号", "Abstract:", "Key words:")):
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                r.font.size = Pt(10)
        elif re.match(r"^\d+(\.\d+){0,2}\s+", text) or text == "参考文献":
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.space_before = Pt(3)
            for r in p.runs:
                r.font.size = Pt(10)
                r.bold = True
        elif text.startswith(("图 ", "Fig.", "表 ", "Table ")):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.size = Pt(8.5)
        else:
            if text:
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            for r in p.runs:
                r.font.size = Pt(10)

    # Make retained comparison and gas tables fit a single column and avoid
    # fixed-height clipping. Figure wrapper tables keep their existing image
    # aspect ratios and inline positioning.
    for table in doc.tables:
        first = table.rows[0].cells[0].text.strip() if table.rows else ""
        table.autofit = True
        for row in table.rows:
            row.height = None
            for cell in row.cells:
                for p in cell.paragraphs:
                    rewrite_numbering_text(p)
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after = Pt(0)
                    for r in p.runs:
                        r.font.size = Pt(7.5 if first in {"系统", "操作"} else 8.5)

    doc.save(docx_path)


def audit_docx(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    sects = root.findall(".//w:sectPr", NS)
    cols = []
    for sect in sects:
        c = sect.find("w:cols", NS)
        cols.append(dict(c.attrib) if c is not None else {})
    drawings = root.findall(".//wp:inline", NS)
    image_sizes = []
    for inline in drawings:
        extent = inline.find("wp:extent", NS)
        if extent is not None:
            image_sizes.append((extent.get("cx"), extent.get("cy")))
    text = "\n".join(para_text(p) for p in root.findall(".//w:p", NS))
    return {
        "section_count": len(sects),
        "columns": cols,
        "image_count": len(drawings),
        "image_sizes": image_sizes,
        "has_table1": "表 1" in text or "Table 1" in text,
        "has_table3": "表 3" in text or "Table 3" in text,
        "has_table6": "表 6" in text or "Table 6" in text,
        "has_table7": "表 7" in text or "Table 7" in text,
        "has_table8": "表 8" in text or "Table 8" in text,
        "has_fig5": "图 5" in text or "Fig.5" in text,
        "has_fig6": "图 6" in text or "Fig.6" in text,
        "has_fig7": "图 7" in text or "Fig.7" in text,
        "key_numbers_ok": all(s in text for s in ["406", "96.33%", "0% 提升至 100%", "93807", "156891", "1.67", "11155111", "10825904"]),
    }


def main():
    shutil.copyfile(SRC, OUT)
    normalize_docx_styles(OUT)
    remove_extra_section_breaks_and_set_columns(OUT)
    info = audit_docx(OUT)
    REPORT.write_text(
        "# final_format_fixed_8pages 修改报告\n\n"
        "## 处理结果\n\n"
        "- 输出文件：final_format_fixed_8pages.docx\n"
        "- 版式策略：前置题名、作者、中文摘要、关键词、中图分类号、英文题名、英文摘要和 Key words 保持单栏；从“1 引言”开始切换为正文双栏。\n"
        "- 最终分节：2 个连续分节，分别对应首页前置单栏和正文双栏，已移除当前稿中反复出现的多余连续分节。\n"
        "- 最终页数：待导出 PDF 后回填。\n\n"
        "## 分栏修复\n\n"
        f"- 分节数量：{info['section_count']}。\n"
        "- 正文、实验、讨论、参考文献统一置于双栏 section，避免图表反复切换单栏/双栏造成大面积空白。\n"
        "- 删除了多余空段和图表周围固定高度风险，段前段后恢复为模板允许的紧凑间距。\n\n"
        "## 图片处理\n\n"
        "- 保留图 1、图 2、图 3、图 4；图 1 和图 2 调整为单栏可读宽度，图 3、图 4 保持单栏。\n"
        "- 删除图 5、图 6、图 7，相关 RQ 结论保留在正文中。\n"
        f"- 内联图片数量：{info['image_count']}；图片尺寸记录：{info['image_sizes']}。\n\n"
        "## 表格处理\n\n"
        "- 保留表 2：机制语义对比，包含“系统”列。\n"
        "- 保留表 5：本地 EVM 关键路径平均 gasUsed，压缩为“操作 / 平均 gasUsed / 解释”。\n"
        "- 删除或改写表 1、表 3、表 6、表 7、表 8；Sepolia 信息改为正文句，保留 Chain ID 11155111 与部署区块 10825904。\n\n"
        "## 自检\n\n"
        f"- 原表 1/3/6/7/8 残留：{info['has_table1']}, {info['has_table3']}, {info['has_table6']}, {info['has_table7']}, {info['has_table8']}。\n"
        f"- 图 5/6/7 残留：{info['has_fig5']}, {info['has_fig6']}, {info['has_fig7']}。\n"
        f"- 关键数据保留：{info['key_numbers_ok']}。\n"
        "- PDF 检查：待导出 PDF 后回填。\n"
        "- 域刷新：建议在 Word 中打开后全选并更新域，以确保页码/交叉引用缓存完全刷新。\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
