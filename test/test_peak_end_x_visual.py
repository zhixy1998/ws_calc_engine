"""
peak_end_x 可视化测试脚本

用法:
    /Users/drq/Documents/persee/venv_dir/calc_venv/bin/python test/test_peak_end_x_visual.py

生成图片到 debug_logs/plots/ 目录。
"""
import numpy as np
from scipy.signal import find_peaks, argrelmin
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
import os


def calc_peak_end_x(x, y_smooth, peaks, local_minima):
    """
    计算每个峰的结束 x 坐标（与 get_peak.py 中逻辑完全一致）
    标准：基线 = max(左侧谷高度, 右侧谷高度)，峰右侧首次回落至基线即为结束点，线性插值。
    """
    peak_end_x_list = []
    for p in peaks:
        left_valleys = local_minima[local_minima < p]
        left_h = float(y_smooth[left_valleys[-1]]) if len(left_valleys) > 0 else float(y_smooth[0])
        right_valleys = local_minima[local_minima > p]
        right_h = float(y_smooth[right_valleys[0]]) if len(right_valleys) > 0 else left_h
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
            peak_end_x_list.append(float(x[-1]))  # fallback: 最后一点
    return peak_end_x_list


def plot_case(ax, x, y, peaks, peak_end_x, local_minima, title, case_id):
    """绘制单个测试用例"""
    ax.plot(x, y, 'o-', color='steelblue', linewidth=1.2, markersize=5, label='原始数据', zorder=1)

    # 标出所有谷
    ax.scatter(x[local_minima], y[local_minima], marker='v', color='green',
               s=80, zorder=4, label='谷 (局部极小值)')

    # 标出峰顶
    ax.scatter(x[peaks], y[peaks], marker='^', color='red',
               s=120, zorder=5, label='峰顶 (peak)')

    # 标出 peak_end_x
    # peak_end_x 可能是插值出的，需要找到对应的 y
    from scipy.interpolate import interp1d
    interp = interp1d(x, y, kind='linear', fill_value='extrapolate')
    end_y_vals = interp(peak_end_x)

    for i, (ex, ey) in enumerate(zip(peak_end_x, end_y_vals)):
        ax.scatter(ex, ey, marker='s', color='darkorange',
                   s=120, zorder=6, edgecolors='black', linewidths=1.5)
        ax.annotate(f'peak_end_x\n({ex:.2f}, {ey:.2f})',
                    (ex, ey), textcoords="offset points", xytext=(10, -20),
                    fontsize=8, color='darkorange', weight='bold',
                    arrowprops=dict(arrowstyle='->', color='darkorange', lw=1.2))

    # 画基线（max(左谷, 右谷)）
    for pi, p in enumerate(peaks):
        left_valleys = local_minima[local_minima < p]
        right_valleys = local_minima[local_minima > p]
        left_h = float(y[left_valleys[-1]]) if len(left_valleys) > 0 else float(y[0])
        right_h = float(y[right_valleys[0]]) if len(right_valleys) > 0 else left_h
        baseline_y = max(left_h, right_h)
        lv_x = x[left_valleys[-1]] if len(left_valleys) > 0 else x[0]
        ex = peak_end_x[pi] if pi < len(peak_end_x) else x[-1]
        ax.hlines(baseline_y, lv_x, ex, colors='purple', linestyles='--',
                  linewidth=1.2, alpha=0.7)
        ax.annotate(f'基线 y={baseline_y:.2f}\n(max(左{left_h:.1f},右{right_h:.1f}))',
                    (lv_x, baseline_y), textcoords="offset points",
                    xytext=(0, -18), fontsize=6.5, color='purple')

    # 标注所有数据点
    for i in range(len(x)):
        ax.annotate(f'({x[i]},{y[i]})', (x[i], y[i]),
                    textcoords="offset points", xytext=(3, 6),
                    fontsize=6, color='gray', alpha=0.7)

    ax.set_title(title, fontsize=12, weight='bold')
    ax.set_xlabel('波长 / nm (x)')
    ax.set_ylabel('吸光度 (y)')
    ax.legend(loc='upper left', fontsize=7)
    ax.grid(True, alpha=0.3)


