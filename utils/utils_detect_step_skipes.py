import io
import base64
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
import matplotlib.pyplot as plt
from exceptions.error import ErrorCode
from exceptions.command_exception import APIException
from scipy.signal import medfilt
from scipy.ndimage import gaussian_filter


# ==================== 台阶校正缓存类 ====================
class StepCorrectionCache:
    """
    用于跨批次处理台阶的缓存类（单例模式，无需session_id）。
    保存上一批次的数据和累计偏移量。
    
    说明：
    - 数据从高波长向低波长传递，每次10个点
    - 换灯波长是台阶点（换灯后第一个点）
    - 需要缓存上一批次的尾部数据，以防换灯点在边界
    """
    def __init__(self):
        self._data: Dict[str, Any] = {
            'last_x': None,            # 上一批次最后一个 x 值
            'last_y': None,            # 上一批次最后一个 y 值
            'last_few_y': [],          # 上一批次最后几个 y 值（用于预测）
            'accumulated_offset': 0.0, # 累计偏移量（可多次跳变累加）
            'pending_breaks': [],      # 尚未处理的跳变前点列表（降序）
        }
    
    def update(self, x_data: List[float], y_data: List[float]):
        """更新缓存，保存当前批次的尾部数据"""
        self._data['last_x'] = x_data[-1] if x_data else None
        self._data['last_y'] = y_data[-1] if y_data else None
        # 保存最后3个点用于预测
        self._data['last_few_y'] = list(y_data[-3:]) if len(y_data) >= 3 else list(y_data)
    
    def set_offset(self, offset: float):
        """累加偏移量（支持多次跳变）"""
        self._data['accumulated_offset'] += offset
    
    def get_offset(self) -> float:
        """获取累计偏移量"""
        return self._data['accumulated_offset']
    
    def get_last_few_y(self) -> List[float]:
        """获取上一批次最后几个 y 值"""
        return self._data['last_few_y']
    
    def get_last_y(self) -> Optional[float]:
        """获取上一批次最后一个 y 值"""
        return self._data['last_y']
    
    def clear(self):
        """清理缓存（测量结束时调用）"""
        self._data = {
            'last_x': None,
            'last_y': None,
            'last_few_y': [],
            'accumulated_offset': 0.0,
            'pending_breaks': [],
        }


class SpikeCorrectionCache:
    """
    用于跨批次处理指定倒刺点的缓存类。

    说明：
    - 与台阶处理保持同样的跨批次模式
    - 缓存上一批次尾部的已修正数据，支持下一批次首点就是倒刺
    - pending_spikes 保存尚未进入当前批次处理范围的目标 x 坐标
    """
    def __init__(self):
        self._data: Dict[str, Any] = {
            'tail_x': [],
            'tail_y': [],
            'pending_spikes': [],
        }

    def update(self, x_data: List[float], y_data: List[float], tail_size: int = 6):
        self._data['tail_x'] = list(x_data[-tail_size:]) if len(x_data) >= tail_size else list(x_data)
        self._data['tail_y'] = list(y_data[-tail_size:]) if len(y_data) >= tail_size else list(y_data)

    def get_tail(self) -> Dict[str, List[float]]:
        return {
            'x': list(self._data['tail_x']),
            'y': list(self._data['tail_y']),
        }

    def clear(self):
        self._data = {
            'tail_x': [],
            'tail_y': [],
            'pending_spikes': [],
        }


