# 3-Node Production Deployment Guide
## Intelligent Auto-Scaling in Kubernetes — ML Based Predictive Approach
### Your Exact Cluster: controller-kub + worker-2 + workernew

---

## Your Actual Node Specs (from baseline recording)

| Node | Role | vCPU | RAM | Disk | IP |
|------|------|------|-----|------|----|
| controller-kub | control-plane | 2 | 4 GB | 50 GB | 10.0.1.68 |
| worker-2 | worker | 2 | 4 GB | 40 GB | 10.0.1.30 |
| workernew | worker | 2 | 4 GB | 40 GB | 10.0.1.29 |

**OS:** Ubuntu 22.04.5 LTS
**K8s version:** v1.30.14
**Runtime:** containerd 1.7.27
**CNI:** Flannel (VXLAN)

**YES — 3 nodes is absolutely possible and this is exactly your current cluster.**

---

## Answer: Is 3 Nodes Enough?

```
YES — with smart resource distribution.

Limitations vs 9-node production:
  - No control plane HA (1 controller = single point of failure)
  - Tighter RAM per node (4 GB each)
  - ML model retraining is slower (fewer CPUs)
  - No node-level redundancy for workers

What still works perfectly:
  - Full ML predictive scaling pipeline
  - All monitoring (Prometheus + Grafana + Loki)
  - ArgoCD GitOps
  - Web app with HPA (2-5 replicas)
  - Traefik ingress + TLS
  - Telegram alerting
  - Predictive scaler controller
```

---

## Workload Distribution Plan

```
┌─────────────────────────────────────────────────────────┐
│  controller-kub  (10.0.1.68)  2vCPU / 4GB              │
│  ─────────────────────────────────────────────────────  │
│  [CONTROL PLANE ONLY — no app workloads]                │
│  - kube-apiserver      (~200m CPU, ~512MB)              │
│  - etcd                (~100m CPU, ~512MB)              │
│  - kube-scheduler      (~50m  CPU, ~100MB)              │
│  - kube-controller-mgr (~100m CPU, ~100MB)              │
│  - kube-proxy          (~50m  CPU, ~64MB)               │
│  - node-exporter       (~50m  CPU, ~50MB)               │
│  ─────────────────────────────────────────────────────  │
│  Used:  ~550m / 2000m CPU  |  ~1.3GB / 4GB RAM          │
│  Free:  ~1450m CPU         |  ~2.7GB RAM                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  workernew  (10.0.1.29)  2vCPU / 4GB                   │
│  ─────────────────────────────────────────────────────  │
│  [APP WORKER — web + ingress + gitops + scaler]         │
│  - web pod (replica 1)   (~100m CPU, ~128MB)            │
│  - web pod (replica 2)   (~100m CPU, ~128MB)            │
│  - traefik               (~200m CPU, ~256MB)            │
│  - argocd-server         (~100m CPU, ~256MB)            │
│  - argocd-repo-server    (~100m CPU, ~256MB)            │
│  - argocd-app-controller (~100m CPU, ~256MB)            │
│  - argocd-redis          (~50m  CPU, ~128MB)            │
│  - argocd-dex            (~50m  CPU, ~128MB)            │
│  - predictive-scaler     (~50m  CPU, ~64MB)             │
│  - node-exporter         (~50m  CPU, ~50MB)             │
│  ─────────────────────────────────────────────────────  │
│  Used:  ~900m / 2000m CPU  |  ~1.6GB / 4GB RAM          │
│  Free:  ~1100m CPU         |  ~2.4GB RAM (headroom OK)  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  worker-2  (10.0.1.30)  2vCPU / 4GB                    │
│  ─────────────────────────────────────────────────────  │
│  [DATA WORKER — ML + monitoring]                        │
│  - ml-predictor          (~500m CPU, ~1GB)              │
│  - prometheus            (~200m CPU, ~1GB)              │
│  - grafana               (~100m CPU, ~256MB)            │
│  - loki                  (~150m CPU, ~512MB)            │
│  - alertmanager          (~50m  CPU, ~128MB)            │
│  - node-exporter         (~50m  CPU, ~50MB)             │
│  ─────────────────────────────────────────────────────  │
│  Used:  ~1050m / 2000m CPU |  ~2.95GB / 4GB RAM         │
│  Free:  ~950m CPU          |  ~1.05GB RAM (tight but OK)│
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### All 3 Nodes Already Have (from your baseline)
- [x] Ubuntu 22.04.5 LTS
- [x] Kubernetes v1.30.14
- [x] containerd 1.7.27
- [x] Flannel CNI
- [x] All nodes in Ready state
- [x] Swap disabled
- [x] Kernel modules configured

### What You Still Need to Install

**On your local machine (Windows PC):**
```bash
# 1. kubectl (to manage cluster from your PC)
# Download from: https://dl.k8s.io/release/v1.30.0/bin/windows/amd64/kubectl.exe
# Place in C:\Windows\System32\

