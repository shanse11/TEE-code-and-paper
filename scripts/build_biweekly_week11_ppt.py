from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET


SLIDE_TEXTS = {
    1: [
        "【4/29 - 5/10】进展汇报",
        "【杨帆】",
    ],
    2: [
        "主要任务【限",
        "1",
        "页】",
        "中长期目标：研究如何在保证去中心化安全性的前提下，提高高频 DApp（如元宇宙、去中心化社交）的性能",
        "前期已完成 Hybrid TEE-Rollup 原型中的执行层、验证层与数据层闭环，并将论文主线收敛为“可恢复交互式挑战 + 轻量 DA 成本评估”。",
        "过去两周拟完成的任务：把论文实验从 smoke run 扩展为正式样本规模，补齐对照组、指标定义和自动报告输出；",
        "同时将关键链上路径映射为 Solidity 合约，完成本地 EVM gas 实测，并推进到 Sepolia 公开测试网部署。",
        "本周产出",
        "正式实验结果 + 本地 EVM gas 基线 + Sepolia 部署记录 + 两周进度汇报",
    ],
    3: [
        "科研工作进展情况",
        "1 正式实验规模补齐",
        "run_paper_experiments.py 已扩展到正式样本：samples=100",
        "当前输出 3200 条成本记录、600 条挑战记录、800 条失败场景记录",
        "2 论文式对照组与指标补齐",
        "成本对照：full-onchain vs compact+external DA / EIP-4844-like / modular DA",
        "挑战对照：no recover vs recover；trace steps=4/8/16/32/64/128",
        "指标定义补齐",
        "byte reduction ratio",
        "amortized gas",
        "reduction ratio",
        "avg bisection rounds",
        "recovery success rate",
        "challenge success rate / slashed rate",
        "3 自动报告同步更新",
        "experiment_report.md 已补齐对照组、指标定义、本地 EVM gas 与 Sepolia 部署结果",
        "当前实验材料已从“组会摘要”推进到“可直接写入 Evaluation 的实验文稿”",
    ],
    4: [
        "科研工作进展情况",
        "正式实验结果进一步明确",
        "成本结果：compact commit + DA 呈现稳定降本趋势",
        "payload=8192 时，full-onchain 单笔 Gas 约 80 万，modular DA 单笔约 2.9 万",
        "最佳降本比例约 96.33%",
        "挑战结果：recoverable challenge 明显改善可完成性",
        "no recover 场景 challenge success=0%",
        "recover 场景 challenge success=100%，slashed=100%",
        "二分定位结果",
        "trace steps=4/8/16/32/64/128",
        "对应轮次=2/3/4/5/6/7",
        "失败场景覆盖",
        "已覆盖 response tampered、attestation invalid、trace length mismatch、DA unavailable、DA proof invalid 等异常",
        "阶段判断：当前实验已能够支撑“可恢复挑战增强鲁棒性 + compact commit + DA 提供稳定降本”这两条核心主张",
    ],
    5: [
        "科研工作进展情况",
        "链上化推进：从本地 EVM 到 Sepolia 部署",
        "Python 原型",
        "   ↓",
        "Solidity 映射：MockTEEVerifier / MockDARegistry / HybridTEERollup",
        "   ↓",
        "Hardhat 本地部署 + gasUsed 实测",
        "   ↓",
        "Sepolia 部署成功 + 地址记录 + ABI 索引导出",
        "已形成“原型 - 本地链 - 公开测试网”的验证路径",
        "本地 EVM gas 基线",
        "submit rollup 299033.67；challenge open 283769.00；challenge recover 156891.00",
        "challenge replay 135632.00；challenge resolve 113402.00",
        "Sepolia 部署结果",
        "MockTEEVerifier：0xC42CB0Cf0D112Bd59E0f212F2DB2002ca50a8b6A",
        "MockDARegistry：0xc42C64a7De05bf3ad4f1c75CbD8E0506F7De99Ff",
        "HybridTEERollup：0xB9B72f10bB8aBC1ed090f1B0443Fe57189c497Fd",
        "当前状态：合约已成功部署；Etherscan 验证请求因 block explorer timeout 待重试",
    ],
    6: [
        "本周阶段成果",
        "《Formal Experiments + Local EVM + Sepolia Deployment》 | 实验与链上推进同步完成",
        "成果摘要：过去两周已经完成“估算模型 -> 正式实验 -> 本地 EVM 实测 -> Sepolia 部署”的渐进式验证路径，研究材料从原型演示推进到阶段论文基础。",
        "理论提炼 1：将挑战协议从“可检测错误”推进到“可恢复地完成仲裁”，强调异常场景下的持续推进能力。",
        "理论提炼 2：将 compact commit 从简单压缩推进到携带 DA Merkle root 与 evidence 字段的可验证提交结构。",
        "理论提炼 3：将异常从单一 invalid execution 细化为 attestation、trace、DA proof、DA availability 与 timeout recovery 等故障类型。",
        "阶段意义",
        "当前工作已经形成“机制设计 + 实验评估 + 公开测试网部署”的连续证据链，更适合作为论文 Evaluation 与 Discussion 的基础材料。",
    ],
    7: [
        "本周学习体会【限1页】",
        "1 论文实验必须从“能说明流程”走向“能支撑结论”",
        "过去两周最大的推进不是继续堆新机制，而是把对照组、指标、样本规模和自动报告补齐，使实验从 smoke run 提升到可直接支撑论文 Evaluation 的程度。",
        "2 公开测试网部署对研究说服力提升很明显",
        "仅有 Python 原型和本地 EVM 实测还不够；当合约真正部署到 Sepolia 后，系统是否具有链上可部署对应物这个问题就能被更直接地回答，论文口径也会更稳。",
    ],
    8: [
        "下周科研计划【限",
        "1",
        "页】",
        "1. 继续压实论文实验材料。核心目标：把现有正式实验进一步整理成论文可直接使用的图表与结果分析。重点任务：补齐失败场景统计图、整理 Sepolia 部署回执，并把实验报告转写为 Evaluation 草稿。",
        "2. 继续细化系统机制与论文表达。核心目标：把 recoverable challenge、evidence 结构和 DA 成本模型写成更规范的论文小节。重点任务：完成 Related Work 对照表、系统架构图与协议流程图，并继续重试 Etherscan 验证。",
    ],
}


def build_biweekly_week11_ppt():
    workspace_root = Path(__file__).resolve().parents[2]
    ppt_root = workspace_root / "meetings" / "weekly_reports" / "ppt"
    source = ppt_root / "26春0422第八周进度汇报-杨帆.pptx"
    target = ppt_root / "26春0510两周进度汇报-杨帆.pptx"
    backup = ppt_root / "26春0510两周进度汇报-杨帆-图表版备份.pptx"
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

        if target.exists() and not backup.exists():
            target.replace(backup)
        elif target.exists():
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
    print(build_biweekly_week11_ppt())
