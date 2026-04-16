# IEEE Paper — Experiment Steps & Verification

## Overview

You will run **6 experiments × 30 minutes = 3 hours total** and fill the results into the paper.

---

## STEP 1: Pre-Flight Checks (5 min)

### 1.1 SSH into master node

```bash
ssh -i kub-cluster-key.pem ubuntu@10.0.1.7
cd ~/HA-K8S1
git pull
```

### 1.2 Verify cluster is healthy

```bash
kubectl get nodes
# Expected: 3 nodes all Ready
#   master      Ready   control-plane   ...
#   worker-app  Ready   <none>          ...
#   worker-data Ready   <none>          ...

kubectl get pods -n monitoring
# Expected: ml-predictor, predictive-scaler, prometheus, grafana all Running
```

### 1.3 Verify services reachable

```bash
# ML Predictor
curl http://10.0.1.114:30050/health
# Expected: {"status":"healthy"}

# Web app
curl http://10.0.1.105:30080/
# Expected: HTML response

# Prometheus
curl http://10.0.1.7:30090/-/healthy
# Expected: Prometheus is Healthy

# Grafana
curl http://10.0.1.7:30030/api/health
# Expected: {"commit":"...","database":"ok"}
```

### ✅ Verify Step 1:
- [ ] All 3 nodes Ready
- [ ] All monitoring pods Running
- [ ] 4 health endpoints respond OK

---

## STEP 2: Install Dependencies (one-time, 2 min)

```bash
pip install requests matplotlib numpy
# Verify
python -c "import requests, matplotlib, numpy; print('OK')"
```

### ✅ Verify Step 2:
- [ ] `python -c "import requests, matplotlib, numpy; print('OK')"` prints OK

---

## STEP 3: Run Experiments (3 hours)

### Option A: Run all at once (recommended)

```bash
cd ~/HA-K8S1
bash scripts/experiment_runbook.sh
```

This runs all 6 experiments automatically. **Don't close the terminal.**

### Option B: Run one at a time (for debugging)

```bash
# Start fresh
mkdir -p results/

# Run each experiment (30 min each)
python scripts/run_ablation_study.py --experiments BASELINE_hpa --duration 1800 --output results/baseline.json
python scripts/run_ablation_study.py --experiments E4_cpu_only --duration 1800 --output results/e4.json
python scripts/run_ablation_study.py --experiments E5_no_cost --duration 1800 --output results/e5.json
python scripts/run_ablation_study.py --experiments E3_no_confidence --duration 1800 --output results/e3.json
python scripts/run_ablation_study.py --experiments E2_no_drift --duration 1800 --output results/e2.json
python scripts/run_ablation_study.py --experiments E1_full --duration 1800 --output results/e1.json
```

### ✅ Verify Step 3 (during each run):
- [ ] Script shows "Experiment: XX_name" header
- [ ] Asks to apply env vars and press ENTER
- [ ] Then starts generating HTTP load
- [ ] Prints JSON result at end of each experiment
- [ ] Each experiment takes ~30 minutes

### Troubleshooting:
| Problem | Fix |
|---|---|
| ConnectionError | Check `curl http://10.0.1.105:30080/` works |
| Predictor not responding | `kubectl logs -n monitoring deploy/ml-predictor` |
| Timeout errors | Expected during spike — this is SLA violation data! |
| Pods CrashLoopBackOff | Check image pull: `kubectl describe pod <name>` |

---

## STEP 4: Record Output (after each experiment)

Each experiment produces one JSON file with this structure:

```json
{
  "experiment": "E1_full",
  "timestamp": "2026-04-16T20:30:00Z",
  "duration_sec": 1800,
  "config": { "ENABLE_DRIFT": "true", ... },
  "latency": {
    "total_requests": 90000,
    "sla_200ms_violations": 2500,
    "violation_pct_200ms": 2.78,
    "avg_latency_ms": 125.4,
    "p95_latency_ms": 230.5,
    "p99_latency_ms": 410.2
  },
  "cost": {
    "total_cost_usd": 0.045,
    "scaling_events": 7
  },
  "drift": {
    "drift_events": 1,
    "current_mape": 12.3
  }
}
```

### ✅ Verify Step 4:
- [ ] 6 JSON files exist in `results/`
- [ ] Each has `total_requests` > 0
- [ ] Each has `avg_latency_ms` value
- [ ] No JSON parsing errors

---

## STEP 5: Generate Figures (2 min)

```bash
python scripts/generate_paper_figures.py \
  --input results/all_experiments.json \
  --outdir thesis/research-paper/figures/
```

Expected output:
```
Saved: fig1_system_architecture.png
Saved: fig3_sla_comparison.png
Saved: fig4_cost_comparison.png
Saved: fig5_latency_distribution.png
```

### ✅ Verify Step 5:
- [ ] `thesis/research-paper/figures/` folder has 4 PNG files
- [ ] Open each PNG — colors visible, labels readable
- [ ] `fig3_sla_comparison.png` shows Full System = lowest violations
- [ ] `fig4_cost_comparison.png` shows relative costs

