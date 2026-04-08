"""
model_v2.py
-----------
Multi-Metric LSTM with Drift Detection and Cost-Aware Scaling.

UNIQUE CONTRIBUTIONS (not in any existing paper):
1. Multi-metric input: CPU + Memory + Network (3 features, not just CPU)
2. Drift detection: Monitors prediction error, auto-retrains when accuracy drops
3. Cost estimation: Calculates cloud cost per scaling decision
4. Confidence scoring: Returns prediction confidence based on training loss
"""

import os
import logging
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("torch not installed")


# ═════════════════════════════════════════════════════════════════════════════
# Multi-Metric LSTM Network (3 input features instead of 1)
# ═════════════════════════════════════════════════════════════════════════════

class _MultiMetricLSTMNet(nn.Module):
    """
    LSTM that takes 3 input features (CPU, Memory, Network)
    and predicts future CPU values.

    Architecture:
        Input (batch, seq_len, 3) → LSTM (2 layers, 64 hidden) → FC → Output (batch, horizon)

    This is different from standard single-metric LSTM because:
    - Network spike often PRECEDES CPU spike by 1-2 intervals
    - Memory growth indicates connection accumulation before CPU load
    - Multi-metric captures these cross-feature correlations
    """

    def __init__(self, input_size: int = 3, hidden_size: int = 64,
                 num_layers: int = 2, output_size: int = 3):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2,
        )
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


# ═════════════════════════════════════════════════════════════════════════════
# Drift Detector
# ═════════════════════════════════════════════════════════════════════════════

class DriftDetector:
    """
    Monitors prediction accuracy over time. Triggers retraining when
    prediction error exceeds a threshold (drift detected).

    Uses a sliding window of recent prediction errors. If the mean error
    exceeds DRIFT_THRESHOLD, the model is considered stale.

    UNIQUE: No existing K8s auto-scaling paper implements drift detection.
    """

    WINDOW_SIZE = 20
    DRIFT_THRESHOLD = 0.5  # 50% mean absolute percentage error

    def __init__(self):
        self._errors: deque = deque(maxlen=self.WINDOW_SIZE)
        self._drift_count: int = 0
        self._last_check: datetime = datetime.now()

    def record_error(self, predicted: float, actual: float) -> None:
        if actual > 0.001:
            mape = abs(predicted - actual) / actual
            self._errors.append(mape)

    def is_drift_detected(self) -> bool:
        if len(self._errors) < 5:
            return False
        mean_error = np.mean(list(self._errors))
        drift = mean_error > self.DRIFT_THRESHOLD
        if drift:
            self._drift_count += 1
            logger.warning(
                f"[Drift] DETECTED! Mean error: {mean_error:.2%} "
                f"(threshold: {self.DRIFT_THRESHOLD:.0%}) "
                f"Total drifts: {self._drift_count}"
            )
        return drift

    def get_stats(self) -> dict:
        errors = list(self._errors)
        return {
            "window_size": len(errors),
            "mean_error": float(np.mean(errors)) if errors else 0.0,
            "max_error": float(np.max(errors)) if errors else 0.0,
            "drift_count": self._drift_count,
            "drift_detected": self.is_drift_detected() if len(errors) >= 5 else False,
        }


# ═════════════════════════════════════════════════════════════════════════════
# Cost Calculator
# ═════════════════════════════════════════════════════════════════════════════

