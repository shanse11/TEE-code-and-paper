# -*- coding: utf-8 -*-
"""第二轮：理论强化后的中文化精修。"""
from docx import Document
from docx.shared import Pt
import re

SRC = r"E:\项目\project_code\paper_outputs\draft\final_chinese_academic_format.docx"
doc = Document(SRC)

# ═══════════════════════════════════════════════════════════════
# Phase 1: Rewrite entire 4.4 section with compressed, polished content
# ═══════════════════════════════════════════════════════════════

# ----- P73: 4.4 intro -----
doc.paragraphs[73].text = (
    "前述讨论已将可恢复挑战机制的核心性质从"超时后可以重试"这一工程事实提升为协议层面的状态转移机制。"
    "本节进一步将这一认识系统化为挑战事实不变性、安全性与活性的分离、仲裁连续性和恢复操作正确性四项性质，"
    "并给出协议不变量表格，以明确恢复机制的协议语义边界。"
)

# ----- P74: (一) heading = fine -----

# ----- P75: 挑战事实不变性 intro -----
doc.paragraphs[75].text = (
    "挑战会话在创建时便将一组不可修改的协议事实绑定在会话上下文中，"
    "这些事实构成争议的"内容面"，包括："
)

# ----- P76: bullet list -----
doc.paragraphs[76].text = (
    "• 状态根（State Root）：约束输入与输出哈希的绑定关系；"
    "\n• 数据可用性根（DA Merkle Root）：约束 DA 层中完整负载的字段级承诺；"
    "\n• 负载哈希（Payload Hash）：标识 DA 层中完整的原始负载；"
    "\n• 执行轨迹（Execution Trace）：挑战方与被挑战方各自提交的执行步骤序列；"
    "\n• 重放证据（Replay Evidence）：二分缩小后定位到的目标步骤与对应的预期哈希和声明哈希；"
    "\n• 不一致证据（Mismatch Evidence）：验证、响应和 DA 字段检查中观测到的字段级不一致记录。"
)

# ----- P77: formal expression -----
doc.paragraphs[77].text = (
    "记挑战会话 cs 的挑战事实集合为 Facts(cs)，则恢复操作满足 "
    "Facts(cs_before) = Facts(cs_after)，即恢复不向挑战会话注入新的状态根、负载哈希、执行轨迹或重放证据。"
)

# ----- P78: implication -----
doc.paragraphs[78].text = (
    "恢复操作恢复的是流程推进能力，而非修改争议内容本身。"
    "在不可恢复的挑战协议中，超时会使会话不可逆地停滞，已观测到的异常无法进入重放与仲裁。"
    "可恢复挑战机制将检测与处理之间的鸿沟打通，同时保证处理过程不脱离原始检测事实。"
)

# ----- P79: (二) heading - rename to 安全性与活性的分离 -----
doc.paragraphs[79].text = "（二）安全性与活性的分离"

# ----- P80: replace intro question with substantive content -----
doc.paragraphs[80].text = (
    "恢复机制设计中的一个关键考量是安全性与活性的边界划分。"
    "恢复操作解决的是活性问题——当挑战会话因交互超时而停滞时，恢复使其重新获得推进能力；"
    "但它不直接改变正确性判断——一个原本错误的执行结果不会因恢复而变为正确。"
)

# ----- P81: merged safety+liveness content -----
doc.paragraphs[81].text = (
    "从安全性角度看，恢复操作受到以下约束："
    "\n\n第一，恢复后的重放阶段仍对预期哈希与声明哈希进行一致性检查，"
    "两者不一致时挑战成功。恢复仅改变流程推进者，不改变正确性标准。"
    "\n\n第二，恢复不修改重放证据中的目标步骤，"
    "二分缩小定位到的争议点在恢复前后保持不变，"
    "恢复不能将失败的预期哈希替换为通过的预期哈希。"
    "\n\n第三，恢复不修改负载承诺。紧凑提交中的 DA Merkle 根和 DA 指针在提交时已锁定，"
    "恢复无法将指针重新指向其他 DA 条目或修改负载哈希。"
)

