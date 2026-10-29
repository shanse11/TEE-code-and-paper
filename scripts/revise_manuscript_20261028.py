#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手稿修订脚本（2026-10-28 专家意见返修）

基于 expert_response_matrix.md §4 检查清单修订手稿。
由于docx格式复杂，本脚本采用策略：
1. 读取原始docx
2. 基于关键词定位段落
3. 执行文本替换/插入
4. 保留原有格式
5. 生成新docx
"""

import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# 路径配置
WORKSPACE = Path("/workspace")
INPUT_DOCX = WORKSPACE / "paper_outputs/draft/论文终版/Hybrid_TEE_Rollup_修订稿.docx"
OUTPUT_DOCX = WORKSPACE / "outputs/revision_20261028/Hybrid_TEE_Rollup_返修稿_20261028.docx"

# 替换规则（关键表述）
REPLACEMENTS = {
    # 删除禁止表述
    "恢复机制降低结算延迟": "恢复机制提供不依赖兜底的交互续推路径",
    "恢复机制加快结算": "恢复机制提供不依赖兜底的交互续推路径",
    "首创第三方争议接续": "在有界模型内提供显式adjudicate兜底",
    "首创动态参与机制": "在有界模型内提供显式adjudicate兜底",
    "完全去信任": "在链下Quote验证前提下",
    "解决全部TEE风险": "通过协议层防重放缓解部分TEE风险",
    "优于所有Rollup": "在有界模型内提供差异化机制",
    
    # 修正创新点表述
    "动态延长窗口": "有界窗口（absoluteDeadline不延长）",
    "降低结算延迟": "提供交互续推路径但延迟未减少",
}

# 需要补充的段落（按章节组织）
ADDITIONS = {
    "摘要_边界标注": """需明确的边界：本地Hardhat性能指标（162.78 tasks/s）为closed-loop口径，不含DA/TEE成本；真实SGX Quote在链下验证（依赖可信验证服务）；Sepolia Blob广播因缺RPC URL/私钥/beacon API仍blocked；计算模型为有界重算（至多128步），非通用EVM Rollup。""",
    
    "引言_模型边界": """需明确的模型边界：本方案为有界执行模型（bounded-task），针对可在128步内完成的确定性计算任务，非通用EVM Rollup；traceRoot为有序向量承诺（keccak256(abi.encode(bytes32[]))），非Merkle单步证明；在单链实例假设下不存在分叉争议场景。""",
    
    "相关工作_OP_FDG对比": """Optimism的Fault Dispute Game (FDG)在move()函数内通过getChallengerDuration()实现三档CLOCK_EXTENSION时钟继承机制，允许挑战方在提交响应时动态延长游戏期限。本文与OP FDG的差异在于：(1)有界重算模型vs无界二分；(2)显式adjudicate兜底vs时钟继承；(3)恢复不刷新绝对截止时间vs动态延期。""",
}


def find_paragraph_by_keywords(doc, keywords):
    """通过关键词查找段落"""
    for para in doc.paragraphs:
        text = para.text
        if any(kw in text for kw in keywords):
            return para
    return None


def replace_text_in_paragraph(para, old_text, new_text):
    """在段落中替换文本（保留格式）"""
    if old_text in para.text:
        # 简单替换（可能丢失部分格式）
        inline = para._element
        for text_elem in inline.findall('.//w:t', {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}):
            if text_elem.text and old_text in text_elem.text:
                text_elem.text = text_elem.text.replace(old_text, new_text)
                return True
    return False


def insert_paragraph_after(doc, ref_para, text, style=None):
    """在参考段落后插入新段落"""
    new_para = doc.add_paragraph(text, style=style)
    # 移动到参考段落后面
    ref_para._element.addnext(new_para._element)
    return new_para


def add_table_from_data(doc, data, headers):
    """添加表格"""
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Table Grid'
    
    # 添加表头
    hdr_cells = table.rows[0].cells
    for i, header in enumerate(headers):
        hdr_cells[i].text = header
    
    # 添加数据行
    for row_data in data:
        row_cells = table.add_row().cells
        for i, val in enumerate(row_data):
            row_cells[i].text = str(val)
    
    return table


def main():
    input_docx = INPUT_DOCX
    print(f"读取原始文档: {input_docx}")
    
    if not input_docx.exists():
        print(f"错误：找不到输入文件 {input_docx}")
        print("尝试使用上传的文件...")
        alt_input = Path("/home/ubuntu/.cursor/projects/workspace/uploads/HTR_paper_draft_7e8e.docx")
        if alt_input.exists():
            input_docx = alt_input
            print(f"使用备用文件: {input_docx}")
        else:
            print("错误：也找不到备用文件")
            return 1
    
    doc = Document(str(input_docx))
    
    print(f"文档加载成功，共 {len(doc.paragraphs)} 段落")
    
    # 阶段1：文本替换（删除禁止表述）
    print("\n阶段1：执行文本替换...")
    replace_count = 0
    for para in doc.paragraphs:
        for old_text, new_text in REPLACEMENTS.items():
            if replace_text_in_paragraph(para, old_text, new_text):
                print(f"  ✓ 替换: {old_text[:30]}... → {new_text[:30]}...")
                replace_count += 1
    print(f"完成 {replace_count} 处替换")
    
    # 阶段2：补充关键段落
    print("\n阶段2：补充关键段落...")
    
    # 补充摘要边界标注
    abstract_para = find_paragraph_by_keywords(doc, ["摘要", "本文提出", "Hybrid TEE-Rollup"])
    if abstract_para:
        # 在摘要段落后添加边界标注
        insert_paragraph_after(doc, abstract_para, ADDITIONS["摘要_边界标注"])
        print("  ✓ 补充摘要边界标注")
    
    # 补充引言模型边界
    intro_para = find_paragraph_by_keywords(doc, ["引言", "研究动机", "区块链扩容"])
    if intro_para:
        insert_paragraph_after(doc, intro_para, ADDITIONS["引言_模型边界"])
        print("  ✓ 补充引言模型边界")
    
    # 补充相关工作OP FDG对比
    related_para = find_paragraph_by_keywords(doc, ["相关工作", "TeeRollup", "Optimism"])
    if related_para:
        insert_paragraph_after(doc, related_para, ADDITIONS["相关工作_OP_FDG对比"])
        print("  ✓ 补充OP FDG对比")
    
    # 阶段3：添加数据表格（StageH证据）
    print("\n阶段3：添加StageH数据表格...")
    
    # 查找实验评估章节
    exp_para = find_paragraph_by_keywords(doc, ["实验评估", "实验结果", "5."])
    if exp_para:
        # 添加G-L1对照表
        g_l1_data = [
            ["本文", "interactive", "30/30", "0", "15,148,776"],
            ["本文", "fault-no-recovery", "30/30", "0", "8,076,444"],
            ["本文", "fault-with-recovery", "30/30", "0", "16,121,160"],
            ["本文", "direct-no-response", "30/30", "0", "3,884,634"],
            ["机制基线", "interactive", "30/30", "0", "11,517,024"],
            ["机制基线", "fault-no-recovery", "0/30", "30", "4,893,744"],
            ["机制基线", "direct-no-response", "0/30", "30", "1,602,852"],
        ]
        g_l1_headers = ["系统", "路径", "正确终局", "错误终局", "resolve gas合计"]
        
        # 在实验段落前添加表格标题
        table_title_para = insert_paragraph_after(doc, exp_para, "表X G-L1机制对照实验结果")
        table_title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 添加表格
        add_table_from_data(doc, g_l1_data, g_l1_headers)
        print("  ✓ 添加G-L1对照表")
        
        # 添加表格说明
        caption = insert_paragraph_after(doc, table_title_para, 
            "关键发现：无兜底时正确终局率0/30，有兜底时30/30。机制基线非官方实现。")
        print("  ✓ 添加表格说明")
    
    # 阶段4：保存修订稿
    print(f"\n保存修订稿到: {OUTPUT_DOCX}")
    OUTPUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUTPUT_DOCX))
    
    print("\n修订完成！")
    print(f"输出文件: {OUTPUT_DOCX}")
    print(f"文件大小: {OUTPUT_DOCX.stat().st_size / 1024:.1f} KB")
    
    # 生成修订日志
    log_file = OUTPUT_DOCX.parent / "manuscript_revision_log_20261028.md"
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("# 手稿修订日志（2026-10-28）\n\n")
        f.write(f"## 基准文件\n\n- 输入: `{input_docx.relative_to(WORKSPACE)}`\n")
        f.write(f"- 输出: `{OUTPUT_DOCX.relative_to(WORKSPACE)}`\n\n")
        f.write(f"## 修订统计\n\n")
        f.write(f"- 文本替换: {replace_count} 处\n")
        f.write(f"- 新增段落: {len(ADDITIONS)} 个\n")
        f.write(f"- 新增表格: 1 个（G-L1对照）\n\n")
        f.write(f"## 主要修订\n\n")
        f.write("1. 删除禁止表述（恢复降低延迟、首创第三方接续等）\n")
        f.write("2. 补充摘要边界标注\n")
        f.write("3. 补充引言模型边界\n")
        f.write("4. 补充OP FDG对比\n")
        f.write("5. 添加G-L1对照实验表格\n\n")
        f.write("## 待完成项\n\n")
        f.write("由于docx格式复杂，以下项目需要手动完成：\n\n")
        f.write("- [ ] §2相关工作：补充4处引用标注（TEEROLLUP[1], opML[新增], DFP[6], LazyLedger[7-10]）\n")
        f.write("- [ ] §3系统：新增威胁模型表（表2）\n")
        f.write("- [ ] §4机制：补充权限矩阵表（表3）\n")
        f.write("- [ ] §5实验：更新故障类型矩阵（表4/表5）\n")
        f.write("- [ ] §5实验：新增真实SGX数据表（表4）\n")
        f.write("- [ ] §5实验：补充口径限制段落（7条限制）\n")
        f.write("- [ ] 参考文献：补充opML条目\n")
        f.write("- [ ] 参考文献：版本锁定（TeeRollup v3, BoLD commit, OP FDG spec）\n\n")
        f.write("详细修订指南见: `manuscript_revision_implementation_zh.md`\n")
    
    print(f"修订日志已生成: {log_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
