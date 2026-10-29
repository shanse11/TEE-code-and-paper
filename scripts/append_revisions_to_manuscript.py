#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
追加式修订脚本 - 在文档末尾添加所有表格和关键段落（2026-10-29）

策略：由于python-docx插入操作复杂，改为：
1. 在文档末尾追加所有新表格和段落
2. 生成详细的插入位置指导文档
3. 用户根据指导手动移动到正确位置（或直接使用）
"""

import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# 路径配置
WORKSPACE = Path("/workspace")
INPUT_DOCX = WORKSPACE / "outputs/revision_20261028/Hybrid_TEE_Rollup_返修稿_20261028.docx"
OUTPUT_DOCX = WORKSPACE / "outputs/revision_20261028/Hybrid_TEE_Rollup_返修稿_final_20261029.docx"

# 中文字体配置
CN_BODY = "宋体"
EN = "Times New Roman"

# ===== 工具函数 =====

def set_run_font(run, cn=CN_BODY, en=EN, size=9, bold=False):
    """设置run字体"""
    run.font.name = en
    run.font.size = Pt(size)
    run.font.bold = bold
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), cn)

def add_table_with_data(doc, data, title=None):
    """添加带数据的表格"""
    if title:
        p = doc.add_paragraph(title)
        p.style = 'Heading 3'
    
    table = doc.add_table(rows=len(data), cols=len(data[0]))
    table.style = 'Table Grid'
    
    # 填充表头（第一行，加粗）
    for j, val in enumerate(data[0]):
        cell = table.rows[0].cells[j]
        cell.text = str(val)
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                set_run_font(run, bold=True, size=9)
        # 表头背景色
        shading_elm = OxmlElement('w:shd')
        shading_elm.set(qn('w:fill'), 'E0E0E0')
        cell._element.get_or_add_tcPr().append(shading_elm)
    
    # 填充数据行
    for i in range(1, len(data)):
        for j, val in enumerate(data[i]):
            cell = table.rows[i].cells[j]
            cell.text = str(val)
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    set_run_font(run, size=9)
    
    return table

# ===== 表格数据（同前） =====

THREAT_MODEL_DATA = [
    ["参与方", "可信假设", "攻击能力边界", "防护机制", "残余风险"],
    ["提交者", "提交有效签名、绑定DA押金", "篡改结果、拒绝披露DA、友好挑战同伙", "B04/B05裁决拒绝；DA罚没(C12)；adjudicate兜底", "经济缺陷：友好挑战获利(C11,未修)"],
    ["挑战者", "绑定挑战押金", "恶意挑战、抢先recover占位", "押金损失；有界recover次数(maxRecoveries=2)", "无"],
    ["观察者/恢复者", "至少一方诚实且可上链", "全部离线、Sybil抢占", "状态链上持久化(C14)；恢复上限", "全部离线+无人调用→terminate"],
    ["DA服务", "绑定押金并承担披露义务", "串谋隐瞒数据", "DA罚没(bindDa/slashDa,C12)", "无(已闭环)"],
    ["TEE执行环境", "链下Quote验证通过", "硬件回滚、密钥泄露", "协议层taskId唯一性(C15)", "需链上DCAP验证(blocked)"],
    ["L1底层链", "按确认策略终局稳定", "共识重组、永久审查", "依赖L1安全假设", "不提供跨重组额外保证"],
]

PERMISSION_MATRIX_DATA = [
    ["操作", "调用者限制", "相位限制", "期限限制"],
    ["submit", "无", "IDLE", "-"],
    ["openChallenge", "非提交方", "SUBMITTED", "timestamp ≤ responseDeadline"],
    ["respond", "仅提交方", "CHALLENGED", "timestamp < responseDeadline"],
    ["recover", "无", "CHALLENGED或RECOVERED", "timeoutAt < timestamp < absoluteDeadline, recoveries < maxRecoveries"],
    ["advance", "无", "RECOVERED", "timestamp < absoluteDeadline"],
    ["replay", "无", "RECOVERED", "timestamp < absoluteDeadline"],
    ["settle", "无", "CHALLENGED或RECOVERED", "timestamp ≥ deadline"],
    ["adjudicate", "无", "CHALLENGED或RECOVERED", "timestamp ≥ deadline, verdict冲突"],
    ["terminate", "无", "任意", "timestamp > absoluteDeadline"],
    ["finalize", "无", "SETTLED", "timestamp > finality window"],
]

FAULT_MATRIX_DATA = [
    ["故障类型", "检测率", "挑战成功率", "罚没比例", "依赖机制", "StageH状态"],
    ["响应篡改", "100%", "100%", "100%", "B04/B05裁决拒绝", "✅证据充分"],
    ["轨迹长度不匹配", "100%", "100%", "100%", "B04", "✅证据充分"],
    ["远程证明无效", "100%", "-", "0%", "需链上DCAP验证", "⚠️部分(协议层检测,链上罚没blocked)"],
    ["DA不可用", "100%", "100%", "100%", "bindDa/slashDa(C12)", "✅完成"],
    ["DA证明无效", "100%", "100%", "100%", "同上", "✅完成"],
    ["提交者失联无证据", "100%", "-", "0%", "协议设计选择(E11)", "⚠️limited(不罚没无责任外部方)"],
]

SGX_DATA_TABLE = [
    ["Quote", "SHA256", "report_data前32字节", "验证结果", "用途"],
    ["quote_bound.dat", "9ab7ae99...", "与buildReportDataDigest一致", "0xA003", "绑定摘要验证"],
    ["quote_bad.dat", "a334b444...", "首字节篡改为0x20", "0xA003", "负例：密码学通过但绑定失败"],
    ["quote_steps4.dat", "75e84914...", "d7ddfc60...(4步result)", "0xA003", "有界哈希链4步"],
    ["quote_steps128.dat", "bf78a99d...", "dd38eea6...(128步result)", "0xA003", "有界哈希链128步"],
]

GL1_COMPARISON_DATA = [
    ["系统", "路径", "正确终局", "错误终局", "resolve gas合计"],
    ["本文", "interactive", "30/30", "0", "15,148,776"],
    ["本文", "fault-no-recovery", "30/30", "0", "8,076,444"],
    ["本文", "fault-with-recovery", "30/30", "0", "16,121,160"],
    ["本文", "direct-no-response", "30/30", "0", "3,884,634"],
    ["机制基线", "interactive", "30/30", "0", "11,517,024"],
    ["机制基线", "fault-no-recovery", "0/30", "30", "4,893,744"],
    ["机制基线", "direct-no-response", "0/30", "30", "1,602,852"],
]

# ===== 主函数 =====

def main():
    print(f"读取输入文档: {INPUT_DOCX}")
    if not INPUT_DOCX.exists():
        print(f"错误：找不到输入文件 {INPUT_DOCX}")
        return 1
    
    doc = Document(str(INPUT_DOCX))
    print(f"文档加载成功，共 {len(doc.paragraphs)} 段落")
    
    # ===== 在文档末尾追加所有新内容 =====
    
    doc.add_page_break()
    
    # 添加分隔标题
    header = doc.add_paragraph("【以下为2026-10-29补充内容，需手动移动到正文相应位置】")
    header.runs[0].font.bold = True
    header.runs[0].font.size = Pt(14)
    header.runs[0].font.color.rgb = RGBColor(255, 0, 0)
    
    doc.add_paragraph()
    
    # 1. 威胁模型表
    doc.add_paragraph("=" * 50)
    doc.add_paragraph("【插入位置】§3 系统概览 → §3.2 威胁模型与信任假设（新增）")
    doc.add_paragraph()
    
    p = doc.add_paragraph("3.2 威胁模型与信任假设")
    p.style = 'Heading 2'
    
    doc.add_paragraph("本方案假设至少存在一个有数据、有资金且可及时上链的诚实观察者。表X列出各参与方的可信假设、攻击能力边界、防护机制与残余风险。")
    
    add_table_with_data(doc, THREAT_MODEL_DATA, "表X 威胁模型（应为表2）")
    
    doc.add_paragraph()
    doc.add_paragraph("=" * 50)
    doc.add_paragraph()
    
    # 2. 权限矩阵表
    doc.add_paragraph("【插入位置】§4核心机制 → §4.1 可恢复挑战协议 → §4.1.1 操作权限约束（新增）")
    doc.add_paragraph()
    
    p = doc.add_paragraph("4.1.1 操作权限约束")
    p.style = 'Heading 3'
    
    doc.add_paragraph("表X列出协议中各操作的权限约束、相位限制与期限限制。recover/advance/replay/settle/adjudicate无调用者限制但受相位与期限约束；openChallenge限非提交方；respond仅提交方可调用。")
    
    add_table_with_data(doc, PERMISSION_MATRIX_DATA, "表X 操作权限矩阵（应为表3）")
    
    doc.add_paragraph()
    doc.add_paragraph("=" * 50)
    doc.add_paragraph()
    
    # 3. 故障类型矩阵
    doc.add_paragraph("【插入位置】§5实验评估 → §5.2 安全与资金闭环 → §5.2.1 故障类型检测与罚没（更新原表或新增）")
    doc.add_paragraph()
    
    p = doc.add_paragraph("5.2.1 故障类型检测与罚没")
    p.style = 'Heading 3'
    
    doc.add_paragraph("表X列出各类故障的检测率、挑战成功率、罚没比例及依赖机制。本轮通过DA披露罚没机制（bindDa/fulfillDa/slashDa）将DA类故障从0%罚没提升至100%（C12测试passing，罚没1 ether，slashDa gas=66,136）。")
    
    add_table_with_data(doc, FAULT_MATRIX_DATA, "表X 故障类型矩阵（应为表4或表5）")
    
    doc.add_paragraph()
    doc.add_paragraph("=" * 50)
    doc.add_paragraph()
    
    # 4. 真实SGX数据表
    doc.add_paragraph("【插入位置】§5实验评估 → §5.4 真实TEE（新增整节）")
    doc.add_paragraph()
    
    p = doc.add_paragraph("5.4 真实SGX DCAP验证")
    p.style = 'Heading 2'
    
    doc.add_paragraph("本方案在阿里云ecs.g7t.large实例（Intel Xeon Platinum 8369B，北京可用区）上获取真实SGX DCAP Quote。软件栈：sgxsdk-2.19.100.3, libsgx-dcap-ql-1.16.100.2。Quote验证结果：两条路径（Intel QvE + Azure Attestation）均返回0xA003 (SGX_QL_QV_RESULT_OUT_OF_DATE_CONFIG_NEEDED)。TCB状态\"过期需配置\"非UpToDate，关联6个Intel security advisory：INTEL-SA-00657/00767/01079/01103/01153/00615。密码学验证通过，但策略判定为非终态。表X列出4条Quote的验证摘要。")
    
    add_table_with_data(doc, SGX_DATA_TABLE, "表X 真实SGX Quote验证摘要（应为表4或表5）")
    
    doc.add_paragraph()
    doc.add_paragraph("Enclave性能：有界哈希链4步0.057ms（Enclave内），128步0.497ms（Enclave内）。同代码宿主环境128步0.305ms，Enclave开销约63%。Enclave输出与本地ethers.solidityKeccak256逐字节一致，证明确定性计算。本地EVM联调：真实SGX计算+本地Hardhat裁决。4步任务respond gas=94,836, adjudicate gas=94,812（verdict=0），SETTLED。128步任务respond gas=166,840, adjudicate gas=164,567（verdict=0），SETTLED。")
    
    doc.add_paragraph()
    doc.add_paragraph("验证边界：当前Quote验证在链下完成（两条路径：Intel QvE + Azure API），链上DCAP验证blocked（需合约集成Intel DCAP验证库或可信验证服务）。本方案依赖链下可信验证服务确认Quote有效性。TCB状态0xA003非UpToDate，需平台升级或collateral更新方可通过严格策略。")
    
    doc.add_paragraph()
    doc.add_paragraph("=" * 50)
    doc.add_paragraph()
    
    # 5. 口径限制段落
    doc.add_paragraph("【插入位置】§5.5 端到端性能（在性能数字后立即插入）")
    doc.add_paragraph()
    
    doc.add_paragraph("口径限制（必须完整标注）：本实验采用本地Hardhat环境进行性能测试，存在以下七条口径限制：(1) Hardhat in-process automining，无真实共识最终性；(2) 每块链钟+1秒（block.timestamp += 1s per block）；(3) Closed-loop到达模式，每批等待前批完成，非open-loop压力测试；(4) 仅3个独立run，不报告p95/p99分位数，无bootstrap置信区间；(5) 费用为local-gas-only，仅计算链上EVM gas，不含DA存储成本与TEE计算成本；(6) Payload维度（1 KiB vs 32 KiB）为名义参数，因dataHash固定32字节，不构成\"扩展到大块数据仍保持吞吐\"的证据；(7) 并发测试（c=1/4/16）无单调增益，受Hardhat串行出块限制。因此，本文性能数字不可直接与生产环境吞吐量或第三方系统主网账单进行跨协议百分比比较。")
    
    doc.add_paragraph()
    doc.add_paragraph("=" * 50)
    doc.add_paragraph()
    
    # 6. G-L1对照表
    doc.add_paragraph("【插入位置】§5.6 同模型机制对照（新增或确认）")
    doc.add_paragraph()
    
    p = doc.add_paragraph("5.6 同模型机制对照")
    p.style = 'Heading 2'
    
    doc.add_paragraph("为量化恢复机制的真实收益与代价，本文设计G-L1同模型对照实验：在相同有界重算模型下，对比\"有兜底adjudicate的本方案\"vs\"无兜底adjudicate的机制基线\"在提交方离线场景的表现。实验配置：3 run × 10 batch/run = 210条记录（非预热），本地Hardhat。表X列出G-L1机制对照结果。")
    
    add_table_with_data(doc, GL1_COMPARISON_DATA, "表X G-L1机制对照实验结果（应为表6）")
    
    doc.add_paragraph()
    doc.add_paragraph("关键发现：(1) 在无兜底adjudicate的机制基线中，提交方离线时正确终局率从30/30跌至0/30；(2) 在有兜底adjudicate的本文实现中，所有路径均30/30正确终局；(3) 恢复机制的价值：提供不依赖兜底重算的交互续推路径；(4) 恢复机制的代价：gas增加47%（fault-with-recovery 16.1M vs fault-no-recovery 8.1M），且延迟未减少（12.6ms vs 7.3ms）。重要标注：机制基线为本项目自建，非Arbitrum/Optimism/TeeRollup官方实现。")
    
    doc.add_paragraph()
    doc.add_paragraph("=" * 50)
    
    # ===== 保存修订后的文档 =====
    print(f"\n保存修订稿到: {OUTPUT_DOCX}")
    OUTPUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUTPUT_DOCX))
    
    print(f"\n追加式修订完成！")
    print(f"输出文件: {OUTPUT_DOCX}")
    print(f"文件大小: {OUTPUT_DOCX.stat().st_size / 1024:.1f} KB")
    
    # 生成插入指导文档
    guide_file = OUTPUT_DOCX.parent / "table_insertion_guide_zh.md"
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write("# 表格与段落插入指导（2026-10-29）\n\n")
        f.write(f"## 源文件\n\n")
        f.write(f"- 输入: `{INPUT_DOCX.relative_to(WORKSPACE)}`\n")
        f.write(f"- 输出: `{OUTPUT_DOCX.relative_to(WORKSPACE)}`\n\n")
        f.write(f"## 插入说明\n\n")
        f.write("所有新增的表格和段落已追加到文档末尾（分页符后），并用红色标题标注。\n\n")
        f.write("请按照以下顺序将内容移动到正文相应位置：\n\n")
        f.write("### 1. 威胁模型表（表2）\n")
        f.write("- 插入位置: §3 系统概览 → §3.2 威胁模型与信任假设（新增小节）\n")
        f.write("- 内容: 7行×5列表格 + 说明段落\n\n")
        f.write("### 2. 权限矩阵表（表3）\n")
        f.write("- 插入位置: §4 核心机制 → §4.1 可恢复挑战协议 → §4.1.1 操作权限约束（新增小节）\n")
        f.write("- 内容: 11行×4列表格 + 说明段落\n\n")
        f.write("### 3. 故障类型矩阵（表4或表5）\n")
        f.write("- 插入位置: §5 实验评估 → §5.2 安全与资金闭环 → §5.2.1 故障类型检测与罚没\n")
        f.write("- 内容: 7行×6列表格 + 说明段落（含DA罚没100%）\n\n")
        f.write("### 4. 真实SGX数据（§5.4整节）\n")
        f.write("- 插入位置: §5 实验评估 → §5.4 真实TEE（新增整节）\n")
        f.write("- 内容: 5行×5列表格 + 3个段落（平台信息、Enclave性能、验证边界）\n\n")
        f.write("### 5. 口径限制段落\n")
        f.write("- 插入位置: §5.5 端到端性能（在性能数字162.78 tasks/s后立即插入）\n")
        f.write("- 内容: 1个段落，7条口径限制完整标注\n\n")
        f.write("### 6. G-L1对照表（表6）\n")
        f.write("- 插入位置: §5.6 同模型机制对照（新增整节或确认已存在）\n")
        f.write("- 内容: 8行×5列表格 + 说明段落 + 关键发现段落\n\n")
        f.write("## 注意事项\n\n")
        f.write("1. 移动内容后，请删除文档末尾的分页符和红色标题\n")
        f.write("2. 检查表格编号（表2-表6）是否连续\n")
        f.write("3. 统一表格样式（Table Grid，表头灰色背景）\n")
        f.write("4. 检查字体（中文=宋体，英文=Times New Roman，字号9pt）\n")
        f.write("5. 检查段落格式（标题=黑体加粗，正文=宋体）\n\n")
        f.write("## 待手动完成的其他修订\n\n")
        f.write("- [ ] §2相关工作：补充4处引用标注（TEEROLLUP[1], opML[新增], DFP[6], LazyLedger[7-10]）\n")
        f.write("- [ ] §6结论：对齐摘要，逐项回答研究问题RQ1-RQ4\n")
        f.write("- [ ] 参考文献：补充opML条目，版本锁定（TeeRollup v3, BoLD commit 30e78f67, OP FDG spec 2026-09-16 + commit c4a68ab）\n")
        f.write("- [ ] 全文审核：术语统一、公式编号、图表交叉引用\n")
    
    print(f"插入指导文档已生成: {guide_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
