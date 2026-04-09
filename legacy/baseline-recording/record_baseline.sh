#!/bin/bash

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="baseline_${TIMESTAMP}"

mkdir -p $REPORT_DIR

echo "============================================================"
echo "RECORDING BASELINE SETUP - $(date)"
echo "============================================================"
echo ""

# ============================================================
# 1. CLUSTER INFORMATION
# ============================================================
echo "📊 Recording Cluster Information..."

cat > $REPORT_DIR/01_cluster_info.txt << EOF
KUBERNETES CLUSTER BASELINE RECORDING
Generated: $(date)
============================================================

CLUSTER VERSION:
EOF

kubectl version --short >> $REPORT_DIR/01_cluster_info.txt 2>&1

cat >> $REPORT_DIR/01_cluster_info.txt << EOF

NODES:
============================================================
EOF

kubectl get nodes -o wide >> $REPORT_DIR/01_cluster_info.txt 2>&1

cat >> $REPORT_DIR/01_cluster_info.txt << EOF

NODE DETAILS:
============================================================
EOF

kubectl describe nodes >> $REPORT_DIR/01_cluster_info.txt 2>&1

echo "✅ Cluster info saved"

# ============================================================
# 2. RESOURCE METRICS
# ============================================================
echo "📊 Recording Resource Metrics..."

cat > $REPORT_DIR/02_resource_metrics.txt << EOF
RESOURCE METRICS BASELINE
Generated: $(date)
============================================================

NODE RESOURCES:
EOF

kubectl top nodes >> $REPORT_DIR/02_resource_metrics.txt 2>&1

cat >> $REPORT_DIR/02_resource_metrics.txt << EOF

POD RESOURCES (ALL NAMESPACES):
============================================================
EOF

kubectl top pods -A >> $REPORT_DIR/02_resource_metrics.txt 2>&1

cat >> $REPORT_DIR/02_resource_metrics.txt << EOF

NAMESPACE RESOURCE QUOTAS:
============================================================
EOF

kubectl get resourcequotas -A >> $REPORT_DIR/02_resource_metrics.txt 2>&1

echo "✅ Resource metrics saved"

# ============================================================
# 3. APPLICATION STATUS
# ============================================================
echo "📊 Recording Application Status..."

cat > $REPORT_DIR/03_application_status.txt << EOF
APPLICATION STATUS BASELINE
Generated: $(date)
============================================================

MYAPP NAMESPACE - DEPLOYMENTS:
EOF

kubectl get deployments -n myapp -o wide >> $REPORT_DIR/03_application_status.txt 2>&1

cat >> $REPORT_DIR/03_application_status.txt << EOF

MYAPP NAMESPACE - PODS:
============================================================
EOF

kubectl get pods -n myapp -o wide >> $REPORT_DIR/03_application_status.txt 2>&1

cat >> $REPORT_DIR/03_application_status.txt << EOF

MYAPP NAMESPACE - SERVICES:
============================================================
EOF

kubectl get svc -n myapp -o wide >> $REPORT_DIR/03_application_status.txt 2>&1

cat >> $REPORT_DIR/03_application_status.txt << EOF

MYAPP NAMESPACE - INGRESSES:
============================================================
EOF

kubectl get ingress -n myapp -o wide >> $REPORT_DIR/03_application_status.txt 2>&1

cat >> $REPORT_DIR/03_application_status.txt << EOF

WEB DEPLOYMENT YAML:
============================================================
EOF

kubectl get deployment web -n myapp -o yaml >> $REPORT_DIR/03_application_status.txt 2>&1

echo "✅ Application status saved"

# ============================================================
# 4. HPA STATUS (if exists)
# ============================================================
echo "📊 Recording HPA Status..."

cat > $REPORT_DIR/04_hpa_status.txt << EOF
HORIZONTAL POD AUTOSCALER BASELINE
Generated: $(date)
============================================================

HPA LIST:
EOF

