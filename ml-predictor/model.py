"""
model.py
--------
ML models for time series forecasting of Kubernetes workload metrics.

Two models are implemented:
  1. ProphetPredictor  – Facebook Prophet (handles daily/weekly seasonality well)
  2. LSTMPredictor     – PyTorch LSTM (better for short-term patterns)

EnsemblePredictor combines both outputs (average) and falls back gracefully
if a dependency is unavailable.
"""

import os
import pickle
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ── Optional dependency: Prophet ─────────────────────────────────────────────
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("prophet not installed – Prophet model disabled")

# ── Optional dependency: PyTorch ─────────────────────────────────────────────
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("torch not installed – LSTM model disabled")

MODEL_DIR = os.getenv("MODEL_DIR", "/models")


# ═════════════════════════════════════════════════════════════════════════════
# Prophet predictor
# ═════════════════════════════════════════════════════════════════════════════

class ProphetPredictor:
    """Facebook Prophet wrapper for long-horizon forecasting."""

    def __init__(self):
        self.model = None
        self.trained = False

    def train(self, df: pd.DataFrame) -> None:
        if len(df) < 10:
            raise ValueError(f"Need ≥10 data points, got {len(df)}")

        model = Prophet(
            changepoint_prior_scale=0.05,   # smooths trend changes
            seasonality_prior_scale=10,
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False,
            interval_width=0.95,
        )
        model.fit(df[["ds", "y"]])
        self.model = model
        self.trained = True
        logger.info(f"[Prophet] Trained on {len(df)} points")

    def predict(self, horizon_minutes: int = 30) -> pd.DataFrame:
        """Return DataFrame with columns [ds, yhat, yhat_lower, yhat_upper]."""
        if not self.trained:
            raise RuntimeError("Prophet model not trained")

        periods = max(1, horizon_minutes // 5)
        future = self.model.make_future_dataframe(periods=periods, freq="5min")
        forecast = self.model.predict(future)

        now = datetime.now()
        result = forecast[forecast["ds"] > now][
            ["ds", "yhat", "yhat_lower", "yhat_upper"]
        ].head(periods).copy()
        result["yhat"] = result["yhat"].clip(lower=0)
        return result

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        logger.info(f"[Prophet] Model saved → {path}")

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            self.model = pickle.load(f)
        self.trained = True
        logger.info(f"[Prophet] Model loaded ← {path}")


# ═════════════════════════════════════════════════════════════════════════════
# LSTM predictor
# ═════════════════════════════════════════════════════════════════════════════

class _LSTMNet(nn.Module):
    """Two-layer LSTM with a fully-connected output head."""

    def __init__(self, hidden_size: int = 64, num_layers: int = 2, output_size: int = 6):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=1,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2,
        )
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):                        # x: (batch, seq, 1)
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])            # (batch, output_size)


class LSTMPredictor:
    """
    LSTM-based predictor.

    Input  : last SEQ_LEN × 5-min samples   (2 hours of history)
    Output : next HORIZON × 5-min samples   (30 minutes of forecast)
    """

    SEQ_LEN = 24   # 24 × 5 min = 2 hours
    HORIZON = 6    # 6  × 5 min = 30 minutes

    def __init__(self):
        self.net = None
        self.trained = False
        self._min = 0.0
        self._max = 1.0

    # ── normalisation ────────────────────────────────────────────────────────

    def _fit_scale(self, values: np.ndarray) -> np.ndarray:
        self._min = float(values.min())
        self._max = float(values.max())
        return self._scale(values)

    def _scale(self, values: np.ndarray) -> np.ndarray:
        rng = self._max - self._min
        if rng == 0:
            return np.zeros_like(values, dtype=float)
        return (values - self._min) / rng

    def _unscale(self, values: np.ndarray) -> np.ndarray:
        return values * (self._max - self._min) + self._min

    # ── training ─────────────────────────────────────────────────────────────

    def train(self, df: pd.DataFrame, epochs: int = 50) -> None:
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available")
        min_len = self.SEQ_LEN + self.HORIZON + 1
        if len(df) < min_len:
            raise ValueError(f"Need ≥{min_len} data points, got {len(df)}")

        values = self._fit_scale(df["y"].values.astype(float))

        X_list, y_list = [], []
        for i in range(len(values) - self.SEQ_LEN - self.HORIZON):
            X_list.append(values[i : i + self.SEQ_LEN])
            y_list.append(values[i + self.SEQ_LEN : i + self.SEQ_LEN + self.HORIZON])

        X = torch.FloatTensor(np.array(X_list)).unsqueeze(-1)   # (N, SEQ, 1)
        y = torch.FloatTensor(np.array(y_list))                 # (N, HORIZON)

        self.net = _LSTMNet(output_size=self.HORIZON)
        optimizer = torch.optim.Adam(self.net.parameters(), lr=0.001)
        criterion = nn.MSELoss()

        self.net.train()
        for epoch in range(1, epochs + 1):
            optimizer.zero_grad()
            loss = criterion(self.net(X), y)
            loss.backward()
            optimizer.step()
            if epoch % 10 == 0:
                logger.info(f"[LSTM] Epoch {epoch}/{epochs}  loss={loss.item():.6f}")

        self.trained = True
        logger.info("[LSTM] Training complete")

    # ── inference ─────────────────────────────────────────────────────────────

    def predict(self, recent_values: np.ndarray) -> np.ndarray:
        if not self.trained:
            raise RuntimeError("LSTM model not trained")

        scaled = self._scale(recent_values[-self.SEQ_LEN :])
        x = torch.FloatTensor(scaled).unsqueeze(0).unsqueeze(-1)  # (1, SEQ, 1)

        self.net.eval()
        with torch.no_grad():
            out = self.net(x).numpy()[0]

        return self._unscale(out).clip(min=0)

    # ── persistence ───────────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save(
            {
                "state_dict": self.net.state_dict(),
                "min": self._min,
                "max": self._max,
            },
            path,
        )
        logger.info(f"[LSTM] Model saved → {path}")

    def load(self, path: str) -> None:
        ckpt = torch.load(path, map_location="cpu")
        self.net = _LSTMNet(output_size=self.HORIZON)
        self.net.load_state_dict(ckpt["state_dict"])
        self._min = ckpt["min"]
        self._max = ckpt["max"]
        self.trained = True
        logger.info(f"[LSTM] Model loaded ← {path}")


