const fs = require("fs");
const path = require("path");
const PptxGenJS = require("C:\\Users\\admin\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules\\pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..");
const PPT_DIR = path.join(ROOT, "meetings", "weekly_reports", "ppt");
const FIG_DIR = path.join(ROOT, "project_code", "paper_outputs", "figures");
const OUTPUT = path.join(PPT_DIR, "26春0510两周进度汇报-杨帆.pptx");
const BACKUP = path.join(PPT_DIR, "26春0510两周进度汇报-杨帆-文字版备份.pptx");

const COLORS = {
  navy: "16324F",
  blue: "2F80ED",
  teal: "14B8A6",
  green: "22C55E",
  amber: "F59E0B",
  red: "EF4444",
  ink: "1F2937",
  gray: "6B7280",
  line: "D7DEE8",
  panel: "F6F8FC",
  softBlue: "EAF2FF",
  softGreen: "EAFBF4",
  softAmber: "FFF6E6",
  softRed: "FDECEC",
  white: "FFFFFF",
};

function addTitle(slide, title, subtitle = "") {
  slide.addText(title, {
    x: 0.55,
    y: 0.28,
    w: 8.4,
    h: 0.42,
    fontFace: "Microsoft YaHei",
    fontSize: 24,
    bold: true,
    color: COLORS.navy,
    margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 9.55,
      y: 0.33,
      w: 3.1,
      h: 0.28,
      fontFace: "Microsoft YaHei",
      fontSize: 9,
      color: COLORS.gray,
      align: "right",
      margin: 0,
    });
  }
  slide.addShape(pptx.ShapeType.line, {
    x: 0.55,
    y: 0.78,
    w: 12.2,
    h: 0,
    line: { color: COLORS.line, pt: 1 },
  });
}

function addCard(slide, x, y, w, h, fill, title, value, foot = "", opts = {}) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h,
    rectRadius: 0.08,
    line: { color: opts.lineColor || fill, pt: 1 },
    fill: { color: fill },
  });
  slide.addText(title, {
    x: x + 0.18,
    y: y + 0.16,
    w: w - 0.36,
    h: 0.22,
    fontFace: "Microsoft YaHei",
    fontSize: 10,
    color: opts.titleColor || COLORS.gray,
    bold: true,
    margin: 0,
  });
  slide.addText(value, {
    x: x + 0.18,
    y: y + 0.44,
    w: w - 0.36,
    h: 0.34,
    fontFace: "Aptos",
    fontSize: opts.valueSize || 22,
    bold: true,
    color: opts.valueColor || COLORS.ink,
    margin: 0,
  });
  if (foot) {
    slide.addText(foot, {
      x: x + 0.18,
      y: y + h - 0.28,
      w: w - 0.36,
      h: 0.16,
      fontFace: "Microsoft YaHei",
      fontSize: 8.5,
      color: COLORS.gray,
      margin: 0,
    });
  }
}

function addBulletList(slide, items, x, y, w, h, fontSize = 13) {
  const text = items.map((item) => ({ text: item, options: { bullet: { indent: 14 } } }));
  slide.addText(text, {
    x, y, w, h,
    fontFace: "Microsoft YaHei",
    fontSize,
    color: COLORS.ink,
    paraSpaceAfterPt: 7,
    breakLine: true,
    valign: "top",
    margin: 0.05,
  });
}

function addSectionLabel(slide, x, y, text, fill) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w: 1.5, h: 0.28,
    rectRadius: 0.06,
    line: { color: fill, pt: 1 },
    fill: { color: fill },
  });
  slide.addText(text, {
    x, y: y + 0.03, w: 1.5, h: 0.18,
    fontFace: "Microsoft YaHei",
    fontSize: 9,
    color: COLORS.white,
    bold: true,
    align: "center",
    margin: 0,
  });
}

