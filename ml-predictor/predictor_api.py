"""
predictor_api_v2.py
-------------------
Enhanced Flask REST API with multi-metric prediction, drift detection, and cost tracking.

Endpoints:
  GET /health           – liveness/readiness + model stats
  GET /predict          – multi-metric forecast with confidence
  GET /drift            – drift detection status
  GET /cost             – cost estimation summary
  GET /metrics/current  – latest raw metrics from Prometheus
"""

import os
import logging
import threading
import time
from flask import Flask, jsonify, request

from data_collector import fetch_multi_metrics, fetch_cpu_metrics
from model import EnhancedPredictor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

RETRAIN_INTERVAL_HOURS = int(os.getenv("RETRAIN_INTERVAL_HOURS", "1"))
HISTORY_HOURS = int(os.getenv("HISTORY_HOURS", "2"))
PORT = int(os.getenv("PORT", "5000"))

app = Flask(__name__)
predictor = EnhancedPredictor()
lock = threading.Lock()


def _retrain_loop() -> None:
    while True:
        try:
            if predictor.needs_retraining(RETRAIN_INTERVAL_HOURS):
                logger.info("Fetching multi-metric data for retraining...")
                df = fetch_multi_metrics(hours=HISTORY_HOURS)
                if df.empty:
                    logger.warning("Prometheus returned no data")
                else:
                    with lock:
                        predictor.train(df)
                    logger.info(
                        f"Model retrained on {len(df)} multi-metric points "
                        f"(CPU+Memory+Network)"
                    )

                    # Check drift against actual values
                    if predictor.lstm and predictor.lstm.trained:
                        try:
                            pred = predictor.predict()
                            actual_cpu = df["cpu"].iloc[-1]
                            predicted_cpu = pred.get("max_predicted", 0)
                            predictor.check_and_handle_drift(predicted_cpu, actual_cpu)
                        except Exception:
                            pass

        except Exception as exc:
            logger.error(f"Retrain error: {exc}", exc_info=True)

        time.sleep(300)


@app.route("/health")
def health():
    trained = predictor.last_trained is not None
    return jsonify({
        "status": "ok",
        "model_trained": trained,
        "model_type": "multi_metric_lstm",
        "features": ["cpu", "memory", "network"],
        "last_trained": predictor.last_trained.isoformat() if trained else None,
        "retrain_count": predictor._retrain_count,
        "drift_retrains": predictor._drift_retrains,
        "drift_stats": predictor.drift_detector.get_stats(),
    }), 200 if trained else 503


@app.route("/predict")
def predict():
    try:
        horizon = int(request.args.get("horizon", 30))
        horizon = max(5, min(horizon, 120))
    except ValueError:
        return jsonify({"error": "horizon must be an integer"}), 400

    with lock:
        if not predictor.last_trained:
            return jsonify({"error": "Model not trained yet"}), 503
        result = predictor.predict(horizon)

    return jsonify(result), 200


@app.route("/drift")
def drift():
    return jsonify({
        "drift_stats": predictor.drift_detector.get_stats(),
        "drift_retrains": predictor._drift_retrains,
        "total_retrains": predictor._retrain_count,
    }), 200


@app.route("/cost")
def cost():
    return jsonify(predictor.cost_calculator.get_summary()), 200


@app.route("/metrics/current")
def current_metrics():
    try:
        df = fetch_multi_metrics(hours=1)
        if df.empty:
            return jsonify({"error": "No metrics available"}), 503
        latest = df.iloc[-1]
        return jsonify({
            "timestamp": latest["ds"].isoformat(),
            "cpu_cores": round(float(latest["cpu"]), 6),
            "memory_mb": round(float(latest["memory"]), 2),
            "network_kbps": round(float(latest["network"]), 2),
        }), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# Start retrain thread at module level (works with gunicorn)
_retrain_thread = threading.Thread(target=_retrain_loop, daemon=True, name="retrain-loop")
_retrain_thread.start()
logger.info("Enhanced retrain thread started (multi-metric + drift detection)")

if __name__ == "__main__":
    logger.info(f"Enhanced Predictor API starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
