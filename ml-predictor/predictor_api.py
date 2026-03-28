"""
predictor_api.py
----------------
Flask REST API that exposes ML predictions to the predictive scaler controller.

Endpoints:
  GET /health            – liveness / readiness probe
  GET /predict?horizon=N – forecast for next N minutes (default 30)
  GET /metrics/current   – latest raw metric from Prometheus

A background thread retrains the model every RETRAIN_INTERVAL_HOURS hours.
"""

import os
import logging
import threading
import time
from flask import Flask, jsonify, request

from data_collector import fetch_cpu_metrics
from model import EnsemblePredictor

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── config from environment ───────────────────────────────────────────────────
RETRAIN_INTERVAL_HOURS = int(os.getenv("RETRAIN_INTERVAL_HOURS", "1"))
HISTORY_HOURS          = int(os.getenv("HISTORY_HOURS", "168"))   # 7 days
PORT                   = int(os.getenv("PORT", "5000"))

# ── shared state ──────────────────────────────────────────────────────────────
app       = Flask(__name__)
predictor = EnsemblePredictor()
lock      = threading.Lock()


# ═════════════════════════════════════════════════════════════════════════════
# Background retraining loop
# ═════════════════════════════════════════════════════════════════════════════

def _retrain_loop() -> None:
    """Periodically fetch fresh metrics from Prometheus and retrain the model."""
    while True:
        try:
            if predictor.needs_retraining(RETRAIN_INTERVAL_HOURS):
                logger.info("Fetching metrics for model retraining …")
                df = fetch_cpu_metrics(hours=HISTORY_HOURS)
                if df.empty:
                    logger.warning("Prometheus returned no data – skipping retraining")
                else:
                    with lock:
                        predictor.train(df)
                    logger.info(
                        f"Model retrained on {len(df)} points  "
                        f"(last={df['ds'].iloc[-1]})"
                    )
        except Exception as exc:
            logger.error(f"Retraining error: {exc}", exc_info=True)

        time.sleep(300)   # wake up every 5 minutes to check


# ═════════════════════════════════════════════════════════════════════════════
# Routes
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/health")
def health():
    """Liveness / readiness probe."""
    trained = predictor.last_trained is not None
    return jsonify({
        "status": "ok",
        "model_trained": trained,
        "last_trained": predictor.last_trained.isoformat() if trained else None,
    }), 200 if trained else 503


@app.route("/predict")
def predict():
    """
    Return forecasted CPU values for the next `horizon` minutes.

    Query params:
      horizon  (int, default=30)  – forecast horizon in minutes (5–120)
    """
    try:
        horizon = int(request.args.get("horizon", 30))
        horizon = max(5, min(horizon, 120))
    except ValueError:
        return jsonify({"error": "horizon must be an integer"}), 400

    with lock:
        if not predictor.last_trained:
            return jsonify({"error": "Model not trained yet – try again shortly"}), 503
        result = predictor.predict(horizon)

    return jsonify(result), 200


@app.route("/metrics/current")
def current_metrics():
    """Return the most recent CPU metric fetched from Prometheus."""
    try:
        df = fetch_cpu_metrics(hours=1)
        if df.empty:
            return jsonify({"error": "No metrics available from Prometheus"}), 503
        latest = df.iloc[-1]
        return jsonify({
            "timestamp": latest["ds"].isoformat(),
            "cpu_cores": round(float(latest["y"]), 6),
        }), 200
    except Exception as exc:
        logger.error(f"/metrics/current error: {exc}")
        return jsonify({"error": str(exc)}), 500


# ═════════════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Start background retraining thread
    t = threading.Thread(target=_retrain_loop, daemon=True, name="retrain-loop")
    t.start()
    logger.info(f"Predictor API starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