kubectl get hpa -A >> $REPORT_DIR/04_hpa_status.txt 2>&1

cat >> $REPORT_DIR/04_hpa_status.txt << EOF

HPA DETAILS (MYAPP):
============================================================
EOF

kubectl describe hpa -n myapp >> $REPORT_DIR/04_hpa_status.txt 2>&1

echo "✅ HPA status saved"

# ============================================================
# 5. MONITORING STACK
# ============================================================
echo "📊 Recording Monitoring Stack..."

cat > $REPORT_DIR/05_monitoring_stack.txt << EOF
MONITORING STACK BASELINE
Generated: $(date)
============================================================

MONITORING NAMESPACE - PODS:
EOF

kubectl get pods -n monitoring -o wide >> $REPORT_DIR/05_monitoring_stack.txt 2>&1

cat >> $REPORT_DIR/05_monitoring_stack.txt << EOF

MONITORING NAMESPACE - SERVICES:
============================================================
EOF

kubectl get svc -n monitoring >> $REPORT_DIR/05_monitoring_stack.txt 2>&1

cat >> $REPORT_DIR/05_monitoring_stack.txt << EOF

PROMETHEUS RULES:
============================================================
EOF

kubectl get prometheusrule -n monitoring >> $REPORT_DIR/05_monitoring_stack.txt 2>&1

cat >> $REPORT_DIR/05_monitoring_stack.txt << EOF

ALERTMANAGER CONFIG:
============================================================
EOF

kubectl get configmap prometheus-alertmanager -n monitoring -o yaml >> $REPORT_DIR/05_monitoring_stack.txt 2>&1

echo "✅ Monitoring stack saved"

# ============================================================
# 6. INGRESS CONTROLLER
# ============================================================
echo "📊 Recording Ingress Controller..."

cat > $REPORT_DIR/06_ingress_controller.txt << EOF
INGRESS CONTROLLER BASELINE
Generated: $(date)
============================================================

TRAEFIK PODS:
EOF

kubectl get pods -n traefik -o wide >> $REPORT_DIR/06_ingress_controller.txt 2>&1

cat >> $REPORT_DIR/06_ingress_controller.txt << EOF

TRAEFIK SERVICES:
============================================================
EOF

kubectl get svc -n traefik >> $REPORT_DIR/06_ingress_controller.txt 2>&1

cat >> $REPORT_DIR/06_ingress_controller.txt << EOF

ALL INGRESSES:
============================================================
EOF

kubectl get ingress -A >> $REPORT_DIR/06_ingress_controller.txt 2>&1

echo "✅ Ingress controller saved"

# ============================================================
# 7. PERFORMANCE TEST - BASELINE
# ============================================================
echo "📊 Running Performance Baseline Test..."

cat > $REPORT_DIR/07_performance_baseline.txt << EOF
PERFORMANCE BASELINE TEST
Generated: $(date)
============================================================

TEST CONFIGURATION:
- Tool: Apache Bench
- Requests: 1000
- Concurrency: 50
- Target: web.mycompany.local

RESPONSE TIME TEST (20 samples):
============================================================
EOF

echo "Running response time samples..."
for i in {1..20}; do
  start=$(date +%s%N)
  curl -s -o /dev/null -H "Host: web.mycompany.local" http://103.192.199.79:30080
  end=$(date +%s%N)
  elapsed=$((($end - $start)/1000000))
  echo "Sample $i: ${elapsed}ms" >> $REPORT_DIR/07_performance_baseline.txt
done

cat >> $REPORT_DIR/07_performance_baseline.txt << EOF

LOAD DISTRIBUTION TEST (50 requests):
============================================================
EOF

echo "Testing load distribution..."
for i in {1..50}; do
  curl -s -H "Host: web.mycompany.local" http://103.192.199.79:30080 | grep -oP 'pod: \K[^<]+' >> $REPORT_DIR/07_performance_baseline.txt
done

