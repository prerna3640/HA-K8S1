"""
test_model.py — Unit tests for model.py (Prophet, LSTM, Ensemble).
Tests the ML prediction logic without Prometheus or Kubernetes.
"""
import math
import pytest
import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) + "/..")

from model import ProphetPredictor, EnsemblePredictor


class TestProphetPredictor:
    """Test the Prophet forecasting model."""

    def test_train_succeeds_with_sufficient_data(self, synthetic_cpu_df):
        """Prophet trains without error when given >= 10 data points."""
        p = ProphetPredictor()
        p.train(synthetic_cpu_df)
        assert p.trained is True

    def test_train_raises_on_insufficient_data(self):
        """Prophet raises ValueError with fewer than 10 rows."""
        p = ProphetPredictor()
        tiny = pd.DataFrame({
            "ds": pd.date_range("2024-01-01", periods=5, freq="5min"),
            "y": [0.05] * 5
        })
        with pytest.raises(ValueError, match="Need"):
            p.train(tiny)

    def test_predict_returns_correct_horizon(self, synthetic_cpu_df):
        """predict(30) returns up to 6 rows (30 min / 5-min intervals)."""
        p = ProphetPredictor()
        p.train(synthetic_cpu_df)
        forecast = p.predict(horizon_minutes=30)
        assert len(forecast) <= 6
        assert len(forecast) > 0

    def test_predict_values_are_non_negative(self, synthetic_cpu_df):
        """All forecast CPU values must be >= 0."""
        p = ProphetPredictor()
        p.train(synthetic_cpu_df)
        forecast = p.predict(horizon_minutes=30)
        assert (forecast["yhat"] >= 0).all()

    def test_predict_raises_if_not_trained(self):
        """predict() raises RuntimeError if called before train()."""
        p = ProphetPredictor()
        with pytest.raises(RuntimeError, match="not trained"):
            p.predict()

    def test_predict_columns_present(self, synthetic_cpu_df):
        """Forecast DataFrame has expected columns."""
        p = ProphetPredictor()
        p.train(synthetic_cpu_df)
        forecast = p.predict(horizon_minutes=30)
        for col in ["ds", "yhat", "yhat_lower", "yhat_upper"]:
            assert col in forecast.columns


class TestEnsemblePredictor:
    """Test the ensemble predictor (combines Prophet + LSTM)."""

    def test_train_sets_last_trained_timestamp(self, synthetic_cpu_df):
        """After training, last_trained is a datetime."""
        from datetime import datetime
        ep = EnsemblePredictor()
        ep.train(synthetic_cpu_df)
        assert ep.last_trained is not None
        assert isinstance(ep.last_trained, datetime)

    def test_train_raises_on_empty_dataframe(self):
        """Training on empty DataFrame raises ValueError."""
        ep = EnsemblePredictor()
        with pytest.raises(ValueError, match="Empty"):
            ep.train(pd.DataFrame())

    def test_predict_returns_ensemble_key(self, synthetic_cpu_df):
        """Prediction dict contains 'ensemble' key."""
        ep = EnsemblePredictor()
        ep.train(synthetic_cpu_df)
        result = ep.predict(horizon_minutes=30)
        assert "ensemble" in result

    def test_predict_ensemble_is_list(self, synthetic_cpu_df):
        """ensemble forecast is a non-empty list of floats."""
        ep = EnsemblePredictor()
        ep.train(synthetic_cpu_df)
        result = ep.predict(horizon_minutes=30)
        assert isinstance(result["ensemble"], list)
        assert len(result["ensemble"]) > 0

    def test_predict_max_predicted_non_negative(self, synthetic_cpu_df):
        """max_predicted value >= 0."""
        ep = EnsemblePredictor()
        ep.train(synthetic_cpu_df)
        result = ep.predict(horizon_minutes=30)
        assert result["max_predicted"] >= 0.0

    def test_needs_retraining_true_before_training(self):
        """Fresh predictor always needs retraining."""
        ep = EnsemblePredictor()
        assert ep.needs_retraining(interval_hours=1) is True

    def test_needs_retraining_false_immediately_after_training(self, synthetic_cpu_df):
        """Immediately after training, needs_retraining(1h) is False."""
        ep = EnsemblePredictor()
        ep.train(synthetic_cpu_df)
        assert ep.needs_retraining(interval_hours=1) is False


class TestReplicaCalculation:
    """Test the scaling formula from the predictive controller."""

    @staticmethod
    def _desired_replicas(max_cpu, cpu_per_replica=0.10,
                          scale_up_buffer=0.80,
                          min_replicas=2, max_replicas=5):
        """Mirror of PredictiveController._desired_replicas()."""
        effective_capacity = cpu_per_replica * scale_up_buffer
        if effective_capacity <= 0:
            return min_replicas
        desired = math.ceil(max_cpu / effective_capacity)
        return max(min_replicas, min(desired, max_replicas))

    def test_zero_cpu_returns_min_replicas(self):
        assert self._desired_replicas(0.0) == 2

    def test_low_cpu_returns_min_replicas(self):
        assert self._desired_replicas(0.05) == 2

    def test_medium_cpu_scales_up(self):
        # 0.20 / (0.10 * 0.80) = ceil(2.5) = 3
        assert self._desired_replicas(0.20) == 3

    def test_high_cpu_reaches_max(self):
        # 0.50 / 0.08 = ceil(6.25) → clamped to 5
        assert self._desired_replicas(0.50) == 5

    def test_result_never_exceeds_max_replicas(self):
        assert self._desired_replicas(999.0) == 5

    def test_result_never_below_min_replicas(self):
        assert self._desired_replicas(0.0) == 2