# ==================== 台阶处理函数（新逻辑） ====================
def process_step_removal(
    x_data: List[float],
    y_data: List[float],
    break_points: List[float],
    wavelength_end: Optional[float],
    cache: StepCorrectionCache
) -> Dict[str, Any]:
    """
    台阶消除主函数（基于已知换灯波长）
    
    参数:
        x_data: 当前批次的波长数据（从高到低）
        y_data: 当前批次的吸光度数据
        break_points: 跳变前的点列表（含换灯和换滤光片），按从高波长到低波长
        wavelength_end: 本次测量的结束波长（最低波长），用于判断是否最后一批
        cache: 缓存对象
    
    返回:
        处理后的结果
    
    逻辑说明:
        1. 数据从高波长向低波长传递，每次10个点
        2. break_points 是跳变前的点（换灯/换滤光片），实际跳变发生在该点之后的下一个波长
        3. 如果跳变前点在当前批次的最后一个位置，需要等待下一批次处理
        4. 计算偏移后，从跳变后的第一个点开始，后续所有点都减去偏移量（累计）
        5. 根据 wavelength_end 判断是否最后一批，最后一批时清理缓存
    """
    try:
        x = np.array([float(val) for val in x_data])
        y = np.array([float(val) for val in y_data])
    except ValueError:
        raise APIException(ErrorCode.X_Y_MUST_NUM)

    if len(x) != len(y):
        raise APIException(ErrorCode.X_Y_LENGTH_MISMATCH)
    
    # 先应用已有的累计偏移
    accumulated_offset = cache.get_offset()
    y_corrected = y - accumulated_offset
    
    # 判断是否是最后一批数据（当前批次包含结束波长）
    is_last_batch = False
    if wavelength_end is not None:
        # 当前批次的最小波长 <= 结束波长，说明是最后一批
        is_last_batch = min(x) <= wavelength_end
    
    # 跳变前点列表：合并缓存中的未处理点与当前传入的点
    pending_breaks = cache._data['pending_breaks']  # 内部使用
    all_breaks = sorted(set(pending_breaks + break_points), reverse=True)

    # 针对当前批次，处理所有已经跨过的跳变点
    for bp in list(all_breaks):
        # 跳变发生在 bp 与紧随其后的点之间，数据从高到低
        # 找到第一个 x < bp 的点作为跳变后的第一个点
        jump_idx = None
        for idx, xv in enumerate(x):
            if xv < bp:
                jump_idx = idx
                break

        if jump_idx is None:
            # 尚未到达该跳变点，保持为待处理
            continue

        # 计算偏移：预测 jump_idx 处的应有值
        if jump_idx == 0:
            # 需要用上一批次的末尾数据
            pre_y = cache.get_last_few_y()
        else:
            pre_y = y_corrected[:jump_idx].tolist()

        if len(pre_y) >= 2:
            predicted_y = predict_next_y_simple(pre_y)
        elif len(pre_y) == 1:
            predicted_y = pre_y[-1]
        else:
            # 无法预测，跳过此跳变点，留待下一批
            continue

        offset = y_corrected[jump_idx] - predicted_y
        accumulated_offset += offset
        # 应用新的累计偏移到 jump_idx 及之后
        y_corrected[jump_idx:] -= offset

        # 该跳变点已处理，从列表移除
        all_breaks.remove(bp)

    # 更新缓存的累计偏移和未处理跳变点
    cache._data['pending_breaks'] = all_breaks
    cache._data['accumulated_offset'] = accumulated_offset
    
    # 更新缓存（保存当前批次尾部数据，供下一批次使用）
    cache.update(x.tolist(), y_corrected.tolist())
    
    # 如果是最后一批，清理缓存
    if is_last_batch:
        cache.clear()
    
    return {
        'code': 200,
        'smoothed_data': y_corrected.tolist(),
        'message': 'success'
    }


def find_wavelength_index(x: np.ndarray, target_wavelength: float, tolerance: float = 0.01) -> Optional[int]:
    """
    在波长数组中查找目标波长的索引
    
    参数:
        x: 波长数组
        target_wavelength: 目标波长
        tolerance: 容差（用于浮点数比较）
    
    返回:
        索引，如果未找到返回 None
    """
    # 查找最接近的点
    diff = np.abs(x - target_wavelength)
    min_idx = np.argmin(diff)
    
    # 检查是否在容差范围内
    if diff[min_idx] <= tolerance:
        return int(min_idx)
    return None


