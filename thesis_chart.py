import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

import os, tempfile
tmp = tempfile.gettempdir()
cpu = pd.read_csv(os.path.join(tmp, 'cpu_7days.csv'))
rep = pd.read_csv(os.path.join(tmp, 'replicas_7days.csv'))
cpu['timestamp'] = pd.to_datetime(cpu['timestamp'])
rep['timestamp'] = pd.to_datetime(rep['timestamp'])

DARK_BG = '#0f0f1a'
PANEL_BG = '#1a1a2e'
GRID = '#2a2a4a'
TEXT = '#e0e0ff'
CYAN = '#00d4ff'
GREEN = '#00ff99'
ORANGE = '#ff9900'
RED = '#ff4466'

fig, axes = plt.subplots(3, 2, figsize=(18, 14), facecolor=DARK_BG)
fig.subplots_adjust(hspace=0.45, wspace=0.3)

def style(ax, title):
    ax.set_facecolor(PANEL_BG)
    ax.tick_params(colors=TEXT, labelsize=7)
    ax.set_title(title, color=CYAN, fontsize=10, fontweight='bold', pad=8)
    ax.grid(color=GRID, linewidth=0.5, linestyle='--', alpha=0.6)
    for s in ax.spines.values():
        s.set_edgecolor(GRID)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)

# Panel 1: 7-day CPU
ax = axes[0, 0]
style(ax, '7-Day CPU Usage (millicores)')
ax.plot(cpu['timestamp'], cpu['cpu_millicores'], color=CYAN, linewidth=0.8)
ax.fill_between(cpu['timestamp'], 0, cpu['cpu_millicores'], color=CYAN, alpha=0.15)
ax.set_ylabel('CPU (millicores)')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right')

# Panel 2: 7-day replicas
ax = axes[0, 1]
style(ax, '7-Day Replica Count')
ax.step(rep['timestamp'], rep['replicas'], color=GREEN, linewidth=1.5, where='post')
ax.fill_between(rep['timestamp'], 0, rep['replicas'], step='post', color=GREEN, alpha=0.15)
ax.axhline(2, color=ORANGE, linewidth=1, linestyle='--', label='Min (2)')
ax.axhline(5, color=RED, linewidth=1, linestyle='--', label='Max (5)')
ax.set_ylabel('Replicas')
ax.set_ylim(0, 6)
ax.legend(fontsize=7, facecolor=PANEL_BG, labelcolor=TEXT, edgecolor=GRID)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right')

# Panel 3: BEFORE ML
ax = axes[1, 0]
style(ax, 'BEFORE ML (Mar 28) - Reactive HPA Only')
t_b = [0, 30, 60, 90, 120, 150, 180, 240, 300]
cpu_b = [0, 36, 136, 100, 103, 55, 56, 0, 0]
rep_b = [2, 2, 3, 4, 5, 5, 5, 5, 2]
ax2 = ax.twinx()
ax.bar(t_b, cpu_b, width=20, color=RED, alpha=0.7, label='CPU %')
ax2.step(t_b, rep_b, color=ORANGE, linewidth=2.5, where='post', label='Replicas')
ax.set_xlabel('Seconds after load start', color=TEXT)
ax.set_ylabel('HPA CPU %', color=RED)
ax2.set_ylabel('Replicas', color=ORANGE)
ax2.set_ylim(0, 6)
ax2.tick_params(colors=ORANGE)
ax.axvspan(0, 120, color=RED, alpha=0.08)
ax.text(60, 130, '~2 min delay!', color=RED, fontsize=9, fontweight='bold', ha='center')
ax.legend(loc='upper left', fontsize=7, facecolor=PANEL_BG, labelcolor=TEXT, edgecolor=GRID)
ax2.legend(loc='upper right', fontsize=7, facecolor=PANEL_BG, labelcolor=TEXT, edgecolor=GRID)

# Panel 4: AFTER ML
ax = axes[1, 1]
style(ax, 'AFTER ML (Apr 5) - Predictive Scaler Active')
t_a = [0, 60, 120, 180, 240, 300, 360, 420, 480, 540]
cpu_a = [0, 44, 103, 161, 218, 261, 229, 170, 113, 59]
rep_a = [4, 4, 4, 4, 4, 4, 4, 4, 4, 4]
ax2 = ax.twinx()
ax.bar(t_a, cpu_a, width=40, color=GREEN, alpha=0.7, label='CPU (millicores)')
ax2.step(t_a, rep_a, color=CYAN, linewidth=2.5, where='post', label='Replicas')
ax.set_xlabel('Seconds after load start', color=TEXT)
ax.set_ylabel('CPU (millicores)', color=GREEN)
ax2.set_ylabel('Replicas', color=CYAN)
ax2.set_ylim(0, 6)
ax2.tick_params(colors=CYAN)
ax.text(270, 250, '0 sec delay!\n4 pods pre-scaled', color=GREEN, fontsize=9, fontweight='bold', ha='center')
ax.legend(loc='upper left', fontsize=7, facecolor=PANEL_BG, labelcolor=TEXT, edgecolor=GRID)
ax2.legend(loc='upper right', fontsize=7, facecolor=PANEL_BG, labelcolor=TEXT, edgecolor=GRID)