# ═════════════════════════════════════════════════════════════════════════════
# Ensemble predictor (Prophet + LSTM)
# ═════════════════════════════════════════════════════════════════════════════

class EnsemblePredictor:
    """
    Trains both Prophet and LSTM on the same data and averages their forecasts.
    Degrades gracefully: if one model fails, uses the other alone.
    """

    def __init__(self):
        self.prophet: ProphetPredictor | None = ProphetPredictor() if PROPHET_AVAILABLE else None
        self.lstm: LSTMPredictor | None = LSTMPredictor() if TORCH_AVAILABLE else None
        self.last_trained: datetime | None = None
        self._last_df: pd.DataFrame | None = None

    # ── training ─────────────────────────────────────────────────────────────

    def train(self, df: pd.DataFrame) -> None:
        if df.empty:
            raise ValueError("Empty DataFrame – nothing to train on")

        self._last_df = df.copy()

        if self.prophet:
            try:
                self.prophet.train(df)
            except Exception as exc:
                logger.error(f"[Prophet] training failed: {exc}")
                self.prophet = None

        if self.lstm:
            try:
                self.lstm.train(df)
            except Exception as exc:
                logger.error(f"[LSTM] training failed: {exc}")
                self.lstm = None

        if self.prophet is None and self.lstm is None:
            raise RuntimeError("Both models failed to train")

        self.last_trained = datetime.now()
        logger.info("[Ensemble] Training complete")

    # ── prediction ────────────────────────────────────────────────────────────

    def predict(self, horizon_minutes: int = 30) -> dict:
        """
        Returns a dict with keys:
          ensemble        – averaged forecast values (list of floats)
          prophet         – Prophet values (if available)
          lstm            – LSTM values (if available)
          timestamps      – ISO strings of forecast timestamps
          max_predicted   – maximum value in ensemble forecast
          horizon_minutes – requested horizon
          predicted_at    – UTC ISO timestamp
        """
        result: dict = {
            "horizon_minutes": horizon_minutes,
            "predicted_at": datetime.now().isoformat(),
        }

        # ── Prophet ──────────────────────────────────────────────────────────
        if self.prophet and self.prophet.trained:
            try:
                pf = self.prophet.predict(horizon_minutes)
                result["prophet"] = pf["yhat"].clip(lower=0).tolist()
                result["prophet_upper"] = pf["yhat_upper"].clip(lower=0).tolist()
                result["prophet_lower"] = pf["yhat_lower"].clip(lower=0).tolist()
                result["timestamps"] = pf["ds"].astype(str).tolist()
            except Exception as exc:
                logger.error(f"[Prophet] prediction error: {exc}")

        # ── LSTM ─────────────────────────────────────────────────────────────
        if self.lstm and self.lstm.trained and self._last_df is not None:
            try:
                recent = self._last_df["y"].values
                result["lstm"] = self.lstm.predict(recent).tolist()
            except Exception as exc:
                logger.error(f"[LSTM] prediction error: {exc}")

        # ── Ensemble (average) ────────────────────────────────────────────────
        prophet_vals = result.get("prophet", [])
        lstm_vals = result.get("lstm", [])

        if prophet_vals and lstm_vals:
            n = min(len(prophet_vals), len(lstm_vals))
            result["ensemble"] = [
                (prophet_vals[i] + lstm_vals[i]) / 2 for i in range(n)
            ]
        elif prophet_vals:
            result["ensemble"] = prophet_vals
        elif lstm_vals:
            result["ensemble"] = lstm_vals
        else:
            result["ensemble"] = []

        result["max_predicted"] = max(result["ensemble"]) if result["ensemble"] else 0.0
        return result

    # ── helpers ───────────────────────────────────────────────────────────────

    def needs_retraining(self, interval_hours: int = 1) -> bool:
        if self.last_trained is None:
            return True
        return datetime.now() - self.last_trained > timedelta(hours=interval_hours)
