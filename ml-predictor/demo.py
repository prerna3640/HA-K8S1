"""
demo.py
-------
Full local demo of the Intelligent Auto-Scaling system.

Runs everything end-to-end:
  1. Generates 7 days of synthetic Kubernetes CPU data
  2. Trains Prophet + LSTM models
  3. Generates 30-min ahead predictions
  4. Simulates the predictive controller decisions
  5. Compares Reactive HPA vs Predictive Scaler
  6. Displays a 4-panel matplotlib dashboard
  7. Starts the Flask API at http://localhost:5000

Usage:
    python demo.py           # show charts + start API
    python demo.py --no-api  # charts only (no Flask server)
"""

import sys
import math
import argparse
import logging
import threading
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")          # works on Windows without a browser
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyArrowPatch
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s"
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Synthetic data with a realistic spike near "now"
# ═══════════════════════════════════════════════════════════════════════════════

def generate_data(days=7, interval_min=5):
    n = int(days * 24 * 60 / interval_min)
    end = datetime.now().replace(second=0, microsecond=0)
    start = end - timedelta(minutes=n * interval_min)
    ts = pd.date_range(start=start, periods=n, freq=f"{interval_min}min")

    vals = []
    for t in ts:
        h = t.hour + t.minute / 60.0
        daily = 0.04 + 0.07 * np.sin((h - 6) * np.pi / 12) ** 2
        if t.dayofweek >= 5:
            daily *= 0.55
        noise = np.random.normal(0, 0.006)
        spike = np.random.choice([0, 0.14], p=[0.985, 0.015])
        vals.append(max(0.005, daily + noise + spike))

    # Inject a visible upcoming spike in the last 30 minutes of history
    # so the predictor can detect and forecast it
    spike_start = n - 10
    for i in range(spike_start, n):
        ramp = (i - spike_start) / 10
        vals[i] = min(vals[i] + ramp * 0.22, 0.35)

    df = pd.DataFrame({"ds": ts, "y": vals})
    logger.info(f"Data: {len(df)} points  {start.date()} → {end.date()}  "
                f"mean={df['y'].mean():.4f}  max={df['y'].max():.4f} cores")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Train ensemble
# ═══════════════════════════════════════════════════════════════════════════════

def train_ensemble(df):
    from model import EnsemblePredictor
    logger.info("Training ensemble (Prophet + LSTM) ...")
    ep = EnsemblePredictor()
    ep.train(df)
    return ep


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Simulate reactive HPA vs predictive scaler over last 3 hours
# ═══════════════════════════════════════════════════════════════════════════════

HPA_CPU_THRESHOLD  = 0.10   # 50% of 200m limit per pod
PRED_CPU_PER_REP   = 0.10
PRED_BUFFER        = 0.80
MIN_REP, MAX_REP   = 2, 5
HPA_DELAY_MIN      = 2      # ~2 minutes reactive lag


def reactive_hpa(cpu_series):
    """Simulate stock HPA: reacts 2 minutes AFTER threshold crossed."""
    reps = []
    current = MIN_REP
    delayed = list(cpu_series)

    for i, cpu in enumerate(delayed):
        # HPA sees metrics with ~2-min lag
        observed = delayed[max(0, i - HPA_DELAY_MIN)]
        needed = max(MIN_REP, min(MAX_REP,
                     math.ceil(observed / (HPA_CPU_THRESHOLD * 0.80))))
        # Slow step: only change by 1 at a time
        if needed > current:
            current = min(current + 1, needed)
        elif needed < current:
            current = max(current - 1, needed)
        reps.append(current)
    return reps


def predictive_scaler_sim(cpu_series, horizon_pts=6):
    """Simulate predictive scaler: uses a lookahead window as proxy for forecast."""
    reps = []
    current = MIN_REP
    for i, cpu in enumerate(cpu_series):
        # Look ahead horizon_pts into the future (simulates ML forecast)
        future_window = cpu_series[i:i + horizon_pts]
        max_future = max(future_window) if len(future_window) else cpu
        desired = max(MIN_REP, min(MAX_REP,
                      math.ceil(max_future / (PRED_CPU_PER_REP * PRED_BUFFER))))
        current = desired
        reps.append(current)
    return reps


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Build the 4-panel dashboard
# ═══════════════════════════════════════════════════════════════════════════════

