# Production Infrastructure Guide
## Intelligent Auto-Scaling in Kubernetes — ML Based Predictive Approach
### Prerna Tank | M.Tech(CS) 2410512 | DAVV

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [EC2 Node Requirements](#2-ec2-node-requirements)
3. [AWS Infrastructure Components](#3-aws-infrastructure-components)
4. [Prerequisites](#4-prerequisites)
5. [Step-by-Step Deployment](#5-step-by-step-deployment)
6. [Kubernetes Namespace Layout](#6-kubernetes-namespace-layout)
7. [Storage Requirements](#7-storage-requirements)
8. [Networking & Security](#8-networking--security)
9. [Monitoring Stack](#9-monitoring-stack)
10. [Cost Estimation](#10-cost-estimation)
11. [Production Checklist](#11-production-checklist)

---

## 1. Architecture Overview

```
                          INTERNET
                             |
                    [AWS Route 53 DNS]
                             |
                  [Application Load Balancer]
                    /                  \
           [Traefik Ingress]      [Prometheus Ingress]
                  |                      |
    ┌─────────────────────────────────────────────────┐
    │              KUBERNETES CLUSTER (EKS / kubeadm) │
    │                                                 │
    │  ┌──────────────────────────────────────────┐   │
    │  │  CONTROL PLANE (3 nodes - HA)            │   │
    │  │  API Server | etcd | Scheduler           │   │
    │  │  Controller Manager | Cloud Controller   │   │
    │  └──────────────────────────────────────────┘   │
    │                                                 │
    │  ┌─────────────┐  ┌─────────────┐              │
    │  │  APP NODES  │  │  ML NODES   │              │
    │  │  (3 nodes)  │  │  (2 nodes)  │              │
    │  │  - web app  │  │  - Prophet  │              │
    │  │  - ArgoCD   │  │  - LSTM     │              │
    │  │  - Traefik  │  │  - Predictor│              │
    │  └─────────────┘  └─────────────┘              │
    │                                                 │
    │  ┌──────────────────────────────────────────┐   │
    │  │  MONITORING NODE (1 dedicated)           │   │
    │  │  Prometheus | Grafana | Loki | Alertmgr  │   │
    │  └──────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────┘
              |                    |
         [RDS / S3]          [ECR Registry]
      (optional backup)     (Docker images)
```

---

## 2. EC2 Node Requirements

### Minimum Production Setup (9 nodes)

| # | Role | EC2 Type | vCPU | RAM | Storage | Count | Purpose |
|---|------|----------|------|-----|---------|-------|---------|
| 1 | Bastion / Jump Host | t3.micro | 2 | 1 GB | 20 GB gp3 | 1 | SSH access gateway |
| 2 | Control Plane | t3.medium | 2 | 4 GB | 50 GB gp3 | 3 | K8s API, etcd, scheduler |
| 3 | App Worker | t3.large | 2 | 8 GB | 80 GB gp3 | 3 | Web app, Traefik, ArgoCD |
| 4 | ML Worker | m5.xlarge | 4 | 16 GB | 100 GB gp3 | 1 | Prophet + LSTM training |
| 5 | Monitoring | t3.large | 2 | 8 GB | 200 GB gp3 | 1 | Prometheus, Grafana, Loki |

**Total: 9 EC2 instances**

---

### Recommended Production Setup (11 nodes)

| # | Role | EC2 Type | vCPU | RAM | Storage | Count | Monthly Cost (approx) |
|---|------|----------|------|-----|---------|-------|----------------------|
| 1 | Bastion | t3.micro | 2 | 1 GB | 20 GB | 1 | ~$9 |
| 2 | Control Plane | m5.large | 2 | 8 GB | 50 GB | 3 | ~$105 each = $315 |
| 3 | App Worker | m5.xlarge | 4 | 16 GB | 100 GB | 3 | ~$192 each = $576 |
| 4 | ML Worker | m5.2xlarge | 8 | 32 GB | 150 GB | 2 | ~$384 each = $768 |
| 5 | Monitoring | m5.xlarge | 4 | 16 GB | 300 GB | 1 | ~$192 |
| 6 | NAT Gateway | — | — | — | — | 1 | ~$35 |

**Total: 11 EC2 nodes | Estimated: ~$1,895/month**

---

### Why These Sizes?

#### Control Plane — m5.large (3 nodes)
```
Why 3 nodes?
  etcd requires odd number for quorum (3 = tolerates 1 failure)
  If 1 goes down, cluster continues working

Why m5.large (8 GB RAM)?
  etcd alone needs 2-4 GB under load
  API server + scheduler + controller manager = 2-3 GB
  OS + buffer = 1 GB
  Total needed: ~6-7 GB -> m5.large (8 GB) is safe
```

#### ML Worker — m5.2xlarge (2 nodes)
```
Why 2 nodes?
  1 active (running Prophet + LSTM training)
  1 standby (rolling updates without downtime)

Why m5.2xlarge (32 GB RAM, 8 vCPU)?
  Prophet training (7 days of 5-min data) = ~1.5 GB RAM
  LSTM model (PyTorch)                   = ~2.0 GB RAM
  Flask API (gunicorn)                   = ~0.5 GB RAM
  OS + buffer                            = ~1.0 GB RAM
  Total per pod: ~5 GB -> 16 GB is safe for 2-3 replicas

  CPU: LSTM training uses 4-6 cores -> 8 vCPU needed
```

#### App Worker — m5.xlarge (3 nodes)
```
Why 3 nodes?
  web app pods (2-5 replicas spread across nodes)
  Traefik ingress controller (1-2 replicas)
  ArgoCD components (5 pods)
  Anti-affinity rules spread pods across all 3 nodes

Why m5.xlarge (16 GB RAM)?
  nginx pods: 100m CPU, 128 MB each x5 = 640 MB
  Traefik:    200m CPU, 256 MB each x2 = 512 MB
  ArgoCD:     500m CPU, 512 MB each x5 = 2.5 GB
  OS + buffer                          = 2 GB
  Total: ~5.6 GB per node -> 16 GB gives 3x headroom
```

#### Monitoring — m5.xlarge (1 node, dedicated)
```
Why dedicated?
  Monitoring must NOT compete with app workloads for resources
  If app is under heavy load, we still need metrics to be accurate

Why m5.xlarge (16 GB)?
  Prometheus (2 weeks retention): 4-6 GB RAM
  Grafana:                        1 GB RAM
  Loki:                           2 GB RAM
  AlertManager:                   256 MB
  Node Exporter (per node):       50 MB
  Total: ~8-9 GB -> 16 GB is right

  Storage: 300 GB for 2 weeks of Prometheus + Loki data
```

---

## 3. AWS Infrastructure Components

### VPC Architecture
```
VPC: 10.0.0.0/16

  Public Subnets (2 AZs):
    <subnet-cidr>  - AZ-a  (Bastion, ALB, NAT Gateway)
    10.0.2.0/24  - AZ-b  (ALB)

  Private Subnets (3 AZs):
    10.0.10.0/24 - AZ-a  (Control plane nodes)
    10.0.11.0/24 - AZ-b  (App worker nodes)
    10.0.12.0/24 - AZ-c  (ML worker + monitoring nodes)

  Pod Network (Flannel/Calico):
    10.244.0.0/16

  Service Network:
    10.96.0.0/12
```

### Required AWS Services
| Service | Purpose | Notes |
|---------|---------|-------|
| EC2 | Kubernetes nodes | See table above |
| VPC | Network isolation | Private subnets for nodes |
| ALB | External load balancer | Routes to Traefik ingress |
| Route 53 | DNS management | `*.mycompany.com` |
| ACM | TLS certificates | Replace self-signed certs |
| ECR | Docker image registry | Store ml-predictor, predictive-scaler |
| S3 | etcd backup, Loki storage | Long-term storage |
| IAM | Node permissions | EC2 + ECR + S3 access |
| Security Groups | Firewall rules | See networking section |
| EBS | Persistent volumes | gp3 volumes for PVCs |
| CloudWatch | Node-level monitoring | Optional, Prometheus preferred |

---

## 4. Prerequisites

### 4.1 Local Machine (your laptop / DevOps machine)

```bash
# Required tools - install all before starting

# 1. AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install
aws configure   # set Access Key, Secret Key, region

# 2. kubectl (matches your K8s version - 1.30)
curl -LO "https://dl.k8s.io/release/v1.30.0/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin/

# 3. kubeadm (for self-managed cluster, not EKS)
sudo apt-get install -y kubeadm=1.30.0-00

# 4. Helm v3 (package manager for K8s)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 5. Docker (for building images)
curl -fsSL https://get.docker.com | sh

# 6. Git
sudo apt-get install -y git

# 7. Terraform (optional, for AWS infra as code)
sudo apt-get install -y terraform

# Verify all tools
kubectl version --client
helm version
docker --version
aws --version
```

### 4.2 Each EC2 Node — OS Prerequisites

**Supported OS:** Ubuntu 22.04 LTS (recommended) or Amazon Linux 2

```bash
# Run on EVERY node (control plane + workers)

# 1. Update system
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install container runtime (containerd)
sudo apt-get install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
# Enable SystemdCgroup
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd

# 3. Disable swap (REQUIRED for Kubernetes)
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# 4. Enable kernel modules
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay
sudo modprobe br_netfilter

# 5. Set sysctl params
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sudo sysctl --system

# 6. Install kubeadm, kubelet, kubectl
sudo apt-get install -y apt-transport-https ca-certificates curl
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | \
  sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] \
  https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | \
  sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update
sudo apt-get install -y kubelet=1.30.0-00 kubeadm=1.30.0-00 kubectl=1.30.0-00
sudo apt-mark hold kubelet kubeadm kubectl
sudo systemctl enable --now kubelet
```

### 4.3 ML Worker Node — Extra Prerequisites

```bash
# Only on ML worker nodes (for Prophet + LSTM)

# Python 3.11 (more stable with Prophet than 3.13)
sudo apt-get install -y python3.11 python3.11-pip python3.11-venv

# Build tools for Prophet/cmdstan
sudo apt-get install -y gcc g++ make cmake libgomp1

# Verify
python3.11 --version   # Python 3.11.x
```

### 4.4 AWS IAM Permissions

Create an IAM role `k8s-node-role` with these policies:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-k8s-backup-bucket",
        "arn:aws:s3:::your-k8s-backup-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "ec2:AttachVolume",
        "ec2:DetachVolume"
      ],
      "Resource": "*"
    }
  ]
}
```

### 4.5 Security Group Rules

**Control Plane Security Group:**
| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 6443 | TCP | Worker nodes SG | Kubernetes API server |
| 2379-2380 | TCP | Control plane SG | etcd |
| 10250 | TCP | All nodes SG | Kubelet API |
| 10259 | TCP | Control plane SG | Kube scheduler |
| 10257 | TCP | Control plane SG | Kube controller manager |
| 22 | TCP | Bastion SG | SSH |

**Worker Node Security Group:**
| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 10250 | TCP | Control plane SG | Kubelet API |
| 30000-32767 | TCP | ALB SG | NodePort services |
| 8472 | UDP | All nodes SG | Flannel VXLAN |
| 22 | TCP | Bastion SG | SSH |

**Monitoring Security Group:**
| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 9090 | TCP | All nodes SG | Prometheus |
| 3000 | TCP | ALB SG | Grafana |
| 3100 | TCP | All nodes SG | Loki |
| 9093 | TCP | All nodes SG | AlertManager |

---

## 5. Step-by-Step Deployment

### Step 1 — Launch EC2 Instances

```bash
# Using AWS CLI to launch nodes (or use Terraform/console)

# Control plane nodes (x3)
for i in 1 2 3; do
  aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \     # Ubuntu 22.04
    --instance-type m5.large \
    --key-name your-key-pair \
    --security-group-ids sg-control-plane \
    --subnet-id subnet-private-a \
    --iam-instance-profile k8s-node-role \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":50,"VolumeType":"gp3"}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=k8s-control-$i},{Key=Role,Value=control-plane}]"
done

# App worker nodes (x3)
for i in 1 2 3; do
  aws ec2 run-instances \
    --instance-type m5.xlarge \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=k8s-worker-app-$i},{Key=Role,Value=worker-app}]" \
    # ... (same flags as above)
done

# ML worker nodes (x2)
for i in 1 2; do
  aws ec2 run-instances \
    --instance-type m5.2xlarge \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":150,"VolumeType":"gp3"}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=k8s-worker-ml-$i},{Key=Role,Value=worker-ml}]" \
    # ...
done

# Monitoring node (x1)
aws ec2 run-instances \
  --instance-type m5.xlarge \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":300,"VolumeType":"gp3"}}]' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=k8s-monitoring},{Key=Role,Value=monitoring}]" \
  # ...
```

### Step 2 — Bootstrap Kubernetes Cluster

```bash
# On FIRST control plane node only
sudo kubeadm init \
  --control-plane-endpoint "k8s-api.mycompany.com:6443" \
  --upload-certs \
  --pod-network-cidr=10.244.0.0/16 \
  --service-cidr=10.96.0.0/12 \
  --kubernetes-version=v1.30.0

# Save the output! You will get:
#   kubeadm join ... --control-plane   (for other control plane nodes)
#   kubeadm join ...                   (for worker nodes)

# Set up kubectl on control plane
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Install Flannel CNI
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
```

```bash
# On the OTHER 2 control plane nodes
sudo kubeadm join k8s-api.mycompany.com:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash> \
  --control-plane \
  --certificate-key <cert-key>
```

```bash
# On ALL worker nodes
sudo kubeadm join k8s-api.mycompany.com:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash>
```

### Step 3 — Label Nodes

```bash
# Label app workers
kubectl label node k8s-worker-app-1 node-role=app
kubectl label node k8s-worker-app-2 node-role=app
kubectl label node k8s-worker-app-3 node-role=app

# Label ML workers
kubectl label node k8s-worker-ml-1 node-role=ml
kubectl label node k8s-worker-ml-2 node-role=ml

# Label monitoring node
kubectl label node k8s-monitoring node-role=monitoring

# Taint ML and monitoring nodes (only specific pods can schedule here)
kubectl taint nodes k8s-worker-ml-1 dedicated=ml:NoSchedule
kubectl taint nodes k8s-worker-ml-2 dedicated=ml:NoSchedule
kubectl taint nodes k8s-monitoring  dedicated=monitoring:NoSchedule
```

### Step 4 — Install Traefik Ingress

```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update
helm install traefik traefik/traefik \
  --namespace kube-system \
  --set deployment.replicas=2 \
  --set service.type=LoadBalancer \
  --set nodeSelector."node-role"=app
```

### Step 5 — Install Monitoring Stack

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Create monitoring namespace
kubectl create namespace monitoring

# Prometheus + AlertManager + Node Exporter
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.retention=15d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=gp3 \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=100Gi \
  --set nodeSelector."node-role"=monitoring

# Loki (log aggregation)
helm install loki grafana/loki-stack \
  --namespace monitoring \
  --set loki.persistence.enabled=true \
  --set loki.persistence.size=100Gi \
  --set nodeSelector."node-role"=monitoring
```

### Step 6 — Install ArgoCD (GitOps)

```bash
kubectl create namespace argocd
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# Expose ArgoCD via ingress (or port-forward for setup)
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### Step 7 — Build and Push Docker Images

```bash
# Create ECR repositories
aws ecr create-repository --repository-name ml-predictor
aws ecr create-repository --repository-name predictive-scaler

# Login to ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS \
  --password-stdin <account-id>.dkr.ecr.ap-south-1.amazonaws.com

# Build and push ml-predictor
cd ml-predictor
docker build -t ml-predictor:v1.0.0 .
docker tag ml-predictor:v1.0.0 \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com/ml-predictor:v1.0.0
docker push \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com/ml-predictor:v1.0.0

# Build and push predictive-scaler
cd ../predictive-scaler
docker build -t predictive-scaler:v1.0.0 .
docker tag predictive-scaler:v1.0.0 \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com/predictive-scaler:v1.0.0
docker push \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com/predictive-scaler:v1.0.0
```

### Step 8 — Deploy Application

```bash
# Create namespaces
kubectl create namespace myapp
kubectl create namespace monitoring   # already exists

# Fix image names in manifests to use ECR
# Update ml-predictor/k8s/deployment.yaml:
#   image: <account-id>.dkr.ecr.ap-south-1.amazonaws.com/ml-predictor:v1.0.0
# Update predictive-scaler/k8s/deployment.yaml:
#   image: <account-id>.dkr.ecr.ap-south-1.amazonaws.com/predictive-scaler:v1.0.0

# Deploy web application
kubectl apply -f web.yaml

# Deploy RBAC for predictive scaler
kubectl apply -f predictive-scaler/k8s/rbac.yaml

# Deploy ML predictor
kubectl apply -f ml-predictor/k8s/deployment.yaml
kubectl apply -f ml-predictor/k8s/service.yaml

# Deploy predictive scaler
kubectl apply -f predictive-scaler/k8s/deployment.yaml

# Deploy HPA (safety net)
kubectl apply -f hpa.yaml

# Verify all pods are running
kubectl get pods -n myapp
kubectl get pods -n monitoring
```

### Step 9 — Secure Secrets

```bash
# IMPORTANT: Remove hardcoded Telegram token from alertmanager.yaml
# Create a proper Kubernetes Secret instead

kubectl create secret generic alertmanager-telegram \
  --namespace monitoring \
  --from-literal=bot_token='YOUR_TELEGRAM_BOT_TOKEN' \
  --from-literal=chat_id='YOUR_CHAT_ID'

# Reference secret in alertmanager config via secretKeyRef
```

---

## 6. Kubernetes Namespace Layout

```
cluster
  ├── kube-system          (Kubernetes core: DNS, proxy, Flannel, Traefik)
  ├── myapp                (Web application + HPA)
  │     ├── web (deployment, 2-5 replicas)
  │     ├── web-service
  │     └── web-hpa
  ├── monitoring           (Full observability stack)
  │     ├── prometheus
  │     ├── grafana
  │     ├── loki
  │     ├── alertmanager
  │     ├── node-exporter (daemonset, runs on all nodes)
  │     ├── ml-predictor
  │     └── predictive-scaler
  └── argocd               (GitOps continuous delivery)
        ├── argocd-server
        ├── argocd-repo-server
        ├── argocd-application-controller
        └── argocd-redis
```

---

## 7. Storage Requirements

| Component | Type | Size | Storage Class | Purpose |
|-----------|------|------|---------------|---------|
| etcd (x3) | EBS gp3 | 20 GB each | — | Cluster state |
| Prometheus | PVC | 100 GB | gp3 | 15-day metrics |
| Loki | PVC | 100 GB | gp3 | 15-day logs |
| Grafana | PVC | 10 GB | gp3 | Dashboards |
| ML Models | PVC | 20 GB | gp3 | Trained Prophet/LSTM models |
| S3 Backup | S3 | Unlimited | — | etcd + Prometheus backup |

```bash
# Create gp3 StorageClass
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
EOF
```

---

## 8. Networking & Security

### TLS Certificates (replace self-signed)
```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml

# Create ClusterIssuer using AWS ACM or Let's Encrypt
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: prerna@mycompany.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: traefik
EOF
```

### Network Policies (restrict pod-to-pod traffic)
```yaml
# Only monitoring namespace can scrape myapp pods
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prometheus-scrape
  namespace: myapp
spec:
  podSelector: {}
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - port: 8080
```

---

## 9. Monitoring Stack

### Grafana Dashboards to Import
| Dashboard | ID | Purpose |
|-----------|-----|---------|
| Kubernetes Cluster | 7249 | Overall cluster health |
| Node Exporter Full | 1860 | Per-node CPU/RAM/Disk |
| Kubernetes Pods | 6417 | Pod resource usage |
| Traefik | 11462 | Ingress traffic |
| **ML Predictor** | Custom | Predicted vs actual CPU |

### Key Prometheus Alerts (add to alert-rules.yaml)
```yaml
- alert: PredictorModelStale
  expr: time() - ml_predictor_last_trained_timestamp > 7200
  for: 5m
  annotations:
    summary: "ML model has not been retrained in 2+ hours"

- alert: PredictiveScalerDown
  expr: absent(up{job="predictive-scaler"})
  for: 2m
  annotations:
    summary: "Predictive scaler controller is down — falling back to reactive HPA"

- alert: ScalingLagDetected
  expr: kube_deployment_spec_replicas{deployment="web"}
        < ceil(sum(rate(container_cpu_usage_seconds_total{pod=~"web-.*"}[5m])) / 0.08)
  for: 3m
  annotations:
    summary: "Reactive scaling lag detected — predictive scaler may be misconfigured"
```

---

## 10. Cost Estimation

### Monthly AWS Cost (Recommended Setup, ap-south-1)

| Resource | Count | Cost/unit | Monthly |
|----------|-------|-----------|---------|
| m5.large (control plane) | 3 | $105 | $315 |
| m5.xlarge (app workers) | 3 | $192 | $576 |
| m5.2xlarge (ML workers) | 2 | $384 | $768 |
| m5.xlarge (monitoring) | 1 | $192 | $192 |
| t3.micro (bastion) | 1 | $9 | $9 |
| EBS gp3 storage (total ~1.2 TB) | — | $0.10/GB | $120 |
| NAT Gateway | 1 | $35 | $35 |
| ALB | 1 | $25 | $25 |
| Data transfer | — | — | ~$20 |
| ECR storage | — | $0.10/GB | ~$5 |

**Total estimated: ~$2,065/month**

### Cost Optimization Options
- Use **Spot Instances** for ML workers (save 60-70%) = ~-$460/month
- Use **Reserved Instances** (1-year) for control plane = ~-$120/month
- Use **EKS** instead of self-managed (removes control plane management) = +$210/month (EKS fee) but saves ops time
- **Total optimized: ~$1,485/month**

---

## 11. Production Checklist

### Before Go-Live

#### Infrastructure
- [ ] All 9-11 EC2 nodes launched and running
- [ ] VPC with public/private subnets configured
- [ ] Security groups applied (only required ports open)
- [ ] IAM roles attached to all nodes
- [ ] NAT Gateway configured for private subnet internet access
- [ ] Bastion host accessible via SSH

#### Kubernetes
- [ ] Cluster initialized with 3 control plane nodes (HA etcd)
- [ ] All worker nodes joined and in Ready state (`kubectl get nodes`)
- [ ] Flannel/Calico CNI installed
- [ ] Node labels and taints applied
- [ ] StorageClass `gp3` created and set as default

#### Application
- [ ] Docker images built and pushed to ECR
- [ ] All manifests updated with ECR image URLs
- [ ] `myapp` and `monitoring` namespaces created
- [ ] Web deployment running (2+ replicas)
- [ ] ML predictor running and reachable
- [ ] Predictive scaler running and fetching predictions
- [ ] HPA configured as safety net

#### Security
- [ ] All secrets moved from YAML files to Kubernetes Secrets
- [ ] Telegram bot token rotated (was exposed in alertmanager.yaml)
- [ ] TLS certificates from cert-manager (not self-signed)
- [ ] Network policies applied
- [ ] RBAC minimal permissions verified
- [ ] Bastion is only SSH entry point

#### Monitoring
- [ ] Prometheus scraping all targets (`/targets` shows all green)
- [ ] Grafana dashboards imported and showing data
- [ ] Loki receiving logs from all pods
- [ ] AlertManager configured and tested (Telegram notification works)
- [ ] All critical alerts firing correctly in test

#### GitOps
- [ ] ArgoCD connected to gitops repository
- [ ] Application syncing automatically on git push
- [ ] ArgoCD admin password changed from default

#### Backup & Recovery
- [ ] etcd backup to S3 configured (via CronJob)
- [ ] Prometheus data retention set to 15 days
- [ ] Disaster recovery procedure documented and tested

---

## Summary

| Category | Minimum | Recommended |
|----------|---------|-------------|
| EC2 Nodes | 9 | 11 |
| vCPU total | 24 | 42 |
| RAM total | 70 GB | 128 GB |
| Storage total | 680 GB | 1.2 TB |
| Monthly cost | ~$1,200 | ~$2,065 |
| HA level | Partial | Full (3 control plane) |
| ML training | 1 replica | 2 replicas (rolling update) |

---

*Document generated: 2026-03-27*
*Project: Intelligent Auto-Scaling in Kubernetes — ML Based Predictive Approach*
*Author: Prerna Tank | M.Tech(CS) 2410512 | DAVV*
