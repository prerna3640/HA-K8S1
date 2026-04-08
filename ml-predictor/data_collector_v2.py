"""
data_collector_v2.py
--------------------
Multi-metric data collector for Kubernetes workload prediction.
Fetches CPU, Memory, and Network metrics from Prometheus.
Returns a multi-feature DataFrame for the MultiMetric LSTM model.

UNIQUE CONTRIBUTION: Unlike existing papers that use single-metric (CPU only),
this collector provides 3 correlated metrics for richer prediction.
"""

import os
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090"
)


def _query_range(query: str, hours: int, step: str = "300") -> pd.DataFrame:
    end = datetime.now()
    start = end - timedelta(hours=hours)
    params = {
        "query": query,
        "start": start.timestamp(),
        "end": end.timestamp(),
        "step": step,
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


def fetch_cpu_metrics(hours: int = 2) -> pd.DataFrame:
    query = (
        'sum(rate(container_cpu_usage_seconds_total'
        '{namespace="myapp", pod=~"web-.*", container="web"}[5m]))'
    )
    df = _query_range(query, hours)
    if not df.empty:
        logger.info(f"[CPU] Fetched {len(df)} data points")
    return df


def fetch_memory_metrics(hours: int = 2) -> pd.DataFrame:
    query = (
        'sum(container_memory_usage_bytes'
        '{namespace="myapp", pod=~"web-.*", container="web"}) / 1024 / 1024'
    )
    df = _query_range(query, hours)
    if not df.empty:
        logger.info(f"[Memory] Fetched {len(df)} data points")
    return df


def fetch_network_metrics(hours: int = 2) -> pd.DataFrame:
    query = (
        'sum(rate(container_network_receive_bytes_total'
        '{namespace="myapp", pod=~"web-.*"}[5m])) / 1024'
    )
    df = _query_range(query, hours)
    if not df.empty:
        logger.info(f"[Network] Fetched {len(df)} data points")
    return df


def fetch_multi_metrics(hours: int = 2) -> pd.DataFrame:
    """
    Fetch CPU, Memory, and Network metrics and merge into a single DataFrame.
    Returns DataFrame with columns: [ds, cpu, memory, network]

    This multi-metric approach captures correlations between resource types
    that single-metric models miss. For example, a network spike often
    precedes a CPU spike by 1-2 intervals.
    """
    cpu_df = fetch_cpu_metrics(hours)
    mem_df = fetch_memory_metrics(hours)
    net_df = fetch_network_metrics(hours)

    if cpu_df.empty:
        logger.warning("No CPU data available")
        return pd.DataFrame(columns=["ds", "cpu", "memory", "network"])

    result = cpu_df.rename(columns={"y": "cpu"})

    if not mem_df.empty:
        mem_df = mem_df.rename(columns={"y": "memory"})
        result = result.merge(mem_df[["ds", "memory"]], on="ds", how="left")
    else:
        result["memory"] = 0.0

    if not net_df.empty:
        net_df = net_df.rename(columns={"y": "network"})
        result = result.merge(net_df[["ds", "network"]], on="ds", how="left")
    else:
        result["network"] = 0.0

    result = result.fillna(0.0)
    logger.info(
        f"[MultiMetric] {len(result)} points | "
        f"CPU: {result['cpu'].mean():.4f} | "
        f"Mem: {result['memory'].mean():.1f}MB | "
        f"Net: {result['network'].mean():.1f}KB/s"
    )
    return result
