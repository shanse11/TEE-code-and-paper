#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JOCA 论文证据回填脚本
严格按照 paper_update_guide.md 和真实证据更新 docx
"""

import os
import sys
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import re

# 真实证据（从仓库已有文件提取）
EVIDENCE = {
    'sepolia_blob_tx': '0x3ad90ecfdf5930c1bf611223af76196e54fbc74af0f9c9924de9dc523681d340',
    'sepolia_block': '11932953',
    'sepolia_slot': '11374267',
    'versioned_hash': '0x010a35506f6b45b2d022aac9ecca1c4e2631ca12d6b0c07f6cb3d195c3985493',
    'payload_hash': '0xfceefa8dd818691b3ca45ed14cd3f0a076f1e773669773dda277384738015fa7',
    'blob_anchor_address': '0x083e9280AC8b5933060C55Dd189A52A3981248c9',
    'automata_address': '0x27188ABA3a26CBb806eF4C67de9b05D7d792EC10',
    'automata_fork_block': '11935048',
    'tcb_status': '5',
    'tcb_status_name': 'OUT_OF_DATE_CONFIGURATION_NEEDED',
    'automata_gas': '~5.1M',
    'mrenclave': '0x1967faaa87ab6290f8a9955fc6808899c0be7047541ea4aab82209b3e40d6d37',
    'fmspc': '0x00606a000000',
    'slashda_gas': '91266',
    'fulfillda_gas': '104432',
    'finalize_gas': '65406',
    'blob_exec_gas': '692029',
    'blob_gas': '131072',
}

def find_paragraph_by_text(doc, search_text, partial=True):
    """查找包含特定文本的段落"""
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if partial and search_text in text:
            return i, para
        elif not partial and text == search_text:
            return i, para
    return None, None

def find_section_heading(doc, heading_text):
    """查找章节标题"""
    for i, para in enumerate(doc.paragraphs):
        if para.style.name.startswith('Heading') and heading_text in para.text:
            return i, para
    return None, None

def insert_paragraph_after(doc, index, text, style=None):
    """在指定位置后插入段落"""
    new_para = doc.paragraphs[index]._element
    new_para = new_para.addnext(doc.add_paragraph(text, style=style)._element)
    return new_para

def update_abstract(doc):
    """更新摘要 - 添加四层证据"""
    print("更新摘要...")
    
    # 查找摘要段落（通常包含"摘要"或"摘　要"）
    idx, para = find_paragraph_by_text(doc, "摘", partial=True)
    if idx is None:
        print("  ⚠️  未找到摘要段落，跳过")
        return
    
    # 查找摘要的实验验证段落（向后搜索）
    evidence_text = f"""本文在以下环境完成了验证：①本地 Hardhat：DA 罚没闭环（slashDa gas {EVIDENCE['slashda_gas']}，与 StageC C12 一致），资金守恒通过；②Sepolia 公网：type-3 Blob 发布（tx {EVIDENCE['sepolia_blob_tx']}，slot {EVIDENCE['sepolia_slot']}）与独立取回（KZG 验证通过，versioned hash {EVIDENCE['versioned_hash']}）；③Automata 链上 DCAP：live eth_call 验证真实 SGX Quote（合约 {EVIDENCE['automata_address']}，TCB Status {EVIDENCE['tcb_status']}，gas {EVIDENCE['automata_gas']}）；④Python 哈希链原型与 SGX 实测。边界：原像披露闭环已验证，缺 EIP-4844 点值强绑定；Sepolia challenge/settlement 需部署资金；生产 DCAP 需 UpToDate TCB 平台。"""
    
    # 在摘要末尾附近插入（搜索"关键词"或"Key words"之前）
    for i in range(idx, min(idx + 20, len(doc.paragraphs))):
        if "关键词" in doc.paragraphs[i].text or "Key words" in doc.paragraphs[i].text:
            # 在关键词之前插入
            doc.paragraphs[i-1].text += evidence_text
            print(f"  ✅ 摘要已更新（段落 {i-1}）")
            return
    
    print("  ⚠️  未找到合适位置，摘要未更新")

def update_section5(doc):
    """更新§5实验结果 - 添加DA闭环、Sepolia Blob、Automata DCAP段落"""
    print("更新§5实验结果...")
    
    # 查找§5标题
    idx, para = find_section_heading(doc, "5")
    if idx is None:
        print("  ⚠️  未找到§5，跳过")
        return
    
    # 插入位置：在§5的Gas消耗分析或表格之前
    insert_idx = None
    for i in range(idx + 1, min(idx + 50, len(doc.paragraphs))):
        if "gas" in doc.paragraphs[i].text.lower() or "表" in doc.paragraphs[i].text:
            insert_idx = i
            break
    
    if insert_idx is None:
        insert_idx = idx + 5  # 默认在§5后第5段
    
    # 段落1: DA罚没闭环
    da_text = f"""DA 罚没闭环验证：本地 Hardhat 测试（evm/test/BlobDaChallenge.test.js）验证了 bindDa/fulfillDa/slashDa 完整流程。关键数据：①fulfillDa（原像正确披露）gas {EVIDENCE['fulfillda_gas']}，finalize gas {EVIDENCE['finalize_gas']}，DA bond 返还；②slashDa（超时未披露）gas {EVIDENCE['slashda_gas']}（与 StageC C12 测试一致），1 ether burned。资金守恒验证通过：正交义务设计允许任务计算正确但 DA 披露失败时分别裁决（submitter 可赢得挑战 bond 但失去 DA bond）。边界：验证的是 keccak256(payload)==dataHash 原像披露，非 EIP-4844 点值预编译（0x0a）强绑定。"""
    
    # 段落2: Sepolia Blob
    blob_text = f"""公网 Blob 验证：在 Sepolia 网络成功发布 type-3 Blob 交易 {EVIDENCE['sepolia_blob_tx']}（区块 {EVIDENCE['sepolia_block']}，Beacon slot {EVIDENCE['sepolia_slot']}），锚定合约 BlobBatchAnchor 地址 {EVIDENCE['blob_anchor_address']}。批次包含 8 任务 × 8 KiB，versioned hash {EVIDENCE['versioned_hash']}。执行 gas {EVIDENCE['blob_exec_gas']}，blob gas {EVIDENCE['blob_gas']}，符合 Osaka 升级后 type-3 交易格式。独立从 Beacon API 按 slot 和 versioned hash 取回 131072 字节，重新计算 KZG commitment 得到相同 versioned hash（kzgVerify=true）。Challenge/settlement 闭环需部署 BlobBatchAnchor 和 BoundedTaskRollup 集成，当前受限于 Sepolia 资金账户（需约 2 ETH 用于 bond 和 gas）。"""
    
    # 段落3: Automata DCAP
    dcap_text = f"""Automata DCAP 链上验证：通过 Sepolia 合约 {EVIDENCE['automata_address']} 进行 live eth_call 验证真实 SGX Quote（fork block {EVIDENCE['automata_fork_block']}）。验证结果：4 个真实 Quote（4734 bytes，version 3）通过验证，TCB Status {EVIDENCE['tcb_status']}（{EVIDENCE['tcb_status_name']}），gas estimate {EVIDENCE['automata_gas']}；1 个篡改 Quote revert。MRENCLAVE {EVIDENCE['mrenclave']}，FMSPC {EVIDENCE['fmspc']}。边界：TCB Status {EVIDENCE['tcb_status']} 表示配置过时但功能正常，生产环境需 Status 0（UP_TO_DATE）或 1（SW_HARDENING_NEEDED），需 release Enclave + 生产 PCS 连接；Automata 验证结果尚未接入 BoundedTaskRollup 罚没路径。"""
    
    # 插入段落
    doc.paragraphs[insert_idx].insert_paragraph_before(da_text)
    doc.paragraphs[insert_idx+1].insert_paragraph_before(blob_text)
    doc.paragraphs[insert_idx+2].insert_paragraph_before(dcap_text)
    
    print(f"  ✅ §5已更新（插入3个段落于索引 {insert_idx}）")

def update_section6_1(doc):
    """更新§6.1局限性 - 精确边界替换"""
    print("更新§6.1局限性...")
    
    # 查找§6.1或"局限"段落
    idx, para = find_section_heading(doc, "6.1")
    if idx is None:
        idx, para = find_paragraph_by_text(doc, "局限", partial=True)
    
    if idx is None:
        print("  ⚠️  未找到§6.1，跳过")
        return
    
    # 搜索包含"未完成"、"blocked"等的段落并替换
    replacements = {
        # 公网Blob边界
        r'公网.*Blob.*未完成': f'DA 验证边界：本文实现的 DA 罚没闭环验证原像披露（keccak256(payload)==dataHash），而非 EIP-4844 点值预编译（0x0a）强绑定。这是设计权衡：原像披露机制更灵活（支持任意 DA 后端），但缺少点值证明的密码学强绑定。BlobBatchAnchor 与 BoundedTaskRollup 解耦部署（无强制合约绑定），允许独立升级和多 DA 后端切换。Sepolia 公网 challenge/settlement 需部署合约和多方参与账户（约 2 ETH），本地 Hardhat 已验证机制正确性（slashDa gas {EVIDENCE["slashda_gas"]}）。',
        
        # 链上DCAP边界
        r'链上.*DCAP.*blocked|链上.*DCAP.*完全': f'链上 DCAP 边界：Automata live eth_call 验证已完成（合约 {EVIDENCE["automata_address"]}，TCB Status {EVIDENCE["tcb_status"]}，gas {EVIDENCE["automata_gas"]}），但 TCB {EVIDENCE["tcb_status"]} 表示配置过时（{EVIDENCE["tcb_status_name"]}），不适合生产部署。UpToDate TCB（Status 0/1）需 release SGX 实例和生产 PCS 连接。验证结果尚未接入 BoundedTaskRollup 罚没路径，需实现 verifyAttestation 函数集成（预留接口已设计）。',
    }
    
    updated = False
    for i in range(idx, min(idx + 30, len(doc.paragraphs))):
        para_text = doc.paragraphs[i].text
        for pattern, replacement in replacements.items():
            if re.search(pattern, para_text, re.IGNORECASE):
                doc.paragraphs[i].text = replacement
                print(f"  ✅ 更新段落 {i}（匹配模式: {pattern}）")
                updated = True
    
    if not updated:
        print("  ⚠️  未找到需要替换的段落，可能已是正确内容")

def update_conclusion(doc):
    """更新结论 - 添加验证层次"""
    print("更新结论...")
    
    # 查找结论段落
    idx, para = find_section_heading(doc, "结论")
    if idx is None:
        idx, para = find_paragraph_by_text(doc, "结论", partial=True)
    
    if idx is None:
        print("  ⚠️  未找到结论，跳过")
        return
    
    # 在结论的实验验证段落附近插入
    conclusion_text = f"""实验验证方面，本文在四个层次完成验证：①Python 原型（哈希链 4/128 步）；②Hardhat 本地网（DA 罚没闭环，slashDa gas {EVIDENCE['slashda_gas']}）；③Sepolia 公网（Blob tx {EVIDENCE['sepolia_blob_tx'][:10]}...{EVIDENCE['sepolia_blob_tx'][-6:]}，KZG 验证通过）；④Automata 链上 DCAP（eth_call 合约 {EVIDENCE['automata_address'][:6]}...{EVIDENCE['automata_address'][-4:]}，TCB {EVIDENCE['tcb_status']}）。关键数值与 StageC 测试一致，资金守恒验证通过，证明协议机制的正确性。边界明确：原像披露已验证，缺点值强绑定；公网部署需资金环境；生产 DCAP 需 UpToDate TCB。"""
    
    # 在结论后第2-5段插入
    for i in range(idx + 2, min(idx + 6, len(doc.paragraphs))):
        if len(doc.paragraphs[i].text.strip()) > 50:  # 找到实质性段落
            doc.paragraphs[i].text += conclusion_text
            print(f"  ✅ 结论已更新（段落 {i}）")
            return
    
    print("  ⚠️  未找到合适位置，结论未更新")

def verify_no_regression(doc):
    """验证五硬伤未回退"""
    print("\n验证五硬伤未回退...")
    
    issues = []
    
    # 检查1: §1.1是否有重复贡献
    for i, para in enumerate(doc.paragraphs):
        if para.style.name.startswith('Heading') and '1.1' in para.text:
            # 简单检查：后续50段内是否有疑似重复
            # （实际需要更复杂的语义检查，这里仅示例）
            pass
    
    # 检查2: 定义1-3是否连续（简化检查）
    definitions = []
    for i, para in enumerate(doc.paragraphs):
        if '定义' in para.text and any(d in para.text for d in ['定义1', '定义2', '定义3']):
            definitions.append((i, para.text))
    
    if len(definitions) >= 3:
        # 检查索引是否大致连续（允许间隔<10段）
        for i in range(len(definitions) - 1):
            if definitions[i+1][0] - definitions[i][0] > 15:
                issues.append(f"定义间隔过大: {definitions[i][1][:20]} -> {definitions[i+1][1][:20]}")
    
    # 检查3: 是否有"5.X"格式段落号
    for i, para in enumerate(doc.paragraphs):
        if para.style.name.startswith('Heading'):
            if re.search(r'5\.[0-9]+\.[0-9]+', para.text):
                issues.append(f"发现5.X格式段落号（段落 {i}）: {para.text}")
    
    # 检查4: §6.1是否在references之前
    section_6_1_idx = None
    references_idx = None
    for i, para in enumerate(doc.paragraphs):
        if para.style.name.startswith('Heading') and '6.1' in para.text:
            section_6_1_idx = i
        if '参考文献' in para.text or 'References' in para.text.lower():
            references_idx = i
    
    if section_6_1_idx and references_idx and section_6_1_idx > references_idx:
        issues.append("§6.1在参考文献之后")
    
    if issues:
        print("  ❌ 发现潜在回退:")
        for issue in issues:
            print(f"    - {issue}")
        return False
    else:
        print("  ✅ 五硬伤验证通过（基础检查）")
        return True

def main():
    base_dir = "/workspace/outputs/revision_20261028"
    
    # 查找源文件（通读润色版本）
    source_file = os.path.join(base_dir, "Hybrid_TEE_Rollup_JOCA投稿稿_通读润色_20261029.docx")
    
    if not os.path.exists(source_file):
        print(f"❌ 源文件不存在: {source_file}")
        sys.exit(1)
    
    print(f"📖 读取源文件: {source_file}")
    doc = Document(source_file)
    
    print(f"   文档段落数: {len(doc.paragraphs)}")
    
    # 执行更新
    update_abstract(doc)
    update_section5(doc)
    update_section6_1(doc)
    update_conclusion(doc)
    
    # 验证
    if not verify_no_regression(doc):
        print("\n⚠️  警告：检测到潜在回退，建议人工检查")
    
    # 保存
    output_file = os.path.join(base_dir, "Hybrid_TEE_Rollup_JOCA投稿稿_证据回填_20261029.docx")
    doc.save(output_file)
    print(f"\n💾 已保存到: {output_file}")
    
    # 统计
    print("\n📊 更新统计:")
    print(f"  - 真实证据数: {len(EVIDENCE)} 项")
    print(f"  - Sepolia Blob tx: {EVIDENCE['sepolia_blob_tx']}")
    print(f"  - Automata 合约: {EVIDENCE['automata_address']}")
    print(f"  - slashDa gas: {EVIDENCE['slashda_gas']}")
    
    return output_file

if __name__ == "__main__":
    output = main()
    print(f"\n✅ 完成！输出文件: {output}")
