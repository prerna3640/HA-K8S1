"""
test_predictor_api.py — Unit tests for Flask REST API in predictor_api.py.
Uses Flask test client with mocked Prometheus.
"""
import json
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_returns_503_when_model_not_trained(self, flask_client):
        client, predictor = flask_client
        predictor.last_trained = None
        resp = client.get("/health")
        assert resp.status_code == 503

    def test_health_returns_200_after_training(self, flask_client, multi_metric_df):
        client, predictor = flask_client
        predictor.train(multi_metric_df)
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_is_valid_json(self, flask_client):
        client, _ = flask_client
        resp = client.get("/health")
        data = json.loads(resp.data)
        assert "status" in data
        assert data["status"] == "ok"

    def test_health_reports_model_trained_flag(self, flask_client, multi_metric_df):
        client, predictor = flask_client
        predictor.train(multi_metric_df)
        resp = client.get("/health")
        data = json.loads(resp.data)
        assert data["model_trained"] is True


class TestPredictEndpoint:
    """Test /predict endpoint."""

    def test_predict_returns_503_when_not_trained(self, flask_client):
        client, predictor = flask_client
        predictor.last_trained = None
        resp = client.get("/predict")
        assert resp.status_code == 503

    def test_predict_returns_200_when_trained(self, flask_client, multi_metric_df):
        client, predictor = flask_client
        predictor.train(multi_metric_df)
        resp = client.get("/predict")
        assert resp.status_code == 200

    def test_predict_response_contains_ensemble(self, flask_client, multi_metric_df):
        client, predictor = flask_client
        predictor.train(multi_metric_df)
        resp = client.get("/predict")
        data = json.loads(resp.data)
        assert "ensemble" in data
        assert isinstance(data["ensemble"], list)

    def test_predict_invalid_horizon_returns_400(self, flask_client):
        client, _ = flask_client
        resp = client.get("/predict?horizon=abc")
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "error" in data


class TestDriftEndpoint:
    """Test /drift endpoint."""

    def test_drift_returns_200(self, flask_client):
        client, _ = flask_client
        resp = client.get("/drift")
        assert resp.status_code == 200

    def test_drift_contains_stats(self, flask_client):
        client, _ = flask_client
        resp = client.get("/drift")
        data = json.loads(resp.data)
        assert "drift_stats" in data


class TestCostEndpoint:
    """Test /cost endpoint."""

    def test_cost_returns_200(self, flask_client):
        client, _ = flask_client
        resp = client.get("/cost")
        assert resp.status_code == 200

    def test_cost_contains_total_events(self, flask_client):
        client, _ = flask_client
        resp = client.get("/cost")
        data = json.loads(resp.data)
        assert "total_events" in data