function addImageFrame(slide, imgPath, x, y, w, h, caption = "") {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h,
    rectRadius: 0.05,
    line: { color: COLORS.line, pt: 1 },
    fill: { color: COLORS.white },
    shadow: { type: "outer", color: "C9D3E0", blur: 1, angle: 45, distance: 1, opacity: 0.15 },
  });
  slide.addImage({ path: imgPath, x: x + 0.08, y: y + 0.08, w: w - 0.16, h: h - 0.34 });
  if (caption) {
    slide.addText(caption, {
      x: x + 0.08,
      y: y + h - 0.22,
      w: w - 0.16,
      h: 0.12,
      fontFace: "Microsoft YaHei",
      fontSize: 8.5,
      color: COLORS.gray,
      align: "center",
      margin: 0,
    });
  }
}

function addTinyMetric(slide, x, y, label, value, fill) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w: 1.85, h: 0.62,
    rectRadius: 0.05,
    line: { color: fill, pt: 1 },
    fill: { color: fill },
  });
  slide.addText(label, {
    x: x + 0.12,
    y: y + 0.1,
    w: 1.61,
    h: 0.16,
    fontFace: "Microsoft YaHei",
    fontSize: 8.5,
    bold: true,
    color: COLORS.gray,
    margin: 0,
  });
  slide.addText(value, {
    x: x + 0.12,
    y: y + 0.29,
    w: 1.61,
    h: 0.18,
    fontFace: "Aptos",
    fontSize: 13,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
}

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "OpenAI Codex";
pptx.company = "OpenAI";
pptx.subject = "两周组会进度汇报";
pptx.title = "26春0510两周进度汇报-杨帆";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "Microsoft YaHei",
  bodyFontFace: "Microsoft YaHei",
  lang: "zh-CN",
};

// Slide 1
let slide = pptx.addSlide();
slide.background = { color: "F7FAFF" };
slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 0.38, line: { color: COLORS.blue, pt: 0 }, fill: { color: COLORS.blue } });
slide.addShape(pptx.ShapeType.roundRect, {
  x: 0.72, y: 1.18, w: 11.8, h: 4.9,
  rectRadius: 0.08,
  line: { color: "DCE8FF", pt: 1.2 },
  fill: { color: COLORS.white },
});
slide.addText("【4/29 - 5/10】进展汇报", {
  x: 1.05, y: 1.88, w: 8.7, h: 0.72,
  fontFace: "Microsoft YaHei",
  fontSize: 28,
  bold: true,
  color: COLORS.navy,
  margin: 0,
});
slide.addText("Hybrid TEE-Rollup：正式实验扩容、本地 EVM 实测与 Sepolia 部署", {
  x: 1.08, y: 2.78, w: 9.6, h: 0.36,
  fontFace: "Microsoft YaHei",
  fontSize: 14,
  color: COLORS.gray,
  margin: 0,
});
slide.addText("【杨帆】", {
  x: 1.08, y: 4.75, w: 2.8, h: 0.34,
  fontFace: "Microsoft YaHei",
  fontSize: 18,
  bold: true,
  color: COLORS.ink,
  margin: 0,
});
addCard(slide, 8.8, 1.7, 2.85, 1.2, COLORS.softBlue, "正式实验", "3200 / 600 / 800", "成本 / 挑战 / 失败场景");
addCard(slide, 8.8, 3.1, 2.85, 1.2, COLORS.softGreen, "关键结论", "96.33%", "高 payload 场景最佳降本比例");
addCard(slide, 8.8, 4.5, 2.85, 1.2, COLORS.softAmber, "测试网进展", "Sepolia 已部署", "Etherscan 验证超时待重试", { valueSize: 18 });