cat >> $REPORT_DIR/07_performance_baseline.txt << EOF

APACHE BENCH FULL TEST:
============================================================
EOF

ab -n 1000 -c 50 -H "Host: web.mycompany.local" http://103.192.199.79:30080/ >> $REPORT_DIR/07_performance_baseline.txt 2>&1

echo "✅ Performance baseline saved"

# ============================================================
# 8. SCALING BEHAVIOR TEST
# ============================================================
echo "📊 Testing Current Scaling Behavior..."

cat > $REPORT_DIR/08_scaling_test.txt << EOF
SCALING BEHAVIOR BASELINE TEST
Generated: $(date)
============================================================

INITIAL STATE:
EOF

kubectl get pods -n myapp >> $REPORT_DIR/08_scaling_test.txt 2>&1
kubectl get hpa -n myapp >> $REPORT_DIR/08_scaling_test.txt 2>&1
kubectl top pods -n myapp >> $REPORT_DIR/08_scaling_test.txt 2>&1

cat >> $REPORT_DIR/08_scaling_test.txt << EOF

LOAD TEST (to trigger scaling):
============================================================
Starting load test for 2 minutes...
EOF

# Generate load in background
for i in {1..120}; do
  for j in {1..10}; do
    curl -s -H "Host: web.mycompany.local" http://103.192.199.79:30080 > /dev/null &
  done
  sleep 1
done &

LOAD_PID=$!

# Monitor for 3 minutes
for i in {1..18}; do
  sleep 10
  echo "" >> $REPORT_DIR/08_scaling_test.txt
  echo "Time: $(($i * 10))s" >> $REPORT_DIR/08_scaling_test.txt
  echo "---" >> $REPORT_DIR/08_scaling_test.txt
  kubectl get pods -n myapp --no-headers | wc -l | xargs echo "Pod count:" >> $REPORT_DIR/08_scaling_test.txt
  kubectl top pods -n myapp --no-headers >> $REPORT_DIR/08_scaling_test.txt 2>&1
  kubectl get hpa -n myapp --no-headers >> $REPORT_DIR/08_scaling_test.txt 2>&1
done

wait $LOAD_PID

cat >> $REPORT_DIR/08_scaling_test.txt << EOF

FINAL STATE:
============================================================
EOF

kubectl get pods -n myapp >> $REPORT_DIR/08_scaling_test.txt 2>&1
kubectl get hpa -n myapp >> $REPORT_DIR/08_scaling_test.txt 2>&1

echo "✅ Scaling test saved"

# ============================================================
# 9. CONFIGURATION FILES
# ============================================================
echo "📊 Backing up Configuration Files..."

mkdir -p $REPORT_DIR/configs

# Export all important resources
kubectl get deployment web -n myapp -o yaml > $REPORT_DIR/configs/web-deployment.yaml
kubectl get svc web-service -n myapp -o yaml > $REPORT_DIR/configs/web-service.yaml 2>/dev/null
kubectl get ingress -n myapp -o yaml > $REPORT_DIR/configs/ingresses.yaml 2>/dev/null
kubectl get hpa -n myapp -o yaml > $REPORT_DIR/configs/hpa.yaml 2>/dev/null
kubectl get prometheusrule -n monitoring -o yaml > $REPORT_DIR/configs/prometheus-rules.yaml 2>/dev/null

echo "✅ Configuration files backed up"

# ============================================================
# 10. PROMETHEUS METRICS SNAPSHOT
# ============================================================
echo "📊 Capturing Prometheus Metrics..."

cat > $REPORT_DIR/10_prometheus_metrics.txt << EOF
PROMETHEUS METRICS SNAPSHOT
Generated: $(date)
============================================================

Attempting to fetch current metrics from Prometheus...
EOF

# Port forward Prometheus (if not already)
kubectl port-forward -n monitoring svc/prometheus-server 9090:80 > /dev/null 2>&1 &
PF_PID=$!
sleep 5

