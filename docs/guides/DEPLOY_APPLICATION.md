# Deploy Frontend + Backend Application

Complete guide to deploy your web application with student info to Kubernetes.

---

## 📋 What's Been Deployed

**Frontend:**
- ✅ Nginx web server with 2-5 auto-scaling replicas
- ✅ Shows pod name and timestamp (proves load balancing)
- ✅ Student info: **Prerna Tank, Roll 2410512, DAVV**
- ✅ Displays backend services available

**Backend:**
- ✅ ML Predictor API (Flask, Python)
- ✅ Predictive Scaler (Kubernetes controller)

**Infrastructure:**
- ✅ Kubernetes 1.30.14 orchestration
- ✅ ArgoCD GitOps (auto-sync from GitHub)
- ✅ Jenkins CI/CD (9-stage pipeline)
- ✅ Monitoring: Prometheus + Grafana

---

## 🚀 How to Deploy

### Option 1: SSH to Master and Run Script

```bash
# SSH to Kubernetes master
ssh -i <your-ssh-key>.pem ubuntu@<master-ip>

# Navigate to repo
cd /tmp/HA-K8S1

# Run deployment script
bash scripts/deploy-frontend.sh
```

### Option 2: Manual kubectl commands

```bash
# 1. Create namespace
kubectl create namespace myapp

# 2. Deploy frontend
kubectl apply -f gitops/applications/myapp/deployment.yaml

# 3. Create service
kubectl apply -f gitops/applications/myapp/service.yaml

# 4. Create ingress
kubectl apply -f gitops/applications/myapp/ingress.yaml

# 5. Wait for ready
kubectl rollout status deployment/web -n myapp --timeout=120s

# 6. Check status
kubectl get pods -n myapp
kubectl get svc -n myapp
kubectl get ingress -n myapp
```

### Option 3: Let ArgoCD Deploy Automatically

ArgoCD can automatically sync this deployment from GitHub:

```bash
# Check if ArgoCD has the app configured
kubectl get applications -n argocd

# If not, apply ArgoCD Application CRD
kubectl apply -f gitops/argocd/myapp-application.yaml

# Trigger sync
argocd app sync myapp
```

---

## 📍 Access the Application

After deployment, access your app here:

### Via Ingress (Recommended)
```
http://<INGRESS_IP>/
```

Get ingress IP:
```bash
kubectl get ingress -n myapp -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}'
```

### Via Port-Forward (If ingress not available)
```bash
# Terminal 1: Port-forward
kubectl port-forward -n myapp svc/web-service 8080:80

# Terminal 2: Open browser
http://localhost:8080
```

### Via NodePort (Alternative)
```bash
# Get NodePort
kubectl get svc -n myapp -o jsonpath='{.items[0].spec.ports[0].nodePort}'

# Access via worker node IP
http://<worker-app-ip>:<NODEPORT>/
```

---

## ✅ Verify Deployment

Check that everything is running:

```bash
# 1. Pods running
kubectl get pods -n myapp
# Expected: 2 running pods (web-xxx)

# 2. Service created
kubectl get svc -n myapp
# Expected: web-service (ClusterIP)

# 3. Ingress created
kubectl get ingress -n myapp
# Expected: web-ingress with IP assigned

# 4. Check pod logs
kubectl logs -n myapp -l app=web -f

# 5. Scale the deployment
kubectl scale deployment/web -n myapp --replicas=5

# 6. Watch pods scale
kubectl get pods -n myapp -w
```

---

## 📸 What Your Teacher Will See

When you open the application in browser, you'll see:

```
╔══════════════════════════════════════════════════════════╗
║  🚀 Intelligent Auto-Scaling in Kubernetes              ║
║     ML-Based Predictive Approach with                    ║
║     Multi-Tier Architecture                              ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  📍 FRONTEND (Current Pod)                               ║
║  Served by pod: web-xyz123                               ║
║  Status: ✓ Running                                       ║
║  Timestamp: 2026-04-09 23:45:30 UTC                      ║
║                                                          ║
║  🔧 BACKEND SERVICES                                     ║
║  ML Predictor API: ✓ Available                           ║
║  - Endpoint: /predict                                    ║
║  - Multi-Metric: CPU + Memory + Network                  ║
║  - Drift Detection: Auto-retrain                         ║
║                                                          ║
║  📊 DEPLOYMENT INFO                                      ║
║  ✓ Namespace: myapp                                      ║
║  ✓ Replicas: 2-5                                         ║
║  ✓ ML Model: LSTM                                        ║
║  ✓ Frontend: nginx ✓ Backend: Flask                      ║
║                                                          ║
║  👤 STUDENT INFO                                         ║
║  Name: Prerna Tank                                       ║
║  Roll No: 2410512                                        ║
║  University: DAVV (CS M.Tech)                            ║
║  Project: Intelligent Auto-Scaling in K8s                ║
║                                                          ║
║  ✓ Application deployed | ✓ CI/CD working |              ║
║  ✓ ArgoCD sync active                                    ║
║                                                          ║
║  Refresh page to see load balancing →                    ║
╚══════════════════════════════════════════════════════════╝
```

