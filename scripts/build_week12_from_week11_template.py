from __future__ import annotations

import html
import re
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[2]
PPT_DIR = ROOT / "meetings" / "weekly_reports" / "ppt"
OUT = PPT_DIR / "26春0519第十二周进度汇报-杨帆.pptx"


def latest_week11() -> Path:
    candidates = sorted(PPT_DIR.glob("*0513*.pptx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError("未找到第十一周 PPT 模板")
    return candidates[0]


def replace_shape_text(shape_xml: str, text: str) -> str:
    escaped = html.escape(text, quote=False)
    seen = False

    def repl(match: re.Match[str]) -> str:
        nonlocal seen
        open_tag = match.group(1)
        if not seen:
            seen = True
            return f"{open_tag}{escaped}</a:t>"
        return f"{open_tag}</a:t>"

    return re.sub(r"(<a:t(?:\s+[^>]*)?>)(.*?)</a:t>", repl, shape_xml, flags=re.S)


def replace_slide_shapes(xml: str, replacements: dict[int, str]) -> str:
    pattern = re.compile(r"<p:sp[\s\S]*?</p:sp>")
    parts = []
    last = 0
    for index, match in enumerate(pattern.finditer(xml), start=1):
        parts.append(xml[last : match.start()])
        block = match.group(0)
        if index in replacements:
            block = replace_shape_text(block, replacements[index])
        parts.append(block)
        last = match.end()
    parts.append(xml[last:])
    return "".join(parts)


SLIDE_TEXT: dict[int, dict[int, str]] = {
    1: {
        1: "【5/13 - 5/19】进展汇报\n【杨帆】",
    },
    2: {
        1: "主要任务【限1页】",
        3: (
            "中长期目标：研究如何在保证去中心化安全性的前提下，提高高频 DApp（如元宇宙、去中心化社交）的性能\n"
            "拟完成的任务：在第十一周完成正式实验和链上部署基础上，本周重点将实验材料整理为课程论文中的论证结构。\n"
            "本周完成的任务：\n"
            "1  将 Evaluation 从结果罗列改为 RQ1-RQ5 驱动，并补充 Setup / Metrics / Takeaway / Limitation；\n"
            "2  补充系统架构图、协议流程图和 Related Work 对照表，强化论文结构表达；\n"
            "3  根据导师反馈整理理论创新点初稿，将创新从实验数值转为问题建模、状态机、证据结构和成本模型。"
        ),
    },
    3: {
        4: "科研工作进展情况",
        5: (
            "1 Evaluation 章节重构\n"
            "第十一周已经完成正式实验规模，本周不再重复汇报实验数量，而是把已有结果重组为五个研究问题：\n"
            "RQ1 compact commit 是否降低链上提交规模；RQ2 batch size 是否降低摊销成本；RQ3 recover 是否改善 timeout 活性；RQ4 failure scenario 如何分类；RQ5 Solidity/EVM/Sepolia 是否支撑链上对应物主张。\n"
            "2 证据类型重新区分\n"
            "Python prototype / JSON ledger / simulated TEE：机制验证；DA cost model：配置化趋势；Hardhat gas：本地链上基线；Sepolia：deployability evidence。"
        ),
        6: (
            "3 论文边界补充\n"
            "在 Evaluation 和 Discussion 中明确：当前结果不能外推为真实 TEE 安全、真实 DA 网络、主网费用或生产可用性。"
        ),
    },
    4: {
        3: "科研工作进展情况",
        4: (
            "本周将上周已有成本实验结果改写为论文式表达：compact commit 约 406 bytes，基本不随 payload size 增长；"
            "full payload bytes 随 payload 增大近似线性上升。该结论用于支撑 RQ1，而不是作为新的实验规模汇报。"
        ),
        5: (
            "轻量 DA 成本模型进一步整理为：C_total = C_commit + C_DA + p_challenge × C_challenge，"
            "C_amortized = C_total / batch_size。当前 96.33% 等降本结果只表述为给定 cost model 下的趋势，不写成主网真实降本。"
        ),
    },
    5: {
        3: "科研工作进展情况",
        4: (
            "本周将 recoverable challenge 的实验结果从“成功率提升”改写为协议性质：recover 不改变 expected trace、"
            "claimed trace 或 replay mismatch，只恢复 timeout 后 challenge session 的推进能力。"
        ),
        5: (
            "失败场景被重新分为四类：normal path；detectable but not unified slashing；challenge + slashing；"
            "timeout liveness comparison。这样可以避免把“检测到异常”直接等同于“完成 slashing”。"
        ),
    },
    6: {
        4: "科研工作进展情况",
        5: (
            "论文结构补强：系统架构图与协议流程图\n"
            "新增 Hybrid TEE-Rollup 原型系统架构图，展示高频 DApp、simulated TEE、mock/verifiable DA、"
            "compact commit 与验证仲裁层之间的关系。\n"
            "新增 Recoverable Challenge 协议流程图，突出 open / respond / step / recover / replay / resolve 的状态推进。"
        ),
        6: (
            "Related Work 对照表\n"
            "已对 TEEROLLUP、Optimistic TEE-Rollups、opML、Dynamic Fraud Proof、LazyLedger、Light Clients、EIP-4844 等工作进行对照。\n"
            "当前论文定位被进一步收敛为：对 Hybrid TEE-Rollup 路线的局部机制补强，而不是提出完整生产级 Rollup 系统。"
        ),
        8: (
            "本周新增价值：把上周已经完成的实验和部署材料，转化为论文中的结构化论证、图表说明和边界表达。"
        ),
    },
    7: {
        1: "本周学习体会【限1页】",
        3: (
            "1 周报要避免重复上周内容\n"
            "第十一周已经汇报正式实验规模、本地 EVM gas 和 Sepolia 部署；本周应强调如何整理、解释和写入论文，而不是再次汇报同一组结果。\n"
            "2 实验结果和理论创新要分工\n"
            "实验回答“是否跑通、趋势如何”；理论创新回答“为什么这样建模、协议语义是什么”。\n"
            "3 论文表达必须克制\n"
            "simulated TEE、mock DA、cost model、本地 EVM、Sepolia deployability 都必须对应各自证据边界。"
        ),
    },
    8: {
        1: "下周科研计划【限1页】",
        3: (
            "1. 实验补充：fault arbitration\n"
            "继续处理 attestation_invalid、da_unavailable、da_proof_invalid 从“可检测/拒绝”到更明确仲裁路径的问题。\n"
            "2. 链上补充：Sepolia interaction\n"
            "补充 Sepolia 交互样本、源码验证重试，并进一步说明本地 EVM gas 与测试网证据的关系。\n"
            "3. 写作补充：贡献段落\n"
            "把理论创新正式嵌入 Introduction / Contribution / Discussion，并统一全文术语与过强表述。"
        ),
    },
}


def build() -> None:
    template = latest_week11()
    tmp = OUT.with_suffix(".tmp.pptx")
    shutil.copyfile(template, tmp)

    with ZipFile(tmp, "r") as zin, ZipFile(OUT, "w", ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            match = re.match(r"ppt/slides/slide(\d+)\.xml$", item.filename)
            if match:
                slide_no = int(match.group(1))
                if slide_no in SLIDE_TEXT:
                    xml = data.decode("utf-8")
                    xml = replace_slide_shapes(xml, SLIDE_TEXT[slide_no])
                    data = xml.encode("utf-8")
            zout.writestr(item, data)
    tmp.unlink(missing_ok=True)
    print(OUT)


if __name__ == "__main__":
    build()
