# -*- coding: utf-8 -*-
"""按《计算机应用》投稿要求重绘论文 4 张插图为矢量图（SVG）+ 600dpi PNG。

要求来源：投稿模版.doc
  - 文章中所有插图请用矢量图格式，矢量图中的文字保持为可编辑文本
  - 普通流程图使用简单框架图，不加底色、灰度或阴影
  - 期刊黑白印刷：不使用彩色区分，曲线用线型与标记区分
  - 图、表中的字号不小于小 5 号（9pt）
  - 图宽按模板版心约 15 cm（5.906 in），图中字号按实际尺寸标注
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper_outputs" / "figures_vector"
OUT.mkdir(parents=True, exist_ok=True)

# ---- 版式常量（对应模板硬性要求）----
FIG_W_IN = 5.906          # 15 cm 版心宽
MIN_PT = 9.0              # 小 5 号
DPI = 600

CN = "Songti SC"          # 中文宋体
EN = "Times New Roman"    # 西文 Times New Roman

plt.rcParams.update(
    {
        "font.family": [EN, CN],   # matplotlib>=3.7 支持按字体列表逐字回退
        "font.size": MIN_PT,
        "axes.unicode_minus": False,
        "svg.fonttype": "none",   # 关键：SVG 中文字保持为可编辑文本，不转曲线
        "pdf.fonttype": 42,
        "axes.linewidth": 0.8,
        "xtick.direction": "in",
        "ytick.direction": "in",
    }
)

INK = "#000000"
EDGE = "#1f2937"


def save(fig, name: str):
    for ext in ("svg", "png"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=DPI, bbox_inches="tight",
                    pad_inches=0.02, facecolor="white")
    plt.close(fig)
    print("saved", name)


def box(ax, x0, y0, x1, y1, lines, title_idx=0, lw=1.0, gap=3.1):
    """白底黑框简单框架图，无底色/灰度/阴影。要求坐标为等比例（aspect equal）。

    gap 为行距，单位与坐标一致（1 单位 ≈ 4.25pt）。
    """
    ax.add_patch(
        FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                       boxstyle="round,pad=0,rounding_size=1.2",
                       linewidth=lw, edgecolor=EDGE, facecolor="white")
    )
    n = len(lines)
    cy = (y0 + y1) / 2
    total = gap * (n - 1)
    for i, txt in enumerate(lines):
        y = cy + total / 2 - gap * i
        ax.text((x0 + x1) / 2, y, txt, ha="center", va="center",
                fontsize=MIN_PT if i != title_idx else MIN_PT + 0.5,
                fontweight="bold" if i == title_idx else "normal",
                color=INK)


def arrow(ax, p0, p1, lw=1.0, style="-|>", color=INK, ls="-"):
    ax.annotate("", xy=p1, xytext=p0,
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                                linestyle=ls, shrinkA=0, shrinkB=0))


# =====================================================================
# 图 1  Hybrid TEE-Rollup 原型系统架构
# =====================================================================
def diagram_ax(xspan, yspan):
    """等比例坐标画布：1 坐标单位 = xspan/FIG_W_IN 英寸（约 4.25pt），字号即真实印刷字号。"""
    h = FIG_W_IN * yspan / xspan
    fig = plt.figure(figsize=(FIG_W_IN, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, xspan)
    ax.set_ylim(0, yspan)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


# =====================================================================
# 图 1  Hybrid TEE-Rollup 原型系统架构
# =====================================================================
def fig1():
    fig, ax = diagram_ax(100, 78)
    T = lambda y: 78 - y   # 顶部向下计量

    box(ax, 1, T(24), 23, T(4), ["高频 DApp 请求", "prompt / input"])
    box(ax, 33, T(26), 61, T(2), ["链下执行层（TEE）", "Simulated TEE", "response + attestation"])
    box(ax, 71, T(26), 98, T(2), ["链上提交层", "HybridTEERollup", "compact commit"])
    box(ax, 33, T(56), 61, T(32), ["数据可用性层", "mock / verifiable DA", "payload + Merkle proof"])
    box(ax, 71, T(56), 98, T(32), ["验证与仲裁层", "open·respond·step", "recover·replay·resolve"])

    arrow(ax, (23, T(14)), (33, T(14)))
    ax.text(28, T(11.6), "请求序列", ha="center", va="top", fontsize=MIN_PT - 0.5)
    arrow(ax, (61, T(14)), (71, T(14)))
    ax.text(66, T(11.6), "紧凑提交", ha="center", va="top", fontsize=MIN_PT - 0.5)
    arrow(ax, (47, T(26)), (47, T(32)))
    ax.text(48.4, T(29), "负载与证明", ha="left", va="center", fontsize=MIN_PT - 0.5)
    arrow(ax, (84.5, T(26)), (84.5, T(32)))
    ax.text(85.9, T(29), "挑战 / 恢复", ha="left", va="center", fontsize=MIN_PT - 0.5)
    arrow(ax, (71, T(44)), (61, T(44)), ls=(0, (4, 2)))
    ax.text(66, T(41.6), "取回证据", ha="center", va="bottom", fontsize=MIN_PT - 0.5)

    box(ax, 22, T(72), 56, T(66), ["正常路径：低延迟、低链上开销"], lw=0.8)
    box(ax, 59, T(72), 99, T(66), ["异常路径：挑战 → 恢复 → 重放 → 结算"], lw=0.8)
    arrow(ax, (47, T(56)), (47, T(66)), color="#333333", lw=0.9)
    arrow(ax, (84.5, T(56)), (84.5, T(66)), color="#333333", lw=0.9)

    ax.text(50, T(76.5), "紧凑提交绑定：状态根 / 输出哈希 / 证明哈希 / DA 指针 / DA 根",
            ha="center", va="center", fontsize=MIN_PT)
    save(fig, "fig1_architecture")


# =====================================================================
# 图 2  可恢复挑战协议流程（状态框宽度按 9pt 实测文字宽度设定）
# =====================================================================
def fig2():
    fig, ax = diagram_ax(100, 62)
    T = lambda y: 62 - y
    PT = 100 / (FIG_W_IN * 72.0)   # 1 单位 = 4.252pt，换算用

    # (英文, 中文, 宽度pt)
    states = [
        ("PENDING", "提交等待", 49), ("OPEN", "挑战开启", 40),
        ("RESPONDED", "回应争议", 61), ("NARROWING", "二分定位", 64),
        ("READY", "单步证据", 40), ("REPLAYED", "单步重放", 57),
        ("RESOLVED", "结算结果", 57),
    ]
    widths = [round(w * PT, 2) for _, _, w in states]
    total = sum(widths)
    gap = (100 - 2 * 1.0 - total) / (len(states) - 1)
    x = 1.0
    centers, boxes_x = [], []
    for (en, cn, _), w in zip(states, widths):
        box(ax, x, T(16), x + w, T(2), [en, cn], gap=3.4)
        centers.append(x + w / 2)
        boxes_x.append((x, x + w))
        x += w + gap

    for i in range(len(states) - 1):
        arrow(ax, (boxes_x[i][1] - 0.4, T(9)), (boxes_x[i + 1][0] + 0.4, T(9)), lw=0.9)

    # 超时恢复支路：置于 NARROWING 正下方，RECOVERED 在其右侧
    w_to, w_rec = round(53 * PT, 2), round(67 * PT, 2)
    cx_n = centers[3]
    to_x0, to_x1 = cx_n - w_to / 2, cx_n + w_to / 2
    rec_x0 = to_x1 + 6
    rec_x1 = rec_x0 + w_rec
    cx_r = (rec_x0 + rec_x1) / 2
    box(ax, to_x0, T(30), to_x1, T(42), ["TIMEOUT", "会话停滞"], gap=3.4)
    box(ax, rec_x0, T(30), rec_x1, T(42), ["RECOVERED", "恢复推进"], gap=3.4)

    arrow(ax, (cx_n, T(16)), (cx_n, T(30)))
    ax.text(cx_n - 1.0, T(23), "超时", ha="right", va="center", fontsize=MIN_PT - 0.5)
    arrow(ax, (to_x1, T(36)), (rec_x0, T(36)))
    ax.text((to_x1 + rec_x0) / 2, T(33.6), "恢复", ha="center", va="bottom", fontsize=MIN_PT - 0.5)
    arrow(ax, (cx_r, T(30)), (centers[4], T(16)))
    ax.text(68.5, T(22), "返回推进", ha="left", va="center", fontsize=MIN_PT - 0.5)

    ax.text(50, T(50), "恢复仅改变挑战会话的活性状态，不改写挑战事实与重放证据；",
            ha="center", va="center", fontsize=MIN_PT)
    ax.text(50, T(56.5), "是否罚没仍由重放结果决定。",
            ha="center", va="center", fontsize=MIN_PT)
    save(fig, "fig2_challenge_flow")


# =====================================================================
# 图 3  完整负载与紧凑提交的字节规模对比（数据源 summary.json）
# =====================================================================
def fig3():
    data = json.loads((ROOT / "paper_outputs" / "summary.json").read_text(encoding="utf-8"))
    rows = [r for r in data["cost_summary"] if r["batch_size"] == 1]
    payloads = sorted({r["payload_size"] for r in rows})

    def mean_over_prompts(field):
        out = []
        for p in payloads:
            vals = [r[field] for r in rows if r["payload_size"] == p]
            out.append(sum(vals) / len(vals))
        return out

    full = mean_over_prompts("avg_full_bytes")
    compact = mean_over_prompts("avg_compact_bytes")

    fig, (a, b) = plt.subplots(1, 2, figsize=(FIG_W_IN, 2.7),
                               gridspec_kw={"width_ratios": [1.5, 1.0]})
    a.plot(payloads, full, marker="o", color="black", lw=1.2, ms=4, label="完整负载")
    a.plot(payloads, compact, marker="s", color="black", lw=1.2, ms=4,
           ls=(0, (5, 2)), label="紧凑提交")
    a.set_xlabel("负载大小 payload size", fontsize=MIN_PT)
    a.set_ylabel("字节数 / B", fontsize=MIN_PT)
    a.set_title("(a) 总体趋势", fontsize=MIN_PT)
    a.legend(fontsize=MIN_PT - 0.5, frameon=False)
    a.tick_params(labelsize=MIN_PT - 0.5)
    a.grid(alpha=0.25, ls=(0, (2, 3)), lw=0.5)

    b.plot(payloads, compact, marker="s", color="black", lw=1.2, ms=4)
    b.set_xlabel("负载大小 payload size", fontsize=MIN_PT)
    b.set_ylabel("紧凑提交 / B", fontsize=MIN_PT)
    b.set_title("(b) 紧凑提交局部放大", fontsize=MIN_PT)
    b.tick_params(labelsize=MIN_PT - 0.5)
    b.set_ylim(395, 418)
    b.grid(alpha=0.25, ls=(0, (2, 3)), lw=0.5)
    for i in (0, len(payloads) - 1):   # 仅标注首末两点，避免重叠
        b.annotate(f"{compact[i]:.0f}", (payloads[i], compact[i]),
                   textcoords="offset points", xytext=(0, 6),
                   ha="center", fontsize=MIN_PT - 1)
    fig.tight_layout()
    save(fig, "fig3_byte_size")


# =====================================================================
# 图 4  不同 DA 配置下的摊销 gas 趋势（数据源 summary.json）
# =====================================================================
def fig4():
    data = json.loads((ROOT / "paper_outputs" / "summary.json").read_text(encoding="utf-8"))
    rows = [r for r in data["cost_summary"]
            if r["payload_size"] == max(x["payload_size"] for x in data["cost_summary"])
            and r["prompt_length"] == 64]
    rows.sort(key=lambda r: r["batch_size"])
    xs = [r["batch_size"] for r in rows]

    series = [
        ("avg_full_onchain_calldata_amortized_gas", "全链上调用数据", "-", "o"),
        ("avg_compact_external_da_amortized_gas", "紧凑外部 DA", (0, (6, 2)), "s"),
        ("avg_compact_eip4844_like_amortized_gas", "紧凑类 EIP-4844", (0, (4, 1, 1, 1)), "^"),
        ("avg_compact_modular_da_sampling_amortized_gas", "紧凑模块化 DA 采样", (0, (2, 1.5)), "D"),
    ]

    fig, ax = plt.subplots(figsize=(FIG_W_IN, 2.9))
    for key, label, ls, mk in series:
        ax.plot(xs, [r[key] for r in rows], color="black", lw=1.2, ls=ls,
                marker=mk, ms=4, mfc="white", label=label)
    ax.set_xscale("log")
    ax.set_xlabel("批大小 batch size", fontsize=MIN_PT)
    ax.set_ylabel("摊销 gas 用量", fontsize=MIN_PT)
    ax.legend(fontsize=MIN_PT - 0.5, frameon=False)
    ax.tick_params(labelsize=MIN_PT - 0.5)
    ax.grid(alpha=0.25, ls=(0, (2, 3)), lw=0.5, which="both")
    fig.tight_layout()
    save(fig, "fig4_da_cost")


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    print("ALL DONE ->", OUT)
