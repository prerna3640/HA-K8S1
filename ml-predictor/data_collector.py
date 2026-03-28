"""
data_collector.py
-----------------
Fetches CPU and memory metrics from Prometheus for the web deployment pods.
These time series are used to train and update the ML forecasting model.
"""

import os
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090"
)


def _query_range(query: str, hours: int, step: str = "300") -> pd.DataFrame:
    """Generic Prometheus range query. Returns a DataFrame with columns [ds, y]."""
    end = datetime.now()
    start = end - timedelta(hours=hours)

    params = {
        "query": query,
        "start": start.timestamp(),
        "end": end.timestamp(),
        "step": step,  # 5-minute intervals by default
    }

    resp = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query_range",
        params=params,
        timeout=30
    )
    resp.raise_for_status()

    data = resp.json()
    if data["status"] != "success" or not data["data"]["result"]:
        return pd.DataFrame(columns=["ds", "y"])

    values = data["data"]["result"][0]["values"]
    df = pd.DataFrame(values, columns=["timestamp", "value"])
    df["ds"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_localize(None)
    df["y"] = df["value"].astype(float)
    return df[["ds", "y"]]


def fetch_cpu_metrics(hours: int = 168) -> pd.DataFrame:
    """
    Fetch total CPU usage rate (in CPU cores) for all web pods
    in the myapp namespace over the past `hours` hours.
    """
    query = (
        'sum(rate(container_cpu_usage_seconds_total'
        '{namespace="myapp", pod=~"web-.*", container="web"}[5m]))'
    )
    df = _query_range(query, hours)
    if not df.empty:
        logger.info(f"Fetched {len(df)} CPU data points from Prometheus")
    return df


def fetch_memory_metrics(hours: int = 168) -> pd.DataFrame:
    """
    Fetch total memory usage (MB) for all web pods over the past `hours` hours.
    """
    query = (
        'sum(container_memory_usage_bytes'
        '{namespace="myapp", pod=~"web-.*", container="web"})'
    )
    df = _query_range(query, hours)
    if not df.empty:
        # Convert bytes → MB
        df["y"] = df["y"] / (1024 * 1024)
        logger.info(f"Fetched {len(df)} memory data points from Prometheus")
    return df


def fetch_request_rate(hours: int = 168) -> pd.DataFrame:
    """
    Fetch HTTP request rate for web pods (if nginx metrics are available).
    Returns empty DataFrame if the metric does not exist.
    """
    query = 'sum(rate(nginx_http_requests_total{namespace="myapp"}[5m]))'
    try:
        df = _query_range(query, hours)
        if not df.empty:
            logger.info(f"Fetched {len(df)} request-rate data points from Prometheus")
        return df
    except Exception as e:
        logger.warning(f"Could not fetch request rate metrics: {e}")
        return pd.DataFrame(columns=["ds", "y"])
