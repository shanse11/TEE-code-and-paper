# -*- coding: utf-8 -*-
"""Phase 2: Comprehensive English cleanup for ch6/7/8, figures, tables."""
from docx import Document
import re

doc = Document(r"E:\项目\project_code\paper_outputs\draft\final_chinese_academic_format.docx")
def st(idx, text):
    doc.paragraphs[idx].text = text

# ============================================================
# Define replacement map (B-class terms: English → Chinese)
# Applied to ALL paragraphs and table cells
# Order matters: longer phrases first to avoid partial matches
# ============================================================
reps = [
    # --- Compound phrases first ---
    ("Evidence-Carrying Compact Commit", "携带证据的紧凑提交"),
    ("Recoverable Challenge Protocol", "可恢复挑战协议"),
    ("Recoverable Challenge", "可恢复挑战机制"),
    ("Arbitration Continuity", "仲裁连续性"),
    ("Challenge Facts", "挑战事实"),
    ("Replay Evidence", "重放证据"),
    ("single-step replay", "单步重放"),
    ("bisection narrowing", "二分缩小"),
    ("synthetic workload", "合成工作负载"),
    ("synthetic timeout workload", "合成超时工作负载"),
    ("no-recover baseline", "不可恢复基线"),
    ("recoverable challenge", "可恢复挑战路径"),
    ("recoverable path", "可恢复路径"),
    ("no-recover", "不可恢复路径"),
    ("compact commit", "紧凑提交"),
    ("Compact Commit", "紧凑提交"),
    ("full payload", "完整负载"),
    ("Full Payload", "完整负载"),
    ("cost model", "成本模型"),
    ("Cost Model", "成本模型"),
    ("DA-aware Cost Model", "数据可用性感知成本模型"),
    ("DA-aware cost model", "数据可用性感知成本模型"),
    ("DA route", "数据可用性路径"),
    ("DA route selection", "数据可用性路径选择"),
    ("batch amortization", "批处理摊销"),
    ("payload scaling", "负载规模扩展"),
    ("payload size", "负载大小"),
    ("batch size", "批大小"),
    ("challenge success", "挑战成功率"),
    ("challenge success rate", "挑战成功率"),
    ("detection rate", "检测率"),
    ("recovery success rate", "恢复成功率"),
    ("slashed rate", "罚没比例"),
    ("recovery success", "恢复成功率"),
    ("state root", "状态根"),
    ("State Root", "状态根"),
    ("output hash", "输出哈希"),
    ("proof hash", "证明哈希"),
    ("payload hash", "负载哈希"),
    ("DA pointer", "数据可用性指针"),
    ("DA root", "数据可用性根"),
    ("DA Merkle root", "数据可用性 Merkle 根"),
    ("da merkle root", "数据可用性 Merkle 根"),
    ("expected hash", "预期哈希"),
    ("claimed hash", "声明哈希"),
    ("mismatch evidence", "不一致证据"),
    ("Mismatch Evidence", "不一致证据"),
    ("fault taxonomy", "故障分类"),
    ("response tampering", "响应篡改"),
    ("trace mismatch", "轨迹不一致"),
    ("trace length mismatch", "轨迹长度不匹配"),
    ("DA unavailable", "数据不可用"),
    ("da unavailable", "数据不可用"),
    ("DA proof invalid", "数据可用性证明无效"),
    ("da proof invalid", "数据可用性证明无效"),
    ("proof retrieval", "证明取回"),
    ("replay-ready", "具备重放准备性"),
    ("DA-traceable", "可追溯至数据可用性证据"),
    ("verification-oriented", "面向验证"),
    ("canonical JSON", "规范 JSON"),
    ("storage layout", "存储布局"),
    ("dispute window", "争议窗口"),
    ("challenge window", "挑战窗口"),
    ("challenge deadline", "挑战截止时间"),
    ("mismatch bits", "不一致位"),
    ("resolution bits", "结算位"),
    ("recovery history", "恢复历史"),
    ("recovery state", "恢复状态"),
    ("timeout detection", "超时检测"),
    ("timeout recovery", "超时恢复"),
    ("Timeout Recovery", "超时恢复"),
    ("timeout threshold", "超时阈值"),
    ("block explorer", "区块浏览器"),
    ("connect timeout", "连接超时"),
    ("deployability evidence", "可部署性证据"),
    ("gas per byte", "单字节燃料"),
    ("onchain gas per byte", "链上单字节燃料"),
    ("da gas per byte", "数据可用性单字节燃料"),
    ("gas reduction ratio", "燃料降幅比例"),
    ("byte reduction ratio", "字节降幅比例"),
    ("amortized gas", "摊销燃料"),
    ("total gas", "总燃料"),
    ("onchain commit gas", "链上提交燃料"),
    ("da data gas", "数据可用性数据燃料"),
    ("reduction ratio", "降幅比例"),
    ("recovery overhead", "恢复开销"),
    ("Recovery Overhead", "恢复开销"),
    ("challenge step", "挑战步骤"),
    ("mock DA registry", "可验证数据可用性注册表"),
    ("mock/verifiable DA", "可验证数据可用性"),
    ("simulated TEE", "模拟可信执行环境"),
    ("Simulated TEE", "模拟可信执行环境"),
    ("synthetic workload", "合成工作负载"),
    ("Synthetic Workload", "合成工作负载"),
    ("watchdog recovery", "观察节点恢复"),
    ("watchdog operator", "观察节点"),
    ("watchdog/operator", "观察节点"),
    ("challenge replay", "挑战重放"),
    ("failure scenarios", "故障场景"),
    ("Failure Scenarios", "故障场景"),
    ("comparison experiments", "对比型实验"),
    ("Comparison-Oriented Evaluation", "对比型实验评估"),
    ("Comparison-oriented evaluation", "对比型实验评估"),
    ("comparison-oriented evaluation", "对比型实验评估"),
    ("calldata", "调用数据"),
    ("Calldata", "调用数据"),
    ("blob data", "blob 数据"),
    ("blob price", "blob 价格"),
    ("blob base fee", "blob 基础费率"),
    ("blob lifecycle", "blob 生命周期"),
    ("blob-carrying", "携带 blob 的"),
    ("network congestion", "网络拥堵"),
    ("MEV", "最大可提取价值"),
    ("mempool", "内存池"),
    ("side channel", "侧信道"),
    ("supply chain", "供应链"),
    ("host I/O", "宿主输入输出"),
    ("remote attestation", "远程证明"),
    ("execution environment", "执行环境"),
    ("Trusted Execution Environment", "可信执行环境"),
    ("Data Availability", "数据可用性"),
    ("data availability", "数据可用性"),
    ("full onchain calldata", "全链上调用数据"),
    ("full-onchain calldata", "全链上调用数据"),
    ("compact external DA", "紧凑外部数据可用性"),
    ("compact EIP-4844-like", "紧凑类 EIP-4844 方案"),
    ("compact modular DA sampling", "紧凑模块化数据可用性采样"),
    ("fraud proof", "欺诈证明"),
    ("Fraud Proof", "欺诈证明"),
    ("dispute game", "争议博弈"),
    ("Dispute Game", "争议博弈"),
    ("challenge state machine", "挑战状态机"),
    ("recovery function", "恢复函数"),
    ("Recovery Function", "恢复函数"),
    ("rollup transaction", "汇总交易"),
    ("Rollup Transaction", "汇总交易"),
    ("light client", "轻客户端"),
    ("Light Client", "轻客户端"),
    ("modular blockchain", "模块化区块链"),
    ("Modular Blockchain", "模块化区块链"),
    ("data availability sampling", "数据可用性采样"),
    ("Data Availability Sampling", "数据可用性采样"),
    ("validity proof", "有效性证明"),
    ("Validity Proof", "有效性证明"),
    ("optimistic verification", "乐观验证"),
    ("interactive fraud proof", "交互式欺诈证明"),
    ("on-chain verification", "链上验证"),
    ("off-chain execution", "链下执行"),
    ("on-chain arbitration", "链上仲裁"),
    ("economic security", "经济安全"),
    ("Economic Security", "经济安全"),
    ("slashing condition", "罚没条件"),
]

