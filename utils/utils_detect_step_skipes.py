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
        new_x = self._data['tail_x'] + list(x_data)
        new_y = self._data['tail_y'] + list(y_data)
        self._data['tail_x'] = new_x[-tail_size:]
        self._data['tail_y'] = new_y[-tail_size:]

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
    spike_points: List[float],
    wavelength_end: Optional[float],
    cache: SpikeCorrectionCache
) -> Dict[str, Any]:
    """
    按指定 x 坐标批量消除倒刺。

    参数:
        x_data: 当前批次 x 数据
        y_data: 当前批次 y 数据
        spike_points: 倒刺的确切 x 坐标列表（不用做推断，传过来对应的点就是要抹平的点）
        wavelength_end: 本次测量的结束波长，用于判断是否最后一批
        cache: 倒刺缓存对象
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
    remaining_pending: List[float] = []

    resolved_indices: List[int] = []

    for target_x in pending_spikes:
        # 直接拿去匹配
        found_idx = None
        for i, xv in enumerate(combined_x):
            if abs(xv - float(target_x)) < 1e-6:
                found_idx = i
                break
        
        if found_idx is None:
            if not combined_x or min(combined_x) > float(target_x) + 1e-6:
                remaining_pending.append(target_x)
            continue
            
        resolved_indices.append(found_idx)

    valid_indices = sorted(set(idx for idx in resolved_indices if idx >= prefix_len))
    
    for segment_indices in _group_nearby_indices(valid_indices, max_gap=1):
        segment_values = _smooth_spike_segment(combined_x, combined_y, corrected_y, segment_indices)
        for idx, value in zip(segment_indices, segment_values):
            corrected_y[idx] = value

    current_y = corrected_y[prefix_len:]
    cache._data['pending_spikes'] = remaining_pending
    cache.update(x, current_y)

    if is_last_batch:
        cache.clear()
        
    return {
        'code': 200,
        'smoothed_data': current_y,
        'message': 'success'
    }


def _is_spike_at_index(
    y_values: List[float],
    idx: int,
    k: float = 2.0,
) -> bool:
    """
    判断 y_values[idx] 是否是一个异常跳变点（刺）。
    用户规则：该点与相邻点的跳变绝对值，大于波动阈值的 k 倍（默认两倍），就是刺。
    仅凭绝对跳变量判定，不用考虑跳变方向相反。
    """
    if idx <= 0 or idx >= len(y_values):
        return False

    y = np.array(y_values, dtype=float)
    diffs = np.abs(np.diff(y))
    avg_deviation = np.mean(diffs) if len(diffs) > 0 else 0.0
    if avg_deviation == 0.0:
        return False

    threshold = k * avg_deviation
    left_jump = abs(y[idx] - y[idx - 1])
    right_jump = abs(y[idx + 1] - y[idx]) if idx < len(y) - 1 else 0.0

    if left_jump > threshold or right_jump > threshold:
        return True
    return False


def process_targeted_spike_removal_v2(
    x_data: List[float],
    y_data: List[float],
    spike_points: List[float],
    wavelength_end: Optional[float],
    cache: SpikeCorrectionCache,
    search_radius: float = 15.0,
    spike_k: float = 2.0,
) -> Dict[str, Any]:
    """
    按指定 x 坐标（中心波长）在邻域范围内检测并消除倒刺（新逻辑）。

    与旧版 process_targeted_spike_removal 的区别：
      - 旧版：spike_points 是精确 x 坐标，命中即平滑，不做刺判断。
      - 新版：spike_points 是候选中心波长，在 [center - search_radius,
              center + search_radius] 范围内（含边界）查找所有候选点，
              对每个候选点判断是否真的是尖刺，是刺才平滑，否则保持原值。

    参数:
        x_data: 当前批次 x 数据（波长，从高到低）
        y_data: 当前批次 y 数据（吸光度）
        spike_points: 候选倒刺中心波长列表（如 [550.0]）
        wavelength_end: 本次测量的结束波长，用于判断是否最后一批
        cache: 倒刺缓存对象（SpikeCorrectionCache）
        search_radius: 中心波长左右各搜索多少 nm 范围，默认 5.0
        spike_k: 刺判断时的门限倍率（k × 平均波动），默认 3.0
    """
    try:
        x = [float(val) for val in x_data]
        y = [float(val) for val in y_data]
    except ValueError:
        raise APIException(ErrorCode.X_Y_MUST_NUM)

    if len(x) != len(y):
        raise APIException(ErrorCode.X_Y_LENGTH_MISMATCH)

    # 拼接上一批次的尾部缓存（与旧版相同，保证跨批次边界的刺也能被检测）
    tail = cache.get_tail()
    combined_x = tail['x'] + x
    combined_y = tail['y'] + y
    corrected_y = list(combined_y)
    prefix_len = len(tail['x'])

    is_last_batch = False
    if wavelength_end is not None and x:
        is_last_batch = min(x) <= wavelength_end

    # 合并 pending_spikes（上批次未处理的中心波长）与本批次传入的中心波长
    pending_spikes = _unique_keep_order(cache._data['pending_spikes'] + list(spike_points or []))
    remaining_pending: List[float] = []

    confirmed_indices: List[int] = []  # 经过刺判断后确认需要平滑的索引

    for center_x in pending_spikes:
        center_x = float(center_x)
        lo = center_x - search_radius
        hi = center_x + search_radius

        # 只要当前批次还没有安全跨过搜索下限（留出一点余量算右侧跳变差分），就保留到下一批
        # 即使我们在本批次查到了 spike 并平滑处理，保留也没关系，因为下一批次该位置已被抚平，不会再次满足 spike 判定
        if not x or min(x) > lo - 2.0:
            remaining_pending.append(center_x)

        # 找出 combined_x 中落在 [lo, hi] 范围内的所有索引（含边界）
        candidate_indices = [
            i for i, xv in enumerate(combined_x)
            if lo <= xv <= hi
        ]

        if not candidate_indices:
            continue

        # 对候选索引逐个判断是否是真正的尖刺
        for idx in candidate_indices:
            # 只处理属于当前批次的点（idx >= prefix_len），缓存尾部只做上下文
            if idx < prefix_len:
                continue
            if _is_spike_at_index(corrected_y, idx, k=spike_k):
                confirmed_indices.append(idx)

    # 将确认的刺索引分组（相邻刺合并成一段），然后统一平滑
    valid_indices = sorted(set(confirmed_indices))
    for segment_indices in _group_nearby_indices(valid_indices, max_gap=1):
        segment_values = _smooth_spike_segment(combined_x, combined_y, corrected_y, segment_indices)
        for idx, value in zip(segment_indices, segment_values):
            corrected_y[idx] = value

    current_y = corrected_y[prefix_len:]
    cache._data['pending_spikes'] = remaining_pending
    cache.update(x, current_y)

    if is_last_batch:
        cache.clear()

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


def _group_nearby_indices(indices: List[int], max_gap: int = 1) -> List[List[int]]:
    # 相距很近的刺按一个连续小段处理
    if not indices:
        return []
    groups = [[indices[0]]]
    for idx in indices[1:]:
        if idx <= groups[-1][-1] + max_gap:
            groups[-1].append(idx)
        else:
            groups.append([idx])
    return [list(range(group[0], group[-1] + 1)) for group in groups]





def _smooth_spike_segment(
    x_values: List[float],
    original_y_values: List[float],
    corrected_y_values: List[float],
    segment_indices: List[int]
) -> List[float]:
    if not segment_indices:
        return []

    start_idx = segment_indices[0]
    end_idx = segment_indices[-1]
    reference_values = _collect_segment_reference_values(corrected_y_values, segment_indices)

    if not reference_values:
        return [float(corrected_y_values[idx]) for idx in segment_indices]

    # average_threshold 是双刺段最终要保留的“平均阈值高度”。
    average_threshold = _calculate_segment_average_threshold(corrected_y_values, segment_indices)

    # baseline_reference 是刺段两侧正常点的参考基线。
    baseline_reference = float(np.median(np.array(reference_values, dtype=float)))
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


def _collect_segment_reference_values(
    corrected_y_values: List[float],
    segment_indices: List[int],
    window_size: int = 6
) -> List[float]:
    if not segment_indices:
        return []

    start_idx = segment_indices[0]
    end_idx = segment_indices[-1]
    left_segment = corrected_y_values[max(0, start_idx - window_size):start_idx]
    right_segment = corrected_y_values[end_idx + 1:min(len(corrected_y_values), end_idx + window_size + 1)]
    return [float(value) for value in left_segment + right_segment]


def _calculate_segment_average_threshold(corrected_y_values: List[float], segment_indices: List[int]) -> float:
    if not segment_indices:
        return 1e-12

    reference_values = _collect_segment_reference_values(corrected_y_values, segment_indices)

    # 只拿刺段两侧正常点的波动来算平均阈值，不让刺本身把阈值抬高。
    diffs = []
    if len(reference_values) >= 2:
        diffs.extend(np.abs(np.diff(np.array(reference_values, dtype=float))).tolist())

    if not diffs:
        return 1e-12

    # 这里的 4.0 就是“平均阈值”的倍率，想调高/调低双刺高度，改这里最直接。
    average_threshold = float(np.mean(diffs)) * 0.5
    return max(average_threshold, 1e-12)


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