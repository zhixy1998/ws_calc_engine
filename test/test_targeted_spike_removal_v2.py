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
    'valid_opposite_double_spike_at_batch_tail': {
        'target_points': [611.0],
        'mutations': {
            612.0: 45.0,
            611.0: -55.0,
        },
        'expect_changed': [612.0, 611.0],
        'expect_unchanged': [613.0],
        'title': '批次尾点一上一下双刺',
        'file_label': '批次尾点一上一下双刺',
    },
    'valid_same_direction_double_spike_up': {
        'target_points': [560.0],
        'mutations': {
            560.0: 45.0,
            559.0: 40.0,
        },
        'expect_changed': [560.0, 559.0],
        'expect_unchanged': [561.0, 558.0],
        'title': '范围内同向向上双刺',
        'file_label': '范围内同向向上双刺',
    },
    'valid_same_direction_double_spike_down': {
        'target_points': [560.0],
        'mutations': {
            560.0: -45.0,
            559.0: -40.0,
        },
        'expect_changed': [560.0, 559.0],
        'expect_unchanged': [561.0, 558.0],
        'title': '范围内同向向下双刺',
        'file_label': '范围内同向向下双刺',
    },
    'valid_spike_at_batch_tail': {
        'target_points': [611.0],
        'mutations': {
            611.0: -60.0,
        },
        'expect_changed': [611.0],
        'expect_unchanged': [612.0],
        'title': '批次尾点有效刺',
        'file_label': '批次尾点有效刺',
    },
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


@pytest.mark.parametrize(
    'scenario',
    [
        {
            'name': '389_and_387_separated_spikes',
            'target': 389.0,
            'prev_x': [400.0, 399.0, 398.0, 397.0, 396.0, 395.0, 394.0, 393.0, 392.0, 391.0],
            'prev_y': [-0.000152020726, -0.000157429766, -0.000249439729, -0.000158677644, -0.000174423260, -0.000174079027, -0.000190594084, -0.000192691845, -0.000195487624, -0.000156280776],
            'cur_x': [390.0, 389.0, 388.0, 387.0, 386.0, 385.0, 384.0, 383.0, 382.0, 381.0],
            'cur_y': [-0.000152440115, -0.019574291460, -0.000185141005, 0.000219367658, -0.000200112871, -0.000220049110, -0.000214775368, -0.000208233498, -0.000186000769, -0.000221100311],
            'expect_changed': [389.0, 387.0],
        },
        {
            'name': '760_and_758_separated_spikes',
            'target': 760.0,
            'prev_x': [770.0, 769.0, 768.0, 767.0, 766.0, 765.0, 764.0, 763.0, 762.0, 761.0],
            'prev_y': [-0.000559255745, -0.000552732387, -0.000557095385, -0.000514311569, -0.000518804929, -0.000547184841, -0.000534496270, -0.000554885045, -0.000566931206, -0.000514125121],
            'cur_x': [760.0, 759.0, 758.0, 757.0, 756.0, 755.0, 754.0, 753.0, 752.0, 751.0],
            'cur_y': [-0.002004632824, -0.000498303202, -0.000771174547, -0.000449440381, -0.000500589179, -0.000463280884, -0.000466176664, -0.000419772115, -0.000461954346, -0.000436618631],
            'expect_changed': [760.0, 758.0],
        },
    ],
    ids=lambda scenario: scenario['name'],
)
def test_process_targeted_spike_removal_v2_separated_spikes(scenario):
    cache = SpikeCorrectionCache()

    first_result = process_targeted_spike_removal_v2(
        x_data=scenario['prev_x'],
        y_data=scenario['prev_y'],
        spike_points=[scenario['target']],
        wavelength_end=WAVELENGTH_END,
        cache=cache,
        search_radius=5.0,
        spike_k=2.0,
    )
    assert first_result['code'] == 200

    second_result = process_targeted_spike_removal_v2(
        x_data=scenario['cur_x'],
        y_data=scenario['cur_y'],
        spike_points=[scenario['target']],
        wavelength_end=WAVELENGTH_END,
        cache=cache,
        search_radius=5.0,
        spike_k=2.0,
    )
    assert second_result['code'] == 200

    index_map = {float(x_value): idx for idx, x_value in enumerate(scenario['cur_x'])}
    for x_value in scenario['expect_changed']:
        idx = index_map[x_value]
        assert second_result['smoothed_data'][idx] != pytest.approx(scenario['cur_y'][idx])


def test_process_targeted_spike_removal_v2_rechecks_failed_candidates_after_confirming_new_spike():
    cache = SpikeCorrectionCache()

    prev_x = [360.0, 359.0, 358.0, 357.0, 356.0, 355.0, 354.0, 353.0, 352.0, 351.0]
    prev_y = [
        -0.000005527762,
        -0.000081680637,
        -0.000070046784,
        -0.000034445481,
        -0.000039286235,
        0.000004858933,
        -0.000026554157,
        0.000003480230,
        -0.000036569699,
        0.000002858673,
    ]
    cur_x = [350.0, 349.0, 348.0, 347.0, 346.0, 345.0, 344.0, 343.0, 342.0, 341.0]
    cur_y = [
        -0.000309921810,
        -0.000042986582,
        0.000648324012,
        -0.000019899048,
        0.000028036809,
        -0.000074587350,
        -0.000058448857,
        -0.000068076652,
        -0.000028828312,
        -0.000069791451,
    ]

    first_result = process_targeted_spike_removal_v2(
        x_data=prev_x,
        y_data=prev_y,
        spike_points=[350.0],
        wavelength_end=341.0,
        cache=cache,
        search_radius=5.0,
        spike_k=2.0,
    )
    assert first_result['code'] == 200

    second_result = process_targeted_spike_removal_v2(
        x_data=cur_x,
        y_data=cur_y,
        spike_points=[350.0],
        wavelength_end=341.0,
        cache=cache,
        search_radius=5.0,
        spike_k=2.0,
    )
    assert second_result['code'] == 200

    index_map = {float(x_value): idx for idx, x_value in enumerate(cur_x)}
    assert second_result['smoothed_data'][index_map[348.0]] != pytest.approx(cur_y[index_map[348.0]])
    assert second_result['smoothed_data'][index_map[350.0]] != pytest.approx(cur_y[index_map[350.0]])
