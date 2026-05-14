"""Generate charts for README report."""

from __future__ import annotations

import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

# Try to use a Chinese font on macOS
plt.rcParams["font.family"] = ["PingFang SC", "Heiti TC", "Arial Unicode MS", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


def _save(fig: plt.Figure, name: str) -> None:
    fig.savefig(f"assets/{name}.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════════
# Chart 1: Pipeline Flow
# ═══════════════════════════════════════════════════════════════════════════


def chart_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(14, 3.5))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 4)
    ax.axis("off")

    steps = [
        ("种子采集", "CourtListener / EDGAR / GitHub\n117 个种子", "#4A90D9"),
        ("LLM 统一生成", "单次结构化调用\n题目 + 答案 + Rubric", "#5CB85C"),
        ("确定性渲染", "docx / xlsx / md / pdf\n无 LLM 参与", "#F0AD4E"),
        ("质量漏斗", "6 项硬校验\n通过率 ~92%", "#D9534F"),
        ("已验收任务", "97 道题\n3 种职业", "#5BC0DE"),
    ]

    box_w = 2.2
    gap = 0.5
    start_x = 0.5

    for i, (title, subtitle, color) in enumerate(steps):
        x = start_x + i * (box_w + gap)
        rect = mpatches.FancyBboxPatch(
            (x, 0.8), box_w, 2.4,
            boxstyle="round,pad=0.05,rounding_size=0.15",
            facecolor=color, edgecolor="white", linewidth=2, alpha=0.92,
        )
        ax.add_patch(rect)
        ax.text(x + box_w / 2, 2.6, title, ha="center", va="center",
                fontsize=12, fontweight="bold", color="white")
        ax.text(x + box_w / 2, 1.5, subtitle, ha="center", va="center",
                fontsize=9, color="white", linespacing=1.4)

        if i < len(steps) - 1:
            ax.annotate(
                "", xy=(x + box_w + gap - 0.05, 2.0), xytext=(x + box_w + 0.05, 2.0),
                arrowprops=dict(arrowstyle="->", color="#666", lw=1.8),
            )

    ax.set_title("GDPval 合成任务生成 Pipeline", fontsize=15, fontweight="bold", pad=15)
    _save(fig, "pipeline_flow")
    print("Chart 1: pipeline_flow.png generated")


# ═══════════════════════════════════════════════════════════════════════════
# Chart 2: Quality Funnel
# ═══════════════════════════════════════════════════════════════════════════


def chart_funnel() -> None:
    fig, ax = plt.subplots(figsize=(10, 5))

    stages = ["种子池", "生成任务", "通过质量门", "已验收"]
    counts = [117, 105, 97, 97]
    colors = ["#B8D4E8", "#7FB3D5", "#4A90D9", "#2E6DA4"]

    # Draw funnel bars (centered, width proportional to count)
    max_w = 8
    y_positions = [3.2, 2.2, 1.2, 0.2]
    heights = 0.7

    for stage, count, color, y in zip(stages, counts, colors, y_positions):
        w = (count / max(counts)) * max_w
        x = (max_w - w) / 2
        rect = mpatches.FancyBboxPatch(
            (x, y), w, heights,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            facecolor=color, edgecolor="white", linewidth=2,
        )
        ax.add_patch(rect)

        # Count inside bar
        ax.text(max_w / 2, y + heights / 2, f"{count}",
                ha="center", va="center", fontsize=16, fontweight="bold", color="white")
        # Stage label on left
        ax.text(x - 0.3, y + heights / 2, stage,
                ha="right", va="center", fontsize=11, color="#333")

        if y > 0.2:
            drop = counts[y_positions.index(y)] - counts[y_positions.index(y) - 1]
            if drop != 0:
                label = f"-{-drop}" if drop < 0 else f"-{drop}"
                ax.annotate(
                    label, xy=(max_w / 2, y + heights), xytext=(max_w / 2 + 3.5, y + heights),
                    ha="center", va="center", fontsize=10, color="#999",
                    arrowprops=dict(arrowstyle="->", color="#ccc", lw=1.2),
                )

    # Rate labels
    ax.text(max_w / 2 + 3.5, 2.7, "通过率\n89.7%", ha="center", va="center",
            fontsize=10, color="#666", bbox=dict(boxstyle="round,pad=0.3", facecolor="#f5f5f5", edgecolor="#ddd"))
    ax.text(max_w / 2 + 3.5, 1.7, "通过率\n92.4%", ha="center", va="center",
            fontsize=10, color="#666", bbox=dict(boxstyle="round,pad=0.3", facecolor="#f5f5f5", edgecolor="#ddd"))

    ax.set_xlim(-1, max_w + 5)
    ax.set_ylim(-0.2, 4.2)
    ax.axis("off")
    ax.set_title("质量漏斗：从种子到已验收任务", fontsize=15, fontweight="bold", pad=15)
    _save(fig, "quality_funnel")
    print("Chart 2: quality_funnel.png generated")


