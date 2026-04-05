# Research Paper Outline
## Intelligent Auto-Scaling in Kubernetes: Reducing Scaling Latency Using LSTM-Based Predictive Approach

**Author:** Prerna Tank, M.Tech (CS), Roll No. 2410512
**Guide:** Dr. Shraddha Masih
**Institution:** School of Computer Science and Information Technology, DAVV, Indore

---

## Abstract (~250 words)

Write about:
- Problem: Kubernetes HPA is reactive, causes ~2 minute scaling delay
- Solution: LSTM-based predictive auto-scaler that forecasts CPU load 30 minutes ahead
- Method: 3-node Kubernetes cluster, Prometheus metrics, LSTM model, custom controller
- Results: Scaling delay reduced from ~120 seconds to 0 seconds (100% improvement)
- Conclusion: ML-based proactive scaling eliminates user-facing performance degradation

**Keywords:** Kubernetes, Auto-scaling, LSTM, Machine Learning, Horizontal Pod Autoscaler, Predictive Scaling, Container Orchestration

---

## 1. Introduction (~1 page)

### 1.1 Background
- Cloud-native applications use Kubernetes for container orchestration
- Auto-scaling ensures availability during traffic fluctuations
- Growing adoption of microservices increases scaling complexity

### 1.2 Problem Statement
- Kubernetes HPA is **reactive** — scales only AFTER metrics cross threshold
- Reactive cycle: Traffic Spike → Metrics Cross Threshold (~30s) → HPA Evaluates → Pods Created (~90s)
- **Total delay: ~2 minutes** during which users experience degraded performance
- Impact: Poor user experience, revenue loss, resource wastage from over-provisioning

### 1.3 Objective
- Develop an ML-based predictive auto-scaling system
- Use LSTM neural network to forecast CPU load 30 minutes ahead
- Implement a custom Kubernetes controller that scales proactively
- Reduce scaling latency from ~2 minutes to 0 seconds

### 1.4 Contributions
1. Design and implementation of LSTM-based CPU usage predictor for Kubernetes workloads
2. Custom Kubernetes controller that performs proactive scaling based on ML predictions
3. Experimental evaluation comparing reactive HPA vs predictive scaler on a real 3-node cluster
4. Demonstration that 8 days of LSTM training eliminates reactive scaling delay entirely

---

## 2. Literature Review (~2 pages)

### 2.1 Container Orchestration and Kubernetes
- Docker, containerd, Kubernetes architecture
- Pods, Deployments, Services, HPA
- Cite: Kubernetes documentation, Burns et al. (2016)

### 2.2 Kubernetes Auto-Scaling Mechanisms
- **HPA** — Horizontal Pod Autoscaler (reactive, metric-based)
- **VPA** — Vertical Pod Autoscaler (adjusts pod resources)
- **Cluster Autoscaler** — adds/removes nodes
- Limitation: All are reactive, no prediction capability
- Cite: Kubernetes SIG Autoscaling

### 2.3 Machine Learning for Cloud Auto-Scaling
- **Dang-Quang & Yoo (2021)** — LSTM-Based CPU Usage Prediction in Cloud Data Centers. IEEE Access.
  - Used LSTM for predicting CPU in cloud VMs
  - Achieved high accuracy but didn't integrate with K8s scaling
- **Mao, Li & Humphrey (2016)** — Cloud Auto-Scaling with Deep Reinforcement Learning. IEEE Cloud Computing.
  - Used DRL for auto-scaling decisions
  - Focused on VM-level, not container/pod-level
- **Other papers to cite:**
  - Rzadca et al. (2020) — Autopilot (Google) — ML for resource management
  - Toka et al. (2021) — Predictive auto-scaling with neural networks
  - Imdoukh et al. (2020) — Machine learning based auto-scaling for containerized applications

### 2.4 Gap Analysis
| Existing Work | Limitation | Our Contribution |
|---------------|-----------|------------------|
| HPA (K8s native) | Reactive only | Proactive + reactive (ML + HPA) |
| LSTM for VMs (Dang-Quang 2021) | Not K8s-integrated | Full K8s pipeline with custom controller |
| DRL scaling (Mao 2016) | VM-level, complex | Pod-level, simpler LSTM approach |
| Google Autopilot | Proprietary, not open | Open-source, reproducible |

