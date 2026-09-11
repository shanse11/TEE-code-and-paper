from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET


SLIDE_TEXTS = {
    1: [
        "【4/15 - 4/21】进展汇报",
        "【杨帆】",
    ],
    2: [
        "主要任务【限",
        "1",
        "页】",
        "中长期目标：研究如何在保证去中心化安全性的前提下，提高高频 DApp（如元宇宙、去中心化社交）的性能",
        "迄今为止的执行情况：已完成执行层（模拟 TEE）、验证层争议流程、数据层轻量化提交，并在本周进一步补齐可恢复挑战状态机与多场景 DA 成本量化实验。",
        "本周拟完成的任务：补充 challenge 会话状态机、超时恢复与可配置轮次控制，完成交互式争议协议细化；",
        "扩展轻量化 DA 成本模型，加入更接近 EIP-4844 / 模块化 DA 的多场景对照，并生成实验报告自动摘要。",
        "本周产出",
        "代码更新 + 自动实验报告 + 第八周进展汇报",
    ],
    3: [
        "科研工作进展情况",
        "1 可恢复挑战状态机",
        "新增 challenge_timeout、max_bisection_rounds 等配置项",
        "challenge-open -> respond -> step -> recover -> replay -> resolve",
        "2 失败恢复与异常处理",
        "会话超时后支持 watchdog 恢复并延长有效期",
        "二分轮次达到上限时可转入恢复或重放阶段",
        "新增接口",
        "challenge-status",
        "challenge-recover",
        "challenge-step",
        "争议流程从“可跑通”提升为“可恢复、可持续推进”",
        "3 多场景 DA 成本量化",
        "在原有 full / compact / blob 基础上加入 external DA、EIP-4844-like、modular DA sampling 对照",
        "自动报告",
        "experiment_report.md + experiment_ppt_snippet.md",
        "实测结果：",
        "轻量提交平均降幅 53.76%",
        "BlobDA 平均降幅 65.32%",
        "恢复流程结果",
        "2 轮二分定位后在 step 2 完成重放",
        "篡改交易最终判定为 SLASHED",
    ],
    4: [
        "科研工作进展情况",
        "核心闭环进一步增强",
        "用户请求",
        "   ↓",
        "链下执行 + TEE 签名",
        "   ↓",
        "轻量 Commit + DA 指针",
        "   ↓",
        "挑战 / 应答 / 二分定位 / 恢复",
        "   ↓",
        "单步重放 / 仲裁 / 罚没",
        "已形成“执行 - 验证 - 数据层”可恢复闭环",
        "OTR / Hybrid 架构对应关系",
        "模块",
        "",
        "当前实现",
        "TEE 执行 / Attestation 已实现",
        "Rollup 提交",
        "",
        "已实现",
        "Optimistic 验证",
        "",
        "",
        "",
        "已扩展为可恢复状态机",
        "数据层 DA",
        "",
        "已支持多场景成本估算",
        "ZK Spot Check",
        "",
        "已有演示原型",
    ],
    5: [
        "多场景成本实验与结果",
        "实验目标",
        "比较全量上链、轻量提交与多类 DA 策略的链上/数据层综合成本",
        "实验设置",
        "5 组样本；自动生成链上轻量提交与 DA 完整数据；对篡改样本执行恢复型争议流程",
        "关键结果",
        "轻量提交平均节省 374.60 bytes",
        "轻量提交 + DA：平均 Gas 降幅 53.76%",
        "轻量提交 + BlobDA：平均 Gas 降幅 65.32%",
        "modular DA sampling 场景平均总 Gas 最低",
        "成本对比",
        "方案",
        "",
        "平均总Gas",
        "",
        "结论",
        "全量上链",
        "",
        "11145.60",
        "",
        "基线最高",
        "compact+external DA",
        "",
        "6684.20",
        "",
        "明显下降",
        "EIP-4844-like / modular DA",
        "",
        "5778.80 / 5465.40",
        "",
        "更适合作为后续重点对照",
        "对研究方向的意义：结果表明，“链上轻量提交 + 可获取 DA”不仅能保留验证入口，还能在更接近真实部署的参数下持续降本，为高频 DApp 的 Hybrid Rollup 路线提供了量化依据。",
    ],
    6: [
        "本周阶段成果",
        "《Recoverable Challenge + DA Cost Curve》 | 代码与实验同步完成",
        "成果摘要：本周围绕第七周计划，已将交互式争议协议从 challenge-open/respond/resolve 扩展为带二分定位、单步重放、超时恢复的可恢复状态机，并将实验结果自动汇总为组会可贴文案。",
        "产出文件：更新 ledger.py、cli.py、tests/test_demo.py、generate_experiment_report.py 与 README.md；生成 experiment_report.md 和 experiment_ppt_snippet.md。",
        "阶段意义",
        "对本研究方向的启发：仅有“能挑战”还不够，争议协议必须具备恢复与持续推进能力，才能支撑更真实的工程部署场景。",
        "工程参考价值：多场景 DA 成本曲线为后续接入更真实 Blob/模块化 DA 参数提供了直接基线，也让后续论文分析和实验汇报更容易对齐。",
    ],
    7: [
        "本周学习体会【限1页】",
        "1 争议协议的重点从“能发现错误”转向“在异常情况下仍能推进”",
        "本周补充超时恢复后，更明显感受到交互式争议协议不是单条 happy path，而是一个需要处理超时、轮次上限与状态持久化的工程化系统，这对后续链上化实现很关键。",
        "2 成本实验需要逐步贴近真实部署参数",
        "仅比较全量上链与轻量提交还不够；当加入 external DA、EIP-4844-like 与 modular DA sampling 后，才能更清楚地看到不同数据层策略的边界与研究价值。",
    ],
    8: [
        "下周科研计划【限",
        "1",
        "页】",
        "1. 继续细化争议协议与链上化约束。核心目标：把当前恢复型状态机进一步补齐为更接近链上仲裁流程的版本。重点任务：增加罚没规则、并发挑战约束、证据字段与会话持久化校验。",
        "2. 深化数据层实验与论文阅读。核心目标：引入更真实的 Blob/模块化 DA 参数并整理与研究方向最相关的论文对照。重点任务：补充多场景实验图表，形成“机制设计 + 成本量化 + 文献支撑”的连续汇报材料。",
    ],
}


def build_week8_ppt():
    workspace_root = Path(__file__).resolve().parents[2]
    ppt_root = workspace_root / "meetings" / "weekly_reports" / "ppt"
    source = next(path for path in ppt_root.glob("*.pptx") if "第六周" in path.name)
    target = source.with_name(source.name.replace("第六周", "第八周"))
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
            if len(nodes) != len(texts):
                raise RuntimeError(
                    "slide {0} text nodes mismatch: {1} != {2}".format(
                        slide_no,
                        len(nodes),
                        len(texts),
                    )
                )
            for index, node in enumerate(nodes):
                node.text = texts[index]
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
    print(build_week8_ppt())