# ----- P82: replaced toxicity claim with arbitration continuity def -----
# Move the original (三) heading's content here: merge safety summary + start of arbitration continuity
doc.paragraphs[82].text = (
    "总结构成安全性的判断：恢复机制恢复的是协议活性，而非重新定义正确性。"
    "正确性的最终裁决由重放阶段完成，恢复只保证该裁决环节能够被执行。"
)

# ----- P83: (三) heading - already "活性分析：仲裁连续性" -----
doc.paragraphs[83].text = "（三）仲裁连续性"

# ----- P84: more rigorous definition -----
doc.paragraphs[84].text = (
    "仲裁连续性（Arbitration Continuity）是本文提出的用于刻画挑战协议活性性质的概念："
    "在挑战事实已经固定、重放证据可获得且数据可用性证明可检查的条件下，"
    "若争议已经被检测到，则协议应保证该争议不会因交互超时永久停滞，"
    "而能够继续推进至重放、结算或惩罚阶段。本文将满足这一性质的协议称为具备仲裁连续性。"
)

# ----- P85: comparison with traditional -----
doc.paragraphs[85].text = (
    "传统基于超时的挑战协议可以完成异常检测——验证者观测到 DA 不一致、响应不匹配或证明无效后，"
    "能够将异常记录为争议。然而，当挑战方或被挑战方在交互中超时未响应时，"
    "争议可能永久停留在中间状态，交易既不能最终确认也不能被罚没。"
    "这就是检测性与完成性的差异：传统方案关注"能否发现异常"，"
    "仲裁连续性关注"已发现的异常能否被处理完毕"。"
    "对于高频去中心化应用，未完成的挑战会话会占用状态、延迟结算，"
    "使链上对象长期处于不确定状态，直接损害结算确定性。"
)

# ----- P86: result -----
doc.paragraphs[86].text = (
    "可恢复挑战机制通过恢复函数在超时后恢复仲裁流程推进能力："
    "监督节点调用恢复功能使超时会话回到可推进状态，从而继续二分缩小、重放和结算。"
    "实验部分（第 7.3 节）在合成超时场景下验证了恢复路径的效果——"
    "在当前原型设定下，恢复机制能够将超时停滞转化为可继续推进的仲裁流程。"
    "上述协议性质的实验验证通过超时场景下不可恢复与可恢复两条路径的对比进行。"
)

# ----- P87: (四) heading - merge 恢复操作正确性 + 抗滥用 -----
doc.paragraphs[87].text = "（四）恢复操作正确性与抗滥用边界"

# ----- P88: merged intro -----
doc.paragraphs[88].text = (
    "恢复操作的协议安全性可以从两个角度考察：操作本身的正确性边界，"
    "以及恶意节点是否可能通过滥用恢复来破坏协议。两者可合并分析。"
)

# ----- P89: allowed modifications -----
doc.paragraphs[89].text = (
    "恢复操作允许修改的状态：超时计时器、会话推进状态标记和交互窗口。"
    "这些字段属于活性层，它们的修改使停滞会话重新获得推进能力。"
)

# ----- P90: disallowed modifications -----
doc.paragraphs[90].text = (
    "恢复操作不允许修改的状态：重放证据（预期哈希、声明哈希和目标步骤）、"
    "执行轨迹承诺（二分缩小区间信息）、负载绑定（DA 指针与 DA Merkle 根）和数据可用性证明（Merkle 证明路径）。"
    "这些字段属于正确性层，恢复操作不能越过此边界。"
)