def predict_next_y_simple(y_values: List[float]) -> float:
    """
    简单预测下一个 y 值（线性外推）
    
    使用最后两个点进行线性预测
    """
    if len(y_values) < 2:
        return y_values[-1] if y_values else 0.0
    
    # 线性外推：y_next = y[-1] + (y[-1] - y[-2])
    slope = y_values[-1] - y_values[-2]
    return y_values[-1] + slope


def process_targeted_spike_removal(
    x_data: List[float],
    y_data: List[float],
    spike_points: List[int],
    wavelength_end: Optional[float],
    cache: SpikeCorrectionCache
) -> Dict[str, Any]:
    """
    按指定 x 坐标批量消除倒刺。

    参数:
        x_data: 当前批次 x 数据
        y_data: 当前批次 y 数据
        spike_points: 倒刺的大致 x 坐标列表，传入的是 x 坐标不是下标
        wavelength_end: 本次测量的结束波长，用于判断是否最后一批
        cache: 倒刺缓存对象

    处理逻辑:
        1. 在目标点的左右两个波长范围内搜索，即 [target-2, target+2]
        2. 逻辑1：两倍阈值不是 y 值的两倍，而是前序正常区间波动的两倍
        3. 逻辑2：连续双刺支持 3 点形态和 4 点形态，并要求参与形态的每个点都超过两倍波动阈值
        4. 若连续形态里有任一点不满足两倍阈值，则不按连续双刺处理，而是视为单独刺
        5. 修复时只用倒刺之前的已知数据做外推平滑，不做简单平均
        6. 保留上一批次尾部点，支持下一批次第一个点就是倒刺
    """
    try:
        x = [float(val) for val in x_data]
        y = [float(val) for val in y_data]
    except ValueError:
        raise APIException(ErrorCode.X_Y_MUST_NUM)

    if len(x) != len(y):
        raise APIException(ErrorCode.X_Y_LENGTH_MISMATCH)

    tail = cache.get_tail()
    combined_x = tail['x'] + x
    combined_y = tail['y'] + y
    corrected_y = list(combined_y)
    prefix_len = len(tail['x'])

    is_last_batch = False
    if wavelength_end is not None and x:
        is_last_batch = min(x) <= wavelength_end

    pending_spikes = _unique_keep_order(cache._data['pending_spikes'] + list(spike_points or []))
    remaining_pending: List[int] = []
    baseline_anchor_idx = 0

    for target_x in pending_spikes:
        # 对每个目标 x，在当前批次和上一批次尾部拼接后的窗口里找刺。
        spike_indices, end_anchor_idx, need_more_data = _resolve_target_spike_segment(
            x_values=combined_x,
            original_y=combined_y,
            corrected_y=corrected_y,
            target_x=float(target_x),
            baseline_anchor_idx=baseline_anchor_idx,
            is_last_batch=is_last_batch,
        )
        if need_more_data:
            remaining_pending.append(target_x)
            continue

        if not spike_indices:
            if not _has_reached_target_window(combined_x, float(target_x)):
                remaining_pending.append(target_x)
            continue

        spike_indices = sorted(set(idx for idx in spike_indices if idx >= prefix_len))
        for segment_indices in _group_nearby_indices(spike_indices):
            # 同一小段里的刺一起修，避免两个刺之间保留一个点后又形成新的凸起/凹陷。
            segment_values = _smooth_spike_segment(combined_x, combined_y, corrected_y, segment_indices)
            for idx, value in zip(segment_indices, segment_values):
                corrected_y[idx] = value

        baseline_anchor_idx = min(end_anchor_idx, len(combined_x) - 1)

    current_y = corrected_y[prefix_len:]
    cache._data['pending_spikes'] = remaining_pending
    cache.update(x, current_y)

    if is_last_batch:
        cache.clear()
    # 清理浮点尾差，避免出现 990.0749999999953 这种展示值。
    current_y = [round(float(i), 10) for i in current_y]
    return {
        'code': 200,
        'smoothed_data': current_y,
        'message': 'success'
    }


