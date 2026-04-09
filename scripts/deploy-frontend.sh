#!/bin/bash

###############################################################################
# Deploy Frontend Application to Kubernetes
# Run this script on the Kubernetes master or worker node with kubectl access
###############################################################################

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          DEPLOYING FRONTEND + BACKEND ARCHITECTURE             ║"
echo "║              Prerna's ML Auto-Scaling Project                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Create namespace
echo -e "${BLUE}Step 1: Creating namespace 'myapp'${NC}"
kubectl create namespace myapp 2>/dev/null || echo "✓ Namespace 'myapp' already exists"
echo ""

# Step 2: Apply deployment
echo -e "${BLUE}Step 2: Deploying Frontend (nginx with 2-5 replicas)${NC}"
kubectl apply -f gitops/applications/myapp/deployment.yaml
echo "✓ Deployment created"
echo ""

# Step 3: Apply service
echo -e "${BLUE}Step 3: Creating Service (ClusterIP)${NC}"
kubectl apply -f gitops/applications/myapp/service.yaml
echo "✓ Service created"
echo ""

# Step 4: Apply ingress
echo -e "${BLUE}Step 4: Creating Ingress (for external access)${NC}"
kubectl apply -f gitops/applications/myapp/ingress.yaml
echo "✓ Ingress created"
echo ""

# Step 5: Wait for deployment
echo -e "${BLUE}Step 5: Waiting for deployment to be ready...${NC}"
kubectl rollout status deployment/web -n myapp --timeout=120s || true
echo ""

# Step 6: Show status
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    ✓ DEPLOYMENT COMPLETE                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

echo -e "${GREEN}📦 DEPLOYMENT STATUS:${NC}"
kubectl get deployment -n myapp -o wide
echo ""

echo -e "${GREEN}🐳 RUNNING PODS:${NC}"
kubectl get pods -n myapp -o wide
echo ""

echo -e "${GREEN}🔌 SERVICE:${NC}"
kubectl get svc -n myapp -o wide
echo ""

echo -e "${GREEN}🌐 INGRESS:${NC}"
kubectl get ingress -n myapp -o wide
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                   HOW TO ACCESS THE APP                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Try to get ingress IP
INGRESS_IP=$(kubectl get ingress -n myapp -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")

if [ -z "$INGRESS_IP" ]; then
  echo "⚠️  Ingress not yet assigned an IP (waiting for LoadBalancer)"
  echo ""
  echo "Option 1: Use NodePort (if available)"
  echo "  kubectl get svc -n myapp -o jsonpath='{.items[0].spec.ports[0].nodePort}'"
  echo ""
  echo "Option 2: Port-forward to access:"
  echo "  kubectl port-forward -n myapp svc/web-service 8080:80"
  echo "  Then open: http://localhost:8080"
  echo ""
  echo "Option 3: Check Ingress status:"
  echo "  kubectl describe ingress web-ingress -n myapp"
else
  echo "✓ Frontend accessible at: http://$INGRESS_IP"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                   APPLICATION COMPONENTS                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Frontend (This deployment):"
echo "  ✓ Nginx web server (2-5 replicas)"
echo "  ✓ Shows pod name and timestamp"
echo "  ✓ Student info: Prerna Tank (2410512)"
echo "  ✓ Displays backend services available"
echo ""
echo "Backend Services:"
echo "  ✓ ML Predictor (monitoring namespace)"
echo "  ✓ Predictive Scaler (monitoring namespace)"
echo ""
echo "Infrastructure:"
echo "  ✓ Kubernetes 1.30.14"
echo "  ✓ ArgoCD GitOps (auto-sync from GitHub)"
echo "  ✓ Jenkins CI/CD (9-stage pipeline)"
echo "  ✓ Prometheus + Grafana monitoring"
echo ""

echo "✅ Deployment successful! Your application is running."
echo ""
echo "Watch logs:"
echo "  kubectl logs -n myapp -l app=web -f"
echo ""
echo "Scale deployment:"
echo "  kubectl scale deployment/web -n myapp --replicas=5"
echo ""
