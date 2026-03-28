#!/bin/bash
# ============================================================
# DEPLOY SCRIPT - Intelligent Auto-Scaling in Kubernetes
# Run this on master-node after SCP'ing the project folder
# ============================================================

set -e

# Your cluster config
WORKER_APP_IP="10.0.1.105"      # worker-node-1
WORKER_DATA_IP="10.0.1.114"     # worker-node-2
SSH_KEY="~/.ssh/kub-cluster-key"

echo "============================================================"
echo " Step 1: Installing Docker on master-node (for building)"
echo "============================================================"
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker ubuntu
    echo "Docker installed. Run: newgrp docker"
    echo "Then re-run this script."
    exit 0
fi
echo "Docker already installed."

echo ""
echo "============================================================"
echo " Step 2: Building ML Predictor image"
echo "============================================================"
cd ~/project/ml-predictor
docker build -t ml-predictor:v1.0.0 .
echo "ml-predictor:v1.0.0 built successfully"

echo ""
echo "============================================================"
echo " Step 3: Building Predictive Scaler image"
echo "============================================================"
cd ~/project/predictive-scaler
docker build -t predictive-scaler:v1.0.0 .
echo "predictive-scaler:v1.0.0 built successfully"

echo ""
echo "============================================================"
echo " Step 4: Saving images as tar files"
echo "============================================================"
docker save ml-predictor:v1.0.0 > /tmp/ml-predictor.tar
docker save predictive-scaler:v1.0.0 > /tmp/predictive-scaler.tar
echo "Images saved to /tmp/"

echo ""
echo "============================================================"
echo " Step 5: Copying images to worker nodes"
echo "============================================================"
echo "Copying ml-predictor.tar to worker-node-2 ($WORKER_DATA_IP)..."
scp -i $SSH_KEY -o StrictHostKeyChecking=no /tmp/ml-predictor.tar ubuntu@$WORKER_DATA_IP:/tmp/

echo "Copying predictive-scaler.tar to worker-node-1 ($WORKER_APP_IP)..."
scp -i $SSH_KEY -o StrictHostKeyChecking=no /tmp/predictive-scaler.tar ubuntu@$WORKER_APP_IP:/tmp/

echo ""
echo "============================================================"
echo " Step 6: Importing images into containerd on workers"
echo "============================================================"
echo "Importing on worker-node-2..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$WORKER_DATA_IP \
    "sudo ctr -n k8s.io images import /tmp/ml-predictor.tar && echo 'ml-predictor imported on worker-node-2'"

echo "Importing on worker-node-1..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$WORKER_APP_IP \
    "sudo ctr -n k8s.io images import /tmp/predictive-scaler.tar && echo 'predictive-scaler imported on worker-node-1'"

echo ""
echo "============================================================"
echo " Step 7: Deploying RBAC for predictive scaler"
echo "============================================================"
kubectl apply -f ~/project/predictive-scaler/k8s/rbac.yaml

echo ""
echo "============================================================"
echo " Step 8: Deploying ML Predictor"
echo "============================================================"
kubectl apply -f ~/project/ml-predictor/k8s/deployment.yaml
kubectl apply -f ~/project/ml-predictor/k8s/service.yaml

echo ""
echo "============================================================"
echo " Step 9: Deploying Predictive Scaler"
echo "============================================================"
kubectl apply -f ~/project/predictive-scaler/k8s/deployment.yaml

echo ""
echo "============================================================"
echo " Step 10: Deploying HPA (safety net)"
echo "============================================================"
kubectl apply -f ~/project/hpa.yaml

echo ""
echo "============================================================"
echo " DEPLOYMENT COMPLETE!"
echo "============================================================"
echo ""
echo "Waiting 30 seconds for pods to start..."
sleep 30

echo ""
echo "Pod Status:"
kubectl get pods -A -o wide | grep -E "(myapp|monitoring.*predictor|monitoring.*scaler)"
echo ""
echo "HPA Status:"
kubectl get hpa -n myapp
echo ""
echo "============================================================"
echo " Next steps:"
echo "   kubectl logs deployment/ml-predictor -n monitoring -f"
echo "   kubectl logs deployment/predictive-scaler -n monitoring -f"
echo "============================================================"
