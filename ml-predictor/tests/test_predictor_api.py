"""
test_predictor_api.py — Unit tests for Flask REST API in predictor_api.py.
Uses Flask test client with mocked Prometheus.
"""
import json
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__) + "/..")


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_returns_503_when_model_not_trained(self, flask_client):
        """
        /health returns HTTP 503 when model has not been trained yet.
        Correct initial state before retraining loop runs.
        """
        client, predictor = flask_client
        predictor.last_trained = None
        resp = client.get("/health")
        assert resp.status_code == 503

    def test_health_returns_200_after_training(self, flask_client, synthetic_cpu_df):
        """
        /health returns HTTP 200 after model is trained.
        """
        client, predictor = flask_client
        predictor.train(synthetic_cpu_df)
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_is_valid_json(self, flask_client):
        """Response body is valid JSON."""
        client, _ = flask_client
        resp = client.get("/health")
        data = json.loads(resp.data)
        assert "status" in data
        assert data["status"] == "ok"

    def test_health_reports_model_trained_flag(self, flask_client, synthetic_cpu_df):
        """Response JSON includes model_trained boolean."""
        client, predictor = flask_client
        predictor.train(synthetic_cpu_df)
        resp = client.get("/health")
        data = json.loads(resp.data)
        assert data["model_trained"] is True


class TestPredictEndpoint:
    """Test /predict endpoint."""

    def test_predict_returns_503_when_not_trained(self, flask_client):
        """/predict returns HTTP 503 before model is trained."""
        client, predictor = flask_client
        predictor.last_trained = None
        resp = client.get("/predict")
        assert resp.status_code == 503

    def test_predict_returns_200_when_trained(self, flask_client, synthetic_cpu_df):
        """/predict returns HTTP 200 after training."""
        client, predictor = flask_client
        predictor.train(synthetic_cpu_df)
        resp = client.get("/predict")
        assert resp.status_code == 200

    def test_predict_response_contains_ensemble(self, flask_client, synthetic_cpu_df):
        """/predict JSON contains 'ensemble' key with non-empty list."""
        client, predictor = flask_client
        predictor.train(synthetic_cpu_df)
        resp = client.get("/predict")
        data = json.loads(resp.data)
        assert "ensemble" in data
        assert isinstance(data["ensemble"], list)
        assert len(data["ensemble"]) > 0

    def test_predict_invalid_horizon_returns_400(self, flask_client):
        """/predict?horizon=abc returns HTTP 400."""
        client, _ = flask_client
        resp = client.get("/predict?horizon=abc")
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "error" in data

    def test_predict_horizon_clamped_to_range(self, flask_client, synthetic_cpu_df):
        """Horizon outside [5, 120] is silently clamped, not errored."""
        client, predictor = flask_client
        predictor.train(synthetic_cpu_df)
        resp = client.get("/predict?horizon=999")
        assert resp.status_code == 200
