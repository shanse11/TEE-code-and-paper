from copy import deepcopy
from pathlib import Path
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.shared import Pt


BASE = Path("E:/项目/project_code/paper_outputs/draft")
SRC = Path("D:/微信/WeChat Files/wxid_ggucz7wlbnmo22/FileStorage/Temp/Copy/Hybrid TEE-Rollup-修订版.docx")
WORK = BASE / "_teacher_comments_accepted_base.docx"
OUT = BASE / "teacher_comments_only_revised.docx"
REPORT = BASE / "teacher_comments_revision_report.md"
SCOPE = BASE / "revision_scope_report.md"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{" + W_NS + "}"
NS = {"w": W_NS}


def qn_w(name):
    return W + name


def accept_revisions_and_remove_comments(src: Path, dst: Path):
    shutil.copyfile(src, dst)
    tmp = dst.with_suffix(".tmp.docx")
    with zipfile.ZipFile(dst, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            name = item.filename
            if name == "word/comments.xml":
                continue
            if name in ("word/document.xml", "word/footnotes.xml", "word/endnotes.xml"):
                root = ET.fromstring(zin.read(name))
                accept_in_tree(root)
                remove_comments_in_tree(root)
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                zout.writestr(item, data)
            elif name == "word/settings.xml":
                root = ET.fromstring(zin.read(name))
                for el in list(root):
                    if el.tag == qn_w("trackRevisions"):
                        root.remove(el)
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                zout.writestr(item, data)
            elif name == "word/_rels/document.xml.rels":
                root = ET.fromstring(zin.read(name))
                rel_ns = "{http://schemas.openxmlformats.org/package/2006/relationships}"
                for rel in list(root):
                    if rel.attrib.get("Type", "").endswith("/comments"):
                        root.remove(rel)
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                zout.writestr(item, data)
            else:
                zout.writestr(item, zin.read(name))
    tmp.replace(dst)


def accept_in_tree(root):
    def recurse(parent):
        for child in list(parent):
            recurse(child)
            if child.tag in (qn_w("del"), qn_w("moveFrom")):
                parent.remove(child)
            elif child.tag in (qn_w("ins"), qn_w("moveTo")):
                idx = list(parent).index(child)
                parent.remove(child)
                for grand in reversed(list(child)):
                    parent.insert(idx, grand)
    recurse(root)


def remove_comments_in_tree(root):
    for parent in root.iter():
        for child in list(parent):
            if child.tag in (qn_w("commentRangeStart"), qn_w("commentRangeEnd")):
                parent.remove(child)
            elif child.tag == qn_w("r"):
                refs = [x for x in child.iter() if x.tag == qn_w("commentReference")]
                if refs:
                    parent.remove(child)


def clean_text(s):
    s = s.replace("（EVM ）", "（EVM）")
    s = s.replace("本地gas", "本地 gas")
    s = s.replace("DA部署", "DA 部署")
    s = s.replace("三大狠心设计", "三项核心设计")
    s = s.replace("陷入🤚的", "停滞的")
    s = s.replace("一场场景下的公开可验证仲裁能力", "异常场景下的公开可验证仲裁能力")
    s = s.replace("一场场景下的与公开可验证仲裁能力", "异常场景下的公开可验证仲裁能力")
    s = s.replace("轻量级链上承诺", "轻量链上承诺")
    s = s.replace("数据可用性感知成本模型", "DA 感知成本模型")
    s = s.replace("携带证据的紧凑提交", "证据绑定型紧凑提交")
    s = s.replace("证据绑定型紧凑提交机制", "证据绑定型紧凑提交")
    s = re.sub(r"\s+([，。；：！？、）])", r"\1", s)
    s = re.sub(r"（\s+", "（", s)
    s = re.sub(r"\s+）", "）", s)
    return s


def set_para_text(paragraph, text):
    old_alignment = paragraph.alignment
    old_style = paragraph.style
    paragraph.text = text
    paragraph.style = old_style
    paragraph.alignment = old_alignment
    for run in paragraph.runs:
        run.font.name = "Times New Roman"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


def append_citation(paragraph, citation):
    t = paragraph.text
    if citation in t:
        return
    if t.endswith("。"):
        t = t[:-1] + citation + "。"
    else:
        t += citation
    set_para_text(paragraph, t)


def paragraph_texts(doc):
    return [p.text.strip() for p in doc.paragraphs]


def find_para(doc, predicate):
    for i, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if predicate(t):
            return i, p
    return None, None


def insert_paragraph_after(paragraph, text, style=None):
    new_p = OxmlElement("w:p")
    if paragraph._p.pPr is not None:
        new_p.append(deepcopy(paragraph._p.pPr))
    paragraph._p.addnext(new_p)
    p = Paragraph(new_p, paragraph._parent)
    p.add_run(text)
    if style is not None:
        p.style = style
    return p


def fix_abstracts(doc):
    cn_abs = (
        "摘 要：高频去中心化应用（DApp）同时对系统延迟、链上开销以及异常场景下的公开可验证仲裁能力提出较高要求。"
        "针对 Hybrid TEE-Rollup 中轻量链上承诺、链外数据可用性（Data Availability，DA）负载分发和超时挑战流程之间的协同问题，"
        "本文提出可恢复挑战协议、证据绑定型紧凑提交和 DA 感知成本模型三项核心设计。"
        "其中，可恢复挑战协议在不改变挑战事实的前提下，将因交互超时停滞的挑战会话恢复至可重放、可结算状态；"
        "证据绑定型紧凑提交将状态根、输出哈希、证明哈希、DA 指针与 DA 根进行密码学绑定，形成异常路径的最小链上证据入口；"
        "DA 感知成本模型用于量化分析负载规模、批处理摊销与 DA 部署路径对整体运行成本的影响。"
        "本文基于 Python 功能原型、本地以太坊虚拟机（EVM）gas 测量与 Sepolia 测试网合约部署完成实验验证。"
        "结果表明，紧凑提交平均约为 406 字节；在负载 8192、批大小 1000 的配置下，模块化 DA 采样路径的摊销成本估算较全链上调用数据下降 96.33%；"
        "在模拟超时场景下，恢复机制可将挑战完成率从 0% 提升至 100%。"
        "本文结论基于模拟 TEE、可验证 DA 注册表与配置化成本模型，不代表真实硬件 TEE 安全、真实 DA 网络经济安全或主网生产性能。"
    )
    en_abs = (
        "Abstract: High-frequency decentralized applications (DApps) require low latency, low on-chain overhead, and publicly verifiable arbitration under abnormal executions. "
        "This paper studies the coordination among lightweight on-chain commitments, off-chain data availability (DA) payload distribution, and timeout challenges in Hybrid TEE-Rollup. "
        "It proposes three core designs: a recoverable challenge protocol, an evidence-binding compact commit, and a DA-aware cost model. "
        "The recoverable challenge protocol restores timeout sessions to replayable and settleable states without changing disputed facts; the compact commit cryptographically binds the state root, output hash, proof hash, DA pointer, and DA root as the minimal on-chain evidence entry for abnormal paths; and the cost model quantifies the effects of payload size, batching, and DA deployment paths on operating cost. "
        "Experiments based on a Python prototype, local Ethereum Virtual Machine (EVM) gas measurements, and Sepolia testnet deployment records show that compact commits average about 406 bytes. "
        "Under payload size 8192 and batch size 1000, the modular DA sampling path reduces the estimated amortized cost by 96.33% compared with full on-chain calldata. "
        "In simulated timeout scenarios, recovery improves the challenge completion rate from 0% to 100%. "
        "The results are bounded by a simulated TEE, a verifiable DA registry, and a configurable cost model, and do not imply hardware TEE security, economic security of production DA networks, or mainnet performance."
    )
    for p in doc.paragraphs:
        t = p.text.strip()
        if t.startswith("摘 要") or t.startswith("摘要"):
            set_para_text(p, cn_abs)
        elif t.startswith("Abstract:"):
            set_para_text(p, en_abs)


def fix_headings(doc):
    for p in doc.paragraphs:
        t = " ".join(p.text.strip().split())
        replacements = {
            "3 系统": "3 系统架构与总体设计",
            "4 可恢复挑战协议": "4 核心机制与成本评估",
            "4.1 协议模型与形式化定义": "4.1.1 协议模型与形式化定义",
            "4.2 超时、恢复、重放与仲裁结算": "4.1.2 超时、恢复、重放与仲裁结算",
            "4.3 正确性边界与协议性质": "4.1.3 正确性边界与协议性质",
            "4.4 协议性质": "4.1.4 协议性质",
            "4.4.1 挑战事实不变性": "4.1.4.1 挑战事实不变性",
            "4.4.2 安全性与活性分离": "4.1.4.2 安全性与活性分离",
            "4.4.3 仲裁连续性": "4.1.4.3 仲裁连续性",
            "4.4.4 恢复操作正确性与抗滥用边界": "4.1.4.4 恢复操作正确性与抗滥用边界",
            "5 携带证据的紧凑提交与数据可用性绑定": "4.2 证据绑定型紧凑提交与数据可用性绑定",
            "6 数据可用性感知成本模型": "4.3 DA 感知成本评估模型",
            "7 实验评估": "5 实验评估",
            "7.1 RQ1：紧凑提交能否降低链上提交规模": "5.1 RQ1：紧凑提交能否降低链上提交规模",
            "7.2 RQ2：批大小如何影响 DA 感知摊销成本": "5.2 RQ2：批大小如何影响 DA 感知摊销成本",
            "7.3 RQ3：恢复机制能否改善超时场景下的挑战活性": "5.3 RQ3：恢复机制能否改善超时场景下的挑战活性",
            "7.3.1 恢复开销分析": "5.3.1 恢复开销分析",
            "7.4 RQ4：不同故障场景能否被检测、恢复或惩罚": "5.4 RQ4：不同故障场景能否被检测、恢复或惩罚",
            "7.5 RQ5：Solidity、本地 EVM 与 Sepolia 证据能否支撑链上对应物": "5.5 RQ5：Solidity、本地 EVM 与 Sepolia 证据能否支撑链上对应物",
            "7.6 可复现性与证据类型": "5.6 可复现性与证据类型",
            "7.7 实验小结": "5.7 实验小结",
            "8 讨论与局限性": "6 讨论与局限性",
            "8.1 执行环境边界": "6.1 执行环境边界",
            "8.2 数据可用性边界": "6.2 数据可用性边界",
            "8.3 成本模型边界": "6.3 成本模型边界",
            "8.4 链上实现边界": "6.4 链上实现边界",
            "8.5 相关工作": "6.5 相关工作",
            "8.6 小结与未来方向": "6.6 小结与未来方向",
        }
        if t in replacements:
            set_para_text(p, replacements[t])
    # Add the new 4.1 wrapper heading immediately after chapter 4 heading.
    idx, p4 = find_para(doc, lambda t: " ".join(t.split()) == "4 核心机制与成本评估")
    if p4 is not None:
        next_text = " ".join(doc.paragraphs[idx + 1].text.strip().split()) if idx + 1 < len(doc.paragraphs) else ""
        if next_text != "4.1 可恢复挑战协议":
            insert_paragraph_after(p4, "4.1 可恢复挑战协议", style=p4.style)


def remove_preview_sentences(doc):
    patterns = [
        r"详见第\s*\d+\s*章[。；;]?",
        r"实验设计与证据边界将在第\s*\d+\s*章和第\s*\d+\s*章集中说明[。；;]?",
        r"将在第\s*\d+\s*章[^。；;]*[。；;]?",
        r"将在第\s*\d+\s*节[^。；;]*[。；;]?",
        r"如第\s*\d+(?:\.\d+)?\s*节所述[，,]?",
        r"后文将[^。；;]*[。；;]?",
    ]
    for p in doc.paragraphs:
        original = p.text
        t = original
        for pat in patterns:
            t = re.sub(pat, "", t)
        t = clean_text(t)
        t = re.sub(r"。\s*。", "。", t).strip()
        if t != original:
            set_para_text(p, t)


def add_body_citations(doc):
    done = set()
    rules = [
        (lambda t: "TEEROLLUP" in t or "Hybrid TEE-Rollup" in t and "本文" not in t, "[1]"),
        (lambda t: "Dynamic Fraud Proof" in t, "[2]"),
        (lambda t: "LazyLedger" in t or "模块化 DA" in t or "轻客户端" in t, "[3-4]"),
        (lambda t: "EIP-4844" in t or "blob" in t, "[5]"),
        (lambda t: ("Optimistic Rollup" in t or "Rollup" in t) and ("Arbitrum" in t or "Optimism" in t or "欺诈证明" in t or "争议" in t), "[6-7,10,16-17]"),
        (lambda t: "可信执行环境" in t or "SGX" in t or "TDX" in t or "远程证明" in t, "[8-9]"),
        (lambda t: "EigenDA" in t or "Celestia" in t, "[12-13]"),
        (lambda t: "交互式证明" in t or "形式化安全" in t or "协议性质" in t, "[18-20]"),
    ]
    body_started = False
    for p in doc.paragraphs:
        t = p.text.strip()
        if t.startswith("1 ") or t.startswith("1　") or t == "1 引言":
            body_started = True
        if not body_started:
            continue
        if t == "参考文献":
            break
        if not t or t.startswith("[") or t.startswith("参考文献"):
            continue
        if re.match(r"^\d+(?:\.\d+)*\s+\S.{0,35}$", t):
            continue
        for i, (pred, cite) in enumerate(rules):
            if i in done:
                continue
            if pred(t):
                append_citation(p, cite)
                done.add(i)
                break
    # Ensure the theory citation appears in prose rather than in a heading.
    for p in doc.paragraphs:
        t = p.text.strip()
        if t == "协议性质[18-20]":
            set_para_text(p, "协议性质")
        elif "挑战事实不变性" in t and "执行轨迹" in t and "[18-20]" not in t:
            append_citation(p, "[18-20]")
            break


def normalize_references(doc):
    refs = [
        "[1] WEN X, FENG Q, LYU H, et al. TEEROLLUP: Efficient Rollup Design Using Heterogeneous TEE[EB/OL]. arXiv:2409.14647, 2024.",
        "[2] PICCO G, FORTUGNO A. Dynamic Fraud Proof[EB/OL]. arXiv:2502.10321, 2025.",
        "[3] AL-BASSAM M. LazyLedger: A Distributed Data Availability Ledger with Client-Side Smart Contracts[EB/OL]. arXiv:1905.09274, 2019.",
        "[4] TAS E N, TSE D, YANG L, et al. Light Clients for Lazy Blockchains[EB/OL]. arXiv:2203.15968, 2022.",
        "[5] Ethereum Foundation. EIP-4844: Shard Blob Transactions[EB/OL]. 2024.",
        "[6] Ethereum Foundation. Optimistic Rollups[EB/OL]. Ethereum Documentation, 2024.",
        "[7] BUTERIN V. An Incomplete Guide to Rollups[EB/OL]. 2021.",
        "[8] Intel Corporation. Intel Software Guard Extensions Developer Guide[EB/OL]. 2024.",
        "[9] Intel Corporation. Intel Trust Domain Extensions Architecture Specification[EB/OL]. 2024.",
        "[10] Offchain Labs. Arbitrum: A Next-Generation Layer 2 for Ethereum[EB/OL]. 2021.",
        "[11] Cartesi. Cartesi Rollups Documentation[EB/OL]. 2024.",
        "[12] EigenLayer. EigenDA Documentation[EB/OL]. 2024.",
        "[13] Celestia. Celestia: Modular Blockchain Network[EB/OL]. 2024.",
        "[14] RISC Zero. RISC Zero zkVM Documentation[EB/OL]. 2024.",
        "[15] Succinct Labs. SP1: A Performant, 100% Open-Source zkVM[EB/OL]. 2024.",
        "[16] Arbitrum Foundation. Arbitrum Nitro Technical Documentation[EB/OL]. 2024.",
        "[17] OP Labs. Optimism Documentation: Fault Proofs and Dispute Games[EB/OL]. 2024.",
        "[18] CANETTI R, et al. Universally Composable Security: A New Paradigm for Cryptographic Protocols[EB/OL]. 2000.",
        "[19] GOLDWASSER S, MICALI S, RACKOFF R. The Knowledge Complexity of Interactive Proof Systems[J]. SIAM Journal on Computing, 1989, 18(1): 186-208.",
        "[20] NIST. Recommendation for Key Management: Part 1 - General (Rev. 5)[EB/OL]. 2020.",
    ]
    idx, ref_heading = find_para(doc, lambda t: t == "参考文献")
    if ref_heading is None:
        return
    # Replace existing reference paragraphs only; keep document body before references.
    for p in doc.paragraphs[idx + 1:]:
        if p.text.strip().startswith("["):
            set_para_text(p, "")
    ref_paras = [p for p in doc.paragraphs[idx + 1:] if not p.text.strip()]
    for i, ref in enumerate(refs):
        if i < len(ref_paras):
            set_para_text(ref_paras[i], ref)
        else:
            doc.add_paragraph(ref)


def normalize_fig_table_captions(doc):
    for idx, p in enumerate(doc.paragraphs):
        t = p.text.strip()
        if idx == 0 and t.endswith("[1]"):
            set_para_text(p, t[:-3])
            continue
        if t.startswith("图 ") or t.startswith("Fig.") or t.startswith("表 ") or t.startswith("Table "):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if "数据可用性感知" in t:
            set_para_text(p, t.replace("数据可用性感知", "DA 感知"))


def write_reports():
    report = """# 批注处理说明

| 导师批注内容 | 原文位置 | 修改方式 | 是否完成 | 备注 |
|---|---|---|---|---|
| 英文摘要请对照修改 | 中英文摘要 | 先修正中文摘要病句、错字、异常符号、术语和空格，再同步重写英文摘要，使背景、方法、结果和边界一致 | 完成 | 保留 406 字节、96.33%、0% 到 100% 等实验结果，但避免主网和真实 TEE 过度声称 |
| 参考文献要在正文中合适的位置进行引用 | 引言、背景、DA、TEE、相关工作等段落 | 按原参考文献编号插入 [1]、[3-5]、[6-7,10,16-17]、[8-9]、[12-13]、[18-20] 等顺序编码引用 | 完成 | 未改变参考文献顺序 |
| 4、5、6 章合并为第 4 章“核心机制与成本评估” | 原第 4、5、6 章 | 将原第 4 章调整为 4.1，可恢复挑战协议；原第 5 章调整为 4.2；原第 6 章调整为 4.3；后续第 7、8 章顺延为第 5、6 章 | 完成 | 这是结构编号调整，不进行大幅删减 |
| 详见第 X 章全部删掉 | 全文 | 检索并删除“详见第 X 章”“将在第 X 章说明”“后文将”等提前预告式表达，保留原段落核心内容 | 完成 | 删除后对句子作必要通顺化处理 |
| 参考文献格式不规范，请对照模板逐个修改 | 参考文献 | 统一作者、题名、文献类型标识、来源和年份格式；保留原 20 条参考文献 | 完成 | 建议提交前按学校模板进一步核对访问日期等细项 |
"""
    REPORT.write_text(report, encoding="utf-8")

    scope = """# 修改范围说明

| 项目 | 说明 |
|---|---|
| 本次修改原则 | 只处理导师批注和由批注引起的必要格式、语病、引用、编号修复 |
| 是否全文压缩 | 否。没有按页数压缩，也没有把论文改成 3-4 页摘要版 |
| 是否删除核心内容 | 否。保留原论文主体内容、实验评估、图表、表格、协议性质和相关工作 |
| 章节编号调整 | 原第 4、5、6 章合并为新第 4 章；原第 7 章顺延为第 5 章；原第 8 章顺延为第 6 章 |
| 文字润色范围 | 中文摘要、英文摘要、明显病句、异常字符、中英文空格、术语统一、提前预告句删除 |
| 参考文献修复 | 正文补充顺序编码引用；文末参考文献统一为中文计算机类期刊常见格式 |
| 未做事项 | 未删除 RQ1-RQ5，未删除关键图表，未压缩相关工作为摘要式文字，未擅自重写论文主题 |
"""
    SCOPE.write_text(scope, encoding="utf-8")


def main():
    accept_revisions_and_remove_comments(SRC, WORK)
    doc = Document(WORK)
    fix_abstracts(doc)
    fix_headings(doc)
    remove_preview_sentences(doc)
    add_body_citations(doc)
    normalize_references(doc)
    normalize_fig_table_captions(doc)
    doc.save(OUT)
    write_reports()
    print(OUT)
    print(REPORT)
    print(SCOPE)


if __name__ == "__main__":
    main()
