"""
controller_v2.py
----------------
Enhanced Predictive Auto-Scaler with Cost-Aware Scaling and Self-Healing.

UNIQUE CONTRIBUTIONS:
1. Cost-aware scaling: Logs cost per scaling decision
2. Self-healing: If ML predictor is down, falls back to HPA (dual-layer)
3. Confidence-based scaling: Only acts on high-confidence predictions
4. Drift-aware: Checks drift status before trusting predictions
"""

import os
import time
import math
import logging
import requests
from datetime import datetime, timedelta

from scaler import KubernetesScaler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  [controller-v2]  %(message)s",
)
logger = logging.getLogger(__name__)

PREDICTOR_URL = os.getenv("PREDICTOR_URL", "http://ml-predictor.monitoring.svc.cluster.local:5000")
NAMESPACE = os.getenv("NAMESPACE", "myapp")
DEPLOYMENT = os.getenv("DEPLOYMENT_NAME", "web")
CPU_PER_REP = float(os.getenv("CPU_PER_REPLICA", "0.10"))
BUFFER = float(os.getenv("SCALE_UP_BUFFER", "0.80"))
MIN_REP = int(os.getenv("MIN_REPLICAS", "2"))
MAX_REP = int(os.getenv("MAX_REPLICAS", "5"))
INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))
COOLDOWN = int(os.getenv("SCALE_DOWN_COOLDOWN_SECONDS", "300"))
HORIZON = int(os.getenv("PREDICTION_HORIZON", "30"))
COST_PER_POD_HOUR = float(os.getenv("COST_PER_POD_HOUR", "0.05"))
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.3"))


class EnhancedController:

    def __init__(self):
        self.scaler = KubernetesScaler(NAMESPACE, DEPLOYMENT)
        self._last_down = None
        self._predictor_failures = 0
        self._total_decisions = 0
        self._proactive_scales = 0
        self._cost_saved = 0.0
        self._self_healing_events = 0

    def _predict(self):
        try:
            r = requests.get(f"{PREDICTOR_URL}/predict", params={"horizon": HORIZON}, timeout=10)
            if r.status_code == 503:
                self._predictor_failures += 1
                logger.warning(
                    f"[Self-Heal] Predictor not ready (failures: {self._predictor_failures}) "
                    f"- HPA safety net active"
                )
                if self._predictor_failures >= 3:
                    self._self_healing_events += 1
                    logger.warning(
                        f"[Self-Heal] ML predictor DOWN for {self._predictor_failures} cycles. "
                        f"Relying on reactive HPA. Self-heal events: {self._self_healing_events}"
                    )
                return None
            r.raise_for_status()
            self._predictor_failures = 0
            return r.json()
        except Exception as e:
            self._predictor_failures += 1
            logger.error(f"Prediction failed: {e}")
            if self._predictor_failures >= 3:
                self._self_healing_events += 1
                logger.warning(f"[Self-Heal] Falling back to HPA. Events: {self._self_healing_events}")
            return None

    def _desired(self, max_cpu):
        cap = CPU_PER_REP * BUFFER
        if cap <= 0:
            return MIN_REP
        return max(MIN_REP, min(MAX_REP, math.ceil(max_cpu / cap)))

    def _estimate_cost(self, replicas):
        return replicas * COST_PER_POD_HOUR

    def _can_down(self):
        if not self._last_down:
            return True
        return (datetime.now() - self._last_down).total_seconds() >= COOLDOWN

    def run_once(self):
        self._total_decisions += 1
        pred = self._predict()

        if pred is None:
            logger.info(
                f"[Decision #{self._total_decisions}] No prediction available. "
                f"HPA safety net handles scaling."
            )
            return

        max_cpu = pred.get("max_predicted", 0.0)
        confidence = pred.get("confidence", 0.0)
        model_type = pred.get("model_type", "unknown")
        drift_stats = pred.get("drift_stats", {})
        drift_detected = drift_stats.get("drift_detected", False)

        current = self.scaler.get_current_replicas()
        if current is None:
            return

        # Confidence check: only act on confident predictions
        if confidence < MIN_CONFIDENCE and max_cpu > 0:
            logger.info(
                f"[Decision #{self._total_decisions}] Low confidence ({confidence:.1%}) "
                f"- skipping proactive scaling, HPA will handle"
            )
            return

        # Drift warning
        if drift_detected:
            logger.warning(
                f"[Drift] Pattern drift detected! Mean error: "
                f"{drift_stats.get('mean_error', 0):.1%}. "
                f"Model is retraining automatically."
            )

        desired = self._desired(max_cpu)
        old_cost = self._estimate_cost(current)
        new_cost = self._estimate_cost(desired)

        if desired > current:
            self._proactive_scales += 1
            logger.info(
                f"[Decision #{self._total_decisions}] SCALE UP {current} -> {desired} | "
                f"Predicted CPU: {max_cpu:.4f} | Confidence: {confidence:.1%} | "
                f"Model: {model_type} | "
                f"Cost: ${old_cost:.3f}/hr -> ${new_cost:.3f}/hr | "
                f"Proactive scales: {self._proactive_scales}"
            )
            self.scaler.scale(desired)

        elif desired < current and self._can_down():
            cost_saving = old_cost - new_cost
            self._cost_saved += cost_saving
            logger.info(
                f"[Decision #{self._total_decisions}] SCALE DOWN {current} -> {desired} | "
                f"Predicted CPU: {max_cpu:.4f} | Confidence: {confidence:.1%} | "
                f"Cost saving: ${cost_saving:.3f}/hr | "
                f"Total saved: ${self._cost_saved:.3f}"
            )
            if self.scaler.scale(desired):
                self._last_down = datetime.now()

        else:
            logger.info(
                f"[Decision #{self._total_decisions}] NO CHANGE {current} replicas | "
                f"Predicted: {max_cpu:.4f} | Confidence: {confidence:.1%} | "
                f"Cost: ${old_cost:.3f}/hr"
            )

    def run(self):
        logger.info(
            f"Enhanced Predictive Controller v2 started | "
            f"target={NAMESPACE}/{DEPLOYMENT} | replicas={MIN_REP}-{MAX_REP} | "
            f"interval={INTERVAL}s | confidence_threshold={MIN_CONFIDENCE:.0%} | "
            f"cost_per_pod=${COST_PER_POD_HOUR}/hr"
        )
        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
            time.sleep(INTERVAL)


if __name__ == "__main__":
    EnhancedController().run()