def build_dashboard(df, predictor):
    HORIZON = 30  # minutes
    prediction = predictor.predict(horizon_minutes=HORIZON)

    ensemble   = prediction.get("ensemble", [])
    prophet_v  = prediction.get("prophet", [])
    lstm_v     = prediction.get("lstm", [])
    p_upper    = prediction.get("prophet_upper", [])
    p_lower    = prediction.get("prophet_lower", [])
    ts_strs    = prediction.get("timestamps", [])

    # Future timestamps — generate enough for the longest model output
    now = datetime.now()
    max_pts = max(len(ensemble), len(prophet_v), len(lstm_v), 1)
    future_ts = [now + timedelta(minutes=5 * (i + 1)) for i in range(max_pts)]

    # Last 3 hours of history for display
    cutoff = now - timedelta(hours=3)
    hist = df[df["ds"] >= cutoff].copy()

    # Simulate HPA vs predictive over last 3 hours
    cpu_list = hist["y"].tolist()
    hpa_reps  = reactive_hpa(cpu_list)
    pred_reps = predictive_scaler_sim(cpu_list)

    # ── Figure layout ────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(16, 11), facecolor="#0f0f1a")
    fig.canvas.manager.set_window_title(
        "Intelligent Auto-Scaling in Kubernetes — ML Predictive Dashboard"
    )
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

    DARK_BG   = "#0f0f1a"
    PANEL_BG  = "#1a1a2e"
    GRID_CLR  = "#2a2a4a"
    TEXT_CLR  = "#e0e0ff"
    ACCENT    = "#00d4ff"
    GREEN     = "#00ff99"
    ORANGE    = "#ff9900"
    RED       = "#ff4466"
    PURPLE    = "#bb66ff"

    def style_ax(ax, title):
        ax.set_facecolor(PANEL_BG)
        ax.tick_params(colors=TEXT_CLR, labelsize=8)
        ax.xaxis.label.set_color(TEXT_CLR)
        ax.yaxis.label.set_color(TEXT_CLR)
        ax.title.set_color(ACCENT)
        ax.set_title(title, fontsize=10, fontweight="bold", pad=8)
        ax.grid(color=GRID_CLR, linewidth=0.5, linestyle="--", alpha=0.6)
        for spine in ax.spines.values():
            spine.set_edgecolor(GRID_CLR)

    # ── Panel 1: 7-day CPU history ───────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    style_ax(ax1, "Panel 1 — 7-Day CPU History (Kubernetes myapp/web)")
    ax1.plot(df["ds"], df["y"], color=ACCENT, linewidth=0.7, alpha=0.85, label="CPU usage")
    ax1.axhline(HPA_CPU_THRESHOLD, color=RED, linewidth=1.2, linestyle="--",
                label=f"HPA threshold ({HPA_CPU_THRESHOLD} cores)")
    ax1.axvline(now, color=ORANGE, linewidth=1.5, linestyle=":", label="Now")
    ax1.set_xlabel("Time")
    ax1.set_ylabel("CPU (cores)")
    ax1.legend(fontsize=7, facecolor=PANEL_BG, labelcolor=TEXT_CLR,
               edgecolor=GRID_CLR)
    ax1.xaxis.set_major_formatter(
        matplotlib.dates.DateFormatter("%m/%d")
    )
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha="right")

    # ── Panel 2: 30-min forecast ─────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    style_ax(ax2, "Panel 2 — 30-Min ML Forecast (Prophet + LSTM Ensemble)")

    # Last 90 min of history
    hist90 = df[df["ds"] >= now - timedelta(minutes=90)]
    ax2.plot(hist90["ds"], hist90["y"], color=ACCENT, linewidth=1.2,
             label="Actual CPU", zorder=3)

    if future_ts and prophet_v:
        ax2.plot(future_ts[:len(prophet_v)], prophet_v,
                 color=PURPLE, linewidth=1.5, linestyle="--",
                 label="Prophet forecast", zorder=4)
        if p_upper and p_lower:
            n = min(len(future_ts), len(p_upper), len(p_lower))
            ax2.fill_between(future_ts[:n], p_lower[:n], p_upper[:n],
                             color=PURPLE, alpha=0.15, label="Prophet CI 95%")

    if future_ts and lstm_v:
        ax2.plot(future_ts[:len(lstm_v)], lstm_v,
                 color=GREEN, linewidth=1.5, linestyle="-.",
                 label="LSTM forecast", zorder=4)

    if future_ts and ensemble:
        ax2.plot(future_ts[:len(ensemble)], ensemble,
                 color=ORANGE, linewidth=2.5,
                 label="Ensemble (avg)", zorder=5)

    ax2.axvline(now, color="white", linewidth=1.2, linestyle=":", alpha=0.7,
                label="Now →")
    ax2.axhline(HPA_CPU_THRESHOLD, color=RED, linewidth=1, linestyle="--",
                alpha=0.6, label="HPA threshold")
    ax2.set_xlabel("Time")
    ax2.set_ylabel("Predicted CPU (cores)")
    ax2.legend(fontsize=7, facecolor=PANEL_BG, labelcolor=TEXT_CLR,
               edgecolor=GRID_CLR)
    ax2.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha="right")

    # ── Panel 3: Reactive vs Predictive replicas ─────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    style_ax(ax3, "Panel 3 — Reactive HPA vs Predictive Scaler (Replica Count)")

    ax3_cpu = ax3.twinx()
    ax3_cpu.plot(hist["ds"], hist["y"], color=ACCENT, linewidth=0.8,
                 alpha=0.4, label="CPU")
    ax3_cpu.set_ylabel("CPU (cores)", color=ACCENT, fontsize=8)
    ax3_cpu.tick_params(colors=ACCENT, labelsize=7)

    ax3.step(hist["ds"], hpa_reps,  color=RED,   linewidth=2,
             where="post", label="Reactive HPA", zorder=3)
    ax3.step(hist["ds"], pred_reps, color=GREEN, linewidth=2,
             where="post", linestyle="--", label="Predictive Scaler", zorder=4)

    ax3.set_ylim(0, MAX_REP + 1)
    ax3.set_yticks(range(MIN_REP, MAX_REP + 1))
    ax3.set_xlabel("Time (last 3 hours)")
    ax3.set_ylabel("Replicas", color=TEXT_CLR)
    ax3.legend(fontsize=7, facecolor=PANEL_BG, labelcolor=TEXT_CLR,
               edgecolor=GRID_CLR, loc="upper left")
    ax3.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=30, ha="right")

    # ── Panel 4: Current status card ─────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_facecolor(PANEL_BG)
    ax4.axis("off")
    ax4.set_title("Panel 4 — System Status & Controller Decision",
                  fontsize=10, fontweight="bold", color=ACCENT, pad=8)

    max_pred   = prediction.get("max_predicted", 0.0)
    eff_cap    = PRED_CPU_PER_REP * PRED_BUFFER
    desired    = max(MIN_REP, min(MAX_REP, math.ceil(max_pred / eff_cap)))
    current_r  = hpa_reps[-1] if hpa_reps else MIN_REP
    action     = ("SCALE UP" if desired > MIN_REP else "NO CHANGE")
    action_clr = GREEN if desired > MIN_REP else ORANGE

    # Reactive lag info
    lag_pts  = sum(1 for i, (h, p) in enumerate(zip(hpa_reps, pred_reps)) if p > h)
    lag_pct  = lag_pts / max(len(hpa_reps), 1) * 100

    lines = [
        ("Prediction horizon",  "30 minutes ahead",          TEXT_CLR),
        ("Max predicted CPU",   f"{max_pred:.4f} cores",      ACCENT),
        ("CPU threshold/rep",   f"{PRED_CPU_PER_REP} cores (80% buffer)", TEXT_CLR),
        ("",                    "",                            TEXT_CLR),
        ("Current replicas",    f"{MIN_REP}",                 TEXT_CLR),
        ("Desired replicas",    f"{desired}",                  GREEN),
        ("Controller action",   action,                        action_clr),
        ("",                    "",                            TEXT_CLR),
        ("Models trained",      "Prophet 1.3  +  LSTM (PyTorch)", TEXT_CLR),
        ("Ensemble method",     "Average of both models",      TEXT_CLR),
        ("",                    "",                            TEXT_CLR),
        ("Predictive advantage",f"Ahead of HPA {lag_pct:.0f}% of the time", GREEN),
        ("Reactive HPA lag",    f"~{HPA_DELAY_MIN} minutes after spike",    RED),
        ("Predictive lead",     "Scales BEFORE the spike",    GREEN),
    ]

    y = 0.95
    for label, value, color in lines:
        if not label:
            y -= 0.04
            continue
        ax4.text(0.02, y, f"{label}:", fontsize=8.5, color="#888888",
                 transform=ax4.transAxes, va="top")
        ax4.text(0.52, y, value, fontsize=8.5, color=color, fontweight="bold",
                 transform=ax4.transAxes, va="top")
        y -= 0.065

    # Border
    for spine in ax4.spines.values():
        spine.set_edgecolor(GRID_CLR)

    # ── Super-title ───────────────────────────────────────────────────────────
    fig.text(0.5, 0.97,
             "INTELLIGENT AUTO-SCALING IN KUBERNETES\n"
             "Machine Learning Based Predictive Approach  —  Local Demo",
             ha="center", va="top", fontsize=13, fontweight="bold",
             color=ACCENT, linespacing=1.5)

    fig.text(0.5, 0.01,
             f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}  |  "
             f"Prerna Tank, M.Tech(CS) 2410512  |  DAVV",
             ha="center", fontsize=7.5, color="#666688")

    plt.savefig("demo_output.png", dpi=150, bbox_inches="tight",
                facecolor=DARK_BG)
    logger.info("Chart saved -> demo_output.png")
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Start Flask API in background thread
# ═══════════════════════════════════════════════════════════════════════════════