def _unique_keep_order(values: List[Any]) -> List[Any]:
    result = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _group_nearby_indices(indices: List[int], max_gap: int = 2) -> List[List[int]]:
    # 相距很近的刺按一个连续小段处理，例如 [560, 558] 会扩成 [560, 559, 558]。
    if not indices:
        return []
    groups = [[indices[0]]]
    for idx in indices[1:]:
        if idx <= groups[-1][-1] + max_gap:
            groups[-1].append(idx)
        else:
            groups.append([idx])
    return [list(range(group[0], group[-1] + 1)) for group in groups]


def _has_reached_target_window(x_values: List[float], target_x: float) -> bool:
    if not x_values:
        return False
    return min(x_values) <= target_x + 2 and max(x_values) >= target_x - 2


def _resolve_target_spike_segment(
    x_values: List[float],
    original_y: List[float],
    corrected_y: List[float],
    target_x: float,
    baseline_anchor_idx: int,
    is_last_batch: bool,
) -> Tuple[List[int], int, bool]:
    """
    基于目标点附近窗口，解析单刺或连续双刺区间。

    返回:
        spike_indices: 需要修复的倒刺点索引列表
        end_anchor_idx: 当前倒刺结束后的正常锚点索引，供后续目标计算波动阈值
        need_more_data: 是否需要等下一批次补足判断数据
    """
    window_indices = [
        idx for idx, xv in enumerate(x_values)
        if target_x - 2 <= xv <= target_x + 2 and idx > 0
    ]

    if not window_indices:
        return [], baseline_anchor_idx, False

    ranked_indices = sorted(window_indices, key=lambda idx: (abs(x_values[idx] - target_x), idx))
    pending_due_to_boundary = False
    resolved_indices: List[int] = []
    consumed_indices = set()
    # working_corrected_y 用来在同一窗口内边修边判断，避免前一个刺影响后一个刺的判断。
    working_corrected_y = list(corrected_y)
    current_end_anchor_idx = baseline_anchor_idx

    for idx in ranked_indices:
        if idx in consumed_indices:
            continue
        if idx + 3 >= len(x_values) and not is_last_batch:
            pending_due_to_boundary = True
            continue

        threshold = _calculate_fluctuation_threshold(working_corrected_y, current_end_anchor_idx, idx)
        if threshold <= 0:
            continue

        # 先判断这个点是单刺，还是连续双刺的起点。
        spike_indices, end_anchor_idx = _detect_spike_pattern(
            x_values=x_values,
            original_y=original_y,
            corrected_y=working_corrected_y,
            spike_idx=idx,
            threshold=threshold,
            is_last_batch=is_last_batch,
        )
        if spike_indices:
            resolved_indices.extend(spike_indices)
            consumed_indices.update(spike_indices)
            current_end_anchor_idx = max(current_end_anchor_idx, end_anchor_idx)
            for spike_idx in spike_indices:
                # 这里只做临时更新，用于同一窗口内后续点的判定，不是最终输出值。
                working_corrected_y[spike_idx] = _predict_point_from_previous(x_values, working_corrected_y, spike_idx)

    if resolved_indices:
        return sorted(set(resolved_indices)), current_end_anchor_idx, False

    return [], baseline_anchor_idx, pending_due_to_boundary


