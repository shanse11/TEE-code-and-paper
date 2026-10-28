# -*- coding: utf-8 -*-
"""模板对齐稿 vs 原始投稿版：逐项对比验证。"""
import hashlib
import re
import zipfile
from pathlib import Path

import docx
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "outputs" / "Hybrid_TEE_Rollup_计算机应用投稿版.docx"
OUT = ROOT / "outputs" / "template_alignment" / "Hybrid_TEE_Rollup_计算机应用模板对齐版.docx"

REPORT = []


def log(*a):
    s = " ".join(str(x) for x in a)
    REPORT.append(s)
    print(s)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def body_xml(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def omml_texts(path):
    """提取所有 OMML 公式的线性文本（m:t 拼接）。"""
    xml = body_xml(path)
    out = []
    for m in re.finditer(r"<m:oMath\b.*?</m:oMath>", xml, re.S):
        ts = re.findall(r"<m:t(?:\s[^>]*)?>(.*?)</m:t>", m.group(0), re.S)
        out.append("".join(ts))
    return out


def effective_runs(doc):
    """返回 (段落索引, 样式名, run文本前20, sz半磅, b, 是否有直接sz覆盖)"""
    rows = []
    for i, p in enumerate(doc.paragraphs):
        style_sz, style_b = None, None
        try:
            st = p.style
            rpr = st.element.find(qn("w:rPr"))
            if rpr is not None:
                sz = rpr.find(qn("w:sz"))
                if sz is not None:
                    style_sz = int(sz.get(qn("w:val")))
                b = rpr.find(qn("w:b"))
                style_b = b is None or b.get(qn("w:val")) not in ("0", "false")
        except Exception:
            pass
        for r in p.runs:
            rpr = r._element.find(qn("w:rPr"))
            direct_sz = None
            if rpr is not None:
                sz = rpr.find(qn("w:sz"))
                if sz is not None:
                    direct_sz = int(sz.get(qn("w:val")))
            rows.append((i, p.style.name, r.text[:20], style_sz, direct_sz))
    return rows


def main():
    log("=" * 70)
    log("模板对齐稿验证报告")
    log("=" * 70)
    log(f"原文: {SRC.name}  sha256={sha(SRC)}")
    log(f"对齐: {OUT.name}  sha256={sha(OUT)}")
    src = docx.Document(SRC)
    out = docx.Document(OUT)

    # ---------- 1. 结构计数 ----------
    log("\n[1] 结构计数（原文 -> 对齐稿）")
    log(f"  段落: {len(src.paragraphs)} -> {len(out.paragraphs)}")
    log(f"  表格: {len(src.tables)} -> {len(out.tables)}")
    s_img = len([r for r in zipfile.ZipFile(SRC).namelist() if r.startswith("word/media/")])
    o_img = len([r for r in zipfile.ZipFile(OUT).namelist() if r.startswith("word/media/")])
    log(f"  图片: {s_img} -> {o_img}")
    s_math = omml_texts(SRC)
    o_math = omml_texts(OUT)
    log(f"  OMML 公式对象: {len(s_math)} -> {len(o_math)}")
    s_sect = body_xml(SRC).count("<w:sectPr")
    o_sect = body_xml(OUT).count("<w:sectPr")
    log(f"  sectPr（节数）: {s_sect} -> {o_sect}")

    # ---------- 2. 公式对应 ----------
    log("\n[2] 公式对象对应（按 m:t 线性文本匹配）")
    from collections import Counter
    cs, co = Counter(s_math), Counter(o_math)
    same = sum((cs & co).values())
    log(f"  完全一致的公式数: {same}")
    only_src = list((cs - co).elements())
    only_out = list((co - cs).elements())
    if only_src:
        log(f"  仅原文有（{len(only_src)}）:")
        for t in only_src:
            log(f"    - {t}")
    if only_out:
        log(f"  仅对齐稿有（{len(only_out)}）:")
        for t in only_out:
            log(f"    - {t}")
    if not only_src and not only_out:
        log("  结论: 公式对象集合未变，仅位置/编号归属调整（去重靠引用式号，不删对象）")

    # ---------- 3. 关键实验数字 ----------
    log("\n[3] 关键实验数字保留检查")
    keys = ["801101.44", "29026.98", "50068.84", "200062", "TP311", "1001-9081"]
    s_all = "\n".join(p.text for p in src.paragraphs) + "\n" + "\n".join(
        c.text for t in src.tables for row in t.rows for c in row.cells)
    o_all = "\n".join(p.text for p in out.paragraphs) + "\n" + "\n".join(
        c.text for t in out.tables for row in t.rows for c in row.cells)
    for k in keys:
        log(f"  {k}: 原文 {s_all.count(k)} 处 -> 对齐稿 {o_all.count(k)} 处")
    nums = re.findall(r"\b\d{3,}\.\d{2}\b", s_all)
    missing = [n for n in set(nums) if n not in o_all]
    log(f"  原文中 >=3位整数两位小数的数值共 {len(set(nums))} 个，缺失 {len(missing)} 个")
    if missing:
        log(f"    缺失: {sorted(missing)[:20]}")

    # ---------- 4. 标题层级与直接格式 ----------
    log("\n[4] 标题实际生效字号 / 直接格式覆盖")
    with zipfile.ZipFile(OUT) as z:
        styles_xml = z.read("word/styles.xml").decode("utf-8")
    for name in ["文题", "作者名", "单位", "摘要关键词", "一级标题", "二级标题", "三级标题", "正文", "图表名称", "文献列表"]:
        m = re.search(r'<w:style [^>]*w:styleId="[^"]*"[^>]*>\s*<w:name w:val="%s"/>.*?</w:style>' % re.escape(name),
                      styles_xml, re.S)
        if not m:
            log(f"  [缺失样式] {name}")
            continue
        blk = m.group(0)
        sz = re.search(r'<w:sz w:val="(\d+)"', blk)
        b = re.search(r"<w:b/>", blk)
        ol = re.search(r'<w:outlineLvl w:val="(\d+)"', blk)
        log(f"  {name}: sz={sz.group(1) if sz else '-'} ({int(sz.group(1))/2 if sz else '-'}pt) "
            f"bold={'是' if b else '否'} outlineLvl={ol.group(1) if ol else '-'}")
    rows = effective_runs(out)
    overridden = [r for r in rows if r[4] is not None]
    log(f"  仍带 run 级直接 sz 覆盖的 run 数: {len(overridden)} / {len(rows)}")
    hz = [(r[0], r[1], r[2], r[4]) for r in rows if r[1] in ("一级标题", "二级标题", "三级标题", "文题") and r[4] is not None]
    if hz:
        log("  [警告] 标题仍被直接字号覆盖:")
        for h in hz[:20]:
            log(f"    段{h[0]} {h[1]} '{h[2]}' direct_sz={h[3]}")
    else:
        log("  标题/文题无 run 级字号覆盖，继承样式字号")

    # ---------- 5. 自动编号 ----------
    log("\n[5] 自动编号")
    dxml = body_xml(OUT)
    nz = zipfile.ZipFile(OUT).read("word/numbering.xml").decode("utf-8") if "word/numbering.xml" in zipfile.ZipFile(OUT).namelist() else ""
    log(f"  numbering.xml 存在: {bool(nz)}")
    log(f"  多级列表 abstractNumId: {sorted(set(re.findall(r'w:abstractNumId w:val=.(\d+)', nz)))}")
    log(f"  正文标题挂 numPr 的段数: {dxml.count('<w:numPr>')}")
    heads = [(i, p.style.name, p.text[:30]) for i, p in enumerate(out.paragraphs)
             if p.style.name in ("一级标题", "二级标题", "三级标题")]
    has_num = 0
    for i, sn, t in heads:
        pPr = out.paragraphs[i]._p.find(qn("w:pPr"))
        if pPr is not None and pPr.find(qn("w:numPr")) is not None:
            has_num += 1
    log(f"  标题段共 {len(heads)} 个，其中 {has_num} 个挂 numPr")
    manual = [t for i, sn, t in heads if re.match(r"^\s*\d+(\.\d+)*[\s\u3000]", t)]
    log(f"  仍残留手工编号的标题: {len(manual)} {manual[:5]}")

    # ---------- 6. 参考文献 ----------
    log("\n[6] 参考文献")
    refs = [p for p in out.paragraphs if p.style.name == "文献列表"]
    log(f"  文献条数: {len(refs)}")
    for i, p in enumerate(refs, 1):
        log(f"   [{i}] {p.text[:90]}")
    nums_in_text = sorted(set(int(x) for x in re.findall(r"\[(\d{1,2})\]", o_all) if int(x) <= 40))
    log(f"  正文出现的引用序号: {nums_in_text}")
    gap = [n for n in nums_in_text if n > len(refs)]
    log(f"  无对应文献的引用: {gap if gap else '无'}")

    # ---------- 7. 模板示例残留 ----------
    log("\n[7] 模板示例内容残留检查")
    bad = ["张", "李", "基金", "国家自然科学基金", "作者简介", "模板", "上标", "注意"]
    tpl_marks = ["三梦", "示例", "xxx", "XXXX"]
    for m in tpl_marks:
        log(f"  '{m}': {o_all.count(m)} 处")

    # ---------- 8. 图表题注位置 ----------
    log("\n[8] 图表与题注顺序（body 元素流）")
    root = out.element.body
    seq = []
    for child in root.iterchildren():
        tag = child.tag.split("}")[1]
        if tag == "p":
            txt = "".join(n.text or "" for n in child.iter(qn("w:t")))
            has_draw = child.find(".//" + qn("w:drawing")) is not None
            st = child.find(qn("w:pPr"))
            stn = ""
            if st is not None:
                ps = st.find(qn("w:pStyle"))
                if ps is not None:
                    stn = ps.get(qn("w:val"))
            seq.append(("P", stn, "IMG" if has_draw else "", txt[:40]))
        elif tag == "tbl":
            seq.append(("TBL", "", "", ""))
    for k, (kind, stn, img, txt) in enumerate(seq):
        if kind == "TBL" or img == "IMG" or "图表名称" in stn:
            log(f"  {k:3d} {kind:3s} style={stn:8s} {img:3s} {txt}")

    outp = ROOT / "outputs" / "template_alignment" / "work" / "verify_report.txt"
    outp.write_text("\n".join(REPORT), encoding="utf-8")
    log(f"\n报告已写入: {outp}")


if __name__ == "__main__":
    main()
