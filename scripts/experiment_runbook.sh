#!/bin/bash
# IEEE Paper Experiment Runbook
# Usage: bash scripts/experiment_runbook.sh
# Run from the project root on the MASTER node (10.0.1.7)

set -e

RESULTS_DIR="results/ieee_paper_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "============================================================"
echo "IEEE Paper - Ablation Study Runbook"
echo "Results will be saved to: $RESULTS_DIR"
echo "============================================================"

# ============================================================
# STEP 1: Pre-flight checks
# ============================================================
echo ""
echo "[STEP 1/7] Pre-flight checks..."

echo "--- Kubernetes nodes ---"
kubectl get nodes -o wide | tee "$RESULTS_DIR/01_nodes.txt"

echo ""
echo "--- All pods in monitoring namespace ---"
kubectl get pods -n monitoring -o wide | tee "$RESULTS_DIR/02_pods_before.txt"

echo ""
echo "--- Current replica counts ---"
kubectl get deployments -n monitoring -o wide | tee "$RESULTS_DIR/03_deployments_before.txt"

echo ""
echo "Proceed? (Check above output looks healthy) [y/N]"
read -r CONFIRM
[ "$CONFIRM" != "y" ] && echo "Aborted." && exit 1

# ============================================================
# STEP 2: Baseline metrics
# ============================================================
echo ""
echo "[STEP 2/7] Capturing baseline Prometheus metrics..."
BASELINE_CPU=$(curl -s "http://10.0.1.7:30090/api/v1/query?query=avg(rate(container_cpu_usage_seconds_total%7Bnamespace%3D%22default%22%7D%5B5m%5D))" | tee "$RESULTS_DIR/04_baseline_cpu.json")
echo "Baseline CPU captured: $RESULTS_DIR/04_baseline_cpu.json"

# ============================================================
# STEP 3: Run each experiment
# ============================================================
echo ""
echo "[STEP 3/7] Running 6 experiments (each ~30 min)..."
echo "Estimated total time: 3 hours"
echo ""

EXPERIMENTS=("BASELINE_hpa" "E4_cpu_only" "E5_no_cost" "E3_no_confidence" "E2_no_drift" "E1_full")

for EXP in "${EXPERIMENTS[@]}"; do
  echo ""
  echo "============================================================"
  echo "Running: $EXP"
  echo "Start time: $(date)"
  echo "============================================================"

  kubectl get pods -n monitoring > "$RESULTS_DIR/pods_before_${EXP}.txt"

  python scripts/run_ablation_study.py \
    --experiments "$EXP" \
    --duration 1800 \
    --rps 50 \
    --output "$RESULTS_DIR/${EXP}.json"

  kubectl get pods -n monitoring > "$RESULTS_DIR/pods_after_${EXP}.txt"
  kubectl get events -n monitoring --sort-by='.lastTimestamp' | tail -30 > "$RESULTS_DIR/events_${EXP}.txt"

  echo "$EXP complete. Cooling down 60s..."
  sleep 60
done

# ============================================================
# STEP 4: Consolidate results
# ============================================================
echo ""
echo "[STEP 4/7] Consolidating results..."
python -c "
import json, glob
from pathlib import Path
all_results = []
for f in sorted(glob.glob('$RESULTS_DIR/E*.json') + glob.glob('$RESULTS_DIR/BASELINE*.json')):
    with open(f) as fp:
        data = json.load(fp)
        if isinstance(data, list):
            all_results.extend(data)
        else:
            all_results.append(data)
with open('$RESULTS_DIR/all_experiments.json', 'w') as fp:
    json.dump(all_results, fp, indent=2)
print(f'Consolidated {len(all_results)} experiments into all_experiments.json')
"

# ============================================================
# STEP 5: Generate figures
# ============================================================
echo ""
echo "[STEP 5/7] Generating paper figures..."
python scripts/generate_paper_figures.py \
  --input "$RESULTS_DIR/all_experiments.json" \
  --outdir "$RESULTS_DIR/figures/"

# ============================================================
# STEP 6: Generate summary table
# ============================================================
echo ""
echo "[STEP 6/7] Generating summary table for paper..."
python -c "
import json
with open('$RESULTS_DIR/all_experiments.json') as f:
    results = json.load(f)

print('\n' + '='*80)
print(f'{\"Experiment\":<25} {\"SLA Viol %\":>12} {\"Avg Lat ms\":>12} {\"P95 ms\":>10} {\"P99 ms\":>10} {\"Cost USD\":>10}')
print('='*80)
for r in results:
    exp = r.get('experiment', '?')
    lat = r.get('latency', {})
    cost = r.get('cost', {}).get('total_cost_usd', 0)
    print(f'{exp:<25} {lat.get(\"violation_pct_200ms\", 0):>12.2f} {lat.get(\"avg_latency_ms\", 0):>12.2f} {lat.get(\"p95_latency_ms\", 0):>10.2f} {lat.get(\"p99_latency_ms\", 0):>10.2f} {cost:>10.4f}')
print('='*80)
" | tee "$RESULTS_DIR/summary_table.txt"

# ============================================================
# STEP 7: Post-experiment verification
# ============================================================
echo ""
echo "[STEP 7/7] Post-experiment verification..."

echo "--- Final pods state ---"
kubectl get pods -n monitoring -o wide | tee "$RESULTS_DIR/99_pods_after.txt"

echo ""
echo "--- Final deployments ---"
kubectl get deployments -n monitoring | tee "$RESULTS_DIR/99_deployments_after.txt"

echo ""
echo "--- Disk space for results ---"
du -sh "$RESULTS_DIR"

echo ""
echo "============================================================"
echo "EXPERIMENT COMPLETE"
echo "============================================================"
echo "Results folder: $RESULTS_DIR"
echo ""
echo "Next: Review $RESULTS_DIR/summary_table.txt"
echo "      Review figures in $RESULTS_DIR/figures/"
echo "      Copy numbers into IEEE_Paper_Prerna_Tank.md Section VI"
echo ""