# ----- P91: merged correctness + anti-abuse conclusion -----
doc.paragraphs[91].text = (
    "因此，恢复操作无法将错误执行伪装为正确执行。"
    "从抗滥用角度看，恢复机制之所以具有这一性质，根本原因在于："
    "恢复操作只能作用于已经链上承诺的挑战会话，而这些会话的挑战事实在创建时即已锁定。"
    "恢复操作恢复了协议活性，但不会为恶意节点提供修改协议正确性判断依据的途径。"
    "具体而言：恶意节点无法通过恢复重写不一致证据，因为恢复前后证据集合保持不变；"
    "无法在恢复后注入新的执行轨迹，因为二分缩小区间信息不被重置；"
    "无法通过反复超时和恢复发起资源耗尽攻击而不付出成本，"
    "因为每次恢复需要在链上执行（本地 EVM 实测约 156,891 gas）；"
    "也无法绕过重放阶段的正确性判断，因为重放对预期哈希与声明哈希的比较是确定性的。"
    "\n\n需要指出，当前研究原型尚未实现恢复频率限制机制，"
    "因此资源耗尽防护的完整方案属于后续工作。"
)

# ----- P92: 协议不变量 heading — keep -----
doc.paragraphs[92].text = "协议不变量与保持性质"

# ----- P93: fix table reference -----
doc.paragraphs[93].text = (
    "表 3 汇总了本文协议设计所依赖的核心不变量及其在恢复操作下的保持方式。"
    "这些不变量界定了恢复机制的安全边界：恢复操作被限制在活性状态空间内，"
    "不能跨越到正确性状态空间。"
)

# ----- P94: after-table text — merge into P93 or remove -----
# P94 is the paragraph after the table. Make it a bridge to experiments.
doc.paragraphs[94].text = (
    "上述协议性质在实验部分（第 7.3 节）通过超时场景下不可恢复与可恢复两条路径的对比进行验证，"
    "重点考察超时后争议是否仍能推进至重放与结算。"
)

# ----- P95: 抗滥用分析 heading — REMOVE (merged into (四)) -----
doc.paragraphs[95].text = ""

# ----- P96-P101: anti-abuse paragraphs — CLEAR (merged into P91) -----
for idx in [96, 97, 98, 99, 100, 101]:
    doc.paragraphs[idx].text = ""

# ═══════════════════════════════════════════════════════════════
# Phase 2: Fix table numbering in text references
# ═══════════════════════════════════════════════════════════════

def shift_table_refs(text):
    """Shift all 表 X references from X>=3 to X+1."""
    # Don't touch 表 1, 表 2, 表 2-A
    # Shift 表 3→表 4, 表 4→表 5, ..., 表 10→表 11
    # Handle "表 N（原表 M）" artifacts too
    text = re.sub(r'表\s*2-A', '表 3', text)
    # Remove "(原表 X)" artifacts
    text = re.sub(r'（原表\s*\d+）', '', text)
    return text

for i, para in enumerate(doc.paragraphs):
    old_text = para.text
    new_text = shift_table_refs(old_text)
    if new_text != old_text:
        para.text = new_text

# ═══════════════════════════════════════════════════════════════
# Phase 3: Fix over-strong claims and terminology
# ═══════════════════════════════════════════════════════════════

# Fix P136: over-strong claim about 100%
doc.paragraphs[136].text = (
    "二分定位行为与理论对数趋势一致，但更关键的是不可恢复与可恢复路径的对比。"
    "在超时不可恢复场景中，检测率达到 100%，但挑战成功率和罚没比例均为 0%，"
    "即会话已被识别为异常，却未完成仲裁。"
    "在超时可恢复场景中，在当前原型合成负载下，检测、恢复、挑战成功和罚没均可达到 100%。"
    "该对比说明，超时检测本身并不等价于协议推进。"
)

# Fix P137: "监管者或运营者" in P99
doc.paragraphs[99].text = ""

# Fix P66: "watchdog/operator" → more neutral
p66_text = doc.paragraphs[66].text
p66_text = p66_text.replace("watchdog/operator", "监督节点（watchdog）")
doc.paragraphs[66].text = p66_text

# Fix P67: same
p67_text = doc.paragraphs[67].text
p67_text = p67_text.replace("watchdog 或 operator", "监督节点")
doc.paragraphs[67].text = p67_text

# Fix P13: unify terminology
p13_text = doc.paragraphs[13].text
p13_text = p13_text.replace("超时", "超时")
p13_text = p13_text.replace("工程恢复", "普通的工程恢复")
doc.paragraphs[13].text = p13_text