# 2. Copy kubeconfig from controller to your PC
# From controller-kub, run:
cat ~/.kube/config
# Copy output to: C:\Users\hp\.kube\config  (create folder if missing)

# 3. Helm (Windows)
# Download from: https://github.com/helm/helm/releases
# Extract and add to PATH

# 4. Docker Desktop for Windows
# https://docs.docker.com/desktop/install/windows-install/
```

**On controller-kub only:**
```bash
# Remove control-plane taint if you want to schedule pods there (OPTIONAL)
# NOT recommended — keep controller clean
# kubectl taint nodes controller-kub node-role.kubernetes.io/control-plane:NoSchedule-
```

**On worker-2 (ML + monitoring workloads):**
```bash
# Add node label for workload targeting
kubectl label node worker-2 node-role=data
kubectl label node workernew node-role=app

# Verify
kubectl get nodes --show-labels
```

---

## Step-by-Step Deployment

### Step 1 — Label the Nodes

```bash
# Run from controller-kub or your local kubectl

kubectl label node workernew  workload=app   --overwrite
kubectl label node worker-2   workload=data  --overwrite

# Verify
kubectl get nodes -L workload
# NAME             STATUS   ROLES           workload
# controller-kub   Ready    control-plane
# worker-2         Ready    <none>          data
# workernew        Ready    <none>          app
```

### Step 2 — Create Namespaces

```bash
kubectl create namespace myapp      2>/dev/null || true
kubectl create namespace monitoring 2>/dev/null || true
kubectl create namespace argocd     2>/dev/null || true
```

### Step 3 — Install Traefik (on workernew)

```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update

helm upgrade --install traefik traefik/traefik \
  --namespace kube-system \
  --set nodeSelector.workload=app \
  --set deployment.replicas=1 \
  --set service.type=NodePort \
  --set ports.web.nodePort=30080 \
  --set ports.websecure.nodePort=30443
```

### Step 4 — Install cert-manager (TLS certificates)

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --namespace cert-manager \
  --for=condition=Ready pod \
  --selector=app.kubernetes.io/instance=cert-manager \
  --timeout=120s

# Create self-signed issuer (upgrade to Let's Encrypt later)
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned-issuer
spec:
  selfSigned: {}
EOF
```

### Step 5 — Install Monitoring Stack (on worker-2)

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Prometheus stack (tuned for 4GB RAM)
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.nodeSelector.workload=data \
  --set prometheus.prometheusSpec.retention=7d \
  --set prometheus.prometheusSpec.resources.requests.memory=512Mi \
  --set prometheus.prometheusSpec.resources.limits.memory=1Gi \
  --set prometheus.prometheusSpec.resources.requests.cpu=100m \
  --set prometheus.prometheusSpec.resources.limits.cpu=500m \
  --set grafana.nodeSelector.workload=data \
  --set grafana.resources.requests.memory=128Mi \
  --set grafana.resources.limits.memory=256Mi \
  --set alertmanager.alertmanagerSpec.nodeSelector.workload=data \
  --set alertmanager.alertmanagerSpec.resources.requests.memory=64Mi \
  --set alertmanager.alertmanagerSpec.resources.limits.memory=128Mi \
  --set prometheusOperator.nodeSelector.workload=data \
  --set kube-state-metrics.nodeSelector.workload=data

# Install Loki (tuned for 4GB RAM)
helm upgrade --install loki grafana/loki-stack \
  --namespace monitoring \
  --set loki.nodeSelector.workload=data \
  --set loki.resources.requests.memory=256Mi \
  --set loki.resources.limits.memory=512Mi \
  --set loki.config.limits_config.ingestion_rate_mb=4 \
  --set promtail.enabled=true

