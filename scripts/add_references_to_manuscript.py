#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充§2引用和参考文献（2026-10-29）
"""

import sys
from pathlib import Path
from docx import Document

WORKSPACE = Path("/workspace")
DOCX_PATH = WORKSPACE / "outputs/revision_20261028/Hybrid_TEE_Rollup_投稿稿_20261029.docx"

def main():
    print(f"读取文档: {DOCX_PATH}")
    doc = Document(str(DOCX_PATH))
    
    print(f"\n[步骤1] 查找§2相关工作...")
    section2_start = -1
    section2_end = -1
    
    for i, para in enumerate(doc.paragraphs):
        text = para.text
        if "相关工作" in text and ("2." in text or "§2" in text):
            section2_start = i
            print(f"  找到§2开始: 段{i}")
        elif section2_start > 0 and ("3." in text or "系统" in text):
            section2_end = i
            print(f"  §2结束: 段{i}")
            break
    
    if section2_start < 0:
        print("  错误：未找到§2相关工作")
        return 1
    
    # ===== 补充引用标注 =====
    print(f"\n[步骤2] 补充§2引用标注...")
    ref_count = 0
    
    for i in range(section2_start, section2_end if section2_end > 0 else section2_start + 30):
        if i >= len(doc.paragraphs):
            break
        
        para = doc.paragraphs[i]
        text = para.text
        modified = False
        
        # TEEROLLUP引用
        if "TEEROLLUP" in text or "TeeRollup" in text:
            if "[1]" not in text:
                text = text.replace("TEEROLLUP", "TEEROLLUP[1]")
                text = text.replace("TeeRollup", "TeeRollup[1]")
                modified = True
                print(f"  ✓ 段{i}: TEEROLLUP引用")
        
        # opML引用
        if "opML" in text and not any(x in text for x in ["[13]", "ML模型", "机器学习"]):
            text = text.replace("opML", "opML[13]")
            modified = True
            print(f"  ✓ 段{i}: opML引用")
        
        # Dynamic Fraud Proof引用
        if "Dynamic Fraud Proof" in text or "动态欺诈证明" in text:
            if "[6]" not in text:
                text = text.replace("Dynamic Fraud Proof", "Dynamic Fraud Proof[6]")
                text = text.replace("动态欺诈证明", "动态欺诈证明[6]")
                modified = True
                print(f"  ✓ 段{i}: Dynamic Fraud Proof引用")
        
        # LazyLedger引用
        if "LazyLedger" in text or "Celestia" in text:
            if "[7]" not in text and "[14]" not in text:
                text = text.replace("LazyLedger", "LazyLedger[7]")
                modified = True
                print(f"  ✓ 段{i}: LazyLedger引用")
        
        # Arbitrum/BoLD引用
        if "Arbitrum" in text or "BoLD" in text:
            if "[8]" not in text:
                text = text.replace("BoLD", "BoLD[8]")
                modified = True
                print(f"  ✓ 段{i}: BoLD引用")
        
        # Optimism FDG引用
        if "Optimism" in text and "FDG" in text or "Fault Dispute Game" in text:
            if "[9]" not in text:
                text = text.replace("FDG", "FDG[9]")
                text = text.replace("Fault Dispute Game", "Fault Dispute Game[9]")
                modified = True
                print(f"  ✓ 段{i}: Optimism FDG引用")
        
        if modified:
            para.text = text
            ref_count += 1
    
    print(f"  共补充 {ref_count} 处引用")
    
    # ===== 查找参考文献章节 =====
    print(f"\n[步骤3] 查找参考文献章节...")
    ref_section_start = -1
    
    for i, para in enumerate(doc.paragraphs):
        text = para.text
        if "参考文献" in text or "REFERENCES" in text.upper():
            ref_section_start = i
            print(f"  找到参考文献: 段{i}")
            break
    
    if ref_section_start < 0:
        print("  警告：未找到参考文献章节")
    else:
        # 补充opML参考文献条目
        print(f"\n[步骤4] 补充参考文献条目...")
        
        # 查找[13]位置或末尾
        insert_pos = ref_section_start + 13  # 假设按编号排列
        if insert_pos < len(doc.paragraphs):
            # 检查是否已有opML
            opml_exists = False
            for i in range(ref_section_start, min(ref_section_start + 30, len(doc.paragraphs))):
                if "opML" in doc.paragraphs[i].text:
                    opml_exists = True
                    break
            
            if not opml_exists:
                # 添加opML条目
                opml_entry = ("[13] OPTIMISTIC ML. opML: Optimistic Machine Learning on Blockchain. "
                             "Available: https://opml.optimism.io/ [Accessed: 2026-10-28]")
                
                new_para = doc.add_paragraph(opml_entry)
                # 移动到合适位置
                new_para._element.getparent().remove(new_para._element)
                doc.paragraphs[insert_pos]._element.addnext(new_para._element)
                
                print(f"  ✓ 添加opML参考文献[13]")
        
        # 更新版本锁定信息
        print(f"\n[步骤5] 版本锁定现有引用...")
        version_count = 0
        
        for i in range(ref_section_start, min(ref_section_start + 50, len(doc.paragraphs))):
            para = doc.paragraphs[i]
            text = para.text
            modified = False
            
            # TeeRollup版本锁定
            if "TeeRollup" in text or "TEEROLLUP" in text:
                if "arXiv" in text and "v3" not in text:
                    text = text.replace("arXiv:2409.14647", "arXiv:2409.14647v3")
                    modified = True
                    print(f"  ✓ TeeRollup版本锁定为v3")
            
            # BoLD commit标注
            if "BoLD" in text or "Arbitrum" in text:
                if "commit" not in text.lower():
                    text = text + " (commit 30e78f67)"
                    modified = True
                    print(f"  ✓ BoLD添加commit")
            
            # OP FDG spec标注
            if "Optimism" in text and ("FDG" in text or "Fault" in text):
                if "2026-09-16" not in text:
                    text = text + " (spec 2026-09-16, commit c4a68ab)"
                    modified = True
                    print(f"  ✓ OP FDG添加spec和commit")
            
            if modified:
                para.text = text
                version_count += 1
        
        print(f"  共版本锁定 {version_count} 处")
    
    # ===== 保存文档 =====
    print(f"\n[步骤6] 保存文档...")
    doc.save(str(DOCX_PATH))
    
    print(f"\n✅ 引用和参考文献补充完成！")
    print(f"§2引用标注: {ref_count} 处")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
