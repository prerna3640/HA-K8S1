"""
test_local.py
-------------
Local test for the ML predictor WITHOUT needing Prometheus or Kubernetes.

It generates synthetic CPU data (simulating a real Kubernetes workload
with daily pattern + noise), trains both models, prints predictions,
and starts a local Flask server so you can call the /predict API from
your browser or curl.

Run:
    python test_local.py
    python test_local.py --api     (also starts Flask on http://localhost:5000)
"""

import sys
import argparse
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s"
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Step 1 – Generate synthetic CPU data
# ═══════════════════════════════════════════════════════════════════════════════

def generate_synthetic_cpu(days: int = 7, interval_minutes: int = 5) -> pd.DataFrame:
    """
    Simulate realistic CPU usage for a web deployment:
      - Low baseline at night  (~0.02 cores)
      - Morning surge  (9-11 AM)
      - Lunch dip      (12-13 PM)
      - Afternoon peak (14-17 PM)
      - Evening ramp-down
      - Random noise
      - Occasional spikes
    """
    n = int(days * 24 * 60 / interval_minutes)
    end = datetime.now().replace(second=0, microsecond=0)
    start = end - timedelta(minutes=n * interval_minutes)
    timestamps = pd.date_range(start=start, periods=n, freq=f"{interval_minutes}min")

    values = []
    for ts in timestamps:
        h = ts.hour + ts.minute / 60.0

        # Daily pattern (sine wave centred on busy hours)
        daily = 0.05 + 0.08 * np.sin((h - 6) * np.pi / 12) ** 2

        # Weekday vs weekend
        if ts.dayofweek >= 5:          # Saturday / Sunday
            daily *= 0.6

        # Add Gaussian noise
        noise = np.random.normal(0, 0.008)

        # Occasional spike (1 % chance each interval)
        spike = np.random.choice([0, 0.12], p=[0.99, 0.01])

        cpu = max(0.005, daily + noise + spike)
        values.append(cpu)

    df = pd.DataFrame({"ds": timestamps, "y": values})
    logger.info(
        f"Generated {len(df)} synthetic data points  "
        f"({start.date()} → {end.date()})  "
        f"mean={df['y'].mean():.4f} cores  max={df['y'].max():.4f} cores"
    )
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# Step 2 – Train & evaluate models
# ═══════════════════════════════════════════════════════════════════════════════

def test_prophet(df: pd.DataFrame) -> list:
    try:
        from model import ProphetPredictor
        logger.info("\n── Prophet ─────────────────────────────────────────")
        p = ProphetPredictor()
        p.train(df)
        forecast = p.predict(horizon_minutes=30)
        logger.info("Prophet 30-min forecast (CPU cores):")
        for _, row in forecast.iterrows():
            logger.info(f"  {row['ds']}  yhat={row['yhat']:.5f}  "
                        f"[{row['yhat_lower']:.5f}, {row['yhat_upper']:.5f}]")
        return forecast["yhat"].tolist()
    except ImportError as e:
        logger.warning(f"Prophet test skipped: {e}")
        return []


def test_lstm(df: pd.DataFrame) -> list:
    try:
        from model import LSTMPredictor
        logger.info("\n── LSTM ─────────────────────────────────────────────")
        lp = LSTMPredictor()
        lp.train(df, epochs=30)
        recent = df["y"].values
        preds = lp.predict(recent)
        logger.info("LSTM 30-min forecast (CPU cores):")
        for i, v in enumerate(preds):
            logger.info(f"  t+{(i+1)*5:3d}min  {v:.5f}")
        return preds.tolist()
    except ImportError as e:
        logger.warning(f"LSTM/PyTorch test skipped: {e}")
        return []


def test_ensemble(df: pd.DataFrame) -> dict:
    from model import EnsemblePredictor
    logger.info("\n── Ensemble ─────────────────────────────────────────")
    ep = EnsemblePredictor()
    ep.train(df)
    result = ep.predict(horizon_minutes=30)
    logger.info(f"Ensemble max_predicted : {result['max_predicted']:.5f} cores")
    logger.info(f"Ensemble forecast      : {[round(v,5) for v in result['ensemble']]}")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Step 3 – Simulate the controller decision
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_controller(max_predicted_cpu: float) -> None:
    import math

    CPU_PER_REPLICA   = 0.10
    SCALE_UP_BUFFER   = 0.80
    MIN_REPLICAS      = 2
    MAX_REPLICAS      = 5

    effective_cap = CPU_PER_REPLICA * SCALE_UP_BUFFER
    desired = max(MIN_REPLICAS, min(math.ceil(max_predicted_cpu / effective_cap), MAX_REPLICAS))

    logger.info("\n── Controller Decision ──────────────────────────────")
    logger.info(f"  max_predicted_cpu  : {max_predicted_cpu:.5f} cores")
    logger.info(f"  CPU per replica    : {CPU_PER_REPLICA}  (buffer {SCALE_UP_BUFFER*100:.0f}%)")
    logger.info(f"  Desired replicas   : {desired}  (range {MIN_REPLICAS}–{MAX_REPLICAS})")
    action = "SCALE UP" if desired > 2 else ("SCALE DOWN" if desired < 2 else "NO CHANGE")
    logger.info(f"  Action             : {action}")


# ═══════════════════════════════════════════════════════════════════════════════
# Step 4 – Optional: start local Flask API with mock Prometheus
# ═══════════════════════════════════════════════════════════════════════════════

def start_mock_api(df: pd.DataFrame) -> None:
    """
    Monkey-patches data_collector.fetch_cpu_metrics so the Flask API
    uses our synthetic data instead of a real Prometheus server.
    Then starts the app on http://localhost:5000
    """
    import data_collector
    import model as model_module
    from predictor_api import app, predictor, lock

    # Inject synthetic data instead of Prometheus
    def _mock_fetch(hours=168):
        logger.info("[mock] Returning synthetic CPU data")
        return df.copy()

    data_collector.fetch_cpu_metrics = _mock_fetch

    # Train immediately so /predict works right away
    logger.info("Pre-training model with synthetic data …")
    with lock:
        predictor.train(df)

    logger.info("\n" + "="*55)
    logger.info("  Flask API running at  http://localhost:5000")
    logger.info("  Try these URLs in your browser:")
    logger.info("    http://localhost:5000/health")
    logger.info("    http://localhost:5000/predict")
    logger.info("    http://localhost:5000/predict?horizon=60")
    logger.info("    http://localhost:5000/metrics/current")
    logger.info("  Press Ctrl+C to stop")
    logger.info("="*55 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=False)


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Local test for ml-predictor")
    parser.add_argument(
        "--api", action="store_true",
        help="Also start the Flask API on http://localhost:5000"
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="Days of synthetic history to generate (default 7)"
    )
    args = parser.parse_args()

    logger.info("=" * 55)
    logger.info("  ML Predictor – Local Test")
    logger.info("=" * 55)

    # 1. Synthetic data
    df = generate_synthetic_cpu(days=args.days)

    # 2. Train & predict
    test_prophet(df)
    test_lstm(df)
    result = test_ensemble(df)

    # 3. Controller simulation
    simulate_controller(result["max_predicted"])

    # 4. (Optional) Flask API
    if args.api:
        start_mock_api(df)
    else:
        logger.info(
            "\nTo also start the local API, run:\n"
            "    python test_local.py --api\n"
        )


if __name__ == "__main__":
    main()
