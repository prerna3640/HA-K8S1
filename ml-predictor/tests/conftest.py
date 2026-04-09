"""
conftest.py — Shared pytest fixtures for ml-predictor tests.
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


@pytest.fixture
def synthetic_cpu_df():
    """
    Returns a realistic CPU DataFrame (200 rows, 5-min intervals).
    Sufficient to train both Prophet and LSTM models.
    """
    n = 200
    end = datetime(2024, 1, 14, 12, 0, 0)
    start = end - timedelta(minutes=n * 5)
    timestamps = pd.date_range(start=start, periods=n, freq="5min")
    np.random.seed(42)
    values = 0.05 + 0.04 * np.sin(np.linspace(0, 4 * np.pi, n)) + \
             np.random.normal(0, 0.005, n)
    values = np.clip(values, 0.005, None)
    return pd.DataFrame({"ds": timestamps, "y": values})


@pytest.fixture
def tiny_cpu_df():
    """Minimal 10-row DataFrame — edge case testing."""
    timestamps = pd.date_range("2024-01-01", periods=10, freq="5min")
    values = [0.05, 0.06, 0.07, 0.06, 0.05, 0.08, 0.09, 0.07, 0.06, 0.05]
    return pd.DataFrame({"ds": timestamps, "y": values})


@pytest.fixture
def flask_client():
    """
    Flask test client with mocked Prometheus.
    Model is NOT pre-trained (tests untrained state).
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__) + "/..")

    import data_collector
    from predictor_api import app, predictor

    def _mock_fetch(hours=168):
        timestamps = pd.date_range("2024-01-01", periods=50, freq="5min")
        values = np.random.uniform(0.03, 0.12, 50)
        return pd.DataFrame({"ds": timestamps, "y": values})

    data_collector.fetch_cpu_metrics = _mock_fetch

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client, predictor
