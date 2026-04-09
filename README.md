# Intelligent Auto-Scaling in Kubernetes

**A Multi-Metric LSTM Approach with Drift Detection, Cost-Aware Scaling, and End-to-End DevOps Pipeline**

---

**Author:** Prerna Tank | **Roll No:** 2410512 | **Degree:** M.Tech (Computer Science)  
**University:** DAVV (Devi Ahilya Vishwavidyalaya), Indore  
**Advisor:** Dr. Shraddha Masih  
**Year:** 2026

**GitHub:** https://github.com/prerna3640/HA-K8S1

---

## Problem

Kubernetes Horizontal Pod Autoscaler (HPA) is **reactive** — it scales pods AFTER load arrives, causing:
- **~120 second delay** before new pods are ready
- SLA violations during traffic spikes
- Resource waste from over-provisioning as a safety buffer

## Solution

**Predictive Auto-Scaling:** An LSTM neural network forecasts CPU load **30 minutes ahead** and scales pods proactively — before the load arrives.

## 4 Research Contributions (No Prior Paper Has All 4)

| # | Innovation | What It Does | Why It Matters |
|---|-----------|-------------|---------------|
| 1 | **Multi-Metric LSTM** | Uses CPU + Memory + Network as input (3 features) | Network spikes predict CPU spikes 1–2 intervals ahead |
| 2 | **Drift Detection** | Monitors prediction accuracy, auto-retrains when MAPE > 50% | Prevents stale models from making wrong scaling decisions |
| 3 | **Cost-Aware Scaling** | Tracks $ per scaling decision ($0.05/pod/hr) | Enables ROI analysis of ML predictions vs reactive HPA |
| 4 | **Confidence-Gated Self-Healing** | Falls back to HPA when model confidence < 70% | Safety net — uncertain predictions don't cause bad scaling |

**Gap Analysis:** We reviewed 10 recent papers (2021–2026) from IEEE, ACM, Springer, Elsevier, and arXiv. No single paper combines all 4 contributions. See [presentation/REFERENCES_AND_GAP_ANALYSIS.md](presentation/REFERENCES_AND_GAP_ANALYSIS.md) for the full literature review.

---

## Results

| Metric | Reactive HPA | Predictive ML (Ours) | Improvement |
|--------|:---:|:---:|:---:|
| Scaling Delay | ~120s | 0s | **100% eliminated** |
| Peak CPU per Pod | 141m | 65m | **54% reduction** |
| User Impact | ~2 min downtime | 0s | **Eliminated** |
| Cost Savings (10 days) | — | ~₹2,450 (~$29) | — |

---

## Architecture

```
                          CI/CD Pipeline (Jenkins)
                    ┌──────────────────────────────────┐
 Git Push           │  Checkout → Unit Tests → flake8  │
 ────────►  GitHub ─┤  → Build Images → Transfer       │
                    │  → Update Manifests → ArgoCD Sync │
                    └──────────┬───────────────────────┘
                               │
                    ┌──────────▼───────────────────────┐
                    │        ArgoCD (GitOps)            │
                    │  Auto-sync manifests from GitHub  │
                    └──────────┬───────────────────────┘
                               │
              ┌────────────────▼────────────────────┐
              │       Kubernetes Cluster (3 nodes)   │
              │                                      │
              │  ┌──────────┐  ┌──────────────────┐ │
              │  │ Frontend │  │  ML Predictor     │ │
              │  │ (nginx)  │  │  (Flask + LSTM)   │ │
              │  └──────────┘  └────────┬─────────┘ │
              │                         │            │
              │  ┌──────────────────────▼─────────┐ │
              │  │  Predictive Scaler              │ │
              │  │  (Confidence gate → K8s API)    │ │
              │  └────────────────────────────────┘ │
              │                                      │
              │  Prometheus ──► Grafana (monitoring) │
              └─────────────────────────────────────┘
```

---

## Repository Structure