# Fetch key metrics
curl -s "http://localhost:9090/api/v1/query?query=up" >> $REPORT_DIR/10_prometheus_metrics.txt 2>&1
echo "" >> $REPORT_DIR/10_prometheus_metrics.txt

curl -s "http://localhost:9090/api/v1/query?query=avg(rate(container_cpu_usage_seconds_total{namespace=\"myapp\"}[5m]))" >> $REPORT_DIR/10_prometheus_metrics.txt 2>&1
echo "" >> $REPORT_DIR/10_prometheus_metrics.txt

curl -s "http://localhost:9090/api/v1/query?query=avg(container_memory_usage_bytes{namespace=\"myapp\"})" >> $REPORT_DIR/10_prometheus_metrics.txt 2>&1

kill $PF_PID 2>/dev/null

echo "✅ Prometheus metrics captured"

# ============================================================
# 11. SUMMARY STATISTICS
# ============================================================
echo "📊 Generating Summary..."

cat > $REPORT_DIR/00_SUMMARY.txt << EOF
============================================================
BASELINE RECORDING SUMMARY
============================================================
Recording Time: $(date)
Report Directory: $REPORT_DIR

CLUSTER OVERVIEW:
============================================================
EOF

kubectl get nodes --no-headers | wc -l | xargs echo "Total Nodes:" >> $REPORT_DIR/00_SUMMARY.txt
kubectl get pods -A --no-headers | wc -l | xargs echo "Total Pods:" >> $REPORT_DIR/00_SUMMARY.txt
kubectl get namespaces --no-headers | wc -l | xargs echo "Total Namespaces:" >> $REPORT_DIR/00_SUMMARY.txt

cat >> $REPORT_DIR/00_SUMMARY.txt << EOF

MYAPP NAMESPACE:
============================================================
EOF

kubectl get pods -n myapp --no-headers | wc -l | xargs echo "Pods:" >> $REPORT_DIR/00_SUMMARY.txt
kubectl get svc -n myapp --no-headers | wc -l | xargs echo "Services:" >> $REPORT_DIR/00_SUMMARY.txt
kubectl get ingress -n myapp --no-headers | wc -l | xargs echo "Ingresses:" >> $REPORT_DIR/00_SUMMARY.txt

cat >> $REPORT_DIR/00_SUMMARY.txt << EOF

MONITORING STACK:
============================================================
EOF

kubectl get pods -n monitoring --no-headers | grep Running | wc -l | xargs echo "Running Pods:" >> $REPORT_DIR/00_SUMMARY.txt
kubectl get prometheusrule -n monitoring --no-headers | wc -l | xargs echo "Alert Rules:" >> $REPORT_DIR/00_SUMMARY.txt

cat >> $REPORT_DIR/00_SUMMARY.txt << EOF

FILES GENERATED:
============================================================
EOF

ls -lh $REPORT_DIR/*.txt | awk '{print $9, "-", $5}' >> $REPORT_DIR/00_SUMMARY.txt

cat >> $REPORT_DIR/00_SUMMARY.txt << EOF

NEXT STEPS:
============================================================
1. Review all generated files in: $REPORT_DIR/
2. Keep this baseline for comparison after ML implementation
3. Run comparison script after project completion

============================================================
EOF

echo "✅ Summary generated"

# ============================================================
# CREATE ARCHIVE
# ============================================================
echo ""
echo "📦 Creating archive..."

tar -czf ${REPORT_DIR}.tar.gz $REPORT_DIR/

echo ""
echo "============================================================"
echo "✅ BASELINE RECORDING COMPLETE!"
echo "============================================================"
echo ""
echo "Generated files:"
echo "  Directory: $REPORT_DIR/"
echo "  Archive:   ${REPORT_DIR}.tar.gz"
echo ""
echo "Summary:"
cat $REPORT_DIR/00_SUMMARY.txt
echo ""
echo "To compare later, run: ./compare_results.sh"
echo "============================================================"