# ═══════════════════════════════════════════════════════════════════════════
# Chart 3: Occupation × Archetype Stacked Bar
# ═══════════════════════════════════════════════════════════════════════════


def chart_stacked_bar() -> None:
    fig, ax = plt.subplots(figsize=(10, 5.5))

    occupations = ["律师\nLawyer", "金融分析师\nFinancial Analyst", "软件工程师\nSoftware Engineer"]
    archetypes = [
        ["legal_memo"],
        ["investment_memo", "credit_memo"],
        ["code_review", "design_doc", "bug_fix_pr"],
    ]
    counts = [
        [34],
        [13, 12],
        [24, 12, 2],
    ]
    colors_map = {
        "legal_memo": "#2E6DA4",
        "investment_memo": "#5CB85C",
        "credit_memo": "#F0AD4E",
        "code_review": "#D9534F",
        "design_doc": "#5BC0DE",
        "bug_fix_pr": "#999999",
    }
    labels_map = {
        "legal_memo": "legal_memo",
        "investment_memo": "investment_memo",
        "credit_memo": "credit_memo",
        "code_review": "code_review",
        "design_doc": "design_doc",
        "bug_fix_pr": "bug_fix_pr",
    }

    x = np.arange(len(occupations))
    bar_width = 0.55

    bottoms = [0, 0, 0]
    legend_handles = []
    legend_labels = []

    for occ_idx in range(len(occupations)):
        for arch_idx, (arch, count) in enumerate(zip(archetypes[occ_idx], counts[occ_idx])):
            color = colors_map[arch]
            bar = ax.bar(
                x[occ_idx], count, bar_width,
                bottom=bottoms[occ_idx], color=color, edgecolor="white", linewidth=1.2,
            )
            # Label inside segment
            ax.text(x[occ_idx], bottoms[occ_idx] + count / 2, f"{count}",
                    ha="center", va="center", fontsize=11, fontweight="bold", color="white")
            bottoms[occ_idx] += count

            if labels_map[arch] not in legend_labels:
                legend_handles.append(bar)
                legend_labels.append(labels_map[arch])

    # Total labels on top
    totals = [sum(c) for c in counts]
    for i, total in enumerate(totals):
        ax.text(x[i], total + 1.5, f"总计: {total}", ha="center", va="bottom",
                fontsize=11, fontweight="bold", color="#333")

    ax.set_xticks(x)
    ax.set_xticklabels(occupations, fontsize=11)
    ax.set_ylabel("任务数量", fontsize=12)
    ax.set_ylim(0, 45)
    ax.legend(legend_handles, legend_labels, loc="upper right", fontsize=9,
              frameon=True, fancybox=True, shadow=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title("职业 × 交付物类型分布", fontsize=15, fontweight="bold", pad=15)

    _save(fig, "occupation_archetype")
    print("Chart 3: occupation_archetype.png generated")


if __name__ == "__main__":
    chart_pipeline()
    chart_funnel()
    chart_stacked_bar()
    print("\nAll charts saved to assets/")
