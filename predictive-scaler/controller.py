"""
controller.py
-------------
Predictive Auto-Scaler Controller for Kubernetes.

Every CHECK_INTERVAL_SECONDS seconds, this controller:
  1. Queries the ML predictor API for the next PREDICTION_HORIZON minutes.
  2. Calculates the desired replica count from the predicted max CPU.
  3. Scales the target deployment BEFORE the traffic spike arrives.

This replaces the reactive lag of the stock HPA (~2 minutes) with
proactive scaling driven by the forecasted load.
"""

import os
import time
import logging
import requests
from datetime import datetime, timedelta

from scaler import KubernetesScaler

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  [controller]  %(message)s",
)
logger = logging.getLogger(__name__)

# ── configuration from environment variables ──────────────────────────────────
PREDICTOR_URL      = os.getenv(
    "PREDICTOR_URL",
    "http://ml-predictor.monitoring.svc.cluster.local:5000"
)
NAMESPACE          = os.getenv("NAMESPACE", "myapp")
DEPLOYMENT_NAME    = os.getenv("DEPLOYMENT_NAME", "web")

# CPU thresholds (in CPU cores, matching Prometheus output)
# HPA kicks in at 50 % × 200 m limit = ~0.10 cores per pod.
# We act BEFORE that by using a lower predicted threshold.
CPU_PER_REPLICA    = float(os.getenv("CPU_PER_REPLICA",    "0.10"))  # cores per replica
SCALE_UP_BUFFER    = float(os.getenv("SCALE_UP_BUFFER",    "0.80"))  # scale up at 80 % of per-replica limit

MIN_REPLICAS       = int(os.getenv("MIN_REPLICAS",   "2"))
MAX_REPLICAS       = int(os.getenv("MAX_REPLICAS",   "5"))

CHECK_INTERVAL     = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))   # 1 minute
SCALE_DOWN_COOLDOWN= int(os.getenv("SCALE_DOWN_COOLDOWN_SECONDS", "300"))  # 5 minutes
PREDICTION_HORIZON = int(os.getenv("PREDICTION_HORIZON", "30"))       # 30 minutes ahead


class PredictiveController:

    def __init__(self):
        self.scaler            = KubernetesScaler(NAMESPACE, DEPLOYMENT_NAME)
        self._last_scale_down: datetime | None = None
        self._last_scale_up:   datetime | None = None

    # ── prediction ────────────────────────────────────────────────────────────

    def _get_prediction(self) -> dict | None:
        """Call the ML predictor API and return the prediction dict."""
        try:
            resp = requests.get(
                f"{PREDICTOR_URL}/predict",
                params={"horizon": PREDICTION_HORIZON},
                timeout=10,
            )
            if resp.status_code == 503:
                logger.warning("Predictor: model not trained yet – skipping this cycle")
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error(f"Predictor unreachable: {exc}")
            return None

    # ── desired replica calculation ───────────────────────────────────────────

    def _desired_replicas(self, max_predicted_cpu: float) -> int:
        """
        Map a predicted CPU value to a replica count.

        Logic:
          desired = ceil(max_predicted_cpu / (CPU_PER_REPLICA * SCALE_UP_BUFFER))

        This means: add another replica before the current ones are 80 % saturated.
        The result is clamped to [MIN_REPLICAS, MAX_REPLICAS].
        """
        import math
        effective_capacity = CPU_PER_REPLICA * SCALE_UP_BUFFER
        if effective_capacity <= 0:
            return MIN_REPLICAS

        desired = math.ceil(max_predicted_cpu / effective_capacity)
        return max(MIN_REPLICAS, min(desired, MAX_REPLICAS))

    # ── cooldown helpers ──────────────────────────────────────────────────────

    def _can_scale_down(self) -> bool:
        if self._last_scale_down is None:
            return True
        elapsed = (datetime.now() - self._last_scale_down).total_seconds()
        return elapsed >= SCALE_DOWN_COOLDOWN

    # ── control loop ──────────────────────────────────────────────────────────

    def _run_once(self) -> None:
        prediction = self._get_prediction()
        if prediction is None:
            return

        max_cpu       = prediction.get("max_predicted", 0.0)
        predicted_at  = prediction.get("predicted_at", "?")
        n_points      = len(prediction.get("ensemble", []))

        logger.info(
            f"Prediction @ {predicted_at} | "
            f"max_predicted_cpu={max_cpu:.4f} cores | "
            f"horizon={PREDICTION_HORIZON} min | "
            f"forecast_points={n_points}"
        )

        current = self.scaler.get_current_replicas()
        if current is None:
            logger.error("Cannot read current replica count – skipping")
            return

        desired = self._desired_replicas(max_cpu)

        if desired > current:
            logger.info(
                f"⬆  SCALE UP  {current} → {desired} replicas  "
                f"(predicted CPU {max_cpu:.4f} cores)"
            )
            if self.scaler.scale(desired):
                self._last_scale_up = datetime.now()

        elif desired < current:
            if self._can_scale_down():
                logger.info(
                    f"⬇  SCALE DOWN  {current} → {desired} replicas  "
                    f"(predicted CPU {max_cpu:.4f} cores)"
                )
                if self.scaler.scale(desired):
                    self._last_scale_down = datetime.now()
            else:
                remaining = int(
                    SCALE_DOWN_COOLDOWN
                    - (datetime.now() - self._last_scale_down).total_seconds()
                )
                logger.info(
                    f"⏳  Scale-down suppressed – cooldown active ({remaining}s remaining)"
                )

        else:
            logger.info(
                f"✔  NO CHANGE – {current} replicas  "
                f"(predicted CPU {max_cpu:.4f} cores)"
            )

    def run(self) -> None:
        logger.info(
            f"Predictive controller started  |  "
            f"target={NAMESPACE}/{DEPLOYMENT_NAME}  |  "
            f"replicas={MIN_REPLICAS}–{MAX_REPLICAS}  |  "
            f"interval={CHECK_INTERVAL}s  |  "
            f"horizon={PREDICTION_HORIZON}min"
        )
        while True:
            try:
                self._run_once()
            except Exception as exc:
                logger.error(f"Unhandled error in control loop: {exc}", exc_info=True)
            time.sleep(CHECK_INTERVAL)


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Predictive Scaler Controller")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run without connecting to Kubernetes (prints decisions only)"
    )
    args = parser.parse_args()

    if args.dry_run:
        # Dry-run mode: mock the scaler so no K8s connection is needed
        import math

        class _MockScaler:
            def __init__(self, ns, name):
                self._replicas = int(os.getenv("MIN_REPLICAS", "2"))
                logger.info(f"[dry-run] Mock scaler for {ns}/{name}")

            def get_current_replicas(self):
                return self._replicas

            def scale(self, replicas):
                logger.info(f"[dry-run] >>> Would scale to {replicas} replicas <<<")
                self._replicas = replicas
                return True

        ctrl = PredictiveController.__new__(PredictiveController)
        ctrl.scaler = _MockScaler(NAMESPACE, DEPLOYMENT_NAME)
        ctrl._last_scale_down = None
        ctrl._last_scale_up = None
        ctrl.run()
    else:
        PredictiveController().run()