# Wait for pods
kubectl rollout status deployment/prometheus-grafana -n monitoring
```

### Step 6 — Install ArgoCD (on workernew)

```bash
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.10.0/manifests/install.yaml

# Patch ArgoCD to run on workernew
kubectl patch deployment argocd-server -n argocd \
  --patch '{"spec":{"template":{"spec":{"nodeSelector":{"workload":"app"}}}}}'
kubectl patch deployment argocd-repo-server -n argocd \
  --patch '{"spec":{"template":{"spec":{"nodeSelector":{"workload":"app"}}}}}'
kubectl patch deployment argocd-dex-server -n argocd \
  --patch '{"spec":{"template":{"spec":{"nodeSelector":{"workload":"app"}}}}}'
kubectl patch statefulset argocd-application-controller -n argocd \
  --patch '{"spec":{"template":{"spec":{"nodeSelector":{"workload":"app"}}}}}'

# Get initial password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d && echo

# Connect ArgoCD to your gitops repo
# Access via: http://10.0.1.29:30080  (or kubectl port-forward)
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Open: https://localhost:8080
```

### Step 7 — Build and Push ML Predictor Image

```bash
# Option A: Build directly on worker-2 (SSH into it)
ssh ubuntu@10.0.1.30

# Install Docker on worker-2
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu

# Copy ml-predictor folder to worker-2
scp -r ml-predictor/ ubuntu@10.0.1.30:~/

# Build image
cd ~/ml-predictor
docker build -t ml-predictor:v1.0.0 .

# Load into containerd (Kubernetes uses containerd, not Docker)
docker save ml-predictor:v1.0.0 | sudo ctr images import -
# OR tag for a local registry

# Option B: Use a registry (recommended)
# Push to Docker Hub:
docker tag ml-predictor:v1.0.0 yourname/ml-predictor:v1.0.0
docker push yourname/ml-predictor:v1.0.0

# Push to Docker Hub for predictive-scaler too:
docker tag predictive-scaler:v1.0.0 yourname/predictive-scaler:v1.0.0
docker push yourname/predictive-scaler:v1.0.0
```

### Step 8 — Deploy Web Application (on workernew)

```bash
# Apply the web deployment with nodeSelector
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: myapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      nodeSelector:
        workload: app          # <-- runs on workernew
      initContainers:
      - name: init-content
        image: busybox
        command: ['sh', '-c', 'echo "<h1>Pod: $HOSTNAME</h1><p>$(date)</p>" > /web/index.html']
        volumeMounts:
        - name: web-content
          mountPath: /web
      containers:
      - name: web
        image: nginx:1.25
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
        volumeMounts:
        - name: web-content
          mountPath: /usr/share/nginx/html
      volumes:
      - name: web-content
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: web-service
  namespace: myapp
spec:
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
EOF
```

### Step 9 — Deploy ML Predictor (on worker-2)

```bash
# Update ml-predictor/k8s/deployment.yaml with nodeSelector
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-predictor
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ml-predictor
  template:
    metadata:
      labels:
        app: ml-predictor
    spec:
      nodeSelector:
        workload: data         # <-- runs on worker-2
      containers:
      - name: ml-predictor
        image: yourname/ml-predictor:v1.0.0   # or local image
        ports:
        - containerPort: 5000
        env:
        - name: PROMETHEUS_URL
          value: "http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090"
        - name: RETRAIN_INTERVAL_HOURS
          value: "2"           # every 2 hrs (save CPU)
        - name: HISTORY_HOURS
          value: "168"
        - name: PORT
          value: "5000"
        resources:
          requests:
            cpu: 300m          # reduced for 4GB node
            memory: 512Mi
          limits:
            cpu: 800m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 90
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 90
          periodSeconds: 15
---
apiVersion: v1
kind: Service
metadata:
  name: ml-predictor
  namespace: monitoring
spec:
  selector:
    app: ml-predictor
  ports:
  - port: 5000
    targetPort: 5000
  type: ClusterIP
EOF
```

### Step 10 — Deploy Predictive Scaler (on workernew)

```bash
# Apply RBAC
kubectl apply -f predictive-scaler/k8s/rbac.yaml

