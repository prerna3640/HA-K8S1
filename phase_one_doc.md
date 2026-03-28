# Phase One — Complete Deployment Document
## Intelligent Auto-Scaling in Kubernetes — ML Based Predictive Approach
### Prerna Tank | M.Tech(CS) 2410512 | DAVV | Guide: Dr. Shraddha Masih

---

## Infrastructure

| Node | Role | vCPU | RAM | Disk | Private IP | Public IP |
|------|------|------|-----|------|-----------|-----------|
| master-node | control-plane | 4 | 8 GB | 60 GB | 10.0.1.7 | 172.83.83.156 |
| worker-node-1 | worker (app) | 4 | 8 GB | 50 GB | 10.0.1.105 | 172.83.83.22 |
| worker-node-2 | worker (data) | 4 | 8 GB | 50 GB | 10.0.1.114 | 172.83.83.158 |

**Provider**: MegaFuse, Central India | **OS**: Ubuntu 22.04 | **K8s**: v1.30.14 | **CNI**: Flannel

---

## Day 1 — Cluster Setup & ML Deployment (2026-03-27)

### Step 1: System Preparation (all 3 nodes)
```bash
# Run on each node
sudo apt update && sudo apt upgrade -y
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab

# Kernel modules
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay
sudo modprobe br_netfilter

# Sysctl
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF
sudo sysctl --system
```

### Step 2: Install containerd (all 3 nodes)
```bash
sudo apt install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd
```

### Step 3: Install K8s packages (all 3 nodes)
```bash
sudo apt-get install -y apt-transport-https ca-certificates curl
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt update
sudo apt install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

### Step 4: Initialize cluster (master-node only)
```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml
```
**Output**: Cluster initialized, Flannel CNI deployed.

### Step 5: Join workers (worker-node-1 & worker-node-2)
```bash
sudo kubeadm join 10.0.1.7:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

### Step 6: Verify cluster (master-node)
```bash
kubectl get nodes
```
**Output**:
```
NAME            STATUS   ROLES           VERSION
master-node     Ready    control-plane   v1.30.14
worker-node-1   Ready    <none>          v1.30.14
worker-node-2   Ready    <none>          v1.30.14
```

### Step 7: Label nodes & create namespaces (master-node)
```bash
kubectl label node worker-node-1 workload=app --overwrite
kubectl label node worker-node-2 workload=data --overwrite
kubectl create namespace myapp
kubectl create namespace monitoring
kubectl create namespace argocd
```

### Step 8: Install Helm (master-node)
```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### Step 9: Install Traefik ingress (master-node)
```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update
helm install traefik traefik/traefik \
  --namespace kube-system \
  --set nodeSelector.workload=app \
  --set service.type=NodePort \
  --set ports.web.nodePort=30080 \
  --set ports.websecure.nodePort=30443
```
**Result**: Traefik on worker-node-1, web at port 30080.

### Step 10: Install Prometheus + Grafana (master-node)
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring \
  --set grafana.resources.requests.memory=128Mi \
  --set grafana.resources.limits.memory=256Mi \
  --set grafana.resources.requests.cpu=50m \
  --set grafana.resources.limits.cpu=200m
```

### Step 11: Install Loki (master-node)
```bash
helm install loki grafana/loki-stack \
  -n monitoring \
  --set loki.nodeSelector.workload=data
```

### Step 12: Install ArgoCD (master-node)
```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.10.0/manifests/install.yaml
kubectl patch deployment argocd-server -n argocd \
  --patch '{"spec":{"template":{"spec":{"nodeSelector":{"workload":"app"}}}}}'
```

### Step 13: Install Metrics Server (master-node)
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
```
**Output**:
```
NAME            CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%
master-node     224m         5%     2289Mi          29%
worker-node-1   110m         2%     1633Mi          20%
worker-node-2   132m         3%     2199Mi          28%
```

### Step 14: Deploy Web Application (master-node)
- 2 replicas of nginx:1.25 on worker-node-1
- Shows pod name on each request (proves load balancing)
- Service: ClusterIP + Traefik Ingress

**Result**: `http://172.83.83.22:30080` — refresh shows different pod names.

### Step 15: Deploy HPA (master-node)
- min: 2, max: 5, CPU threshold: 70%

**Output**: `web-hpa  Deployment/web  cpu: 0%/70%  2  5  2`