# ============================================================
# Apply replacements to ALL paragraphs
# ============================================================
count = 0
for i, p in enumerate(doc.paragraphs):
    text = p.text
    for eng, chn in reps:
        if eng in text:
            text = text.replace(eng, chn)
            count += 1
    if text != p.text:
        doc.paragraphs[i].text = text

print(f"Paragraph replacements: {count}")

# ============================================================
# Apply replacements to ALL table cells
# ============================================================
tcount = 0
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                text = para.text
                for eng, chn in reps:
                    if eng in text:
                        text = text.replace(eng, chn)
                        tcount += 1
                if text != para.text:
                    para.text = text

print(f"Table cell replacements: {tcount}")

# ============================================================
# Special: Fix formula explanations (P109, P114-P116)
# ============================================================
# P109: C_total formula explanation
st(109,
    "模型表达为 C_total = C_commit + C_DA + p_challenge \u00d7 C_challenge。"
    "其中 C_commit 表示链上紧凑提交或完整负载提交成本，C_DA 表示不同数据可用性路径下的数据成本，"
    "C_challenge 表示发生争议时的挑战、恢复、重放和结算成本，p_challenge 表示争议发生概率。"
    "批处理后单笔摊销成本记为 C_amortized = C_total / batch_size。")

# P114: formula (1)
st(114, "C_total = C_commit + C_DA + p_challenge \u00d7 C_challenge    （1）")

# P115: formula (2) 
st(115, "C_amortized = C_total / batch_size    （2）")

# P116: formula explanation
st(116,
    "其中，C_commit 表示配置中的链上提交成本，C_DA 表示配置化数据发布成本，"
    "C_challenge 表示挑战、恢复、重放与结算的异常路径成本，"
    "p_challenge 表示争议发生概率。该模型用于不同数据可用性配置下的摊销比较，而非真实费用预测。")

# ============================================================
# Special: Fix experiment section introductions
# ============================================================
# P112: 7 intro
st(112,
    "实验评估不仅验证原型能否运行，还围绕结果含义组织对比分析。"
    "RQ1 关注紧凑提交是否在保留证据关联的同时隔离负载增长；"
    "RQ2 关注批处理摊销与数据可用性路径选择对摊销燃料的影响；"
    "RQ3 关注恢复机制是否改善超时场景下的挑战活性；"
    "RQ4 关注不同故障类型能否被检测、恢复或惩罚；"
    "RQ5 则关注 Solidity 合约、本地以太坊虚拟机实测与 Sepolia 部署能否支撑链上对应物。")

# ============================================================
# Save
# ============================================================
doc.save(r"E:\项目\project_code\paper_outputs\draft\final_chinese_academic_format.docx")
print("Phase 2 complete. Document saved.")
