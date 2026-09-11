# -*- coding: utf-8 -*-
"""图表版式平衡优化：缩小尺寸、居中单行、禁止环绕、表格优先。"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
DRAFT = ROOT / "project_code" / "paper_outputs" / "draft"
DOCX_PATH = DRAFT / "Hybrid_TEE_Rollup_中文论文初稿.docx"
BACKUP_DIR = DRAFT / "backups"
ASSETS = DRAFT / "readability_assets_20260528"

NS_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# 图题 -> 页面宽度占比（图1 在 rename 后使用 Figure 1 标题）
FIGURE_WIDTH_RATIO = {
    "Figure 1 Threat Model of RCP": 0.55,
    "图 2 可恢复挑战驱动的 Hybrid TEE-Rollup 原型架构": 0.70,
    "图 3 RCP 协议交互时序": 0.70,
    "图 4 可恢复挑战协议状态机": 0.65,
    "图 5 恢复对超时场景挑战完成率的影响": 0.57,
    "图 6 二分挑战轮次与 trace steps 的关系": 0.57,
    "图 7 full payload 与 compact commit 的字节规模对比": 0.57,
    "图 8 不同 DA profile 下的摊销 gas 趋势": 0.57,
    "图 9 失败场景检测与仲裁结果": 0.57,
}

# 在这些图题对应的图片段前插入分页符
PAGE_BREAK_BEFORE_CAPTION = {
    "图 3 RCP 协议交互时序",
}

# 在这些表题段落前插入分页符（表格优先、避免与图4挤在同一页）
PAGE_BREAK_BEFORE_TABLE_CAPTION = {
    "表 5 RCP 状态转移",
}


def content_width_inches(doc: Document) -> float:
    s = doc.sections[0]
    return (s.page_width - s.left_margin - s.right_margin) / 914400


def para_has_image(paragraph) -> bool:
    xml = paragraph._element.xml
    return "pic:pic" in xml or "w:drawing" in xml


def find_prev_image_paragraph(doc: Document, caption_text: str):
    cap_idx = None
    for i, p in enumerate(doc.paragraphs):
        if p.text.strip() == caption_text:
            cap_idx = i
            break
    if cap_idx is None:
        return None
    for j in range(cap_idx - 1, -1, -1):
        if para_has_image(doc.paragraphs[j]):
            return doc.paragraphs[j]
        if doc.paragraphs[j].text.strip():
            break
    return None


def remove_keep_lines(paragraph):
    p_pr = paragraph._element.pPr
    if p_pr is None:
        return
    for child in list(p_pr):
        if child.tag.endswith("keepLines"):
            p_pr.remove(child)


def strip_wrap_and_floating(paragraph):
    """确保段落为上下型（无文字环绕、无浮动锚点）。"""
    p_pr = paragraph._element.get_or_add_pPr()
    for child in list(p_pr):
        if child.tag.endswith("framePr"):
            p_pr.remove(child)
    # 移除 run 级 framePr
    for run in paragraph._element.findall(f".//{{{NS_W}}}r"):
        r_pr = run.find(f"{{{NS_W}}}rPr")
        if r_pr is not None:
            for child in list(r_pr):
                if child.tag.endswith("framePr"):
                    r_pr.remove(child)


def resize_paragraph_image(paragraph, width_in: float):
    inline_tag = f"{{{NS_WP}}}inline"
    ext_tag = f"{{{NS_A}}}ext"
    for inline in paragraph._element.findall(f".//{inline_tag}"):
        ext = inline.find(f".//{ext_tag}")
        if ext is None:
            continue
        cx = int(ext.get("cx"))
        cy = int(ext.get("cy"))
        if cx <= 0:
            continue
        ratio = cy / cx
        new_cx = int(width_in * 914400)
        new_cy = int(new_cx * ratio)
        ext.set("cx", str(new_cx))
        ext.set("cy", str(new_cy))


def style_image_paragraph(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(3)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.keep_with_next = True
    remove_keep_lines(paragraph)
    strip_wrap_and_floating(paragraph)


def style_caption_paragraph(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(10)
    paragraph.paragraph_format.keep_with_next = False
    paragraph.paragraph_format.widow_control = True
    remove_keep_lines(paragraph)
    strip_wrap_and_floating(paragraph)
    for run in paragraph.runs:
        run.bold = True
        run.font.size = Pt(10.5)


def insert_page_break_before(paragraph):
    """在目标段落前插入分页符（若尚未存在）。"""
    prev = paragraph._element.getprevious()
    if prev is not None and prev.tag.endswith("p"):
        text = "".join(
            n.text or ""
            for n in prev.findall(f".//{{{NS_W}}}t")
        )
        if text.strip() == "" and prev.find(f".//{{{NS_W}}}br") is not None:
            return
    new_p = OxmlElement("w:p")
    paragraph._element.addprevious(new_p)
    from docx.text.paragraph import Paragraph

    br_para = Paragraph(new_p, paragraph._parent)
    br_para.add_run().add_break(WD_BREAK.PAGE)


def prioritize_tables(doc: Document):
    for table in doc.tables:
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        # 表格行尽量不拆页
        for row in table.rows:
            tr_pr = row._tr.get_or_add_trPr()
            cant_split = tr_pr.find(qn("w:cantSplit"))
            if cant_split is None:
                cant_split = OxmlElement("w:cantSplit")
                tr_pr.append(cant_split)
        for ri, row in enumerate(table.rows):
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.space_before = Pt(1)
                    p.paragraph_format.space_after = Pt(1)
                    for run in p.runs:
                        if run.font.size is None or run.font.size < Pt(9):
                            run.font.size = Pt(9)
                        if ri == 0:
                            run.bold = True


def clear_paragraph_text(paragraph):
    element = paragraph._element
    for child in list(element):
        if child.tag.endswith("r"):
            element.remove(child)


def rename_fig1_caption(doc: Document):
    for p in doc.paragraphs:
        t = p.text.strip()
        if t in ("图 1 Threat Model of RCP", "Figure 1 Threat Model of RCP"):
            clear_paragraph_text(p)
            run = p.add_run("Figure 1 Threat Model of RCP")
            run.bold = True
            run.font.size = Pt(10.5)
            style_caption_paragraph(p)
            return


def apply_layout():
    backup = BACKUP_DIR / (
        f"Hybrid_TEE_Rollup_中文论文初稿_before_layout_{datetime.now():%Y%m%d_%H%M%S}.docx"
    )
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DOCX_PATH, backup)

    doc = Document(str(DOCX_PATH))
    cw = content_width_inches(doc)

    rename_fig1_caption(doc)

    for caption, ratio in FIGURE_WIDTH_RATIO.items():
        width_in = cw * ratio
        cap_para = next((p for p in doc.paragraphs if p.text.strip() == caption), None)
        if cap_para is None:
            continue
        img_para = find_prev_image_paragraph(doc, caption)
        if caption in PAGE_BREAK_BEFORE_CAPTION and img_para is not None:
            insert_page_break_before(img_para)
        style_caption_paragraph(cap_para)
        if img_para is not None:
            style_image_paragraph(img_para)
            resize_paragraph_image(img_para, width_in)

    for table_cap in PAGE_BREAK_BEFORE_TABLE_CAPTION:
        cap = next((p for p in doc.paragraphs if p.text.strip() == table_cap), None)
        if cap is not None:
            insert_page_break_before(cap)

    prioritize_tables(doc)
    doc.save(str(DOCX_PATH))
    return backup, cw


def main():
    backup, cw = apply_layout()
    print(f"Content width: {cw:.2f} in")
    for cap, ratio in FIGURE_WIDTH_RATIO.items():
        print(f"  {cap}: {cw * ratio:.2f} in ({ratio * 100:.0f}%)")
    print(f"Backup: {backup}")
    print(f"Saved: {DOCX_PATH}")


if __name__ == "__main__":
    main()