---

## 3. Proposed Architecture (~2 pages)

### 3.1 System Overview
```
Prometheus → ML Predictor (LSTM) → Predictive Scaler → Web Deployment
   (metrics)    (forecast 30min)      (scale pods)        (2-5 replicas)
```

### 3.2 Kubernetes Cluster Design
- 3-node cluster: 1 control-plane + 2 workers
- Specs: 4 vCPU, 8 GB RAM per node
- Worker-node-1 (app workloads): web pods, Traefik ingress, predictive scaler
- Worker-node-2 (data workloads): ML predictor, Prometheus, Grafana, Loki

### 3.3 Monitoring Stack
- **Prometheus**: Scrapes container_cpu_usage_seconds_total every 15s
- **Grafana**: 5 custom dashboards for visualization
- **AlertManager**: 8 alert rules → Telegram notifications
- **Loki**: Log aggregation from all pods

### 3.4 ML Predictor Service
- **Data Collection**: Fetches CPU metrics from Prometheus via PromQL
- **Model**: LSTM neural network (PyTorch)
  - Input: Last 6 × 5-min intervals (30 min of history)
  - Output: Next 3 × 5-min intervals (15 min forecast)
  - Hidden size: 64, Layers: 2, Dropout: 0.2
  - Training: 50 epochs, Adam optimizer, MSE loss
  - Retraining: Every 1 hour on latest data
- **API**: Flask REST service exposing /predict and /health endpoints
- **Ensemble**: Prophet (time series) + LSTM combined (graceful fallback)

### 3.5 Predictive Scaler Controller
- **Input**: ML predictions from predictor API
- **Logic**: 
  - desired_replicas = ceil(max_predicted_cpu / (CPU_PER_REPLICA × BUFFER))
  - Scale up immediately when predicted load is high
  - Scale down with 5-min cooldown to prevent flapping
- **Output**: Patches Kubernetes deployment replica count
- **RBAC**: ServiceAccount with minimal permissions (get/patch deployments/scale)

### 3.6 HPA Safety Net
- Reactive HPA at 70% CPU threshold acts as fallback
- If ML model is inaccurate, HPA catches unhandled spikes
- Dual-layer protection: Proactive (ML) + Reactive (HPA)

---

## 4. Implementation (~2 pages)

### 4.1 Technology Stack
| Layer | Tools |
|-------|-------|
| Orchestration | Kubernetes v1.30.14, containerd, Flannel CNI |
| Ingress | Traefik v2 (NodePort 30080) |
| Monitoring | Prometheus, Grafana 12.4, Loki, AlertManager |
| ML Framework | PyTorch (LSTM), Prophet (time series) |
| API | Flask + Gunicorn (Python 3.11) |
| Alerting | Telegram Bot (8 custom rules) |
| GitOps | ArgoCD v2.10 |
| Image Build | nerdctl + buildkit (containerd-native) |

### 4.2 Deployment Steps (summary)
1. Cluster bootstrap with kubeadm
2. Flannel CNI + Metrics Server
3. Helm-based monitoring stack deployment
4. Docker image build for ML predictor and scaler
5. RBAC, Deployments, Services via kubectl apply
6. Traffic simulator CronJob for data generation

### 4.3 Key Implementation Details
- **data_collector.py**: Prometheus range query for CPU rate over configurable window
- **model.py**: EnsemblePredictor combining Prophet + LSTM with graceful fallback
- **predictor_api.py**: Gunicorn with background retraining thread
- **controller.py**: Main loop polling /predict every 60 seconds
- **scaler.py**: Kubernetes Python client patching deployment scale

---

## 5. Experimental Setup (~1 page)

### 5.1 Cluster Configuration
| Node | Role | vCPU | RAM | Disk |
|------|------|------|-----|------|
| master-node | control-plane | 4 | 8 GB | 60 GB |
| worker-node-1 | app workloads | 4 | 8 GB | 50 GB |
| worker-node-2 | data/ML workloads | 4 | 8 GB | 50 GB |