# ═══════════════════════════════════════════════════════════════
# Phase 4: Add cross-references 7.3 ↔ 4.4
# ═══════════════════════════════════════════════════════════════

# P134: add reference to 4.4
p134_text = doc.paragraphs[134].text
if "第 4.4 节" not in p134_text:
    p134_text = p134_text.replace(
        "关键问题是：",
        "该实验对应第 4.4 节定义的仲裁连续性，关键问题是："
    )
    doc.paragraphs[134].text = p134_text

# ═══════════════════════════════════════════════════════════════
# Phase 5: Fix invariants table content (more Chinese)
# ═══════════════════════════════════════════════════════════════

# Table index 2 is the invariants table
table = doc.tables[2]
# Update header
table.cell(0, 2).text = "恢复操作下的保持方式"

# Update data rows
row0_cells = table.rows[1].cells
row0_cells[1].text = "状态根、DA 根、负载哈希、执行轨迹、重放证据和不一致证据在会话生命周期内不可修改"

row1_cells = table.rows[2].cells
row1_cells[1].text = "重放阶段对预期哈希与声明哈希的一致性检查是裁决正确性的唯一依据"
row1_cells[2].text = "恢复操作不修改预期哈希、声明哈希和目标步骤"

row2_cells = table.rows[3].cells
row2_cells[2].text = "恢复操作是保持仲裁连续性的核心机制；将超时停滞会话恢复至可推进状态"

row3_cells = table.rows[4].cells
row3_cells[1].text = "紧凑提交中的 DA Merkle 根约束 DA 条目的字段级内容"
row3_cells[2].text = "恢复操作不修改 DA 指针或 DA Merkle 根"

row4_cells = table.rows[5].cells
row4_cells[2].text = "恢复操作不重置或重写区间信息"

# ═══════════════════════════════════════════════════════════════
# Phase 6: Clean up P140 "原表" artifact and fix text references
# ═══════════════════════════════════════════════════════════════

# Now table numbering shifted: 表 3→表 4, etc.
# P140 originally said "表 4（原表 3）" → now should just say "表 5"
# Since shift_table_refs already ran, "表 4" became "表 4" (unchanged for < 3)
# Wait - shift_table_refs only shifts 3→4, 4→5, etc. 
# But in the original text, "表 4（原表 3）" would become: 表 4 → 表 5 (shifted), but "原表 3" was already removed.
# Actually the shift pattern is wrong. Let me fix this more carefully.

# The original table numbers (before this round of editing) were:
# 表 1 (mechanism), 表 2 (comparison), 表 2-A (invariants) → now 表 3
# Old 表 3 (failure taxonomy) → now 表 4
# Old 表 4 (gas) → now 表 5
# Old 表 5 (Sepolia) → now 表 6
# Old 表 6 (timeout) → now 表 7
# ... etc. up to 表 10 → 表 11

# The shift_table_refs already changed 表 2-A → 表 3 and removed (原表 X)
# But the text references like "表 3" in P155 and P140 now need to be 表 4, etc.
# Actually wait - the current document text already has old table numbers.
# After "表 2-A" → "表 3", we need to shift all existing "表 3" through "表 10" by +1.

# Let me redo this more carefully.
# First, let me understand: shift_table_refs runs on ALL paragraphs.
# It replaces 表 2-A → 表 3, then removes (原表 X).
# But it doesn't shift 表 3→表 4 etc. because my regex was tailored for something else.

# Let me fix the existing reference numbers now.
# The current doc has references: 表 3, 表 4, 表 5, ... 表 10
# After inserting 表 3 (invariants), these need to become: 表 4, 表 5, 表 6, ... 表 11

# But my shift_table_refs function only replaced 表 2-A and removed (原表 X).
# The actual shifting needs to happen for all paragraphs.

# Let me do this properly now.

print("Phase 1-5 done. Now fixing all table references...")
doc.save(SRC)
print("Intermediate save done.")