def _detect_spike_pattern(
    x_values: List[float],
    original_y: List[float],
    corrected_y: List[float],
    spike_idx: int,
    threshold: float,
    is_last_batch: bool,
) -> Tuple[List[int], int]:
    if spike_idx >= len(x_values):
        return [], spike_idx

    max_pattern_len = min(4, len(x_values) - spike_idx)
    if max_pattern_len < 4 and not is_last_batch:
        return [], spike_idx

    predicted_values, residuals = _build_predicted_segment(
        x_values=x_values,
        original_y=original_y,
        corrected_y=corrected_y,
        start_idx=spike_idx,
        count=max_pattern_len,
    )
    if not residuals or abs(residuals[0]) <= threshold:
        return [], spike_idx

    residual_sign = 1 if residuals[0] > 0 else -1

    if max_pattern_len >= 4:
        # 四点连续双刺：都必须同方向偏离基线，并满足高低低高的形态。
        if _matches_same_direction_pattern(
            residuals=residuals[:4],
            threshold=threshold,
            expected_sign=residual_sign,
        ) and _matches_four_point_shape(original_y[spike_idx:spike_idx + 4]):
            return list(range(spike_idx, spike_idx + 4)), min(spike_idx + 4, len(x_values) - 1)

    if max_pattern_len >= 3:
        # 三点连续双刺：都必须同方向偏离基线，并满足高低高的形态。
        if _matches_same_direction_pattern(
            residuals=residuals[:3],
            threshold=threshold,
            expected_sign=residual_sign,
        ) and _matches_three_point_shape(original_y[spike_idx:spike_idx + 3]):
            return list(range(spike_idx, spike_idx + 3)), min(spike_idx + 3, len(x_values) - 1)

    # 既不是三点连续双刺，也不是四点连续双刺，就按单刺处理。
    return [spike_idx], min(spike_idx + 1, len(x_values) - 1)


def _build_predicted_segment(
    x_values: List[float],
    original_y: List[float],
    corrected_y: List[float],
    start_idx: int,
    count: int,
) -> Tuple[List[float], List[float]]:
    simulated_y = list(corrected_y)
    predicted_values: List[float] = []
    residuals: List[float] = []

    for idx in range(start_idx, min(start_idx + count, len(x_values))):
        predicted = _predict_point_from_previous(x_values, simulated_y, idx)
        predicted_values.append(predicted)
        residuals.append(original_y[idx] - predicted)
        simulated_y[idx] = predicted

    return predicted_values, residuals


def _matches_same_direction_pattern(residuals: List[float], threshold: float, expected_sign: int) -> bool:
    if not residuals:
        return False

    for residual in residuals:
        if abs(residual) <= threshold:
            return False
        sign = 1 if residual > 0 else -1
        if sign != expected_sign:
            return False
    return True


def _matches_three_point_shape(y_segment: List[float]) -> bool:
    if len(y_segment) < 3:
        return False
    first, second, third = y_segment[:3]
    all_positive = first > 0 and second > 0 and third > 0
    all_negative = first < 0 and second < 0 and third < 0
    if not (all_positive or all_negative):
        return False
    return first > second and third > second


def _matches_four_point_shape(y_segment: List[float]) -> bool:
    if len(y_segment) < 4:
        return False
    first, second, third, fourth = y_segment[:4]
    all_positive = first > 0 and second > 0 and third > 0 and fourth > 0
    all_negative = first < 0 and second < 0 and third < 0 and fourth < 0
    if not (all_positive or all_negative):
        return False
    return first > second and second >= third and fourth > third


def _calculate_fluctuation_threshold(y_values: List[float], baseline_anchor_idx: int, spike_idx: int) -> float:
    """
    两倍阈值定义为：前序正常区间相邻波动最大值的两倍。

    示例：
    - 若 spike_idx 对应 361，则起始点是它前一个点，阈值取起始点之前正常区间的波动
    - 若前一个倒刺结束点已知，则下一次阈值从该结束点开始累计正常波动
    """
    start_idx = max(0, baseline_anchor_idx)
    end_idx = max(start_idx, spike_idx - 1)
    baseline_segment = y_values[start_idx:end_idx]

    if len(baseline_segment) < 2:
        baseline_segment = y_values[:end_idx]
    if len(baseline_segment) < 2:
        return 1e-12

    # 这里的“阈值”来自前序正常区间的波动，不直接拿某个 y 值去比较。
    diffs = np.abs(np.diff(np.array(baseline_segment, dtype=float)))
    if len(diffs) == 0:
        return 1e-12

    max_fluctuation = float(np.max(diffs))
    median_fluctuation = float(np.median(diffs))
    # 先把正常波动放大一层，再乘 2，避免把普通小波纹误判成刺。
    base_fluctuation = max(max_fluctuation * 1.5, median_fluctuation * 3)
    return max(base_fluctuation * 2, 1e-12)


