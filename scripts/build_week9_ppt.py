from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET


SLIDE_TEXTS = {
    1: [
        "【4/22 - 4/28】进展汇报",
        "【杨帆】",
    ],
    2: [
        "主要任务【限",
        "1",
        "页】",
        "中长期目标：研究如何在保证去中心化安全性的前提下，提高高频 DApp（如元宇宙、去中心化社交）的性能",
        "迄今为止的执行情况：已完成 Hybrid TEE-Rollup 原型中的执行层、验证层与数据层闭环，并将论文主线收敛为“可恢复交互式挑战 + 轻量 DA 成本评估”。",
        "本周拟完成的任务：把原有 5 组组会实验扩展为论文实验骨架，支持 payload size、batch size、trace steps 与 DA profile 的批量实验；",
        "同时阅读 Lazy Blockchain 轻客户端验证相关论文，补充数据可用性与二分验证机制的理论支撑。",
        "本周产出：论文主线重构 + 批量实验脚本 + 新论文阅读 + 第九周进展汇报",
    ],
    3: [
        "科研工作进展情况",
        "1 论文主线完成收敛",
        "从“泛 Hybrid Rollup 设计”调整为：研究异常场景中交互式挑战的可恢复性",
        "同时量化轻量 DA 提交对高频 DApp 批量交互的成本收益",
        "2 新增论文实验骨架脚本",
        "新增 scripts/run_paper_experiments.py",
        "支持 cost grid 与 challenge grid 两类实验",
        "输出 CSV / JSON / Markdown，便于后续生成论文图表",
        "核心变量",
        "payload size",
        "batch size",
        "trace steps",
        "DA profile",
        "3 实验范围从组会样本扩展到批量样本",
        "成本实验：full-onchain / external DA / EIP-4844-like / modular DA",
        "挑战实验：timeout recovery + bisection + single-step replay",
        "脚本默认输出",
        "cost_grid.csv",
        "challenge_grid.csv",
        "summary.json + paper_experiment_report.md",
        "论文工作从“可运行 demo”推进到“可复现实验框架”",
    ],
    4: [
        "科研工作进展情况",
        "论文实验闭环",
        "高频 DApp 交互样本",
        "   ↓",
        "TEE 模拟执行 + Attestation",
        "   ↓",
        "Compact Commit + DA payload",
        "   ↓",
        "异常注入 / 超时恢复 / 二分定位",
        "   ↓",
        "单步重放 / 成本统计 / CSV 输出",
        "已形成“机制设计 - 批量实验 - 论文图表”的基础链路",
        "论文主线对应关系",
        "对应论文问题",
        "",
        "实现路径",
        "性能：batch size 与 DA 成本摊销",
        "",
        "安全：TEE attestation + challenge + slashing",
        "恢复：timeout recover + replay",
        "",
        "成本：多 DA profile 成本曲线",
        "产出：CSV / JSON / Markdown 报告",
        "",
        "下一步：图表化与协议形式化",
    ],
    5: [
        "批量实验设计与初步结果",
        "实验目标",
        "把原有 5 组样本扩展为可复现实验网格，支撑论文 Evaluation 章节",
        "实验设置",
        "samples=10；payload=128/512/2048；batch=1/10/100/1000；trace=4/8/16/32/64",
        "关键结果",
        "成本实验 120 条记录，挑战实验 50 条记录",
        "payload=2048 时，full payload 均值 13118.20 bytes，compact commit 322.00 bytes",
        "compact commit 字节降幅约 97.41%",
        "trace steps=4/8/16/32/64 时，二分轮次分别为 2/3/4/5/6",
        "实验变量与论文作用",
        "payload size：控制 DA 数据规模",
        "",
        "评估高频交互负载",
        "",
        "batch size：控制摊销粒度",
        "",
        "体现 Rollup 批处理收益",
        "",
        "trace steps：控制争议轨迹长度",
        "",
        "评估二分挑战复杂度",
        "",
        "DA profile：比较不同数据层价格路线",
        "",
        "比较不同 DA 路线",
    ],
    6: [
        "论文阅读",
        "《Light Clients for Lazy Blockchains》 | Ertem Nusret Tas, David Tse, Lei Yang, Dionysis Zindros",
        "论文摘要：Lazy blockchain 将共识排序与交易执行/验证解耦以提升吞吐，但链上可能包含无效交易；轻客户端无法下载完整历史，因此需要低通信复杂度的验证协议。",
        "核心设计：通过 bisection game 在 Merkle tree 上定位分歧节点，使交互轮数和通信复杂度随执行时间呈对数增长。",
        "研究意义：为当前 challenge-step / single-step replay 提供理论支撑，也说明高频 DApp 扩容需要兼顾轻量验证与数据可得性。",
    ],
    7: [
        "本周学习体会【限1页】",
        "1 论文主线需要主动贴合高频 DApp 场景",
        "如果只讲 TEE-Rollup，容易显得偏底层机制；把问题表述为“高频 DApp 的低成本批量交互 + 异常可恢复验证”，就能更直接回应导师给定的研究方向。",
        "2 实验必须从组会演示转向论文可复现",
        "组会中 5 组样本足以说明流程，但论文需要变量、规模和可重复输出；因此本周重点是搭建批量实验骨架，而不是继续堆新机制。",
    ],
    8: [
        "谢谢，敬请批评指正！",
    ],
}


def build_week9_ppt():
    workspace_root = Path(__file__).resolve().parents[2]
    ppt_root = workspace_root / "meetings" / "weekly_reports" / "ppt"
    source = next(path for path in ppt_root.glob("*.pptx") if "第八周" in path.name)
    target = ppt_root / "26春0429第九周进度汇报-杨帆.pptx"
    final_target = target

    ET.register_namespace("a", "http://schemas.openxmlformats.org/drawingml/2006/main")
    ET.register_namespace("p", "http://schemas.openxmlformats.org/presentationml/2006/main")
    ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")

    with TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        with ZipFile(source, "r") as archive:
            archive.extractall(temp_dir)

        for slide_no, texts in SLIDE_TEXTS.items():
            slide_path = temp_dir / "ppt" / "slides" / f"slide{slide_no}.xml"
            tree = ET.parse(slide_path)
            root_node = tree.getroot()
            nodes = root_node.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}t")
            for index, node in enumerate(nodes):
                node.text = texts[index] if index < len(texts) else ""
            tree.write(slide_path, encoding="UTF-8", xml_declaration=True)

        if target.exists():
            try:
                target.unlink()
            except PermissionError:
                final_target = target.with_name(target.stem + "-修正版" + target.suffix)
        with ZipFile(final_target, "w", ZIP_DEFLATED) as archive:
            for file_path in temp_dir.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(temp_dir))

    return final_target


if __name__ == "__main__":
    print(build_week9_ppt())
