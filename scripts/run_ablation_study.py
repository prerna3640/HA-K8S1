"""
Ablation Study Runner for IEEE Paper
Runs 5 experiment configurations and generates results for Section VI.

Usage:
    python scripts/run_ablation_study.py --duration 3600 --output results/ablation.json

Configurations:
    E1: Full system (all 4 contributions)
    E2: Full system - Drift Detection
    E3: Full system - Confidence Gate
    E4: Full system - Multi-Metric (CPU only)
    E5: Full system - Cost Awareness
    BASELINE: Default Kubernetes HPA
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


PREDICTOR_URL = os.getenv("PREDICTOR_URL", "http://10.0.1.114:30050")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://10.0.1.7:30090")
COST_PER_POD_HOUR = 0.05


def configure_experiment(name: str):
    """Set env vars on predictor/scaler for each experiment."""
    configs = {
        "E1_full": {
            "ENABLE_DRIFT": "true",
            "ENABLE_CONFIDENCE_GATE": "true",
            "NUM_FEATURES": "3",
            "ENABLE_COST": "true",
        },
        "E2_no_drift": {
            "ENABLE_DRIFT": "false",
            "ENABLE_CONFIDENCE_GATE": "true",
            "NUM_FEATURES": "3",
            "ENABLE_COST": "true",
        },
        "E3_no_confidence": {
            "ENABLE_DRIFT": "true",
            "ENABLE_CONFIDENCE_GATE": "false",
            "NUM_FEATURES": "3",
            "ENABLE_COST": "true",
        },
        "E4_cpu_only": {
            "ENABLE_DRIFT": "true",
            "ENABLE_CONFIDENCE_GATE": "true",
            "NUM_FEATURES": "1",
            "ENABLE_COST": "true",
        },
        "E5_no_cost": {
            "ENABLE_DRIFT": "true",
            "ENABLE_CONFIDENCE_GATE": "true",
            "NUM_FEATURES": "3",
            "ENABLE_COST": "false",
        },
        "BASELINE_hpa": {
            "ENABLE_DRIFT": "false",
            "ENABLE_CONFIDENCE_GATE": "false",
            "NUM_FEATURES": "0",
            "ENABLE_COST": "false",
            "USE_HPA_ONLY": "true",
        },
    }
    return configs.get(name)


def measure_latency(url: str, duration_sec: int, rps: int) -> dict:
    """Generate load and measure SLA violations."""
    total = 0
    violations_200ms = 0
    violations_500ms = 0
    latencies = []
    end_time = time.time() + duration_sec

    while time.time() < end_time:
        start = time.time()
        try:
            r = requests.get(url, timeout=2.0)
            latency_ms = (time.time() - start) * 1000
            latencies.append(latency_ms)
            total += 1
            if latency_ms > 200:
                violations_200ms += 1
            if latency_ms > 500:
                violations_500ms += 1
        except requests.RequestException:
            total += 1
            violations_200ms += 1
            violations_500ms += 1
        time.sleep(1.0 / rps)

    return {
        "total_requests": total,
        "sla_200ms_violations": violations_200ms,
        "sla_500ms_violations": violations_500ms,
        "violation_pct_200ms": (violations_200ms / total * 100) if total else 0,
        "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
        "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
        "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0,
    }


def get_cost_summary() -> dict:
    """Fetch cost summary from predictor."""
    try:
        r = requests.get(f"{PREDICTOR_URL}/cost/summary", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e), "total_cost_usd": 0.0}


def get_drift_events() -> dict:
    """Fetch drift detection events from predictor."""
    try:
        r = requests.get(f"{PREDICTOR_URL}/drift", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e), "drift_events": 0}


def run_experiment(name: str, duration_sec: int, web_url: str, rps: int) -> dict:
    """Run a single experiment configuration."""
    print(f"\n{'=' * 60}")
    print(f"Experiment: {name}")
    print(f"Duration: {duration_sec}s  |  Load: {rps} req/s")
    print(f"{'=' * 60}")

    config = configure_experiment(name)
    if config is None:
        print(f"Unknown experiment: {name}")
        return {}

    print(f"Config: {config}")
    print("Apply these env vars on the cluster, then press ENTER to start load test")
    input()

    latency_metrics = measure_latency(web_url, duration_sec, rps)
    cost_summary = get_cost_summary()
    drift_summary = get_drift_events()

    result = {
        "experiment": name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_sec": duration_sec,
        "config": config,
        "latency": latency_metrics,
        "cost": cost_summary,
        "drift": drift_summary,
    }

    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description="IEEE Paper Ablation Study")
    parser.add_argument("--duration", type=int, default=1800, help="Seconds per experiment (default 1800 = 30min)")
    parser.add_argument("--rps", type=int, default=50, help="Requests per second load")
    parser.add_argument("--web-url", default="http://10.0.1.105:30080/", help="Web service URL")
    parser.add_argument("--output", default="results/ablation_study.json", help="Output JSON path")
    parser.add_argument("--experiments", nargs="+",
                        default=["E1_full", "E2_no_drift", "E3_no_confidence",
                                 "E4_cpu_only", "E5_no_cost", "BASELINE_hpa"],
                        help="Which experiments to run")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    for exp in args.experiments:
        result = run_experiment(exp, args.duration, args.web_url, args.rps)
        results.append(result)
        with out_path.open("w") as f:
            json.dump(results, f, indent=2)
        print(f"\nIntermediate results saved to {out_path}")

    print(f"\n{'=' * 60}")
    print("ALL EXPERIMENTS COMPLETE")
    print(f"{'=' * 60}")

    print("\nSummary Table:")
    print(f"{'Experiment':<25} {'SLA Viol %':<12} {'Avg Lat ms':<12} {'Cost $':<10}")
    print("-" * 60)
    for r in results:
        exp = r.get("experiment", "?")
        viol = r.get("latency", {}).get("violation_pct_200ms", 0)
        lat = r.get("latency", {}).get("avg_latency_ms", 0)
        cost = r.get("cost", {}).get("total_cost_usd", 0)
        print(f"{exp:<25} {viol:<12.2f} {lat:<12.2f} {cost:<10.4f}")

    print(f"\nResults saved to: {out_path.absolute()}")
    print("Copy these numbers into Section VI of IEEE_Paper_Prerna_Tank.md")


if __name__ == "__main__":
    main()
