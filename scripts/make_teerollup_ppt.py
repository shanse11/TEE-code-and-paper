import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
ET.register_namespace("a", A_NS)
ET.register_namespace("p", P_NS)
ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")

NS = {"p": P_NS, "a": A_NS}


SLIDE_TEXTS = {
    1: {
        1: "TEEROLLUP: 利用异构 TEE 的高效 Rollup 设计",
        2: "Xiaoqing Wen, Quanbi Feng, Hanzheng Lyu, Jianyu Niu, Yinqian Zhang, Chen Feng\narXiv: 2409.14647",
        3: "组会汇报",
    },
    2: {
        1: "研究背景",
        2: "Rollup 通过把交易执行移到链下，缓解主链吞吐和 gas 压力\n"
           "ZK-rollup 安全性强，但证明生成和链上验证成本高\n"
           "OP-rollup 成本更低，但提现需要等待挑战期，通常长达一周\n"
           "论文目标：同时拿到低成本和短提现延迟",
    },
    3: {
        1: "现有方案痛点",
        2: "ZK-rollup：验证贵，工程复杂，EVM 兼容性和开发成本都高\n"
           "OP-rollup：正常交易便宜，但用户资金退出很慢\n"
           "单 TEE 方案：一旦 TEE 被攻破或宿主阻断 I/O，安全性和可用性都出问题\n"
           "作者的问题意识：TEE 能不能用，但不能把 TEE 当成绝对可信",
    },
    4: {
        1: "论文核心想法",
        2: "用 TEE 承担链下执行，减少主链验证工作量\n"
           "不用单个 TEE，而是用异构 TEE 组成 sequencer 委员会\n"
           "每次状态更新都需要至少 f+1 个 TEE 签名，抵抗部分 TEE 被攻破\n"
           "把完整元数据交给 DAP 存，主链只存状态摘要和必要哈希\n"
           "当 sequencer 不可用时，用户可发起 challenge 并在主链结算",
        3: "一句话：用 TEE 降低成本，用“异构多 TEE + challenge + DAP 激励”补齐安全与可用性",
    },
    5: {
        1: "系统设计",
    },
    6: {
        1: "系统架构",
        2: "四个核心角色：TSC、MSC、Sequencer Committee、DAP\n"
           "TSC：记录 rollup 状态摘要，处理 challenge 与结算\n"
           "MSC：注册和管理各个 TEE，对 QC 做认证\n"
           "Sequencer：在 TEE 中执行交易、广播状态、收集签名并上链\n"
           "DAP：离线保存账户树和交易列表，为结算提供证明",
    },
    7: {
        1: "威胁模型与目标",
        2: "作者明确不假设 TEE 完全可信：最多 f 个 TEE 可能被攻破\n"
           "恶意宿主可以暂停、重启、丢弃或篡改 TEE 的 I/O，破坏可用性\n"
           "所有 sequencer 都可能 Byzantine，DAP 被视为 rational\n"
           "系统只追求两个核心性质：Correctness 和 Redeemability",
    },
    8: {
        1: "正常流程",
        2: "Issue：用户先在主链存款，rollup 给用户铸造 TTokens\n"
           "Transfer：sequencer 在 TEE 内批处理交易，生成新状态并收集 QC\n"
           "Redeem：用户在 rollup 销毁 TTokens，主链据此退款\n"
           "主链接受状态更新的条件：高度连续、前态哈希匹配、QC 验证通过",
    },
    9: {
        1: "如果用户交易长时间未被处理，可以把交易提交到 TSC 发起 challenge\n"
           "若 sequencer 在等待窗口内返回 QC，说明交易已被真实处理，challenge 结束\n"
           "若一直无人响应，rollup 会进入 frozen settlement，用户可直接在主链提款\n"
           "这个设计是 redeemability 的关键兜底：系统挂掉也不能把用户钱锁死",
        2: "Challenge 机制",
    },
    10: {
        1: "DAP 与惰性惩罚",
        2: "主链只保存状态摘要，完整元数据由 DAP 离线存储\n"
           "用户结算时，需要 DAP 给出账户余额和对应的 Merkle proof\n"
           "DAP 进入系统前要先抵押 collateral\n"
           "若随机抽查时未按时返回有效数据，就会被 slash，避免“假装存数据”",
    },
    11: {
        1: "实验设置",
        2: "实现：Golang 原型 + Solidity 0.8，部署在 Sepolia\n"
           "TEE 平台：Intel SGX、Intel TDX、Hygon CSV\n"
           "规模：最多 20 个 sequencer，异构比例约为 1:2:2\n"
           "指标：on-chain cost、throughput、latency，以及 TEE 带来的额外开销",
    },
    12: {
        1: "UPDATESTATE 最贵：约 156K gas，约 10.16 美元\n"
           "但作者按 batch size = 2000 做均摊后，单笔只要约 78 gas\n"
           "普通交易单笔费用约 0.005 到 0.006 美元\n"
           "challenge-resolve 和 settle-withdraw 只在异常场景触发",
        2: "156K gas\nUPDATESTATE",
        3: "$0.006 / tx\n2000 笔均摊",
        4: "关键结果：链上成本",
    },
    13: {
        1: "与公开数据对比：StarkNet 平均约 0.043 美元/笔，Scroll 约 0.114 美元/笔\n"
           "TEEROLLUP 约 0.006 美元/笔，相比 StarkNet 降低约 86%\n"
           "费用量级已经接近 Optimism 和 Arbitrum\n"
           "正常提现延迟仍是几分钟，而不是 OP-rollup 常见的一周",
        2: "关键结果：与现有 Rollup 对比",
    },
    14: {
        1: "LAN 场景下，5 个 sequencer、batch = 2000 时吞吐可达约 28 KTPS\n"
           "WAN 场景吞吐下降、延迟上升，但链下处理能力仍超过 5000 TPS\n"
           "引入 TEE 后，在 WAN + 20 节点场景中吞吐下降 15.74%，延迟上升 20.17%\n"
           "结论：TEE 的确带来额外开销，但仍在可接受范围内",
        2: "补充：论文测到的是 rollup 链下处理能力，最终整体吞吐仍受主链约束",
        3: "关键结果：吞吐与延迟",
    },
    15: {
        1: "本文创新点",
        2: "不把 TEE 当成绝对可信单点，而是改成异构多 TEE 委员会\n"
           "把可用性问题显式纳入设计，用 challenge 保证 redeemability\n"
           "引入 DAP + laziness penalty，降低链上存储成本\n"
           "性能上实现了“成本接近 OP-rollup，提现时间接近 ZK-rollup”的折中",
    },
    16: {
        1: "局限性与我的思考",
        2: "安全性依赖异构 TEE 不会被大规模同时攻破，这个假设仍偏工程化\n"
           "DAP 被视为 rational，但真实开放环境中的激励稳定性还需要进一步验证\n"
           "用户结算仍依赖 DAP 提供证明，数据可得性并非完全 trustless\n"
           "实验是测试网原型，离真实生产环境还有实现和运维层面的距离",
    },
    17: {
        1: "THANKS\nQ&A",
    },
}


