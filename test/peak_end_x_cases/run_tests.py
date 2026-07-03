"""
peak_end_x 测试脚本

读取 test_cases.json，对每个用例运行寻峰 + peak_end_x 计算，
生成标注图保存到同目录下。

用法:
    cd /Users/drq/Documents/persee/ws_x_calc_engine
    /Users/drq/Documents/persee/venv_dir/calc_venv/bin/python test/peak_end_x_cases/run_tests.py
"""
import json
import os
import numpy as np
from scipy.signal import find_peaks, argrelmin
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ---------- 算法（与 get_peak.py 完全一致） ----------

def find_peaks_and_end_x(x, y, distance, height):
    y_smooth = y.copy()
    global_range = np.max(y_smooth) - np.min(y_smooth)
    prominence_threshold = global_range * height if height is not None else None
    peaks, _ = find_peaks(y_smooth, distance=distance, prominence=prominence_threshold)
    local_minima = argrelmin(y_smooth, order=1)[0]

    peak_end_x_list = []
    for p in peaks:
        lv = local_minima[local_minima < p]
        rv = local_minima[local_minima > p]
        left_h  = float(y_smooth[lv[-1]]) if len(lv) > 0 else float(y_smooth[0])
        right_h = float(y_smooth[rv[0]])  if len(rv) > 0 else left_h
        baseline_y = max(left_h, right_h)

        found = False
        for i in range(int(p) + 1, len(x)):
            if float(y_smooth[i]) <= baseline_y:
                if i > int(p) + 1 and float(y_smooth[i - 1]) > baseline_y:
                    x1, x2 = float(x[i - 1]), float(x[i])
                    y1, y2 = float(y_smooth[i - 1]), float(y_smooth[i])
                    if y1 != y2:
                        end_x = x1 + (x2 - x1) * (baseline_y - y1) / (y2 - y1)
                    else:
                        end_x = x2
                else:
                    end_x = float(x[i])
                peak_end_x_list.append(end_x)
                found = True
                break
        if not found:
            peak_end_x_list.append(float(x[-1]))

    return peaks, local_minima, peak_end_x_list


# ---------- 绘图 ----------

def plot_case(x, y, peaks, local_minima, peak_end_x, title, out_path):
    fig, ax = plt.subplots(figsize=(14, 5))

    # 数据折线 + 散点
    ax.plot(x, y, 'o-', color='#4A90D9', lw=1.5, ms=7, zorder=1)

    # 标注每个点 (x,y)
    for xi, yi in zip(x, y):
        ax.annotate(f'({xi:.1f},{yi:.1f})', (xi, yi),
                    xytext=(0, 10), textcoords='offset points',
                    fontsize=7, ha='center', color='gray', alpha=0.8)

    # 谷（绿色倒三角）
    if len(local_minima) > 0:
        ax.scatter(x[local_minima], y[local_minima], marker='v', s=120,
                   color='#2ECC40', zorder=3, edgecolors='#1B7A24', linewidths=1.5,
                   label='valley')
        for vi in local_minima:
            ax.annotate('valley', (x[vi], y[vi]), xytext=(0, -15),
                        textcoords='offset points', fontsize=8, ha='center',
                        color='#1B7A24', weight='bold')

    # 峰顶（红色三角）
    ax.scatter(x[peaks], y[peaks], marker='^', s=160,
               color='#E74C3C', zorder=4, edgecolors='#922B21', linewidths=1.5,
               label='peak')
    for pi in peaks:
        ax.annotate(f'peak\n({x[pi]:.1f},{y[pi]:.1f})', (x[pi], y[pi]),
                    xytext=(12, 8), textcoords='offset points',
                    fontsize=9, ha='left', color='#922B21', weight='bold')

    # peak_end_x（橙色方块）
    for pe in peak_end_x:
        pe = float(pe)
        # 线性插值取对应的 y
        if pe in x:
            ey = float(y[list(x).index(pe)])
        else:
            idx = np.searchsorted(x, pe)
            if idx == 0:
                ey = float(y[0])
            elif idx >= len(x):
                ey = float(y[-1])
            else:
                x1, x2 = float(x[idx - 1]), float(x[idx])
                y1, y2 = float(y[idx - 1]), float(y[idx])
                ey = y1 + (y2 - y1) * (pe - x1) / (x2 - x1) if x2 != x1 else y1

        ax.scatter(pe, ey, marker='s', s=160,
                   color='#F39C12', zorder=5, edgecolors='black', linewidths=2,
                   label='peak_end_x')
        ax.annotate(f'peak_end_x\n({pe:.3f},{ey:.3f})', (pe, ey),
                    xytext=(15, -20), textcoords='offset points',
                    fontsize=9, ha='left', color='#E67E22', weight='bold',
                    arrowprops=dict(arrowstyle='->', color='#E67E22', lw=1.5))

    # 基线虚线（对每个峰画一条从左侧谷到 peak_end_x 的水平线）
    for pi, pe in zip(peaks, peak_end_x):
        lv = local_minima[local_minima < pi]
        rv = local_minima[local_minima > pi]
        left_h  = float(y[lv[-1]]) if len(lv) > 0 else float(y[0])
        right_h = float(y[rv[0]])  if len(rv) > 0 else left_h
        baseline_y = max(left_h, right_h)
        lv_x = float(x[lv[-1]]) if len(lv) > 0 else float(x[0])
        ax.hlines(baseline_y, lv_x, float(pe), colors='#8E44AD', linestyles='--',
                  lw=1.5, alpha=0.7, label='_baseline')
        ax.annotate(f'baseline={baseline_y:.1f}\nmax(L={left_h:.1f},R={right_h:.1f})',
                    (lv_x, baseline_y), xytext=(0, -22),
                    textcoords='offset points', fontsize=7, ha='left',
                    color='#6C3483', weight='bold')

    ax.set_title(title, fontsize=13, weight='bold')
    ax.set_xlabel('x (wavelength)')
    ax.set_ylabel('y (absorbance)')
    ax.grid(True, alpha=0.25)

    # 去重 legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper left', fontsize=8)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  -> {out_path}')


# ---------- main ----------

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'test_cases.json')
    with open(json_path, 'r') as f:
        cases = json.load(f)

    for case in cases:
        name = case['name']
        x = np.array(case['x'], dtype=float)
        y = np.array(case['y'], dtype=float)
        distance = case.get('distance', 2)
        height = case.get('height', None)

        peaks, local_minima, peak_end_x = find_peaks_and_end_x(x, y, distance, height)

        print(f'\n{"="*50}')
        print(f'[{name}]')
        print(f'  peaks (x)     : {x[peaks].tolist()}')
        print(f'  peaks (y)     : {y[peaks].tolist()}')
        print(f'  valleys       : {[(x[i],y[i]) for i in local_minima]}')
        print(f'  peak_end_x    : {[f"{v:.3f}" for v in peak_end_x]}')

        safe_name = name.replace(' ', '_').replace('→', '_to_')
        out_path = os.path.join(script_dir, f'{safe_name}.png')
        plot_case(x, y, peaks, local_minima, peak_end_x, name, out_path)

    print(f'\nDone. All plots saved to: {script_dir}')


if __name__ == '__main__':
    main()
