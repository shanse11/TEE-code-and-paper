from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path
from lxml import etree

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def qn(name: str) -> str:
    prefix, local = name.split(":")
    return f"{{{NS[prefix]}}}{local}"


def text_of(el) -> str:
    return "".join(el.xpath(".//w:t/text()", namespaces=NS)).strip()


def set_para_text(p, text: str) -> None:
    ppr = p.find("w:pPr", NS)
    first_rpr = p.find("w:r/w:rPr", NS)
    for child in list(p):
        if child is not ppr:
            p.remove(child)
    r = etree.SubElement(p, qn("w:r"))
    if first_rpr is not None:
        r.append(etree.fromstring(etree.tostring(first_rpr)))
    t = etree.SubElement(r, qn("w:t"))
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text


def main() -> None:
    draft = Path(__file__).resolve().parent
    src = draft / "final_layout_fixed_only.docx"
    out = draft / "final_refs_12_core.docx"
    shutil.copyfile(src, out)

    with zipfile.ZipFile(out, "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    root = etree.fromstring(files["word/document.xml"])
    body = root.find("w:body", NS)
    paragraphs = body.findall("w:p", NS)

    ref_heading = None
    for p in paragraphs:
        if text_of(p) == "参考文献":
            ref_heading = p
            break
    if ref_heading is None:
        raise RuntimeError("Reference heading not found.")

    replacements = {
        "Hybrid TEE-Rollup 将 TEE 快速路径与链上异常路径结合[1]": "Hybrid TEE-Rollup 将 TEE 快速路径与链上异常路径结合[1]",
        "Rollup 的基本思想是将大量执行过程移至链下完成，并将状态承诺、证明或争议入口提交到链上[2]。ZK-Rollup 通过有效性证明保证提交状态的正确性，验证属性较强，但证明生成、验证电路和系统实现成本较高[3][4]。Optimistic Rollup 默认链下执行结果正确，仅在挑战期内出现有效争议时进行仲裁；其链上负担较轻，但争议窗口和交互过程会引入状态不确定性[5]。": "Rollup 的基本思想是将大量执行过程移至链下完成，并将状态承诺、证明或争议入口提交到链上[2]。ZK-Rollup 通过有效性证明保证提交状态的正确性，验证属性较强，但证明生成、验证电路和系统实现成本较高。Optimistic Rollup 默认链下执行结果正确，仅在挑战期内出现有效争议时进行仲裁；其链上负担较轻，但争议窗口和交互过程会引入状态不确定性[3]。",
        "乐观挑战是 Rollup 系统处理异常的重要机制。典型流程包括提交状态承诺、开启挑战、交互式缩小争议范围，并在必要时执行单步重放或链上仲裁[6][7][8][9]。对于长执行轨迹，二分定位能够将争议定位复杂度从线性扫描降低到对数轮次；挑战过程本身也可能遭遇超时、应答缺失或证据不可用，因此活性和恢复性需要进入协议设计[10]。": "乐观挑战是 Rollup 系统处理异常的重要机制。典型流程包括提交状态承诺、开启挑战、交互式缩小争议范围，并在必要时执行单步重放或链上仲裁[4][5]。对于长执行轨迹，二分定位能够将争议定位复杂度从线性扫描降低到对数轮次；挑战过程本身也可能遭遇超时、应答缺失或证据不可用，因此活性和恢复性需要进入协议设计[6]。",
        "数据可用性关注链下或链外数据能否被验证者获取。模块化区块链和惰性账本等路线将数据可用性从执行验证中解耦，使共识层主要负责数据排序和可用性保证，执行与验证由独立的 Rollup 或客户端完成[11][12][13][14]。当执行者将完整负载放在数据可用性层而非链上时，链上提交必须与数据可用性条目形成可验证绑定。": "数据可用性关注链下或链外数据能否被验证者获取。模块化区块链和惰性账本等路线将数据可用性从执行验证中解耦，使共识层主要负责数据排序和可用性保证，执行与验证由独立的 Rollup 或客户端完成[7][8][9][10]。当执行者将完整负载放在数据可用性层而非链上时，链上提交必须与数据可用性条目形成可验证绑定。",
        "执行层负责处理高频 DApp 请求。当前原型采用确定性模拟模型或可选模型后端生成响应，并使用模拟可信执行环境远程证明对输入哈希、输出哈希、nonce 和执行环境标识进行绑定[15][16]。远程证明的作用是为链下执行结果提供最小可信摘要，使后续验证层能够检查提交结果是否与声明的执行过程一致。": "执行层负责处理高频 DApp 请求。当前原型采用确定性模拟模型或可选模型后端生成响应，并使用模拟可信执行环境远程证明对输入哈希、输出哈希、nonce 和执行环境标识进行绑定[11]。远程证明的作用是为链下执行结果提供最小可信摘要，使后续验证层能够检查提交结果是否与声明的执行过程一致。",
        "验证层负责处理异常路径。当前原型实现挑战打开、响应、步骤、恢复、重放和结算等状态推进；争议出现后，验证层通过证据加载、二分定位、单步重放和仲裁结算，将异常状态推进为可解释的协议结果[17]。": "验证层负责处理异常路径。当前原型实现挑战打开、响应、步骤、恢复、重放和结算等状态推进；争议出现后，验证层通过证据加载、二分定位、单步重放和仲裁结算，将异常状态推进为可解释的协议结果[4][5]。",
        "前述讨论已将可恢复挑战机制的核心性质从“超时后可以重试”这一工程事实提升为协议层面的状态转移机制。本节进一步将这一认识系统化为挑战事实不变性、安全性与活性的分离、仲裁连续性和恢复操作正确性四项性质，并给出协议不变量表格，以明确恢复机制的协议语义边界[18]。": "前述讨论已将可恢复挑战机制的核心性质从“超时后可以重试”这一工程事实提升为协议层面的状态转移机制。本节进一步将这一认识系统化为挑战事实不变性、安全性与活性的分离、仲裁连续性和恢复操作正确性四项性质，并给出协议不变量表格，以明确恢复机制的协议语义边界。",
        "模型比较四类 DA 路径：全链上调用数据、紧凑外部 DA、紧凑类 EIP-4844 方案和紧凑模块化 DA 采样[19]。该比较作为研究原型的成本建模工具，用于刻画不同数据发布路径的结构性差异。": "模型比较四类 DA 路径：全链上调用数据、紧凑外部 DA、紧凑类 EIP-4844 方案和紧凑模块化 DA 采样[12]。该比较作为研究原型的成本建模工具，用于刻画不同数据发布路径的结构性差异。",
    }

    changed = []
    for p in paragraphs:
        t = text_of(p)
        if t in replacements and replacements[t] != t:
            set_para_text(p, replacements[t])
            changed.append(t[:40])

    # Replace the reference list with 12 core references in first-citation order.
    new_refs = [
        "[1] WEN X, FENG Q, LYU H, et al. TEEROLLUP: efficient Rollup design using heterogeneous TEE[EB/OL]. arXiv:2409.14647, 2024. https://arxiv.org/abs/2409.14647.",
        "[2] BUTERIN V. An incomplete guide to Rollups[EB/OL]. 2021 [2026-06-15]. https://vitalik.ca/general/2021/01/05/rollup.html.",
        "[3] ETHEREUM FOUNDATION. Optimistic Rollups[EB/OL]. 2024 [2026-06-15]. https://ethereum.org/en/developers/docs/scaling/optimistic-rollups/.",
        "[4] ARBITRUM FOUNDATION. Arbitrum Nitro technical documentation[EB/OL]. 2024 [2026-06-15]. https://docs.arbitrum.io/.",
        "[5] OP LABS. Optimism documentation: fault proofs and dispute games[EB/OL]. 2024 [2026-06-15]. https://docs.optimism.io/.",
        "[6] PICCO G, FORTUGNO A. Dynamic fraud proof[EB/OL]. arXiv:2502.10321, 2025. https://arxiv.org/abs/2502.10321.",
        "[7] AL-BASSAM M. LazyLedger: a distributed data availability ledger with client-side smart contracts[EB/OL]. arXiv:1905.09274, 2019. https://arxiv.org/abs/1905.09274.",
        "[8] TAS E N, TSE D, YANG L, et al. Light clients for lazy blockchains[EB/OL]. arXiv:2203.15968, 2022. https://arxiv.org/abs/2203.15968.",
        "[9] EIGENLABS. EigenDA documentation[EB/OL]. 2024 [2026-06-15]. https://docs.eigencloud.xyz/products/eigenda/.",
        "[10] CELESTIA. Celestia: modular blockchain network[EB/OL]. 2024 [2026-06-15]. https://docs.celestia.org/.",
        "[11] INTEL CORPORATION. Intel Software Guard Extensions developer guide[EB/OL]. 2024 [2026-06-15]. https://www.intel.com/content/www/us/en/developer/tools/software-guard-extensions/overview.html.",
        "[12] ETHEREUM FOUNDATION. EIP-4844: shard blob transactions[EB/OL]. 2024 [2026-06-15]. https://eips.ethereum.org/EIPS/eip-4844.",
    ]

    ref_idx = body.index(ref_heading)
    ref_paras = []
    for child in list(body)[ref_idx + 1 :]:
        if child.tag == qn("w:p") and re.match(r"^\[\d+\]", text_of(child)):
            ref_paras.append(child)
    if not ref_paras:
        raise RuntimeError("No reference paragraphs found.")

    template = ref_paras[0]
    for old in ref_paras:
        body.remove(old)
    insert_at = body.index(ref_heading) + 1
    for ref in new_refs:
        p = etree.fromstring(etree.tostring(template))
        set_para_text(p, ref)
        body.insert(insert_at, p)
        insert_at += 1

    files["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)

    print(f"Wrote {out}")
    print(f"Changed paragraphs: {len(changed)}")


if __name__ == "__main__":
    main()
