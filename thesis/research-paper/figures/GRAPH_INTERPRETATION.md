# Graph Interpretation Notes

## Best graphs to include

1. `fig_sla_violations.png`
   Shows the clearest performance claim in the repo: the full system reduces SLA violations from 4 to 2, which is a 50.0% reduction relative to baseline HPA.

2. `fig_latency_profile.png`
   Shows that every configuration stays far below the 200 ms SLA, but the full system also improves tail latency compared with baseline. This is useful to show robustness, not just average-case performance.

3. `fig_drift_retraining.png`
   Shows that the full system has lower mean prediction error (3.128) than baseline (3.589) while retraining more often (27 vs 25).

4. `fig_full_vs_baseline.png`
   Works well as a summary figure because it compresses the main gains into one visual comparison.

## What the results say

- The strongest result is SLA improvement. The full system halves the number of >200 ms violations compared with baseline HPA.
- Multi-metric input matters. The CPU-only ablation records 4 SLA violations versus 2 for the full system, so the richer feature set appears to help.
- Drift handling appears useful for model quality. The no-drift ablation has the same violation count as baseline and worse SLA behavior than the full system.
- Tail latency improves modestly, not dramatically. Baseline P99 is 10.06 ms and full-system P99 is 9.64 ms.

## Important limitation to mention in the paper

- The current experiment files do not support a strong cost graph. Every run stores `total_cost_usd = 0.0`, so a cost-comparison figure would be visually empty and weak for publication.
- The latency differences are real but small because the tested workload stayed comfortably below the 200 ms SLA. This means the paper should frame the result as improved reliability and stability, not dramatic latency collapse.
- No drift-triggered retrains were recorded in these files (`drift_retrains = 0`), so the drift figure demonstrates stability and retraining activity, but not a real drift event recovery.