```
HA-K8S1/
├── ml-predictor/                  # LSTM prediction service
│   ├── model.py                   # Multi-Metric LSTM + Drift + Cost
│   ├── predictor_api.py           # Flask REST API (/predict, /health, /drift, /cost)
│   ├── data_collector.py          # Prometheus multi-metric fetcher
│   ├── Dockerfile                 # Container image
│   ├── requirements.txt           # Python dependencies
│   ├── tests/                     # 21 pytest unit tests
│   │   ├── conftest.py            # Fixtures (multi_metric_df, flask_client)
│   │   ├── test_model.py          # DriftDetector, CostCalculator, EnhancedPredictor
│   │   └── test_predictor_api.py  # /health, /predict, /drift, /cost endpoints
│   └── k8s/                       # Kubernetes manifests
│       ├── deployment.yaml
│       └── service.yaml
│
├── predictive-scaler/             # Custom Kubernetes scaling controller
│   ├── controller.py              # Confidence-gated scaling logic
│   ├── scaler.py                  # K8s API wrapper
│   ├── Dockerfile
│   ├── requirements.txt
│   └── k8s/
│       ├── deployment.yaml
│       └── rbac.yaml
│
├── gitops/                        # GitOps infrastructure
│   ├── applications/myapp/        # Web frontend (nginx, 2–5 replicas)
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml
│   └── argocd/
│       └── myapp-application.yaml # ArgoCD Application CRDs
│
├── Jenkinsfile                    # 9-stage CI/CD pipeline
├── .flake8                        # PEP 8 config (max-line-length=100)
│
├── k8s-configs/                   # Cluster-wide K8s configs
│   ├── hpa.yaml                   # HPA safety net (70% CPU threshold)
│   └── alert-rules.yaml           # Prometheus alerting rules
│
├── grafana-dashboards/            # 5 Grafana dashboard JSONs
├── scripts/                       # Deployment & utility scripts
│   ├── deploy.sh                  # Full cluster deployment
│   ├── deploy-frontend.sh         # Frontend deployment
│   ├── demo_proof.sh              # Research proof demo
│   └── thesis_chart.py            # Performance chart generator
│
├── thesis/research-paper/
│   └── main.tex                   # IEEE format research paper
│
├── presentation/
│   ├── thesis-presentation.html   # 21-slide interactive presentation
│   └── REFERENCES_AND_GAP_ANALYSIS.md  # 10 papers literature review
│
├── docs/                          # Documentation
│   ├── PROJECT_README.md          # Detailed project overview
│   ├── END_TO_END_DEVOPS_SETUP.md # CI/CD pipeline guide
│   ├── 3NODE_DEPLOYMENT.md        # Cluster setup guide
│   └── guides/                    # Step-by-step guides
│
└── legacy/                        # Archived configs & backups
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **ML Model** | PyTorch LSTM (Multi-Metric, 2-layer, 64 hidden units) |
| **API** | Python 3.11, Flask, Gunicorn |
| **CI/CD** | Jenkins (9-stage pipeline) |
| **GitOps** | ArgoCD v2.10 (auto-sync from GitHub) |
| **Container Runtime** | containerd + nerdctl (no Docker daemon) |
| **Orchestration** | Kubernetes 1.30.14 (3-node cluster) |
| **Monitoring** | Prometheus + Grafana + Loki |
| **Testing** | pytest (21 unit tests), flake8 (PEP 8) |
| **Ingress** | Traefik |
| **Notifications** | Telegram Bot |

---

## Infrastructure

| Node | Role | Services |
|------|------|----------|
| **Master** | Control Plane | Jenkins, ArgoCD, K8s API |
| **Worker-App** | Application | Web frontend, Predictive Scaler |
| **Worker-Data** | Data/ML | ML Predictor, Prometheus, Grafana |

---

## CI/CD Pipeline (Jenkins — 9 Stages)

```
┌──────────┬────────────┬─────────────┬──────────────┬──────────────┐
│ Checkout │ Unit Tests │   Static    │  Build ML    │  Build       │
│          │ (pytest)   │  Analysis   │  Predictor   │  Scaler      │
│          │ 21 tests   │  (flake8)   │  (nerdctl)   │  (nerdctl)   │
├──────────┼────────────┼─────────────┼──────────────┼──────────────┤
│ Transfer │  Update    │  ArgoCD     │   Verify     │  Telegram    │
│ to       │  GitOps    │   Sync      │  Deployment  │  Notify      │
│ Workers  │  Manifests │             │              │              │
└──────────┴────────────┴─────────────┴──────────────┴──────────────┘
```

**Flow:** Code push → Jenkins auto-triggers → Tests pass → Images built → Manifests updated → ArgoCD syncs → Pods updated → Telegram notification

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/prerna3640/HA-K8S1.git
cd HA-K8S1
```