### Step 16: Install nerdctl + buildkit (master-node)
```bash
# nerdctl (Docker-compatible CLI for containerd)
wget -q https://github.com/containerd/nerdctl/releases/download/v1.7.6/nerdctl-1.7.6-linux-amd64.tar.gz
sudo tar -xzf nerdctl-1.7.6-linux-amd64.tar.gz -C /usr/local/bin/

# buildkit (image builder)
wget -q https://github.com/moby/buildkit/releases/download/v0.13.2/buildkit-v0.13.2.linux-amd64.tar.gz
sudo tar -xzf buildkit-v0.13.2.linux-amd64.tar.gz -C /usr/local/
sudo /usr/local/bin/buildkitd &>/tmp/buildkit.log &
```

### Step 17: Build Docker images (master-node)
```bash
cd ~/ml-predictor
sudo nerdctl --namespace k8s.io build -t ml-predictor:v1.0.2 .
# Output: Loaded image: ml-predictor:v1.0.2 (449 MB)

cd ~/predictive-scaler
sudo nerdctl --namespace k8s.io build -t predictive-scaler:v1.0.0 .
# Output: Loaded image: predictive-scaler:v1.0.0 (53 MB)
```

### Step 18: Transfer images to workers
```bash
# Save as tar
sudo nerdctl --namespace k8s.io save -o /tmp/ml-predictor.tar ml-predictor:v1.0.2
sudo nerdctl --namespace k8s.io save -o /tmp/predictive-scaler.tar predictive-scaler:v1.0.0

# Import on worker-node-2:
sudo ctr -n k8s.io images import /tmp/ml-predictor.tar
# Import on worker-node-1:
sudo ctr -n k8s.io images import /tmp/predictive-scaler.tar
```

### Step 19: Deploy RBAC (master-node)
- ServiceAccount: predictive-scaler
- ClusterRole: get/list/watch deployments, get/update/patch deployments/scale
- ClusterRoleBinding

### Step 20: Deploy ML Predictor (master-node → worker-node-2)
- Image: ml-predictor:v1.0.2
- Fetches CPU metrics from Prometheus
- LSTM model trains on data, predicts 30 min ahead
- Flask API at port 5000

**Logs**:
```
Fetched 17 CPU data points from Prometheus
[LSTM] Epoch 50/50  loss=0.000004
[Ensemble] Training complete
```

### Step 21: Deploy Predictive Scaler (master-node → worker-node-1)
- Image: predictive-scaler:v1.0.0
- Polls ml-predictor every 60 seconds
- Scales web deployment proactively

**Logs**:
```
Predictive controller started | target=myapp/web | replicas=2-5
NO CHANGE - 2 replicas (predicted CPU 0.0000 cores)
```

---

## Day 2 — Grafana, Telegram & Load Test (2026-03-28)

### Step 22: Expose Grafana (master-node)
```bash
kubectl patch svc prometheus-grafana -n monitoring --type=merge \
  -p '{"spec":{"type":"NodePort","ports":[{"port":80,"targetPort":3000,"nodePort":31000}]}}'
```
**Result**: Grafana at `http://172.83.83.158:31000`

### Step 23: Create 5 Grafana dashboards (master-node)
Pushed via Grafana API into "Auto-Scaling Project" folder.
Removed 28 built-in dashboards (deleted ConfigMaps).

| # | Dashboard | What it shows |
|---|-----------|--------------|
| 1 | Cluster Overview | Nodes, CPU/RAM gauges, CPU/RAM over time |
| 2 | Web Application | Replicas, HPA, CPU vs limits, memory, network |
| 3 | ML Auto-Scaling Pipeline | Predictor/Scaler status, CPU vs threshold, scaling events |
| 4 | Monitoring & Alerts | Firing alerts, restarts, disk usage, targets |
| 5 | Prometheus Stack | All monitoring components, scrape duration, targets table |

### Step 24: Configure Telegram Alerts (master-node)
```bash
# AlertManager config with Telegram receiver
# 8 custom PrometheusRule alerts
# Noisy alerts (Watchdog, TargetDown, etcd) silenced to null receiver
```

**Telegram Bot**: @Fire_k8s_bot | Chat ID: 1150673339

**8 Active Alerts**:

| Alert | Severity | When |
|-------|----------|------|
| HighCPUUsage | warning | CPU > 50% for 2 min |
| CriticalCPUUsage | critical | CPU > 80% for 1 min |
| PodScaledUp | warning | Replicas > 2 |
| MLPredictorDown | critical | Predictor pod down 2 min |
| PredictiveScalerDown | critical | Scaler pod down 2 min |
| HighMemoryUsage | warning | Node RAM > 85% |
| DiskSpaceLow | warning | Disk > 85% |
| PodCrashLooping | critical | >3 restarts in 10 min |

### Step 25: Load Test (master-node)
50 concurrent connections for 5 minutes.

**Results**:

| Time | CPU% | Replicas | Event |
|------|------|----------|-------|
| +0s | 0% | 2 | Baseline |
| +30s | 36% | 2 | Load ramping |
| +60s | **136%** | **3→4** | HPA scale-up! |
| +90s | 100% | 4 | New pods starting |
| +120s | 103% | **5** | Max replicas! |
| +150s | 55% | 5 | Load distributed |
| +300s | 0% | 5 | Load stopped |
| +600s | 0% | **2** | Scaled back down |

**Telegram**: PodScaledUp FIRING → RESOLVED received.

---

## Final Architecture

```
                    INTERNET
                       |
              http://172.83.83.22:30080
                       |
┌──────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER                        │
│                                                              │
│  master-node (10.0.1.7)                                     │
│  ├── kube-apiserver, etcd, scheduler, controller-manager     │
│  ├── metrics-server                                          │
│  └── flannel, kube-proxy                                     │
│                                                              │
│  worker-node-1 (10.0.1.105) [workload=app]                  │
│  ├── web pod 1 (nginx) ──┐                                   │
│  ├── web pod 2 (nginx) ──┤── Traefik load balances           │
│  ├── traefik ingress     ┘                                   │
│  ├── predictive-scaler ──────► polls ml-predictor every 60s  │
│  ├── argocd (server, redis, dex, controller)                 │
│  └── node-exporter, promtail                                 │
│                                                              │
│  worker-node-2 (10.0.1.114) [workload=data]                 │
│  ├── ml-predictor ──────────► LSTM model, Flask API :5000    │
│  ├── prometheus ────────────► scrapes all pods/nodes          │
│  ├── grafana ───────────────► 5 dashboards, port 31000       │
│  ├── loki ──────────────────► log aggregation                │
│  ├── alertmanager ──────────► 8 rules → Telegram bot         │
│  └── node-exporter, promtail                                 │
│                                                              │
│  Data Flow:                                                  │
│  Prometheus → ml-predictor → predictive-scaler → web (scale) │
│  AlertManager → Telegram (8 custom alerts)                   │
└──────────────────────────────────────────────────────────────┘
```

---

## Access URLs

| Service | URL | Credentials |
|---------|-----|------------|
| Web App | `http://172.83.83.22:30080` | — |
| Grafana | `http://172.83.83.158:31000` | admin / VgltzC2tAy0J7u1GSKY5NoflV3zSxKk27GYfvhrw |
| Telegram Bot | @Fire_k8s_bot | Chat ID: 1150673339 |

---

## All Components

| Component | Version | Status | Node |
|-----------|---------|--------|------|
| Kubernetes | v1.30.14 | Running | all |
| containerd | 1.7.x | Running | all |
| Flannel CNI | latest | Running | all |
| Traefik | helm chart | Running | worker-node-1 |
| nginx web app | 1.25 | 2 replicas | worker-node-1 |
| HPA | v2 | Active (2-5, 70%) | — |
| ML Predictor | v1.0.2 (LSTM) | Running | worker-node-2 |
| Predictive Scaler | v1.0.0 | Running | worker-node-1 |
| Prometheus | kube-prometheus-stack | Running | worker-node-2 |
| Grafana | 12.4.2 | 5 dashboards | worker-node-2 |
| Loki | loki-stack | Running | worker-node-2 |
| AlertManager | kube-prometheus-stack | 8 rules → Telegram | worker-node-1 |
| ArgoCD | v2.10.0 | Running | worker-node-1 |
| Metrics Server | latest | Running | master-node |

---

*Phase One Complete*
*Project: Intelligent Auto-Scaling in Kubernetes — ML Based Predictive Approach*
*Author: Prerna Tank | M.Tech(CS) 2410512 | DAVV*
*Date: 2026-03-27 to 2026-03-28*
