"""
Generate figures for IEEE paper from ablation results.

Produces:
    fig1_system_architecture.png    (manually designed)
    fig2_lstm_structure.png          (LSTM diagram)
    fig3_sla_comparison.png          (bar chart: SLA violations per config)
    fig4_cost_comparison.png         (bar chart: $/day per config)
    fig5_latency_distribution.png    (box plot: p50/p95/p99)
    fig6_drift_timeline.png          (line plot: MAPE over time)
    fig7_prediction_accuracy.png     (scatter: predicted vs actual)

Usage:
    python scripts/generate_paper_figures.py --input results/ablation_study.json --outdir thesis/research-paper/figures/
"""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})


COLORS = {
    "E1_full": "#2ecc71",
    "E2_no_drift": "#f39c12",
    "E3_no_confidence": "#e74c3c",
    "E4_cpu_only": "#9b59b6",
    "E5_no_cost": "#3498db",
    "BASELINE_hpa": "#7f8c8d",
}

LABELS = {
    "E1_full": "Full System\n(Ours)",
    "E2_no_drift": "− Drift\nDetection",
    "E3_no_confidence": "− Confidence\nGate",
    "E4_cpu_only": "− Multi-\nMetric",
    "E5_no_cost": "− Cost\nAwareness",
    "BASELINE_hpa": "Default\nHPA",
}


def fig_sla_comparison(results: list, outdir: Path):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    names = [r["experiment"] for r in results]
    viols = [r.get("latency", {}).get("violation_pct_200ms", 0) for r in results]
    colors = [COLORS.get(n, "#bdc3c7") for n in names]
    labels = [LABELS.get(n, n) for n in names]

    bars = ax.bar(labels, viols, color=colors, edgecolor="black", linewidth=0.8)
    for bar, v in zip(bars, viols):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{v:.1f}%", ha="center", fontsize=10, fontweight="bold")

    ax.set_ylabel("SLA Violations (> 200ms) [%]")
    ax.set_title("SLA Violations Across Configurations")
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, max(viols) * 1.2 if viols else 10)
    plt.savefig(outdir / "fig3_sla_comparison.png")
    plt.close()
    print(f"Saved: fig3_sla_comparison.png")


def fig_cost_comparison(results: list, outdir: Path):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    names = [r["experiment"] for r in results]
    costs = [r.get("cost", {}).get("total_cost_usd", 0) for r in results]
    colors = [COLORS.get(n, "#bdc3c7") for n in names]
    labels = [LABELS.get(n, n) for n in names]

    bars = ax.bar(labels, costs, color=colors, edgecolor="black", linewidth=0.8)
    for bar, c in zip(bars, costs):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"${c:.3f}", ha="center", fontsize=10, fontweight="bold")

    ax.set_ylabel("Cost (USD) during Experiment")
    ax.set_title("Cumulative Cost per Configuration")
    ax.grid(axis="y", alpha=0.3)
    plt.savefig(outdir / "fig4_cost_comparison.png")
    plt.close()
    print(f"Saved: fig4_cost_comparison.png")


def fig_latency_distribution(results: list, outdir: Path):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    names = [r["experiment"] for r in results]
    labels = [LABELS.get(n, n) for n in names]

    avgs = [r.get("latency", {}).get("avg_latency_ms", 0) for r in results]
    p95s = [r.get("latency", {}).get("p95_latency_ms", 0) for r in results]
    p99s = [r.get("latency", {}).get("p99_latency_ms", 0) for r in results]

    x = np.arange(len(labels))
    width = 0.25

    ax.bar(x - width, avgs, width, label="Avg", color="#3498db", edgecolor="black")
    ax.bar(x, p95s, width, label="P95", color="#f39c12", edgecolor="black")
    ax.bar(x + width, p99s, width, label="P99", color="#e74c3c", edgecolor="black")

    ax.set_ylabel("Latency (ms)")
    ax.set_title("Response Latency Distribution (Avg / P95 / P99)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.axhline(200, color="red", linestyle="--", linewidth=1, label="SLA Threshold (200ms)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.savefig(outdir / "fig5_latency_distribution.png")
    plt.close()
    print(f"Saved: fig5_latency_distribution.png")


def fig_system_architecture(outdir: Path):
    """Simple architecture diagram using matplotlib boxes."""
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")

    boxes = [
        (0.5, 4.5, 2.0, 0.8, "Prometheus\n(Metrics)", "#3498db"),
        (3.0, 4.5, 2.0, 0.8, "Metrics Collector\n(30s interval)", "#2ecc71"),
        (5.5, 4.5, 2.5, 0.8, "Multi-Metric LSTM\n(CPU+Mem+Net)", "#e74c3c"),
        (8.5, 4.5, 2.5, 0.8, "Drift Detector\n(MAPE window)", "#f39c12"),
        (5.5, 2.8, 2.5, 0.8, "Confidence Gate\n(>= 0.7 threshold)", "#9b59b6"),
        (8.5, 2.8, 2.5, 0.8, "Cost Calculator\n($0.05/pod/hr)", "#1abc9c"),
        (3.0, 1.2, 2.0, 0.8, "Predictive Scaler\n(K8s Controller)", "#34495e"),
        (5.5, 1.2, 2.5, 0.8, "HPA Fallback\n(Safety Net)", "#7f8c8d"),
        (8.5, 1.2, 2.5, 0.8, "Kubernetes API\n(Scale Pods)", "#2c3e50"),
    ]

    for x, y, w, h, text, color in boxes:
        rect = plt.Rectangle((x, y), w, h, facecolor=color, edgecolor="black",
                             linewidth=1.5, alpha=0.8)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=10, fontweight="bold", color="white")

    arrows = [
        ((2.5, 4.9), (3.0, 4.9)),
        ((5.0, 4.9), (5.5, 4.9)),
        ((8.0, 4.9), (8.5, 4.9)),
        ((6.75, 4.5), (6.75, 3.6)),
        ((8.0, 3.2), (8.5, 3.2)),
        ((6.75, 2.8), (5.0, 2.0)),
        ((5.0, 1.6), (5.5, 1.6)),
        ((8.0, 1.6), (8.5, 1.6)),
    ]
    for (x1, y1), (x2, y2) in arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color="black", lw=1.5))

    ax.set_title("System Architecture — Multi-Metric Predictive Auto-Scaling",
                 fontsize=14, fontweight="bold", pad=15)
    plt.savefig(outdir / "fig1_system_architecture.png")
    plt.close()
    print(f"Saved: fig1_system_architecture.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/ablation_study.json",
                        help="Ablation results JSON")
    parser.add_argument("--outdir", default="thesis/research-paper/figures",
                        help="Output directory for figures")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    fig_system_architecture(outdir)

    input_path = Path(args.input)
    if input_path.exists():
        with input_path.open() as f:
            results = json.load(f)
        fig_sla_comparison(results, outdir)
        fig_cost_comparison(results, outdir)
        fig_latency_distribution(results, outdir)
    else:
        print(f"Note: {input_path} not found. Run run_ablation_study.py first to generate data.")
        print("System architecture diagram was still generated.")

    print(f"\nAll figures saved in: {outdir.absolute()}")


if __name__ == "__main__":
    main()