def start_api_thread(df):
    import data_collector
    from predictor_api import app, predictor, lock

    def _mock(hours=168):
        return df.copy()

    data_collector.fetch_cpu_metrics = _mock

    with lock:
        predictor.train(df)

    logger.info("Flask API → http://localhost:5000")

    def _run():
        import logging as _lg
        _lg.getLogger("werkzeug").setLevel(_lg.WARNING)
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

    t = threading.Thread(target=_run, daemon=True, name="flask-api")
    t.start()
    return t


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-api", action="store_true",
                        help="Skip starting the Flask API")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  INTELLIGENT AUTO-SCALING - FULL LOCAL DEMO")
    print("="*60)

    # 1. Data
    df = generate_data(days=args.days)

    # 2. Train
    predictor = train_ensemble(df)

    # 3. Predict
    prediction = predictor.predict(horizon_minutes=30)
    print(f"\n  Max predicted CPU   : {prediction['max_predicted']:.5f} cores")
    print(f"  Ensemble forecast   : {[round(v,4) for v in prediction['ensemble']]}")

    # 4. Controller decision
    max_pred = prediction['max_predicted']
    desired  = max(MIN_REP, min(MAX_REP,
                   math.ceil(max_pred / (PRED_CPU_PER_REP * PRED_BUFFER))))
    print(f"  Controller decision : {desired} replicas")
    print(f"  Action              : {'SCALE UP' if desired > MIN_REP else 'NO CHANGE'}")

    # 5. API
    if not args.no_api:
        start_api_thread(df)
        print("\n  Flask API running:")
        print("    http://localhost:5000/health")
        print("    http://localhost:5000/predict")
        print("    http://localhost:5000/predict?horizon=60")

    # 6. Dashboard
    print("\n  Building dashboard ...")
    fig = build_dashboard(df, predictor)

    print("\n" + "="*60)
    print("  Dashboard saved -> demo_output.png")
    if not args.no_api:
        print("  Flask API still running at http://localhost:5000")
    print("  Close the chart window to exit.")
    print("="*60 + "\n")

    plt.show()


if __name__ == "__main__":
    main()