def _smooth_spike_segment(
    x_values: List[float],
    original_y_values: List[float],
    corrected_y_values: List[float],
    segment_indices: List[int]
) -> List[float]:
    if not segment_indices:
        return []
    if len(segment_indices) == 1:
        # 单刺仍然按前序点预测，尽量保持单点修复自然。
        idx = segment_indices[0]
        return [_predict_point_from_previous(x_values, corrected_y_values, idx)]

    start_idx = segment_indices[0]
    end_idx = segment_indices[-1]
    left_anchor_idx = start_idx - 1 if start_idx - 1 >= 0 else None
    right_anchor_idx = end_idx + 1 if end_idx + 1 < len(corrected_y_values) else None

    if left_anchor_idx is None and right_anchor_idx is None:
        return [_predict_point_from_previous(x_values, corrected_y_values, idx) for idx in segment_indices]

    # average_threshold 是双刺段最终要保留的“平均阈值高度”。
    average_threshold = _calculate_segment_average_threshold(corrected_y_values, segment_indices)
    reference_values = []
    if left_anchor_idx is not None:
        reference_values.append(corrected_y_values[left_anchor_idx])
    if right_anchor_idx is not None:
        reference_values.append(corrected_y_values[right_anchor_idx])

    # baseline_reference 是刺段两侧正常点的参考基线。
    baseline_reference = float(np.mean(reference_values)) if reference_values else float(corrected_y_values[start_idx])
    original_residuals = [original_y_values[idx] - baseline_reference for idx in segment_indices]
    residual_mean = float(np.mean(original_residuals))
    direction = 1.0 if residual_mean >= 0 else -1.0
    # 再加一个上限，避免所谓“平均阈值”反而比原始刺还高。
    residual_cap = float(np.quantile(np.abs(np.array(original_residuals, dtype=float)), 0.75)) * 0.85
    target_offset = min(average_threshold, residual_cap)
    target_offset = max(target_offset, 1e-12)

    # 多点刺整段统一成同一个目标高度，避免中间再出现一个凹点。
    target_value = baseline_reference + direction * target_offset
    smoothed_values = [target_value for _ in segment_indices]
    return [float(value) for value in smoothed_values]


def _calculate_segment_average_threshold(corrected_y_values: List[float], segment_indices: List[int]) -> float:
    if not segment_indices:
        return 1e-12

    start_idx = segment_indices[0]
    end_idx = segment_indices[-1]
    left_segment = corrected_y_values[max(0, start_idx - 6):start_idx]
    right_segment = corrected_y_values[end_idx + 1:min(len(corrected_y_values), end_idx + 7)]

    # 只拿刺段两侧正常点的波动来算平均阈值，不让刺本身把阈值抬高。
    diffs = []
    if len(left_segment) >= 2:
        diffs.extend(np.abs(np.diff(np.array(left_segment, dtype=float))).tolist())
    if len(right_segment) >= 2:
        diffs.extend(np.abs(np.diff(np.array(right_segment, dtype=float))).tolist())

    if not diffs:
        return 1e-12

    # 这里的 4.0 就是“平均阈值”的倍率，想调高/调低双刺高度，改这里最直接。
    average_threshold = float(np.mean(diffs)) * 0.5
    return max(average_threshold, 1e-12)


def _estimate_baseline_step(y_values: List[float]) -> float:
    if len(y_values) < 2:
        return 1.0
    diffs = np.abs(np.diff(np.array(y_values, dtype=float)))
    median_diff = float(np.median(diffs)) if len(diffs) > 0 else 0.0
    return max(median_diff, 1.0)


def _predict_point_from_previous(x_values: List[float], y_values: List[float], target_idx: int, history_size: int = 4) -> float:
    # 单刺修复用：只根据前面几个正常点外推当前点应该落在哪。
    history_start = max(0, target_idx - history_size)
    history_x = x_values[history_start:target_idx]
    history_y = y_values[history_start:target_idx]
    target_x = float(x_values[target_idx])

    return _predict_value_from_history(history_x, history_y, target_x, fallback_value=float(y_values[target_idx]))


