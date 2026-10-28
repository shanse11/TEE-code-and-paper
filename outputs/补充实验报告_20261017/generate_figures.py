#!/usr/bin/env python3
"""Figures for the October 2026 supplementary experiment report."""

from pathlib import Path

import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.sans-serif": ["PingFang SC", "Heiti SC", "Arial Unicode MS", "Songti SC"],
    "axes.unicode_minus": False,
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 12,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#222222",
    "axes.linewidth": 0.8,
    "xtick.color": "#222222",
    "ytick.color": "#222222",
    "text.color": "#222222",
})

OURS = "#1f4e79"
BASE = "#8d8d8d"
ACCENT = "#9a3412"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_finality():
    labels = ["双方在线", "提交方离线", "离线后恢复", "直接裁决"]
    ours = [30, 30, 30, 30]
    base = [30, 0, None, 0]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = range(len(labels))
    width = 0.36
    ax.bar([i - width / 2 for i in x], ours, width, label="本文有界任务", color=OURS)
    base_x = []
    base_y = []
    for i, value in enumerate(base):
        if value is None:
            continue
        base_x.append(i + width / 2)
        base_y.append(value)
    ax.bar(base_x, base_y, width, label="无兜底重算基线", color=BASE)
    for xpos, value in zip(base_x, base_y):
        if value == 0:
            ax.text(xpos, 1.0, "0", ha="center", va="bottom", fontsize=10)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("正确终局数 / 30")
    ax.set_ylim(0, 36)
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    save(fig, "fig1_finality.png")


def fig_gas():
    labels = ["双方在线", "提交方离线", "离线后恢复", "直接裁决"]
    ours = [504959.2, 269214.8, 537372.0, 129487.8]
    base = [383900.8, 163124.8, None, 53428.4]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = range(len(labels))
    width = 0.36
    ax.bar([i - width / 2 for i in x], [v / 1000 for v in ours], width, label="本文有界任务", color=OURS)
    ax.bar(
        [i + width / 2 for i, v in enumerate(base) if v is not None],
        [v / 1000 for v in base if v is not None],
        width,
        label="无兜底重算基线",
        color=BASE,
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("裁决阶段平均 gas / 千")
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    save(fig, "fig2_resolve_gas.png")


def fig_enclave():
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 4.0))
    ax = axes[0]
    ax.bar(["4 步", "128 步"], [0.057, 0.497], color=OURS, width=0.55)
    ax.set_ylabel("Enclave 调用耗时 / ms")
    ax.set_title("哈希链在 Enclave 内的耗时")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = axes[1]
    ax.bar(["宿主计算", "Enclave 调用"], [0.305, 0.497], color=[BASE, OURS], width=0.55)
    ax.set_ylabel("单次耗时 / ms")
    ax.set_title("128 步：宿主与 Enclave")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    save(fig, "fig3_enclave_latency.png")


def fig_fees():
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    labels = ["执行费", "Blob 费"]
    values = [11072464, 131072]
    bars = ax.bar(labels, [v / 1e6 for v in values], color=[OURS, ACCENT], width=0.5)
    ax.set_ylabel("费用 / 百万 wei")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15, f"{value:,}", ha="center", va="bottom", fontsize=10)
    ax.set_ylim(0, 14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    save(fig, "fig4_sepolia_fees.png")


def fig_optimism():
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    labels = ["move 测试", "step 测试", "resolve 测试"]
    values = [365885, 2778766, 3731850]
    bars = ax.bar(labels, [v / 1e6 for v in values], color="#3f3f46", width=0.55)
    ax.set_ylabel("测试函数 gas / 百万")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05, f"{value:,}", ha="center", va="bottom", fontsize=10)
    ax.set_ylim(0, 4.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    save(fig, "fig5_optimism_tests.png")


if __name__ == "__main__":
    fig_finality()
    fig_gas()
    fig_enclave()
    fig_fees()
    fig_optimism()
    print("wrote", OUT)
