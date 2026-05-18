# Multi-Metric LSTM with Drift Detection and Cost-Aware Proactive Auto-Scaling in Kubernetes

> M.Tech Research Project — School of Computer Science and Information Technology, DAVV Indore  
> Guide: Dr. Shraddha Masih | Author: Prerna Tank (2410512)

---

## Overview

This project implements a **proactive auto-scaling system** for Kubernetes that predicts workload demand before it happens, using a multi-metric LSTM deep learning model. Unlike the standard Kubernetes Horizontal Pod Autoscaler (HPA) which reacts only after CPU thresholds are breached, this system anticipates traffic spikes 60–90 seconds in advance and scales proactively.

---

## Key Results

Tested over 7 days with **412,341 real HTTP requests**:

| Metric | Standard HPA | This System | Improvement |
|---|---|---|---|
| SLA Violations | 0.021% | 0.0029% | **7× reduction** |
| P99 Latency | 287ms | 8.3ms | **34× faster** |
| Average Pods | 3.8 | 2.1 | **50% cost saving** |

---

## System Architecture

```
Traffic → Traefik Ingress → Web Application (2–10 replicas)
                                    ↑
                         Predictive Scaler (custom controller)
                                    ↑
                         ML Predictor (LSTM model via Flask API)
                                    ↑
                         Prometheus (metrics: CPU + Memory + Network I/O)
```

---

## Novel Contributions

1. **Multi-Metric LSTM** — 2-layer LSTM (hidden=64) trained on CPU%, Memory%, and Network I/O simultaneously. Network I/O serves as an early warning signal, rising 60–90 seconds before CPU spikes.

2. **MAPE-Based Drift Detection** — Sliding window of 20 predictions monitors MAPE. If MAPE > 50%, automatic retraining is triggered. 27 retrains occurred over the 7-day experiment.

3. **Confidence-Gated Fallback** — `confidence = 1.0 − training_loss × 100`. If confidence < 0.70, the system falls back to rule-based HPA to avoid bad-prediction damage.

4. **Cost-Aware Scaling** — Every scaling decision is logged with cost estimate at $0.05/pod/hour. Scale-down is conservative (cooldown + step-down) to prevent thrashing.

---

## Repository Structure

```
├── ml-predictor/          # PyTorch LSTM model + Flask prediction API
├── predictive-scaler/     # Custom Kubernetes controller (scale decisions)
├── k8s-configs/           # Kubernetes manifests (HPA, alerts)
├── gitops/                # ArgoCD GitOps application configs
├── grafana-dashboards/    # Grafana dashboard JSON configs
├── results/               # Ablation study experiment results (JSON)
├── docs/                  # Infrastructure and deployment documentation
├── thesis/research-paper/ # IEEE research paper + figures
└── Jenkinsfile            # 9-stage CI/CD pipeline
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Orchestration | Kubernetes v1.28, Containerd, Flannel CNI |
| Ingress | Traefik v2.x |
| ML Model | PyTorch, 2-layer LSTM, Flask REST API |
| Monitoring | Prometheus, Grafana, Alertmanager |
| CI/CD | Jenkins (9-stage pipeline) |
| GitOps | ArgoCD |
| Containerization | Docker, DockerHub |

---

## Ablation Study

Six configurations were tested to measure each component's contribution:

| Config | Description | SLA Violations |
|---|---|---|
| E1 | Full system (all components) | **0.0029%** |
| E2 | Without drift detection | 0.012% |
| E3 | Without confidence gate | 0.009% |
| E4 | CPU-only (no memory/network) | 0.018% |
| E5 | Without cost awareness | 0.003% |
| BASELINE | Standard Kubernetes HPA | 0.021% |

---

## Research Paper

Full IEEE-format research paper: [`thesis/research-paper/IEEE_Paper_Prerna_Tank.md`](thesis/research-paper/IEEE_Paper_Prerna_Tank.md)

Target venue: IEEE Access

---

## Cluster Setup

3-node Kubernetes cluster deployed on cloud VMs:
- 1 Master node (control plane + monitoring + CI/CD)
- 2 Worker nodes (application + ML workloads separated via nodeSelector)

Continuous uptime: 49+ days at time of writing.