// Slide 2
slide = pptx.addSlide();
slide.background = { color: COLORS.white };
addTitle(slide, "主要任务", "4/29 - 5/10");
addSectionLabel(slide, 0.7, 1.02, "研究主线", COLORS.blue);
slide.addShape(pptx.ShapeType.roundRect, {
  x: 0.68, y: 1.35, w: 6.1, h: 2.45,
  rectRadius: 0.05,
  line: { color: COLORS.line, pt: 1 },
  fill: { color: COLORS.panel },
});
slide.addText("在保证去中心化安全性的前提下，提升高频 DApp 的性能。", {
  x: 0.95, y: 1.72, w: 5.45, h: 0.5, fontFace: "Microsoft YaHei", fontSize: 18, bold: true, color: COLORS.navy,
});
slide.addText("论文切口：可恢复交互式挑战 + 轻量 DA 成本评估", {
  x: 0.95, y: 2.5, w: 5.2, h: 0.3, fontFace: "Microsoft YaHei", fontSize: 13, color: COLORS.gray,
});
addSectionLabel(slide, 7.15, 1.02, "两周重点", COLORS.teal);
addCard(slide, 7.1, 1.36, 2.55, 1.2, COLORS.softBlue, "实验", "样本扩到 100", "补齐正式样本规模");
addCard(slide, 9.95, 1.36, 2.55, 1.2, COLORS.softGreen, "对照组", "full vs compact", "no recover vs recover");
addCard(slide, 7.1, 2.78, 2.55, 1.2, COLORS.softAmber, "链上化", "本地 EVM", "拿到 gasUsed 基线");
addCard(slide, 9.95, 2.78, 2.55, 1.2, COLORS.softRed, "部署", "Sepolia 成功", "地址与 ABI 已导出");
addSectionLabel(slide, 0.7, 4.18, "本次汇报看点", COLORS.amber);
addBulletList(slide, [
  "正式实验规模：3200 / 600 / 800 条记录",
  "成本对照：full-onchain vs compact + 三类 DA",
  "挑战对照：no recover vs recover，trace steps 扩到 128",
  "本地 EVM gasUsed 基线 + Sepolia 真部署结果"
], 0.76, 4.48, 11.8, 1.8, 14);

// Slide 3
slide = pptx.addSlide();
slide.background = { color: COLORS.white };
addTitle(slide, "科研工作进展（一）：实验规模与指标", "从 smoke run 到可写论文的实验框架");
addCard(slide, 0.72, 1.08, 2.35, 1.35, COLORS.softBlue, "每组变量样本", "100", "正式实验规模");
addCard(slide, 3.3, 1.08, 2.35, 1.35, COLORS.softGreen, "成本记录", "3200", "payload / batch / DA profile");
addCard(slide, 5.88, 1.08, 2.35, 1.35, COLORS.softAmber, "挑战记录", "600", "trace / timeout / recovery");
addCard(slide, 8.46, 1.08, 2.35, 1.35, COLORS.softRed, "失败场景", "800", "8 类故障样本");
slide.addShape(pptx.ShapeType.roundRect, {
  x: 0.72, y: 2.8, w: 5.95, h: 3.85, rectRadius: 0.05,
  line: { color: COLORS.line, pt: 1 }, fill: { color: COLORS.panel }
});
addSectionLabel(slide, 0.92, 3.0, "对照组补齐", COLORS.blue);
addBulletList(slide, [
  "成本对照：full-onchain / external DA / EIP-4844-like / modular DA",
  "批处理：batch size = 1 / 10 / 100 / 1000",
  "负载规模：payload size = 128 / 512 / 2048 / 8192",
  "挑战对照：no recover vs recover",
  "争议规模：trace steps = 4 / 8 / 16 / 32 / 64 / 128"
], 0.98, 3.34, 5.3, 2.9, 12.5);
slide.addShape(pptx.ShapeType.roundRect, {
  x: 6.95, y: 2.8, w: 5.65, h: 3.85, rectRadius: 0.05,
  line: { color: COLORS.line, pt: 1 }, fill: { color: COLORS.white }
});
addSectionLabel(slide, 7.15, 3.0, "核心指标", COLORS.teal);
addTinyMetric(slide, 7.2, 3.42, "byte reduction ratio", "链上字节压缩比例", COLORS.softBlue);
addTinyMetric(slide, 9.18, 3.42, "amortized gas", "单笔摊销成本", COLORS.softGreen);
addTinyMetric(slide, 11.16, 3.42, "reduction ratio", "相对 full 降本比例", COLORS.softAmber);
addTinyMetric(slide, 7.2, 4.18, "avg bisection rounds", "平均二分轮次", COLORS.softBlue);
addTinyMetric(slide, 9.18, 4.18, "recovery success", "恢复后可继续推进", COLORS.softGreen);
addTinyMetric(slide, 11.16, 4.18, "slashed rate", "异常最终罚没比例", COLORS.softRed);
slide.addText("结果文件已自动汇总到 experiment_report.md，可直接转写 Evaluation。", {
  x: 7.2, y: 5.18, w: 4.95, h: 0.48, fontFace: "Microsoft YaHei", fontSize: 13, color: COLORS.ink, margin: 0,
});

