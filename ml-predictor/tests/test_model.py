"""
test_model.py — Unit tests for model.py
Tests: DriftDetector, CostCalculator, EnhancedPredictor, replica formula.
"""
import math
import pytest
import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from model import DriftDetector, CostCalculator, EnhancedPredictor


class TestDriftDetector:
    """Test the drift detection component."""

    def test_no_drift_with_empty_errors(self):
        dd = DriftDetector()
        assert dd.is_drift_detected() is False

    def test_no_drift_with_low_errors(self):
        dd = DriftDetector()
        for _ in range(10):
            dd.record_error(predicted=0.05, actual=0.05)
        assert dd.is_drift_detected() is False

    def test_drift_detected_with_high_errors(self):
        dd = DriftDetector()
        for _ in range(10):
            dd.record_error(predicted=0.90, actual=0.10)
        assert dd.is_drift_detected() is True

    def test_stats_returns_dict(self):
        dd = DriftDetector()
        stats = dd.get_stats()
        assert "window_size" in stats
        assert "mean_error" in stats
        assert "drift_count" in stats

    def test_record_error_skips_near_zero_actual(self):
        dd = DriftDetector()
        dd.record_error(predicted=0.05, actual=0.0001)
        assert dd.get_stats()["window_size"] == 0


class TestCostCalculator:
    """Test the cost estimation component."""

    def test_estimate_cost_single_pod(self):
        cc = CostCalculator(cost_per_pod_per_hour=0.05)
        cost = cc.estimate_cost(replicas=1, duration_hours=1.0)
        assert cost == pytest.approx(0.05)

    def test_estimate_cost_multiple_pods(self):
        cc = CostCalculator(cost_per_pod_per_hour=0.05)
        cost = cc.estimate_cost(replicas=5, duration_hours=2.0)
        assert cost == pytest.approx(0.50)

    def test_record_scaling_event_returns_dict(self):
        cc = CostCalculator()
        event = cc.record_scaling_event(old_replicas=2, new_replicas=4)
        assert "old_replicas" in event
        assert "new_replicas" in event
        assert "cost_change_per_hour" in event

    def test_summary_empty_when_no_events(self):
        cc = CostCalculator()
        summary = cc.get_summary()
        assert summary["total_events"] == 0

    def test_summary_counts_scale_ups(self):
        cc = CostCalculator()
        cc.record_scaling_event(2, 4)
        cc.record_scaling_event(4, 3)
        summary = cc.get_summary()
        assert summary["scale_ups"] == 1
        assert summary["scale_downs"] == 1


class TestEnhancedPredictor:
    """Test the main EnhancedPredictor (multi-metric LSTM + drift + cost)."""

    def test_needs_retraining_true_before_training(self):
        ep = EnhancedPredictor()
        assert ep.needs_retraining(interval_hours=1) is True

    def test_train_raises_on_empty_dataframe(self):
        ep = EnhancedPredictor()
        with pytest.raises(ValueError, match="Empty"):
            ep.train(pd.DataFrame())

    def test_train_sets_last_trained(self, multi_metric_df):
        from datetime import datetime
        ep = EnhancedPredictor()
        ep.train(multi_metric_df)
        assert ep.last_trained is not None
        assert isinstance(ep.last_trained, datetime)

    def test_needs_retraining_false_after_training(self, multi_metric_df):
        ep = EnhancedPredictor()
        ep.train(multi_metric_df)
        assert ep.needs_retraining(interval_hours=1) is False

    def test_predict_returns_dict_with_keys(self, multi_metric_df):
        ep = EnhancedPredictor()
        ep.train(multi_metric_df)
        result = ep.predict(horizon_minutes=30)
        assert "ensemble" in result
        assert "max_predicted" in result
        assert "drift_stats" in result
        assert "cost_summary" in result

    def test_predict_ensemble_is_list(self, multi_metric_df):
        ep = EnhancedPredictor()
        ep.train(multi_metric_df)
        result = ep.predict(horizon_minutes=30)
        assert isinstance(result["ensemble"], list)

    def test_predict_max_predicted_non_negative(self, multi_metric_df):
        ep = EnhancedPredictor()
        ep.train(multi_metric_df)
        result = ep.predict(horizon_minutes=30)
        assert result["max_predicted"] >= 0.0

    def test_record_scaling_cost(self):
        ep = EnhancedPredictor()
        event = ep.record_scaling_cost(old_replicas=2, new_replicas=4)
        assert event["new_replicas"] == 4


class TestReplicaCalculation:
    """Test the scaling formula from the predictive controller."""

    @staticmethod
    def _desired_replicas(max_cpu, cpu_per_replica=0.10,
                          scale_up_buffer=0.80,
                          min_replicas=2, max_replicas=5):
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
        assert self._desired_replicas(0.20) == 3

    def test_high_cpu_reaches_max(self):
        assert self._desired_replicas(0.50) == 5

    def test_result_never_exceeds_max_replicas(self):
        assert self._desired_replicas(999.0) == 5

    def test_result_never_below_min_replicas(self):
        assert self._desired_replicas(0.0) == 2