# Panel 5: Comparison bars
ax = axes[2, 0]
style(ax, 'Before vs After - Key Metrics')
metrics = ['Scaling\nDelay (s)', 'Pods at\nLoad Start', 'Peak CPU\nper Pod (m)', 'User Impact\nDuration (s)']
before = [120, 2, 141, 120]
after = [0, 4, 65, 0]
x = np.arange(len(metrics))
w = 0.35
b1 = ax.bar(x - w/2, before, w, color=RED, alpha=0.8, label='Before ML (Reactive)')
b2 = ax.bar(x + w/2, after, w, color=GREEN, alpha=0.8, label='After ML (Predictive)')
ax.set_xticks(x)
ax.set_xticklabels(metrics, color=TEXT, fontsize=8)
ax.legend(fontsize=8, facecolor=PANEL_BG, labelcolor=TEXT, edgecolor=GRID)
for bar in b1:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
            str(int(bar.get_height())), ha='center', color=RED, fontsize=9, fontweight='bold')
for bar in b2:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
            str(int(bar.get_height())), ha='center', color=GREEN, fontsize=9, fontweight='bold')

# Panel 6: Results summary
ax = axes[2, 1]
ax.set_facecolor(PANEL_BG)
ax.axis('off')
ax.set_title('Thesis Results Summary', color=CYAN, fontsize=10, fontweight='bold', pad=8)
for s in ax.spines.values():
    s.set_edgecolor(GRID)

rows = [
    ('Metric', 'Before ML', 'After ML', 'Improvement'),
    ('Scaling delay', '~120 sec', '0 sec', '100% faster'),
    ('Pods at load start', '2 (min)', '4 (pre-scaled)', '2x capacity'),
    ('Peak CPU/pod', '141m', '65m', '54% lower'),
    ('User impact', '~2 min', '0 sec', 'Eliminated'),
    ('ML prediction', '0.000', '0.054 cores', 'Learned'),
    ('Training period', 'N/A', '8 days LSTM', '25 data points'),
    ('Infrastructure', '3 nodes', '3 nodes', 'Same'),
    ('', '', '', ''),
    ('Project:', 'Intelligent Auto-Scaling in Kubernetes', '', ''),
    ('Author:', 'Prerna Tank, M.Tech(CS) 2410512', '', ''),
    ('Guide:', 'Dr. Shraddha Masih, DAVV', '', ''),
]

y = 0.95
for i, (c1, c2, c3, c4) in enumerate(rows):
    clr = CYAN if i == 0 else (TEXT if c1 else '#444')
    fw = 'bold' if i == 0 else 'normal'
    c2c = RED if 0 < i < 8 else TEXT
    c3c = GREEN if 0 < i < 8 else TEXT
    c4c = ORANGE if 0 < i < 8 else TEXT
    ax.text(0.01, y, c1, fontsize=8, color=clr, fontweight=fw, transform=ax.transAxes, va='top')
    ax.text(0.32, y, c2, fontsize=8, color=c2c, fontweight=fw, transform=ax.transAxes, va='top')
    ax.text(0.55, y, c3, fontsize=8, color=c3c, fontweight=fw, transform=ax.transAxes, va='top')
    ax.text(0.78, y, c4, fontsize=8, color=c4c, fontweight=fw, transform=ax.transAxes, va='top')
    y -= 0.07

fig.text(0.5, 0.98,
         'INTELLIGENT AUTO-SCALING IN KUBERNETES\nML-Based Predictive Approach - Final Results',
         ha='center', va='top', fontsize=14, fontweight='bold', color=CYAN, linespacing=1.5)
fig.text(0.5, 0.005,
         'Prerna Tank | M.Tech(CS) 2410512 | DAVV | Guide: Dr. Shraddha Masih | 2026-04-05',
         ha='center', fontsize=7.5, color='#666688')

plt.savefig('D:/Prerna_project/project/project/thesis_results.png', dpi=150, bbox_inches='tight', facecolor=DARK_BG)
print('Chart saved: thesis_results.png')
