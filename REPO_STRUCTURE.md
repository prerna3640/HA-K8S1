# Repository Structure

Clean, organized folder layout for the Intelligent Auto-Scaling in Kubernetes project.

```
HA-K8S1/
│
├── 📄 Core CI/CD Configuration
│   ├── Jenkinsfile ........................... Jenkins pipeline (9 stages)
│   └── .flake8 ............................. Static analysis config
│
├── 🚀 ml-predictor/ (LSTM Prediction Service)
│   ├── Dockerfile, Dockerfile.v2 ........... Container images
│   ├── model.py, model_v2.py .............. LSTM + Prophet models
│   ├── predictor_api.py, predictor_api_v2.py .. Flask REST API
│   ├── data_collector.py, data_collector_v2.py . Prometheus fetch
│   ├── requirements.txt ................... Python dependencies
│   ├── test_local.py ...................... Local testing script
│   │
│   ├── tests/ (NEW - Unit Tests) ........... ✅ 21 pytest tests
│   │   ├── __init__.py
│   │   ├── conftest.py ................... Pytest fixtures
│   │   ├── test_model.py ................ 13 tests for ML models
│   │   └── test_predictor_api.py ........ 8 API endpoint tests
│   │
│   └── k8s/
│       ├── deployment.yaml ............... K8s deployment
│       └── service.yaml .................. ClusterIP service
│
├── 🔧 predictive-scaler/ (Custom K8s Controller)
│   ├── Dockerfile, Dockerfile.v2 ......... Container images
│   ├── controller.py, controller_v2.py ... Scaling logic
│   ├── scaler.py .......................... K8s API wrapper
│   ├── requirements.txt .................. Python dependencies
│   │
│   └── k8s/
│       ├── deployment.yaml ............... K8s deployment
│       └── rbac.yaml ..................... RBAC permissions
│
├── 🌍 gitops/ (GitOps Infrastructure)
│   ├── applications/
│   │   └── myapp/ (Web Frontend)
│   │       ├── deployment.yaml .......... nginx (2-5 replicas)
│   │       ├── service.yaml ............ ClusterIP service
│   │       └── ingress.yaml ............ Traefik routing
│   │
│   └── argocd/ (NEW - ArgoCD Config)
│       └── myapp-application.yaml ...... ArgoCD Applications CRD
│
├── 📊 grafana-dashboards/ (Monitoring)
│   ├── 1-cluster-overview.json
│   ├── 2-web-application.json
│   ├── 3-ml-autoscaling.json
│   ├── 4-monitoring-alerts.json
│   └── 5-prometheus-monitoring.json
│
├── 📚 docs/ (Documentation)
│   ├── PROJECT_README.md ................. Project overview
│   ├── 3NODE_DEPLOYMENT.md .............. Cluster setup guide
│   ├── END_TO_END_DEVOPS_SETUP.md ....... CI/CD pipeline guide
│   ├── phase_one_doc.md ................. Day 1 deployment log
│   └── ci-cd-working-diagram.svg ........ Architecture diagrams
│
├── 🔒 k8s-configs/ (Kubernetes Configuration)
│   ├── hpa.yaml .......................... HPA safety net (70% CPU)
│   └── alert-rules.yaml ................. Prometheus alerts
│
├── 🎓 thesis/ (Research Paper)
│   └── research-paper/
│       └── main.tex ...................... IEEE paper (multi-metric LSTM + drift + cost)
│
├── 📦 scripts/ (Deployment & Utility Scripts)
│   ├── deploy.sh ......................... Automated deployment
│   └── thesis_chart.py ................... Performance chart generator
│
├── 🗄️ legacy/ (Reference/Archived)
│   ├── old-configs/ ..................... Deprecated K8s manifests
│   ├── baseline-recording/ .............. Cluster snapshot (Feb 2026)
│   └── baseline-backup.tar.gz ........... Backup archive
│
└── 🔑 Security & Config
    ├── .gitignore ....................... Git ignore rules
    ├── kub-cluster-key.pem .............. SSH key (private)
    ├── REPO_STRUCTURE.md (this file)
    └── Jenkinsfile, .flake8 (root level)
```

---

## Folder Summary

| Folder | Purpose | Contains |
|--------|---------|----------|
| **ml-predictor/** | LSTM prediction service | Model, API, Docker, K8s, tests |
| **predictive-scaler/** | Custom scaling controller | Controller logic, K8s manifests, RBAC |
| **gitops/** | Declarative infrastructure | ArgoCD apps, web deployment manifests |
| **grafana-dashboards/** | Monitoring dashboards | 5 JSON dashboard configs |
| **docs/** | Documentation | Guides, deployment logs, diagrams |
| **k8s-configs/** | K8s configurations | HPA, alert rules (global) |
| **thesis/** | Research paper | LaTeX main.tex |
| **scripts/** | Automation & tools | Deploy script, chart generator |
| **legacy/** | Old/archived files | Reference configs, backups |

---

## Key Files

### CI/CD
- `Jenkinsfile` ......................... 9-stage pipeline with tests + analysis
- `.flake8` ............................ Static code analysis config
- `gitops/argocd/myapp-application.yaml` . ArgoCD Applications CRD

### ML Pipeline
- `ml-predictor/predictor_api.py` ...... Flask REST API (/predict, /health)
- `ml-predictor/model_v2.py` ........... Multi-metric LSTM + drift + cost
- `ml-predictor/tests/` ................ 21 unit tests (NEW)

### Kubernetes
- `predictive-scaler/controller_v2.py` . Proactive scaler with confidence gating
- `gitops/applications/myapp/` ........ Web app manifests
- `k8s-configs/hpa.yaml` ............... HPA safety net

### Deployment
- `scripts/deploy.sh` .................. Automated full cluster deployment
- `docs/3NODE_DEPLOYMENT.md` ........... Step-by-step setup

### Documentation
- `docs/PROJECT_README.md` ............. Project overview
- `docs/END_TO_END_DEVOPS_SETUP.md` ... CI/CD pipeline guide
- `thesis/research-paper/main.tex` .... IEEE research paper

---

## Quick Navigation

### To understand the project:
1. Start with `docs/PROJECT_README.md`
2. Read `docs/END_TO_END_DEVOPS_SETUP.md` for CI/CD pipeline
3. Check `thesis/research-paper/main.tex` for research context

### To deploy:
1. Follow `docs/3NODE_DEPLOYMENT.md`
2. Run `scripts/deploy.sh`
3. Monitor via Grafana dashboards

### To develop:
1. Code in `ml-predictor/` or `predictive-scaler/`
2. Run tests: `cd ml-predictor && pytest tests/`
3. Check style: `flake8 ml-predictor/`
4. Commit and push → Jenkins triggers → ArgoCD deploys

### To troubleshoot:
1. Check `scripts/` for utility tools
2. Reference `legacy/` for old configs
3. Read `k8s-configs/` for monitoring rules

---

## What's New (April 9, 2026)

✅ **Unit Tests** — `ml-predictor/tests/` with 21 pytest tests  
✅ **Static Analysis** — `.flake8` config for PEP 8 enforcement  
✅ **ArgoCD GitOps** — `gitops/argocd/myapp-application.yaml` CRD  
✅ **Updated Jenkinsfile** — 9 stages with tests + analysis + ArgoCD sync  
✅ **Organized Repo** — Clean folder structure (this file)  

---

## GitHub Repository

🔗 https://github.com/prerna3640/HA-K8S1

All files organized and committed with clean history.