### 5.2 Web Application
- nginx:1.25 with custom HTML (shows pod name for load balancing proof)
- Resource limits: 200m CPU, 256Mi memory per pod
- HPA: min 2, max 5 replicas, 70% CPU threshold

### 5.3 Traffic Simulator
- CronJob running every 10 minutes
- Simulates daily pattern: low (night), medium (morning/evening), high (midday)
- 2-30 concurrent workers depending on hour of day
- Running duration: 8 days (Mar 28 — Apr 5, 2026)

### 5.4 Evaluation Metrics
- **Scaling delay**: Time from load start to pods being ready
- **Pod count at load start**: How many pods ready when traffic spike arrives
- **Peak CPU per pod**: Load distribution across available pods
- **User impact duration**: Time period of degraded performance
- **ML prediction accuracy**: Predicted vs actual CPU values

---

## 6. Results and Analysis (~3 pages)

### 6.1 Baseline: Reactive HPA Only (March 28, 2026)
- LSTM model had only 17 data points (1 hour), predicted 0.000 cores
- Load test: 50 concurrent workers for 5 minutes

| Time | CPU | Replicas | Event |
|------|-----|----------|-------|
| +0s | 0% | 2 | Load started |
| +30s | 36% | 2 | HPA hasn't reacted |
| +60s | 136% | 3→4 | HPA triggered (LATE) |
| +120s | 103% | 5 | Max replicas reached |

**Scaling delay: ~120 seconds. Users impacted for 2 minutes.**

### 6.2 After ML Training: Predictive Scaler (April 5, 2026)
- LSTM model trained for 8 days on traffic patterns (25 data points per retrain)
- Predicted CPU: 0.054 cores (learned daily pattern)
- Predictive scaler pre-scaled to 4 pods during traffic hours

| Time | CPU (millicores) | Replicas | Event |
|------|-----------------|----------|-------|
| +0s | 0.3m | 4 | Already pre-scaled! |
| +60s | 44m | 4 | Handling load |
| +120s | 103m | 4 | No scaling needed |
| +240s | 218m | 4 | Peak absorbed |

**Scaling delay: 0 seconds. No user impact.**

### 6.3 Comparison

| Metric | Reactive HPA | Predictive Scaler | Improvement |
|--------|-------------|-------------------|-------------|
| Scaling delay | ~120 sec | 0 sec | **100%** |
| Pods at load start | 2 | 4 | **2× capacity** |
| Peak CPU per pod | 141m | 65m | **54% lower** |
| User impact | ~2 min | 0 sec | **Eliminated** |

### 6.4 ML Model Performance
- Training loss: 0.125 → 0.096 over 50 epochs
- Model retrains hourly on latest Prometheus data
- Prediction: 0.054 cores (matches actual traffic baseline)
- LSTM learns daily patterns after ~7 days of data

### 6.5 7-Day Operational Data
- Include graphs from Grafana (CPU usage over 7 days)
- Include graphs from thesis_results.png
- Show replica count scaling patterns matching traffic patterns

### 6.6 Alert System Validation
- 8 custom Prometheus alert rules
- PodScaledUp alert fired correctly during load test
- Telegram notifications delivered within seconds
- AlertManager routing working (noisy system alerts silenced)

---

## 7. Discussion (~1 page)

### 7.1 Advantages of Proposed System
- Eliminates reactive scaling delay
- Works alongside existing HPA (dual-layer protection)
- Open-source, reproducible on any Kubernetes cluster
- Lightweight: ML predictor uses only 300m CPU, 512Mi RAM

### 7.2 Limitations
- Prophet model had compatibility issues (stan_backend) — only LSTM used
- LSTM requires 7+ days of training data to learn patterns
- Simulated traffic, not real user traffic
- Prediction limited to patterns seen in training data
- Single-metric prediction (CPU only, not memory or request rate)

### 7.3 Comparison with Existing Work
| Approach | Our System | Dang-Quang (2021) | Mao (2016) |
|----------|-----------|-------------------|------------|
| Target | K8s Pods | Cloud VMs | Cloud VMs |
| ML Model | LSTM | LSTM | DRL |
| Integration | Full K8s pipeline | Standalone | Standalone |
| Controller | Custom K8s controller | None | Policy-based |
| Monitoring | Prometheus + Grafana | Custom | Custom |
| Open source | Yes | Partial | No |