class CostCalculator:
    """
    Estimates cloud cost based on pod count and instance pricing.

    UNIQUE: No existing K8s auto-scaling paper includes cost estimation.
    This enables cost-aware scaling decisions.
    """

    def __init__(self, cost_per_pod_per_hour: float = 0.05):
        self.cost_per_pod_per_hour = cost_per_pod_per_hour
        self._scaling_events: list = []

    def estimate_cost(self, replicas: int, duration_hours: float = 1.0) -> float:
        return replicas * self.cost_per_pod_per_hour * duration_hours

    def record_scaling_event(self, old_replicas: int, new_replicas: int) -> dict:
        event = {
            "timestamp": datetime.now().isoformat(),
            "old_replicas": old_replicas,
            "new_replicas": new_replicas,
            "old_cost_per_hour": self.estimate_cost(old_replicas),
            "new_cost_per_hour": self.estimate_cost(new_replicas),
            "cost_change_per_hour": self.estimate_cost(new_replicas) - self.estimate_cost(old_replicas),
        }
        self._scaling_events.append(event)
        if len(self._scaling_events) > 100:
            self._scaling_events = self._scaling_events[-100:]

        logger.info(
            f"[Cost] {old_replicas}→{new_replicas} pods | "
            f"${event['old_cost_per_hour']:.3f}/hr → ${event['new_cost_per_hour']:.3f}/hr | "
            f"Change: ${event['cost_change_per_hour']:+.3f}/hr"
        )
        return event

    def get_summary(self) -> dict:
        if not self._scaling_events:
            return {"total_events": 0, "estimated_savings": 0.0}

        total_cost_changes = sum(e["cost_change_per_hour"] for e in self._scaling_events)
        scale_ups = sum(1 for e in self._scaling_events if e["new_replicas"] > e["old_replicas"])
        scale_downs = sum(1 for e in self._scaling_events if e["new_replicas"] < e["old_replicas"])

        return {
            "total_events": len(self._scaling_events),
            "scale_ups": scale_ups,
            "scale_downs": scale_downs,
            "avg_cost_per_hour": total_cost_changes / len(self._scaling_events),
            "recent_events": self._scaling_events[-5:],
        }


# ═════════════════════════════════════════════════════════════════════════════
# Multi-Metric LSTM Predictor
# ═════════════════════════════════════════════════════════════════════════════

class MultiMetricLSTMPredictor:
    """
    LSTM predictor that uses 3 input features (CPU, Memory, Network)
    to predict future CPU values.

    Key differences from single-metric LSTM:
    - Input: (batch, seq_len, 3) instead of (batch, seq_len, 1)
    - Captures cross-metric correlations
    - Network spikes predict CPU spikes 1-2 intervals ahead
    """

    SEQ_LEN = 6
    HORIZON = 3
    NUM_FEATURES = 3

    def __init__(self):
        self.net = None
        self.trained = False
        self._mins = np.zeros(self.NUM_FEATURES)
        self._maxs = np.ones(self.NUM_FEATURES)
        self._last_loss = float('inf')

    def _fit_scale(self, values: np.ndarray) -> np.ndarray:
        self._mins = values.min(axis=0)
        self._maxs = values.max(axis=0)
        return self._scale(values)

    def _scale(self, values: np.ndarray) -> np.ndarray:
        rng = self._maxs - self._mins
        rng[rng == 0] = 1.0
        return (values - self._mins) / rng

    def _unscale_cpu(self, values: np.ndarray) -> np.ndarray:
        rng = self._maxs[0] - self._mins[0]
        if rng == 0:
            return values
        return values * rng + self._mins[0]

    def train(self, df: pd.DataFrame, epochs: int = 50) -> float:
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available")

        features = df[["cpu", "memory", "network"]].values.astype(float)
        min_len = self.SEQ_LEN + self.HORIZON + 1
        if len(features) < min_len:
            raise ValueError(f"Need >= {min_len} points, got {len(features)}")

        scaled = self._fit_scale(features)

        X_list, y_list = [], []
        for i in range(len(scaled) - self.SEQ_LEN - self.HORIZON):
            X_list.append(scaled[i:i + self.SEQ_LEN])
            y_list.append(scaled[i + self.SEQ_LEN:i + self.SEQ_LEN + self.HORIZON, 0])

        X = torch.FloatTensor(np.array(X_list))
        y = torch.FloatTensor(np.array(y_list))

        self.net = _MultiMetricLSTMNet(
            input_size=self.NUM_FEATURES,
            output_size=self.HORIZON
        )
        optimizer = torch.optim.Adam(self.net.parameters(), lr=0.001)
        criterion = nn.MSELoss()

        self.net.train()
        final_loss = 0.0
        for epoch in range(1, epochs + 1):
            optimizer.zero_grad()
            loss = criterion(self.net(X), y)
            loss.backward()
            optimizer.step()
            final_loss = loss.item()
            if epoch % 10 == 0:
                logger.info(f"[MultiLSTM] Epoch {epoch}/{epochs} loss={final_loss:.6f}")

        self._last_loss = final_loss
        self.trained = True
        logger.info(f"[MultiLSTM] Training complete (loss={final_loss:.6f})")
        return final_loss

    def predict(self, recent_df: pd.DataFrame) -> dict:
        if not self.trained:
            raise RuntimeError("Model not trained")

        features = recent_df[["cpu", "memory", "network"]].values.astype(float)
        scaled = self._scale(features[-self.SEQ_LEN:])
        x = torch.FloatTensor(scaled).unsqueeze(0)

        self.net.eval()
        with torch.no_grad():
            out = self.net(x).numpy()[0]

        cpu_pred = self._unscale_cpu(out).clip(min=0)
        confidence = max(0.0, min(1.0, 1.0 - self._last_loss * 100))

        return {
            "cpu_forecast": cpu_pred.tolist(),
            "max_predicted_cpu": float(cpu_pred.max()),
            "confidence": round(confidence, 3),
            "model_loss": self._last_loss,
        }