### 2. Run Unit Tests

```bash
cd ml-predictor
pip install pytest flask pandas numpy torch --index-url https://download.pytorch.org/whl/cpu
python -m pytest tests/ -v --tb=short
```

Expected output: **21 tests passed**

### 3. Run Static Analysis

```bash
pip install flake8
flake8 ml-predictor/ --count --statistics --max-line-length=100 --exclude=ml-predictor/tests
```

Expected output: **0 errors**

### 4. Run ML Model Locally

```bash
cd ml-predictor
python -c "
from model import EnhancedPredictor, DriftDetector, CostCalculator
import pandas as pd, numpy as np

# Generate synthetic multi-metric data
np.random.seed(42)
n = 200
df = pd.DataFrame({
    'ds': pd.date_range('2026-01-01', periods=n, freq='5min'),
    'cpu': np.clip(np.cumsum(np.random.randn(n)*0.01) + 0.05, 0.01, 0.95),
    'memory': np.clip(np.cumsum(np.random.randn(n)*0.01) + 0.30, 0.05, 0.90),
    'network': np.clip(np.cumsum(np.random.randn(n)*5) + 100, 0, 500),
})

# Train and predict
predictor = EnhancedPredictor()
predictor.train(df)
result = predictor.predict(horizon_minutes=30)

print('Model trained successfully')
print(f'Predictions: {result[\"ensemble\"]}')
print(f'Max predicted CPU: {result[\"max_predicted\"]:.4f}')
print(f'Confidence: {result[\"confidence\"]}')
print(f'Drift stats: {result[\"drift_stats\"]}')
print(f'Cost summary: {result[\"cost_summary\"]}')
"
```

### 5. Deploy to Kubernetes

```bash
# SSH to master node
ssh -i <your-key>.pem ubuntu@<master-ip>

# Deploy all services
git clone https://github.com/prerna3640/HA-K8S1.git && cd HA-K8S1
bash scripts/deploy.sh

# Or deploy frontend only
bash scripts/deploy-frontend.sh
```

### 6. View Presentation

Open in browser:
```
presentation/thesis-presentation.html
```
Navigate with arrow keys (21 slides).

---

## API Endpoints

The ML Predictor exposes these REST endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness check + model status (200 if trained, 503 if not) |
| `/predict` | GET | Multi-metric forecast with confidence score |
| `/predict?horizon=60` | GET | Custom horizon (5–120 minutes) |
| `/drift` | GET | Drift detection stats (MAPE, window, retrain count) |
| `/cost` | GET | Cost estimation summary (scaling events, $/hr) |
| `/metrics/current` | GET | Latest raw metrics from Prometheus |

Example response from `/predict`:
```json
{
  "horizon_minutes": 30,
  "model_type": "multi_metric_lstm",
  "features_used": ["cpu", "memory", "network"],
  "ensemble": [0.067, 0.071, 0.069],
  "max_predicted": 0.071,
  "confidence": 0.85,
  "drift_stats": {"mean_error": 0.12, "drift_detected": false},
  "cost_summary": {"total_events": 5, "scale_ups": 3, "scale_downs": 2}
}
```

---

## Key Files