# ============================================================
# 测试用例定义
# ============================================================

# --- 用例1：标准单峰，无基线偏移 ---
# 基线 ~10，峰高 ~18，回落到 ~10
x1 = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
y1 = np.array([10, 11, 9, 10, 12, 18, 15, 12, 10, 9, 11, 10, 9, 10, 11], dtype=float)

# --- 用例2：基线偏移 ---
# 基线 ~10，峰高 ~15，回落后稳定在 ~12（不回到 10）
x2 = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])
y2 = np.array([10, 11, 9, 10, 11, 15, 14, 13, 12, 13, 12, 11, 12, 13, 12], dtype=float)

# --- 用例3：双峰，第二个峰基线偏移 ---
x3 = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19])
y3 = np.array([10, 11, 10, 12, 16, 13, 11, 10, 11, 12, 15, 14, 13, 14, 13, 12, 13, 12, 13, 12], dtype=float)

# --- 用例4：峰在右边界，数据截断 ---
x4 = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
y4 = np.array([10, 11, 10, 12, 15, 18, 16, 13, 11, 10], dtype=float)

# --- 用例5：更明显的基线偏移（10→15→12波动）---
x5 = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19])
y5 = np.array([10, 11, 9, 10, 11, 10, 15, 13, 12, 11, 12, 13, 12, 11, 12, 13, 12, 11, 12, 13], dtype=float)

cases = [
    (x1, y1, 2, None,   "用例1：标准单峰，基线10→峰18→回10"),
    (x2, y2, 2, None,   "用例2：基线偏移（10→15→12，不回10）"),
    (x3, y3, 2, None,   "用例3：双峰，含基线偏移"),
    (x4, y4, 2, None,   "用例4：峰在边界"),
    (x5, y5, 3, None,   "用例5：明显基线偏移 10→15→12波动"),
]


# ============================================================
# 运行计算 + 绘图
# ============================================================
def run_and_plot():
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'debug_logs', 'plots')
    os.makedirs(output_dir, exist_ok=True)

    n = len(cases)
    fig, axes = plt.subplots(n, 1, figsize=(14, 5.5 * n))
    if n == 1:
        axes = [axes]

    for idx, (ax, (x, y, dist, height, title)) in enumerate(zip(axes, cases)):
        y_smooth = y.copy()
        global_range = np.max(y_smooth) - np.min(y_smooth)
        prominence_threshold = global_range * height if height is not None else None
        peaks, properties = find_peaks(y_smooth, distance=dist, prominence=prominence_threshold)
        local_minima = argrelmin(y_smooth, order=1)[0]

        peak_end_x = calc_peak_end_x(x, y_smooth, peaks, local_minima)

        print(f"\n{'='*60}")
        print(f"【{title}】")
        print(f"  peaks (x)      : {x[peaks].tolist()}")
        print(f"  peaks (y)      : {y_smooth[peaks].tolist()}")
        print(f"  local_minima   : {local_minima.tolist()} -> x={x[local_minima].tolist()}")
        print(f"  peak_end_x     : {[f'{v:.3f}' for v in peak_end_x]}")
        for i, p in enumerate(peaks):
            lv = local_minima[local_minima < p]
            bl = float(y_smooth[lv[-1]]) if len(lv) > 0 else float(y_smooth[0])
            print(f"    峰#{i} x={x[p]:.1f} y={y_smooth[p]:.1f}  基线y={bl:.1f}  结束x={peak_end_x[i]:.3f}")

        plot_case(ax, x, y_smooth, peaks, peak_end_x, local_minima, title, idx)

    plt.tight_layout()
    out_path = os.path.join(output_dir, 'peak_end_x_test.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    print(f"\n图片已保存: {out_path}")
    plt.close(fig)


if __name__ == '__main__':
    run_and_plot()
