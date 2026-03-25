from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pytest
import numpy as np

from utils.utils_detect_step_skipes import SpikeCorrectionCache, process_targeted_spike_removal_v2

matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

IMG_DIR = Path(__file__).resolve().parents[1] / 'utils' / 'img'
BATCH_SIZE = 10
TOTAL_POINTS = 220
START_X = 620.0
WAVELENGTH_END = START_X - TOTAL_POINTS + 1

# 数据说明：
# y值的基础起伏波动（Ripple）极差在 +/- 2左右。平均差分大约在 1.5 左右。
# k=3时，阈值大约为 4.5。因此跳变大于 5 且方向反转的点即可被判定为真正的刺。
# 这里统一使用 30.0 以上的绝对跳变构造“明显正/负刺”。
# 使用 2.0 的绝对跳变构造“轻微扰动（非刺）”。

SCENARIOS = {
    'single_valid_spike_at_center': {
        'target_points': [560.0],
        'mutations': {
            560.0: 50.0,    # 明显的正刺，位于指定中心波长
        },
        'expect_changed': [560.0],
        'expect_unchanged': [561.0, 559.0],
        'title': '单刺且在目标中心波长',
        'file_label': '单刺且在目标中心波长',
    },
    'valid_spike_off_center_but_in_radius': {
        'target_points': [560.0],
        'mutations': {
            557.0: -60.0,   # 明显的负刺，不在中心波长560，但在[555, 565]范围内
        },
        'expect_changed': [557.0],
        'expect_unchanged': [560.0, 558.0, 556.0],
        'title': '范围内偏离中心的有效刺',
        'file_label': '范围内偏离中心的有效刺',
    },
    'spike_outside_radius_is_ignored': {
        'target_points': [560.0], # 搜索范围[555, 565]
        'mutations': {
            550.0: 50.0,   # 正刺，但在搜索范围外，应被忽略
        },
        'expect_changed': [],
        'expect_unchanged': [550.0, 560.0], # 550被保留原样
        'title': '范围外的刺被忽略',
        'file_label': '范围外的刺被忽略',
    },
    'outlier_in_radius_not_a_spike': {
        'target_points': [560.0],
        'mutations': {
            560.0: 2.0,    # 波动太小（<5），达不到 k=3 判定条件，不应被平滑
        },
        'expect_changed': [],
        'expect_unchanged': [560.0],
        'title': '范围内的非刺微小波动保留',
        'file_label': '范围内的非刺微小波动保留',
    },
    'valid_continuous_double_spike': {
        'target_points': [560.0],
        'mutations': {
            559.0: 45.0,
            558.0: 50.0,
        },
        'expect_changed': [559.0, 558.0],
        'expect_unchanged': [560.0, 557.0],
        'title': '范围内连续双刺',
        'file_label': '范围内连续双刺',
    },
    'cross_batch_spike_detection': {
        'target_points': [550.0], # 550正好在批次边界首点，需要跨批次尾部缓存的数据才能判别左右跳变
        'mutations': {
            550.0: 60.0,
        },
        'expect_changed': [550.0],
        'expect_unchanged': [551.0, 549.0],
        'title': '跨批次首点刺检测',
        'file_label': '跨批次首点刺检测',
    },
}

def _build_base_series():
    x_data = [START_X - idx for idx in range(TOTAL_POINTS)]
    y_data = []
    # 构造有一定规律波动的背景
    for idx in range(TOTAL_POINTS):
        base_value = 1000.0 - idx * 0.5
        ripple = [0.0, 1.5, -1.2, 2.1, -1.8, 1.0][idx % 6]
        y_data.append(round(base_value + ripple, 4))
    return x_data, y_data

def _build_scenario_data(scenario_name):
    x_data, y_data = _build_base_series()
    scenario = SCENARIOS[scenario_name]
    x_index_map = {float(x_value): idx for idx, x_value in enumerate(x_data)}

    expected_original = {x_value: y_data[x_index_map[x_value]] for x_value in scenario['mutations']}
    for x_value, delta in scenario['mutations'].items():
        y_data[x_index_map[x_value]] = round(y_data[x_index_map[x_value]] + delta, 4)

    return x_data, y_data, expected_original

def _run_batched_removal(x_data, y_data, target_points):
    cache = SpikeCorrectionCache()
    smoothed_data = []

    for start_idx in range(0, len(x_data), BATCH_SIZE):
        batch_x = x_data[start_idx:start_idx + BATCH_SIZE]
        batch_y = y_data[start_idx:start_idx + BATCH_SIZE]
        batch_targets = target_points if start_idx == 0 else []
        result = process_targeted_spike_removal_v2(
            x_data=batch_x,
            y_data=batch_y,
            spike_points=batch_targets,
            wavelength_end=WAVELENGTH_END,
            cache=cache,
            search_radius=5.0,
            spike_k=2.0,
        )
        assert result['code'] == 200
        smoothed_data.extend(result['smoothed_data'])

    assert len(smoothed_data) == len(y_data)
    return smoothed_data

def _run_case_and_assert(scenario_name):
    x_data, y_data, expected_original = _build_scenario_data(scenario_name)
    smoothed_data = _run_batched_removal(
        x_data=x_data,
        y_data=y_data,
        target_points=SCENARIOS[scenario_name]['target_points'],
    )

    x_index_map = {float(x_value): idx for idx, x_value in enumerate(x_data)}
    
    # 判断预期被改变的点，由于平滑应该使得值靠近基线（修复刺）
    for x_value in SCENARIOS[scenario_name]['expect_changed']:
        idx = x_index_map[x_value]
        original_y = y_data[idx]
        baseline_y = expected_original[x_value]
        smoothed_y = smoothed_data[idx]
        
        # 处理后的点相对于突变点的变化，必须显著趋近于原始基线
        assert abs(smoothed_y - baseline_y) < abs(original_y - baseline_y) * 0.5
        
    return smoothed_data

@pytest.mark.parametrize(
    'scenario_name',
    list(SCENARIOS.keys())
)
def test_process_targeted_spike_removal_v2_scenarios(scenario_name):
    _run_case_and_assert(scenario_name)