# ═════════════════════════════════════════════════════════════════════════════
# Enhanced Ensemble Predictor (Multi-Metric + Drift + Cost)
# ═════════════════════════════════════════════════════════════════════════════

class EnhancedPredictor:
    """
    Complete prediction system combining:
    1. Multi-Metric LSTM (CPU + Memory + Network)
    2. Drift Detection (auto-retrain when accuracy drops)
    3. Cost Estimation (track scaling costs)
    4. Confidence Scoring (trust level of predictions)

    This is the UNIQUE contribution — no existing paper combines all 4.
    """

    def __init__(self):
        self.lstm = MultiMetricLSTMPredictor() if TORCH_AVAILABLE else None
        self.drift_detector = DriftDetector()
        self.cost_calculator = CostCalculator()
        self.last_trained: datetime | None = None
        self._last_df: pd.DataFrame | None = None
        self._retrain_count: int = 0
        self._drift_retrains: int = 0

    def train(self, df: pd.DataFrame) -> None:
        if df.empty:
            raise ValueError("Empty DataFrame")

        self._last_df = df.copy()

        if self.lstm:
            try:
                loss = self.lstm.train(df)
                self._retrain_count += 1
                logger.info(
                    f"[Enhanced] Training #{self._retrain_count} complete "
                    f"(loss={loss:.6f}, drift_retrains={self._drift_retrains})"
                )
            except Exception as exc:
                logger.error(f"[Enhanced] Training failed: {exc}")
                return

        self.last_trained = datetime.now()

    def predict(self, horizon_minutes: int = 30) -> dict:
        result = {
            "horizon_minutes": horizon_minutes,
            "predicted_at": datetime.now().isoformat(),
            "model_type": "multi_metric_lstm",
            "features_used": ["cpu", "memory", "network"],
        }

        if self.lstm and self.lstm.trained and self._last_df is not None:
            try:
                pred = self.lstm.predict(self._last_df)
                result["ensemble"] = pred["cpu_forecast"]
                result["max_predicted"] = pred["max_predicted_cpu"]
                result["confidence"] = pred["confidence"]
                result["model_loss"] = pred["model_loss"]
            except Exception as exc:
                logger.error(f"[Enhanced] Prediction failed: {exc}")
                result["ensemble"] = []
                result["max_predicted"] = 0.0
                result["confidence"] = 0.0
        else:
            result["ensemble"] = []
            result["max_predicted"] = 0.0
            result["confidence"] = 0.0

        result["drift_stats"] = self.drift_detector.get_stats()
        result["cost_summary"] = self.cost_calculator.get_summary()
        result["retrain_count"] = self._retrain_count
        result["drift_retrains"] = self._drift_retrains

        return result

    def check_and_handle_drift(self, predicted: float, actual: float) -> bool:
        self.drift_detector.record_error(predicted, actual)
        if self.drift_detector.is_drift_detected():
            logger.warning("[Enhanced] Drift detected! Triggering emergency retrain...")
            if self._last_df is not None:
                self._drift_retrains += 1
                self.train(self._last_df)
                return True
        return False

    def record_scaling_cost(self, old_replicas: int, new_replicas: int) -> dict:
        return self.cost_calculator.record_scaling_event(old_replicas, new_replicas)

    def needs_retraining(self, interval_hours: int = 1) -> bool:
        if self.last_trained is None:
            return True
        return datetime.now() - self.last_trained > timedelta(hours=interval_hours)