---

## 8. Conclusion and Future Work (~1 page)

### 8.1 Conclusion
- Successfully designed and implemented an LSTM-based predictive auto-scaling system for Kubernetes
- Reduced scaling latency from ~120 seconds to 0 seconds on a real 3-node cluster
- The system works alongside existing HPA as a dual-layer scaling mechanism
- After 8 days of training, the LSTM model learned traffic patterns and enabled proactive scaling
- Full monitoring, alerting, and visualization pipeline deployed

### 8.2 Future Work
1. **Multi-metric prediction**: Extend to memory, network I/O, and HTTP request rate
2. **Prophet model fix**: Resolve compatibility issues for ensemble predictions
3. **Real-world deployment**: Test with actual user traffic on production systems
4. **Advanced models**: Explore Transformer-based models and reinforcement learning
5. **Cost optimization**: Add cost-aware scaling (spot instances, node auto-scaling)
6. **CI/CD integration**: ArgoCD-based auto-deployment of model updates
7. **Multi-cluster support**: Federated scaling across multiple Kubernetes clusters

---

## 9. References

[1] Dang-Quang, N.-M., & Yoo, M. (2021). An LSTM-Based Approach for Predicting CPU Usage in Cloud Data Centers. IEEE Access. https://doi.org/10.1109/ACCESS.2021.3052064

[2] Mao, M., Li, J., & Humphrey, M. (2016). Cloud Auto-Scaling with Deep Reinforcement Learning. IEEE International Conference on Cloud Computing. https://doi.org/10.1109/CLOUD.2016.56

[3] Burns, B., Grant, B., Oppenheimer, D., Brewer, E., & Wilkes, J. (2016). Borg, Omega, and Kubernetes. ACM Queue, 14(1), 70-93.

[4] Rzadca, K., et al. (2020). Autopilot: Workload Autoscaling at Google. EuroSys.

[5] Toka, L., et al. (2021). Adaptive AI-based Auto-scaling for Kubernetes. IEEE/ACM CCGrid.

[6] Imdoukh, M., Ahmad, I., & Alfailakawi, M. (2020). Machine Learning-Based Auto-Scaling for Containerized Applications. Neural Computing and Applications.

[7] Hochreiter, S., & Schmidhuber, J. (1997). Long Short-Term Memory. Neural Computation, 9(8), 1735-1780.

[8] Kubernetes Documentation. Horizontal Pod Autoscaler. https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/

[9] Prometheus Documentation. https://prometheus.io/docs/

[10] PyTorch Documentation. LSTM. https://pytorch.org/docs/stable/generated/torch.nn.LSTM.html

---

## Appendix

### A. Project Repository
https://github.com/prerna3640/HA-K8S1

### B. Project Structure
```
project/
├── ml-predictor/           # ML Prediction Service (LSTM + Flask)
├── predictive-scaler/      # Custom K8s Controller
├── grafana-dashboards/     # 5 Grafana Dashboard JSONs
├── gitops/                 # ArgoCD manifests
├── baseline-recording/     # Performance baseline (before ML)
├── docs/                   # Documentation
├── hpa.yaml               # HPA safety net manifest
├── deploy.sh              # Deployment script
├── phase_one_doc.md       # Complete deployment log
├── thesis_results.png     # Results comparison chart
└── README.md              # Project overview
```

### C. Key Figures (from thesis_results.png)
1. 7-Day CPU Usage History
2. 7-Day Replica Count
3. Before ML — Reactive HPA Scaling Timeline
4. After ML — Predictive Scaling Timeline
5. Before vs After Comparison Bar Chart
6. Results Summary Table

### D. Access URLs
| Service | URL |
|---------|-----|
| Web App | http://172.83.83.22:30080 |
| Grafana | http://172.83.83.158:31000 |
| GitHub | https://github.com/prerna3640/HA-K8S1 |

---

*Estimated paper length: 12-15 pages*
*Target journals: IEEE Access, IJCA, IJERT, or DAVV internal journal*