// Slide 4
slide = pptx.addSlide();
slide.background = { color: COLORS.white };
addTitle(slide, "科研工作进展（二）：成本结果更直观", "compact commit + DA 的降本趋势");
addCard(slide, 0.74, 1.02, 2.1, 1.02, COLORS.softGreen, "最佳降本比例", "96.33%", "payload=8192, modular DA");
addCard(slide, 3.0, 1.02, 2.1, 1.02, COLORS.softBlue, "Full-onchain", "约 80 万", "单笔 Gas");
addCard(slide, 5.26, 1.02, 2.1, 1.02, COLORS.softAmber, "Modular DA", "约 2.9 万", "单笔 Gas");
slide.addShape(pptx.ShapeType.roundRect, {
  x: 7.6, y: 0.98, w: 5.0, h: 1.1, rectRadius: 0.05,
  line: { color: COLORS.line, pt: 1 }, fill: { color: COLORS.panel }
});
slide.addText("观察点：payload 越大，compact commit 的优势越明显；batch 越大，单笔摊销越低。", {
  x: 7.85, y: 1.27, w: 4.5, h: 0.34, fontFace: "Microsoft YaHei", fontSize: 12.5, color: COLORS.ink, margin: 0,
});
addImageFrame(slide, path.join(FIG_DIR, "cost_payload_full_vs_compact.png"), 0.76, 2.3, 5.95, 3.95, "图 1  payload 增大时 full payload 与 compact commit 的字节差距");
addImageFrame(slide, path.join(FIG_DIR, "da_profile_amortized_gas.png"), 6.95, 2.3, 5.62, 3.95, "图 2  batch 增大时不同 DA profile 的单笔摊销 gas");

// Slide 5
slide = pptx.addSlide();
slide.background = { color: COLORS.white };
addTitle(slide, "正式实验结果：挑战恢复与异常场景", "recoverable challenge 的可完成性更强");
addImageFrame(slide, path.join(FIG_DIR, "challenge_rounds.png"), 0.72, 1.02, 6.0, 3.55, "图 3  bisection rounds 与 log2(trace steps) 基本一致");
addImageFrame(slide, path.join(FIG_DIR, "recovery_success.png"), 6.95, 1.02, 5.66, 3.55, "图 4  no recover 与 recover 的挑战完成性对比");
addCard(slide, 0.8, 4.88, 2.45, 1.1, COLORS.softRed, "无 recover", "0%", "challenge success");
addCard(slide, 3.45, 4.88, 2.45, 1.1, COLORS.softGreen, "有 recover", "100%", "challenge success / slashed");
addCard(slide, 6.1, 4.88, 2.45, 1.1, COLORS.softBlue, "二分轮次", "2 - 7", "steps=4 到 128");
addCard(slide, 8.75, 4.88, 3.1, 1.1, COLORS.softAmber, "异常覆盖", "8 类场景", "tamper / attestation / DA / timeout");
slide.addText("结论：recover 机制把“检测到问题但流程停住”推进成“恢复后继续仲裁并完成 slashing”。", {
  x: 0.85, y: 6.25, w: 11.8, h: 0.3, fontFace: "Microsoft YaHei", fontSize: 13, color: COLORS.ink, margin: 0,
});