def _predict_value_from_history(
    history_x: List[float],
    history_y: List[float],
    target_x: float,
    fallback_value: Optional[float] = None
) -> float:
    history_x = np.array(history_x, dtype=float)
    history_y = np.array(history_y, dtype=float)

    if len(history_y) == 0:
        return float(fallback_value if fallback_value is not None else 0.0)
    if len(history_y) == 1:
        return float(history_y[-1])

    degree = 1 if len(history_y) == 2 else min(2, len(history_y) - 1)
    try:
        coeffs = np.polyfit(history_x, history_y, deg=degree)
        return float(np.polyval(coeffs, target_x))
    except Exception:
        if len(history_y) >= 2:
            slope = history_y[-1] - history_y[-2]
            return float(history_y[-1] + slope)
        return float(history_y[-1])


# ==================== 倒刺处理函数（保持原有逻辑） ====================
def process_spike_removal(
    x_data: List[float],
    y_data: List[float],
    k: float
) -> Dict[str, Any]:
    """
    倒刺消除主函数（保持原有逻辑不变）
    """
    try:
        x = np.array([float(val) for val in x_data])
        y = np.array([float(val) for val in y_data])
    except ValueError:
        raise APIException(ErrorCode.X_Y_MUST_NUM)

    if len(x) != len(y):
        raise APIException(ErrorCode.X_Y_LENGTH_MISMATCH)

    # 自动检测倒刺
    spikes = detect_spikes_adaptive(y, k)

    # 去除倒刺
    if len(spikes) > 0:
        try:
            y = remove_spikes(y, spike_indices=spikes)
        except Exception as e:
            raise APIException(ErrorCode.OPERATION_FAILED)
    
    return {'code': 200, 'smoothed_data': [round(v, 4) for v in y]}


# ==================== 以下是原有的辅助函数，保持不变 ====================

# 自动检测倒刺（保持原有逻辑）
def detect_spikes_adaptive(data: List[float], k: float, exclude_indices: List[int] = []) -> Optional[List[int]]:
    """
    基于相邻点变化的平均波动 × k 倍门限，检测最大尖刺点。
    排除台阶点，避免重复判断。
    """
    data = np.array(data)
    diffs = np.abs(np.diff(data))
    avg_deviation = np.mean(diffs)
    threshold = k * avg_deviation

    # 动态设置 sustain_window（方法一：基于数据长度）
    sustain_window = max(3, len(data) // 100)

    candidate_spikes = []

    for i in range(1, len(data) - 1):
        if i in exclude_indices:
            continue
        left_jump = abs(data[i] - data[i - 1])
        right_jump = abs(data[i + 1] - data[i])
        if left_jump > threshold and right_jump > threshold:
            # 判断是否为瞬时跳变（尖刺），即两边跳变方向一致（向上再向下 or 向下再向上）
            if (data[i] - data[i - 1]) * (data[i + 1] - data[i]) < 0:
                total_jump = left_jump + right_jump
                candidate_spikes.append((i, total_jump))

    if not candidate_spikes:
        return []

    max_spike = max(candidate_spikes, key=lambda x: x[1])[0]
    return [max_spike]


# 倒刺去除函数（保持原有逻辑）
def remove_spikes(data, spike_indices):
    """倒刺修复：中值滤波替换尖点"""
    data = data.copy()
    for idx in spike_indices:
        window = data[max(0, idx - 2): min(len(data), idx + 3)]
        data[idx] = np.median(window)
    return data


# 平滑函数（多种方法）
def smooth_data(data, method="gaussian"):
    return gaussian_filter(data, sigma=2)


# 移动平均平滑
def moving_average(data, window_size=5):
    return np.convolve(data, np.ones(window_size)/window_size, mode='valid')