**Perfect for teacher demo!** 📸

---

## 🔄 Load Balancing Demo

To show your teacher the load balancing in action:

```bash
# 1. Open application in browser
http://<IP>/

# 2. Refresh the page multiple times
# Each refresh shows a DIFFERENT pod name (web-xxx changes)
# This proves:
#   ✓ Multiple replicas running
#   ✓ Load balancer routing traffic
#   ✓ Auto-scaling working

# 3. Watch live scaling
kubectl get pods -n myapp -w
# Pods will scale up to 5 when load increases

# 4. Check HPA status
kubectl get hpa -n myapp
```

---

## 📊 Complete Architecture Your Teacher Sees

```
┌─────────────────────────────────────────────────────────┐
│  Internet / Teacher's Browser                           │
│         ↓                                                │
├─────────────────────────────────────────────────────────┤
│  Ingress / LoadBalancer                                 │
│  (web-ingress)                                          │
│         ↓                                                │
├─────────────────────────────────────────────────────────┤
│  Kubernetes Service (web-service)                       │
│         ↓                                                │
├─────────────────────────────────────────────────────────┤
│  FRONTEND - nginx (2-5 replicas, auto-scaling)          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  web-abc123  │  │  web-def456  │  │  web-ghi789  │  │
│  │  Pod 1       │  │  Pod 2       │  │  Pod 3       │  │
│  │  Running     │  │  Running     │  │  Running     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
├─────────────────────────────────────────────────────────┤
│  BACKEND SERVICES (in monitoring namespace)             │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  ML Predictor    │  │  Predictive      │            │
│  │  (Flask API)     │  │  Scaler (K8s)    │            │
│  │  port: 5000      │  │  Port: 8000      │            │
│  └──────────────────┘  └──────────────────┘            │
├─────────────────────────────────────────────────────────┤
│  MONITORING & CI/CD                                     │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  Prometheus      │  │  ArgoCD          │            │
│  │  + Grafana       │  │  (GitOps Sync)   │            │
│  └──────────────────┘  └──────────────────┘            │
│           ↓                     ↓                        │
│  GitHub: prerna3640/HA-K8S1  (auto-sync)               │
│  Jenkins: 9-stage CI/CD pipeline                       │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Demo Flow for Teacher (5 minutes)

1. **Show Frontend** → Open browser, show application with your name
2. **Refresh Page** → Show pod name changes (load balancing)
3. **Show Backend Info** → Point out "Backend Services" section
4. **Show Kubernetes** → Run `kubectl get pods -n myapp`
5. **Show Auto-Scaling** → Scale pods up: `kubectl scale deployment/web -n myapp --replicas=5`
6. **Show GitOps** → Explain ArgoCD auto-deploys from GitHub
7. **Show Pipeline** → Screenshot of Jenkins 9-stage pipeline with tests passing
8. **Explain Research** → Multi-metric LSTM, drift detection, cost-aware, confidence gating

**Total time: 5-7 minutes**

---

## ⚠️ Troubleshooting

### Problem: Pods not starting
```bash
kubectl describe pod -n myapp <pod-name>
kubectl logs -n myapp <pod-name>
```

### Problem: Service not accessible
```bash
# Check service
kubectl get svc -n myapp

# Check ingress
kubectl get ingress -n myapp

# Check ingress controller
kubectl get pods -n ingress-nginx
```

### Problem: Can't deploy
- Check namespace exists: `kubectl get ns`
- Check YAML syntax: `kubectl apply -f ... --dry-run=client`
- Check RBAC: `kubectl auth can-i create deployments --as=system:serviceaccount:myapp:default`

---

## 🔗 Related Documentation

- [JENKINS_ACCESS_VERIFY.md](JENKINS_ACCESS_VERIFY.md) - How to verify Jenkins pipeline
- [REPO_STRUCTURE.md](REPO_STRUCTURE.md) - Project folder structure
- [docs/PROJECT_README.md](docs/PROJECT_README.md) - Complete project overview

---

**Your application is ready to deploy! 🚀**
