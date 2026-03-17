from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pytest

from utils.utils_detect_step_skipes import SpikeCorrectionCache, process_targeted_spike_removal


matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

IMG_DIR = Path(__file__).resolve().parents[1] / 'utils' / 'img'
BATCH_SIZE = 10
TOTAL_POINTS = 220
START_X = 620.0
WAVELENGTH_END = START_X - TOTAL_POINTS + 1


SCENARIOS = {
    'single_up_spike': {
        'target_points': [560],
        'mutations': {
            560: 210.0,
            559: 0.0,
            558: 0.0,
            557: 0.0,
        },
        'expect_changed': [560],
        'expect_unchanged': [559, 558, 557],
        'title': '单个向上倒刺',
        'file_label': '单个向上倒刺',
    },
    'continuous_double_spike_three_points': {
        'target_points': [560],
        'mutations': {
            560: 210.0,
            559: 110.0,
            558: 190.0,
            557: 0.0,
        },
        'expect_changed': [560, 559, 558],
        'expect_unchanged': [557],
        'title': '连续双刺三点形态',
        'file_label': '连续双刺三点形态',
    },
    'continuous_double_spike_four_points': {
        'target_points': [560],
        'mutations': {
            560: 210.0,
            559: 120.0,
            558: 105.0,
            557: 200.0,
            556: 0.0,
        },
        'expect_changed': [560, 559, 558, 557],
        'expect_unchanged': [556],
        'title': '连续双刺四点形态',
        'file_label': '连续双刺四点形态',
    },
    'single_down_spike': {
        'target_points': [560],
        'mutations': {
            560: -210.0,
            559: 0.0,
            558: 0.0,
            557: 0.0,
        },
        'expect_changed': [560],
        'expect_unchanged': [559, 558, 557],
        'title': '单个向下倒刺',
        'file_label': '单个向下倒刺',
    },
    'discontinuous_double_spike': {
        'target_points': [560],
        'mutations': {
            560: 210.0,
            559: 8.0,
            558: 200.0,
            557: 0.0,
        },
        'expect_changed': [560, 559, 558],
        'expect_unchanged': [557],
        'title': '不连续双刺',
        'file_label': '不连续双刺',
    },
    'cross_batch_first_point_spike': {
        'target_points': [550],
        'mutations': {
            550: 215.0,
            549: 0.0,
            548: 0.0,
            547: 0.0,
        },
        'expect_changed': [550],
        'expect_unchanged': [549, 548, 547],
        'title': '跨批次首点单刺',
        'file_label': '跨批次首点单刺',
    },
    'cross_batch_first_point_continuous_double_spike': {
        'target_points': [550],
        'mutations': {
            550: 215.0,
            549: 120.0,
            548: 205.0,
            547: 0.0,
        },
        'expect_changed': [550, 549, 548],
        'expect_unchanged': [547],
        'title': '跨批次首点连续双刺',
        'file_label': '跨批次首点连续双刺',
    },
}


def _build_base_series():
    x_data = [START_X - idx for idx in range(TOTAL_POINTS)]
    y_data = []
    for idx in range(TOTAL_POINTS):
        base_value = 1000.0 - idx * 0.5
        ripple = [0.0, 1.5, -1.2, 2.1, -1.8, 1.0][idx % 6]
        y_data.append(round(base_value + ripple, 4))
    return x_data, y_data


def _build_scenario_data(scenario_name):
    x_data, y_data = _build_base_series()
    scenario = SCENARIOS[scenario_name]
    x_index_map = {int(x_value): idx for idx, x_value in enumerate(x_data)}

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
        result = process_targeted_spike_removal(
            x_data=batch_x,
            y_data=batch_y,
            spike_points=batch_targets,
            wavelength_end=WAVELENGTH_END,
            cache=cache,
        )
        assert result['code'] == 200
        smoothed_data.extend(result['smoothed_data'])

    assert len(smoothed_data) == len(y_data)
    return smoothed_data


def _save_curve_image(x_data, y_data, file_name, title):
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(16, 6), dpi=160)
    ax.plot(x_data, y_data, color='tab:blue', linewidth=1.2)
    ax.set_title(title)
    ax.set_xlabel('波长 x')
    ax.set_ylabel('吸光度 y')
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.invert_xaxis()
    fig.tight_layout()
    fig.savefig(IMG_DIR / file_name)
    plt.close(fig)


def _run_case_and_assert(scenario_name):
    x_data, y_data, expected_original = _build_scenario_data(scenario_name)
    smoothed_data = _run_batched_removal(
        x_data=x_data,
        y_data=y_data,
        target_points=SCENARIOS[scenario_name]['target_points'],
    )

    file_label = SCENARIOS[scenario_name]['file_label']
    before_file = f"{file_label}_处理前.png"
    after_file = f"{file_label}_处理后.png"
    _save_curve_image(x_data, y_data, before_file, f"{SCENARIOS[scenario_name]['title']} 处理前")
    _save_curve_image(x_data, smoothed_data, after_file, f"{SCENARIOS[scenario_name]['title']} 处理后")

    x_index_map = {int(x_value): idx for idx, x_value in enumerate(x_data)}
    for x_value in SCENARIOS[scenario_name]['expect_changed']:
        idx = x_index_map[x_value]
        original_y = y_data[idx]
        baseline_y = expected_original[x_value]
        smoothed_y = smoothed_data[idx]
        if scenario_name in {'single_up_spike', 'single_down_spike', 'cross_batch_first_point_spike'}:
            assert abs(smoothed_y - baseline_y) < abs(original_y - baseline_y)
        else:
            assert abs(smoothed_y - baseline_y) < abs(original_y - baseline_y) * 0.95 or abs(smoothed_y - baseline_y) < 20

    for x_value in SCENARIOS[scenario_name]['expect_unchanged']:
        idx = x_index_map[x_value]
        assert smoothed_data[idx] == pytest.approx(y_data[idx])

    if scenario_name == 'continuous_double_spike_three_points':
        segment = [smoothed_data[x_index_map[x_value]] for x_value in [560, 559, 558]]
        assert max(segment) - min(segment) < 1e-6
        assert min(segment) > smoothed_data[x_index_map[557]]

    if scenario_name == 'continuous_double_spike_four_points':
        segment = [smoothed_data[x_index_map[x_value]] for x_value in [560, 559, 558, 557]]
        assert max(segment) - min(segment) < 1e-6
        assert min(segment) > smoothed_data[x_index_map[556]]

    if scenario_name == 'discontinuous_double_spike':
        segment = [
            smoothed_data[x_index_map[560]],
            smoothed_data[x_index_map[559]],
            smoothed_data[x_index_map[558]],
        ]
        assert max(segment) - min(segment) < 10
        assert min(segment) > smoothed_data[x_index_map[557]]

    if scenario_name == 'cross_batch_first_point_continuous_double_spike':
        segment = [smoothed_data[x_index_map[x_value]] for x_value in [550, 549, 548]]
        assert max(segment) - min(segment) < 1e-6
        assert min(segment) > smoothed_data[x_index_map[547]]

    return smoothed_data


@pytest.mark.parametrize(
    'scenario_name',
    [
        'single_up_spike',
        'continuous_double_spike_three_points',
        'continuous_double_spike_four_points',
        'single_down_spike',
        'discontinuous_double_spike',
        'cross_batch_first_point_spike',
        'cross_batch_first_point_continuous_double_spike',
    ],
)
def test_process_targeted_spike_removal_scenarios(scenario_name):
    _run_case_and_assert(scenario_name)