| File | Purpose |
|------|---------|
| `ml-predictor/model.py` | Multi-Metric LSTM + Drift Detection + Cost Calculator |
| `ml-predictor/predictor_api.py` | Flask REST API (5 endpoints) |
| `ml-predictor/data_collector.py` | Prometheus multi-metric data fetcher |
| `predictive-scaler/controller.py` | Confidence-gated scaling controller |
| `Jenkinsfile` | 9-stage CI/CD pipeline |
| `gitops/argocd/myapp-application.yaml` | ArgoCD Application CRDs |
| `thesis/research-paper/main.tex` | IEEE format research paper |
| `presentation/thesis-presentation.html` | 21-slide thesis presentation |

---

## Literature Review (10 Papers, 2021–2026)

We reviewed recent work from IEEE, ACM, Springer, Elsevier, and arXiv:

| Paper | Year | Venue | Multi-Metric | Drift | Cost | Confidence |
|-------|:---:|-------|:---:|:---:|:---:|:---:|
| Toka et al. | 2021 | IEEE TNSM | - | - | Partial | - |
| Dang-Quang & Yoo | 2021 | MDPI | - | - | - | - |
| Xu et al. | 2022 | ACM KDD | - | Partial | - | - |
| Patil & Singh | 2023 | JTIT | **Yes** | - | - | - |
| Santos et al. (Gwydion) | 2024 | Elsevier | Partial | - | Partial | - |
| Agarwal et al. | 2025 | arXiv | Partial | - | - | Partial |
| Kholidy et al. | 2025 | Frontiers | - | - | - | - |
| DInos | 2025 | Springer | Partial | Partial | - | - |
| Attention-LSTM | 2026 | arXiv | - | - | - | - |
| Rossi et al. | 2025 | Elsevier | **Yes** | Partial | - | - |
| **This Work** | **2026** | — | **Yes** | **Yes** | **Yes** | **Yes** |

**No single paper combines all 4 contributions.** Full references: [REFERENCES_AND_GAP_ANALYSIS.md](presentation/REFERENCES_AND_GAP_ANALYSIS.md)

---

## Testing

```bash
# Run all tests
cd ml-predictor && python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=. --cov-report=term-missing

# Run specific test class
python -m pytest tests/test_model.py::TestDriftDetector -v
python -m pytest tests/test_model.py::TestCostCalculator -v
python -m pytest tests/test_model.py::TestEnhancedPredictor -v
python -m pytest tests/test_predictor_api.py::TestHealthEndpoint -v
python -m pytest tests/test_predictor_api.py::TestPredictEndpoint -v
python -m pytest tests/test_predictor_api.py::TestDriftEndpoint -v
python -m pytest tests/test_predictor_api.py::TestCostEndpoint -v

# Run code quality check
flake8 ml-predictor/ --count --statistics --max-line-length=100 --exclude=ml-predictor/tests
```

**Test coverage:**
- `test_model.py` — DriftDetector (5), CostCalculator (5), EnhancedPredictor (8), ReplicaCalculation (6)
- `test_predictor_api.py` — /health (4), /predict (3), /drift (2), /cost (2)

---

## Monitoring

| Dashboard | Purpose |
|-----------|---------|
| `grafana-dashboards/1-cluster-overview.json` | Cluster-wide resource usage |
| `grafana-dashboards/2-web-application.json` | Web app performance |
| `grafana-dashboards/3-ml-autoscaling.json` | ML predictor metrics |
| `grafana-dashboards/4-monitoring-alerts.json` | Alert status |
| `grafana-dashboards/5-prometheus-monitoring.json` | Prometheus health |

---

## Access

| Service | URL |
|---------|-----|
| **GitHub** | https://github.com/prerna3640/HA-K8S1 |
| **Jenkins** | `http://<master-ip>:8080` |
| **ArgoCD** | `https://<master-ip>:31443` |
| **Grafana** | `http://<master-ip>:3000` |

---

## License

This project is part of an M.Tech thesis at DAVV, Indore. For academic use.

---

**Prerna Tank** | M.Tech (CS) | Roll: 2410512 | DAVV, Indore | 2026
