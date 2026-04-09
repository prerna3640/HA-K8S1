"""
conftest.py — Shared pytest fixtures for ml-predictor tests.
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def multi_metric_df():
    """
    Returns a multi-metric DataFrame (200 rows, 5-min intervals).
    Columns: ds (timestamp), cpu, memory, network
    Sufficient to train the MultiMetricLSTMPredictor.
    """
    n = 200
    end = datetime(2024, 1, 14, 12, 0, 0)
    start = end - timedelta(minutes=n * 5)
    timestamps = pd.date_range(start=start, periods=n, freq="5min")
    np.random.seed(42)
    cpu = 0.05 + 0.04 * np.sin(np.linspace(0, 4 * np.pi, n)) + np.random.normal(0, 0.005, n)
    cpu = np.clip(cpu, 0.005, 0.95)
    memory = 0.30 + 0.10 * np.sin(np.linspace(0, 2 * np.pi, n)) + np.random.normal(0, 0.02, n)
    memory = np.clip(memory, 0.05, 0.90)
    network = 100 + 50 * np.sin(np.linspace(0, 3 * np.pi, n)) + np.random.normal(0, 10, n)
    network = np.clip(network, 0, 500)
    return pd.DataFrame({
        "ds": timestamps,
        "cpu": cpu,
        "memory": memory,
        "network": network,
    })


@pytest.fixture
def tiny_metric_df():
    """Minimal 5-row DataFrame — too small for LSTM training."""
    timestamps = pd.date_range("2024-01-01", periods=5, freq="5min")
    return pd.DataFrame({
        "ds": timestamps,
        "cpu": [0.05, 0.06, 0.07, 0.06, 0.05],
        "memory": [0.30, 0.31, 0.32, 0.31, 0.30],
        "network": [100, 110, 120, 110, 100],
    })


@pytest.fixture
def flask_client(multi_metric_df):
    """
    Flask test client with mocked Prometheus.
    Model is NOT pre-trained (tests untrained state).
    """
    import data_collector
    from predictor_api import app, predictor

    def _mock_fetch_multi(hours=2):
        return multi_metric_df.copy()

    def _mock_fetch_cpu(hours=2):
        return multi_metric_df[["ds", "cpu"]].copy()

    data_collector.fetch_multi_metrics = _mock_fetch_multi
    data_collector.fetch_cpu_metrics = _mock_fetch_cpu

    predictor.last_trained = None
    predictor._retrain_count = 0

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client, predictor