def set_shape_text(shape, text):
    tx_body = shape.find("p:txBody", NS)
    if tx_body is None:
        return

    body_pr = tx_body.find("a:bodyPr", NS)
    lst_style = tx_body.find("a:lstStyle", NS)
    for para in list(tx_body.findall("a:p", NS)):
        tx_body.remove(para)

    if text is None:
        text = ""

    lines = text.split("\n") if text else [""]
    for line in lines:
        para = ET.SubElement(tx_body, f"{{{A_NS}}}p")
        run = ET.SubElement(para, f"{{{A_NS}}}r")
        rpr = ET.SubElement(run, f"{{{A_NS}}}rPr")
        rpr.set("lang", "zh-CN")
        t = ET.SubElement(run, f"{{{A_NS}}}t")
        t.text = line
        ET.SubElement(para, f"{{{A_NS}}}endParaRPr").set("lang", "zh-CN")

    if body_pr is not None and tx_body.find("a:bodyPr", NS) is None:
        tx_body.insert(0, body_pr)
    if lst_style is not None and tx_body.find("a:lstStyle", NS) is None:
        insert_pos = 1 if tx_body.find("a:bodyPr", NS) is not None else 0
        tx_body.insert(insert_pos, lst_style)


def rewrite_slide(xml_bytes, slide_number):
    root = ET.fromstring(xml_bytes)
    sp_tree = root.find(".//p:cSld/p:spTree", NS)
    if sp_tree is not None:
        for child in list(sp_tree):
            if child.tag not in {
                f"{{{P_NS}}}nvGrpSpPr",
                f"{{{P_NS}}}grpSpPr",
                f"{{{P_NS}}}sp",
            }:
                sp_tree.remove(child)

    shapes = root.findall(".//p:sp", NS)
    replacements = SLIDE_TEXTS.get(slide_number, {})

    for idx, shape in enumerate(shapes, start=1):
        set_shape_text(shape, replacements.get(idx, ""))

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_ppt(template_path, output_path):
    tmp_path = output_path.with_suffix(".tmp.pptx")
    if tmp_path.exists():
        try:
            tmp_path.unlink()
        except PermissionError:
            pass
    shutil.copyfile(template_path, tmp_path)

    with zipfile.ZipFile(tmp_path, "r") as zin:
        file_map = {name: zin.read(name) for name in zin.namelist()}

    for slide_no in range(1, 18):
        slide_name = f"ppt/slides/slide{slide_no}.xml"
        if slide_name in file_map:
            file_map[slide_name] = rewrite_slide(file_map[slide_name], slide_no)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in file_map.items():
            zout.writestr(name, data)

    try:
        tmp_path.unlink()
    except PermissionError:
        pass


if __name__ == "__main__":
    workspace_root = Path(__file__).resolve().parents[2]
    template = workspace_root / "meetings" / "templates" / "template.pptx"
    output = workspace_root / "meetings" / "paper_shares" / "ppt" / "teerollup_group_meeting.pptx"
    build_ppt(template, output)
    print(output)