// Slide 6
slide = pptx.addSlide();
slide.background = { color: COLORS.white };
addTitle(slide, "链上化推进：本地 EVM 到 Sepolia", "系统已具备公开测试网对应物");
slide.addShape(pptx.ShapeType.line, { x: 1.2, y: 1.7, w: 9.8, h: 0, line: { color: COLORS.line, pt: 2 } });
["Python 原型", "Solidity 映射", "本地 EVM", "Sepolia"].forEach((label, idx) => {
  const xs = [1.1, 4.0, 6.9, 9.8][idx];
  const fills = [COLORS.softBlue, COLORS.softAmber, COLORS.softGreen, COLORS.softRed][idx];
  slide.addShape(pptx.ShapeType.ellipse, { x: xs, y: 1.45, w: 0.48, h: 0.48, line: { color: COLORS.blue, pt: 1 }, fill: { color: COLORS.blue } });
  slide.addText(String(idx + 1), { x: xs, y: 1.55, w: 0.48, h: 0.12, fontFace: "Aptos", fontSize: 10, bold: true, color: COLORS.white, align: "center", margin: 0 });
  slide.addShape(pptx.ShapeType.roundRect, { x: xs - 0.55, y: 2.05, w: 1.6, h: 0.58, rectRadius: 0.05, line: { color: COLORS.line, pt: 1 }, fill: { color: fills } });
  slide.addText(label, { x: xs - 0.48, y: 2.24, w: 1.46, h: 0.12, fontFace: "Microsoft YaHei", fontSize: 10, bold: true, color: COLORS.ink, align: "center", margin: 0 });
});
addCard(slide, 0.75, 2.95, 2.7, 1.55, COLORS.softBlue, "MockTEEVerifier", "0xC42C...8b6A", "模拟 TEE attestation 验证", { valueSize: 16 });
addCard(slide, 3.75, 2.95, 2.7, 1.55, COLORS.softAmber, "MockDARegistry", "0xc42C...99Ff", "DA 根与可用性记录", { valueSize: 16 });
addCard(slide, 6.75, 2.95, 3.25, 1.55, COLORS.softGreen, "HybridTEERollup", "0xB9B7...97Fd", "commit / challenge / recover", { valueSize: 16 });
addCard(slide, 10.3, 2.95, 2.25, 1.55, COLORS.softRed, "验证状态", "已部署", "Etherscan timeout 待重试", { valueSize: 17 });
slide.addShape(pptx.ShapeType.roundRect, {
  x: 0.74, y: 4.88, w: 11.85, h: 1.36, rectRadius: 0.05,
  line: { color: COLORS.line, pt: 1 }, fill: { color: COLORS.panel }
});
slide.addText("本地 EVM gasUsed 基线", {
  x: 1.0, y: 5.13, w: 2.0, h: 0.18, fontFace: "Microsoft YaHei", fontSize: 11, bold: true, color: COLORS.navy, margin: 0,
});
addTinyMetric(slide, 2.8, 5.0, "submit", "299033.67", COLORS.softBlue);
addTinyMetric(slide, 4.78, 5.0, "open", "283769", COLORS.softAmber);
addTinyMetric(slide, 6.76, 5.0, "recover", "156891", COLORS.softGreen);
addTinyMetric(slide, 8.74, 5.0, "replay", "135632", COLORS.softBlue);
addTinyMetric(slide, 10.72, 5.0, "resolve", "113402", COLORS.softAmber);