# Deploy controller with nodeSelector
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: predictive-scaler
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: predictive-scaler
  template:
    metadata:
      labels:
        app: predictive-scaler
    spec:
      serviceAccountName: predictive-scaler
      nodeSelector:
        workload: app          # <-- runs on workernew
      containers:
      - name: predictive-scaler
        image: yourname/predictive-scaler:v1.0.0
        env:
        - name: PREDICTOR_URL
          value: "http://ml-predictor.monitoring.svc.cluster.local:5000"
        - name: NAMESPACE
          value: "myapp"
        - name: DEPLOYMENT_NAME
          value: "web"
        - name: MIN_REPLICAS
          value: "2"
        - name: MAX_REPLICAS
          value: "4"           # reduced from 5 (RAM constraint on 4GB nodes)
        - name: CHECK_INTERVAL_SECONDS
          value: "60"
        - name: PREDICTION_HORIZON
          value: "30"
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 100m
            memory: 128Mi
EOF
```

### Step 11 — Deploy HPA (Safety Net)

```bash
kubectl apply -f hpa.yaml
```

### Step 12 — Fix Telegram Secret (Security)

```bash
# Remove hardcoded token from alertmanager.yaml
# Create a proper Kubernetes Secret

kubectl create secret generic alertmanager-telegram \
  --namespace monitoring \
  --from-literal=bot_token='REDACTED_BOT_TOKEN'
  # IMPORTANT: Rotate this token first! It was exposed in your repo.
  # Go to @BotFather on Telegram → /revoke → get new token

# Then reference in alertmanager config via:
# env:
#   - name: TELEGRAM_BOT_TOKEN
#     valueFrom:
#       secretKeyRef:
#         name: alertmanager-telegram
#         key: bot_token
```

### Step 13 — Verify Everything is Running

```bash
# Check all pods across all namespaces
kubectl get pods -A

# Expected output:
# NAMESPACE    NAME                          READY  STATUS   NODE
# myapp        web-xxxx-1                   1/1    Running  workernew
# myapp        web-xxxx-2                   1/1    Running  workernew
# monitoring   ml-predictor-xxxx            1/1    Running  worker-2
# monitoring   predictive-scaler-xxxx       1/1    Running  workernew
# monitoring   prometheus-xxxx              1/1    Running  worker-2
# monitoring   grafana-xxxx                 1/1    Running  worker-2
# monitoring   loki-xxxx                    1/1    Running  worker-2
# monitoring   alertmanager-xxxx            1/1    Running  worker-2
# argocd       argocd-server-xxxx           1/1    Running  workernew
# kube-system  traefik-xxxx                 1/1    Running  workernew

# Check HPA
kubectl get hpa -n myapp

# Check predictive scaler logs
kubectl logs -f deployment/predictive-scaler -n monitoring

# Check ML predictor logs
kubectl logs -f deployment/ml-predictor -n monitoring

# Test predictor API from inside cluster
kubectl run test --image=curlimages/curl -it --rm \
  -- curl http://ml-predictor.monitoring.svc.cluster.local:5000/health
```

---

## Resource Budget per Node (Final)

### workernew — App Worker (2vCPU / 4GB)

| Pod | CPU Request | RAM Request |
|-----|-------------|-------------|
| web (x2 replicas) | 200m | 256 MB |
| traefik | 100m | 128 MB |
| argocd-server | 100m | 256 MB |
| argocd-repo-server | 100m | 256 MB |
| argocd-app-controller | 100m | 256 MB |
| argocd-redis | 50m | 128 MB |
| argocd-dex | 50m | 128 MB |
| predictive-scaler | 50m | 64 MB |
| node-exporter | 50m | 50 MB |
| **TOTAL** | **800m / 2000m** | **1.5 GB / 4 GB** |
| **FREE** | **1200m (60%)** | **2.5 GB (62%)** |

### worker-2 — Data Worker (2vCPU / 4GB)

| Pod | CPU Request | RAM Request |
|-----|-------------|-------------|
| ml-predictor | 300m | 512 MB |
| prometheus | 100m | 512 MB |
| grafana | 100m | 128 MB |
| loki | 150m | 256 MB |
| alertmanager | 50m | 64 MB |
| node-exporter | 50m | 50 MB |
| **TOTAL** | **750m / 2000m** | **1.5 GB / 4 GB** |
| **FREE** | **1250m (62%)** | **2.5 GB (62%)** |

### controller-kub — Control Plane (2vCPU / 4GB)

| Component | CPU | RAM |
|-----------|-----|-----|
| kube-apiserver | ~200m | ~512 MB |
| etcd | ~100m | ~512 MB |
| kube-scheduler | ~50m | ~100 MB |
| kube-controller-mgr | ~100m | ~100 MB |
| kube-proxy | ~50m | ~64 MB |
| node-exporter | ~50m | ~50 MB |
| **TOTAL** | **~550m** | **~1.3 GB** |
| **FREE** | **1450m** | **2.7 GB** |

---

## What Changes vs 9-Node Setup

| Feature | 9-Node Production | Your 3-Node Setup |
|---------|-------------------|-------------------|
| Control plane HA | 3 nodes (survives 1 failure) | 1 node (if it dies, cluster stops) |
| Max web replicas | 5 | 4 (RAM constraint) |
| ML retraining speed | Fast (8 vCPU) | Slower (1.2 vCPU available) |
| ML retrain interval | Every 1 hour | Every 2 hours |
| Monitoring retention | 15 days | 7 days (disk constraint) |
| ArgoCD HA | Yes | No (single replica) |
| Zero-downtime deploy | Full rolling update | Possible but tight |
| **Cost** | **~$2,065/month** | **~$150-300/month** |

---

## Upgrading Your Current Cluster

Your cluster is already running (from baseline). You just need to deploy the new components:

```bash
# From controller-kub, run these in order:

# 1. Label nodes
kubectl label node workernew workload=app --overwrite
kubectl label node worker-2  workload=data --overwrite

# 2. Apply RBAC for scaler
kubectl apply -f /path/to/predictive-scaler/k8s/rbac.yaml

# 3. Deploy ML predictor (update image name first)
kubectl apply -f /path/to/ml-predictor/k8s/deployment.yaml
kubectl apply -f /path/to/ml-predictor/k8s/service.yaml

# 4. Deploy predictive scaler
kubectl apply -f /path/to/predictive-scaler/k8s/deployment.yaml

# 5. Apply updated HPA (safety net at 70%)
kubectl apply -f /path/to/hpa.yaml

# 6. Watch everything come up
kubectl get pods -A -w
```

---

## Access URLs (from your cluster)

| Service | Internal URL | External Access |
|---------|-------------|-----------------|
| Web App | `http://web-service.myapp.svc.cluster.local` | `http://103.192.199.79:30080` |
| ML Predictor API | `http://ml-predictor.monitoring.svc.cluster.local:5000` | Port-forward only |
| Prometheus | `http://prometheus.mycompany.local` | Via Traefik ingress |
| Grafana | `http://grafana.mycompany.local` | Via Traefik ingress |
| ArgoCD | Port-forward: `kubectl port-forward svc/argocd-server -n argocd 8080:443` | |

---

## Quick Troubleshooting

```bash
# Pod stuck in Pending? (usually node selector mismatch or resource constraint)
kubectl describe pod <pod-name> -n <namespace>
# Look for: "0/3 nodes are available" or "Insufficient memory"

# Check node resource usage
kubectl top nodes

# Check pod resource usage
kubectl top pods -A

# ML predictor not training? Check logs
kubectl logs deployment/ml-predictor -n monitoring --tail=50

# Predictive scaler not scaling? Check logs
kubectl logs deployment/predictive-scaler -n monitoring --tail=50

# Prometheus not scraping? Check targets
kubectl port-forward svc/prometheus-operated -n monitoring 9090:9090
# Open: http://localhost:9090/targets
```

---

## Summary

```
3 Nodes is PERFECTLY SUFFICIENT for your project because:

1. Total resources available across workers:
   - CPU:  4 vCPU total  → using ~1.6 vCPU (40%)
   - RAM:  8 GB total    → using ~3.1 GB  (39%)
   - Disk: 80 GB total   → using ~30 GB   (38%)

2. All components fit comfortably with room to scale

3. This is exactly your existing cluster — zero new infrastructure needed

4. Only NEW things to deploy:
   - ml-predictor     (1 new pod on worker-2)
   - predictive-scaler (1 new pod on workernew)
   - Updated HPA      (replace existing hpa config)
```

---

*Document: 3-Node Production Deployment*
*Cluster: controller-kub + worker-2 + workernew*
*K8s: v1.30.14 | Ubuntu 22.04 | containerd 1.7.27*
*Author: Prerna Tank | M.Tech(CS) 2410512 | DAVV*
*Date: 2026-03-27*
