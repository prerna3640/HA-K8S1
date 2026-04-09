# ⚡ Quick Deploy Command

Copy-paste this command on your Kubernetes master (<master-ip>) to deploy the application:

---

## 🚀 Deploy in One Command

SSH to master and run:

```bash
ssh -i <your-ssh-key>.pem ubuntu@<master-ip>

# Once logged in, run:
cd /tmp && \
git clone https://github.com/prerna3640/HA-K8S1.git 2>/dev/null || (cd HA-K8S1 && git pull origin main) && \
cd HA-K8S1 && \
bash scripts/deploy-frontend.sh
```

---

## ✅ What This Does

1. ✅ SSH to Kubernetes master
2. ✅ Clone latest code from GitHub
3. ✅ Create `myapp` namespace
4. ✅ Deploy frontend (nginx 2-5 replicas)
5. ✅ Create service and ingress
6. ✅ Shows deployment status
7. ✅ Shows your name: **Prerna Tank, 2410512, DAVV**

---

## 📍 After Deployment

You'll see output showing:
- ✓ Deployment created
- ✓ Service created
- ✓ Ingress created
- ✓ 2 pods running (web-xxx, web-yyy)

Get the application URL:

```bash
# Check ingress IP
kubectl get ingress -n myapp -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}'

# Or use port-forward
kubectl port-forward -n myapp svc/web-service 8080:80
# Then open: http://localhost:8080
```

---

## 📸 What Your Teacher Sees

When you open the URL, the page shows:

```
🚀 Intelligent Auto-Scaling in Kubernetes
   ML-Based Predictive Approach

📍 FRONTEND (Current Pod)
   Served by: web-abc123
   Status: ✓ Running

🔧 BACKEND SERVICES
   ML Predictor API: ✓ Available
   - Multi-Metric: CPU + Memory + Network
   - Drift Detection: Auto-retrain

📊 DEPLOYMENT INFO
   ✓ Namespace: myapp
   ✓ Replicas: 2-5 (auto-scaling)
   ✓ Frontend: nginx ✓ Backend: Flask

👤 STUDENT INFO
   Name: Prerna Tank
   Roll No: 2410512
   University: DAVV (M.Tech CS)
   Project: Intelligent Auto-Scaling in K8s

---

Refresh page to see load balancing (pod name changes)
```

Perfect for showing your teacher! 📸

---

## 🔄 Demo Tips

**To show load balancing:**
```bash
# Refresh browser multiple times
# Watch the pod name change with each refresh
```

**To show auto-scaling:**
```bash
# Scale up to 5 replicas
kubectl scale deployment/web -n myapp --replicas=5

# Watch pods scale
kubectl get pods -n myapp -w
```

**To show CI/CD integration:**
```bash
# Make a change to deployment.yaml
# Commit and push to GitHub
# ArgoCD automatically syncs and deploys
# Jenkins runs tests automatically
```

---

**That's it! Run the command and your application is deployed!** 🚀