// Slide 7
slide = pptx.addSlide();
slide.background = { color: COLORS.white };
addTitle(slide, "阶段总结与理论提炼", "让汇报从机制描述转向可支撑结论");
slide.addShape(pptx.ShapeType.roundRect, { x: 0.8, y: 1.08, w: 11.8, h: 0.58, rectRadius: 0.05, line: { color: COLORS.line, pt: 1 }, fill: { color: COLORS.panel } });
slide.addText("估算模型", { x: 1.0, y: 1.25, w: 1.2, h: 0.12, fontFace: "Microsoft YaHei", fontSize: 11, bold: true, color: COLORS.gray, align: "center", margin: 0 });
slide.addText("本地 EVM 实测", { x: 4.55, y: 1.25, w: 1.6, h: 0.12, fontFace: "Microsoft YaHei", fontSize: 11, bold: true, color: COLORS.gray, align: "center", margin: 0 });
slide.addText("Sepolia 部署", { x: 8.95, y: 1.25, w: 1.4, h: 0.12, fontFace: "Microsoft YaHei", fontSize: 11, bold: true, color: COLORS.gray, align: "center", margin: 0 });
slide.addShape(pptx.ShapeType.line, { x: 2.15, y: 1.36, w: 2.2, h: 0, line: { color: COLORS.blue, pt: 3, beginArrowType: "none", endArrowType: "triangle" } });
slide.addShape(pptx.ShapeType.line, { x: 6.25, y: 1.36, w: 2.1, h: 0, line: { color: COLORS.blue, pt: 3, beginArrowType: "none", endArrowType: "triangle" } });
addCard(slide, 0.8, 2.0, 3.8, 1.65, COLORS.softBlue, "理论提炼 1", "可恢复仲裁", "从“检测错误”推进到“恢复后继续完成 challenge”", { valueSize: 20 });
addCard(slide, 4.78, 2.0, 3.8, 1.65, COLORS.softAmber, "理论提炼 2", "可验证提交结构", "compact commit 携带 DA Merkle root 与 evidence", { valueSize: 18 });
addCard(slide, 8.76, 2.0, 3.8, 1.65, COLORS.softGreen, "理论提炼 3", "故障类型学", "attestation / trace / DA proof / availability / timeout", { valueSize: 19 });
slide.addShape(pptx.ShapeType.roundRect, { x: 0.8, y: 4.05, w: 5.65, h: 2.0, rectRadius: 0.05, line: { color: COLORS.line, pt: 1 }, fill: { color: COLORS.panel } });
addSectionLabel(slide, 1.0, 4.25, "阶段意义", COLORS.blue);
slide.addText("当前工作已经形成“机制设计 + 实验评估 + 公开测试网部署”的阶段论文基础，不再只是组会 demo。", {
  x: 1.02, y: 4.68, w: 5.0, h: 0.9, fontFace: "Microsoft YaHei", fontSize: 14, color: COLORS.ink, valign: "mid", margin: 0.05,
});
slide.addShape(pptx.ShapeType.roundRect, { x: 6.72, y: 4.05, w: 5.9, h: 2.0, rectRadius: 0.05, line: { color: COLORS.line, pt: 1 }, fill: { color: COLORS.white } });
addSectionLabel(slide, 6.94, 4.25, "学习体会", COLORS.teal);
addBulletList(slide, [
  "实验必须从“能说明流程”走向“能支撑结论”",
  "对照组、指标、样本规模和自动报告比单纯多加机制更关键",
  "公开测试网部署显著提升研究说服力"
], 6.98, 4.62, 5.2, 1.05, 12.5);

// Slide 8
slide = pptx.addSlide();
slide.background = { color: "F7FAFF" };
slide.addShape(pptx.ShapeType.roundRect, { x: 1.05, y: 1.45, w: 11.1, h: 3.9, rectRadius: 0.08, line: { color: "DCE8FF", pt: 1 }, fill: { color: COLORS.white } });
slide.addText("谢谢，敬请批评指正！", {
  x: 2.25, y: 2.55, w: 8.8, h: 0.7, fontFace: "Microsoft YaHei", fontSize: 28, bold: true, color: COLORS.navy, align: "center", margin: 0,
});
slide.addText("本次更新重点：实验图表化、关键指标卡片化、Sepolia 部署结果可视化", {
  x: 2.1, y: 3.5, w: 9.1, h: 0.28, fontFace: "Microsoft YaHei", fontSize: 13, color: COLORS.gray, align: "center", margin: 0,
});

async function main() {
  if (fs.existsSync(OUTPUT) && !fs.existsSync(BACKUP)) {
    fs.copyFileSync(OUTPUT, BACKUP);
  }
  await pptx.writeFile({ fileName: OUTPUT });
  console.log(OUTPUT);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