---

## STEP 6: Fill Results into Paper (30 min)

Open `thesis/research-paper/IEEE_Paper_Prerna_Tank.md` and replace all **XX** placeholders.

### Abstract (line ~17):
```
BEFORE: "shows X% reduction in SLA violations, Y% cost savings, and Z seconds pre-emptive"
AFTER:  "shows 65% reduction in SLA violations, 12% cost savings, and 60 seconds pre-emptive"
```
(Use your actual numbers from `results/summary_table.txt`)

### Section VI Tables — Replace XX with real numbers:

**Table VI.A — Scaling Performance:**
```
| Default HPA              | XX → 18.5% | XX → 285 ms | XX → 12 |
| Single-Metric LSTM (E4)  | XX → 8.2%  | XX → 180 ms | XX → 5  |
| Our Full System (E1)     | XX → 2.8%  | XX → 125 ms | XX → 1  |
```

### ✅ Verify Step 6:
- [ ] All "XX" replaced with real numbers
- [ ] Abstract numbers match Section VI numbers
- [ ] No placeholder text remaining
- [ ] Figures referenced: "as shown in Fig. 3..."

---

## STEP 7: Final Verification Before Submission (15 min)

### 7.1 Content Check

```bash
# Search for remaining placeholders
grep -n "XX" thesis/research-paper/IEEE_Paper_Prerna_Tank.md
# Expected: NO results (all replaced)

grep -n "TODO" thesis/research-paper/IEEE_Paper_Prerna_Tank.md
# Expected: NO results
```

### 7.2 Numbers Make Sense

| Sanity Check | Expected |
|---|---|
| Full System has LOWEST SLA violations | ✓ |
| BASELINE HPA has HIGHEST SLA violations | ✓ |
| Cost: Full System > HPA (you spend more, get better SLA) | ✓ |
| MAPE of Multi-Metric < MAPE of CPU-only | ✓ |
| Drift events detected > 0 during 30 min | ✓ |

### 7.3 Cross-Reference Figures

- [ ] Every figure mentioned in text is in `figures/` folder
- [ ] Every figure in `figures/` folder is referenced in text

### ✅ Verify Step 7:
- [ ] No "XX" in paper
- [ ] No "TODO" in paper
- [ ] All 5 sanity checks pass
- [ ] All figures referenced

---

## STEP 8: Commit Complete Paper and Push

### 8.1 Remove from gitignore

Edit `.gitignore` and REMOVE this line:
```
thesis/research-paper/IEEE_Paper_Prerna_Tank.md
```

### 8.2 Commit and push

```bash
cd d:/Prerna_project/project/project
git add .gitignore thesis/research-paper/IEEE_Paper_Prerna_Tank.md thesis/research-paper/figures/ results/
git commit -m "feat: complete IEEE paper with ablation experiment results

- Ran 6 experiment configurations (E1-E5 + HPA baseline)
- Generated 4 publication figures
- All XX placeholders replaced with real measurements
- Paper ready for IEEE Access submission"

git push origin main
```

### ✅ Verify Step 8:
- [ ] GitHub shows `IEEE_Paper_Prerna_Tank.md` with all real numbers
- [ ] GitHub shows `thesis/research-paper/figures/` folder with PNGs
- [ ] GitHub shows `results/` folder with JSON files

---

## Quick Checklist Summary

| Step | Time | Artifact | Verified? |
|---|---|---|---|
| 1. Pre-flight | 5 min | Cluster healthy | ☐ |
| 2. Dependencies | 2 min | Python libs installed | ☐ |
| 3. Run experiments | 3 hrs | 6 JSON files | ☐ |
| 4. Record output | (during 3) | results/ folder | ☐ |
| 5. Generate figures | 2 min | 4 PNG files | ☐ |
| 6. Fill paper | 30 min | No XX left | ☐ |
| 7. Verify | 15 min | Sanity checks pass | ☐ |
| 8. Commit + push | 5 min | On GitHub | ☐ |

**Total time: ~4 hours**

---

## Emergency Recovery

If something breaks mid-experiment:

```bash
# Reset cluster to clean state
kubectl scale deployment/web -n monitoring --replicas=1
kubectl scale deployment/ml-predictor -n monitoring --replicas=1
kubectl scale deployment/predictive-scaler -n monitoring --replicas=1

# Restart predictor (clears drift window, cost log)
kubectl rollout restart deployment/ml-predictor -n monitoring
kubectl rollout restart deployment/predictive-scaler -n monitoring

# Wait for ready
kubectl wait --for=condition=ready pod -l app=ml-predictor -n monitoring --timeout=300s

# Resume from the failed experiment (don't re-run completed ones)
python scripts/run_ablation_study.py --experiments <failed_exp_name> --duration 1800 --output results/<exp>.json
```
