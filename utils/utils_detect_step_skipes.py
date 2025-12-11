import io
import base64
import numpy as np
from typing import List, Optional, Dict, Any
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
            'last_x': None,           # 上一批次最后一个 x 值
            'last_y': None,           # 上一批次最后一个 y 值
            'last_few_y': [],         # 上一批次最后几个 y 值（用于预测）
            'accumulated_offset': 0.0, # 累计偏移量
            'step_corrected': False,   # 是否已经完成台阶校正
        }
    
    def update(self, x_data: List[float], y_data: List[float]):
        """更新缓存，保存当前批次的尾部数据"""
        self._data['last_x'] = x_data[-1] if x_data else None
        self._data['last_y'] = y_data[-1] if y_data else None
        # 保存最后3个点用于预测
        self._data['last_few_y'] = list(y_data[-3:]) if len(y_data) >= 3 else list(y_data)
    
    def set_offset(self, offset: float):
        """设置累计偏移量"""
        self._data['accumulated_offset'] = offset
        self._data['step_corrected'] = True
    
    def get_offset(self) -> float:
        """获取累计偏移量"""
        return self._data['accumulated_offset']
    
    def is_step_corrected(self) -> bool:
        """检查是否已经完成台阶校正"""
        return self._data['step_corrected']
    
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
            'step_corrected': False,
        }


# ==================== 台阶处理函数（新逻辑） ====================
def process_step_removal(
    x_data: List[float],
    y_data: List[float],
    change_lamp_wavelength: Optional[float],
    wavelength_end: Optional[float],
    cache: StepCorrectionCache
) -> Dict[str, Any]:
    """
    台阶消除主函数（基于已知换灯波长）
    
    参数:
        x_data: 当前批次的波长数据（从高到低）
        y_data: 当前批次的吸光度数据
        change_lamp_wavelength: 换灯波长（换灯后第一个点的波长，即台阶点）
        wavelength_end: 本次测量的结束波长（最低波长），用于判断是否最后一批
        cache: 缓存对象
    
    返回:
        处理后的结果
    
    逻辑说明:
        1. 数据从高波长向低波长传递，每次10个点
        2. 换灯波长是台阶点（换灯后第一个点，会出现跳变）
        3. 如果换灯点在当前批次的第一个位置，需要用上一批次的数据计算偏移
        4. 计算偏移后，从换灯点开始，后续所有点都减去偏移量
        5. 根据 wavelength_end 判断是否最后一批，最后一批时清理缓存
    """
    try:
        x = np.array([float(val) for val in x_data])
        y = np.array([float(val) for val in y_data])
    except ValueError:
        raise APIException(ErrorCode.X_Y_MUST_NUM)

    if len(x) != len(y):
        raise APIException(ErrorCode.X_Y_LENGTH_MISMATCH)
    
    y_corrected = y.copy()
    
    # 判断是否是最后一批数据（当前批次包含结束波长）
    is_last_batch = False
    if wavelength_end is not None:
        # 当前批次的最小波长 <= 结束波长，说明是最后一批
        is_last_batch = min(x) <= wavelength_end
    
    # 情况1：已经完成台阶校正，后续批次直接应用累计偏移
    if cache.is_step_corrected():
        # print(f'debug 台阶校正: offset {cache.get_offset()}')
        offset = cache.get_offset()
        # print('原始y:', y)
        y_corrected = y - offset
        # print('校正后y:', y_corrected)
    
    # 情况2：需要检测和处理台阶
    elif change_lamp_wavelength is not None:
        # 查找换灯波长在当前批次中的位置
        # print(f'输入的x{x}')
        # print(f'换灯波长: {change_lamp_wavelength}')
        step_idx = find_wavelength_index(x, change_lamp_wavelength)
        
        if step_idx is not None:
            # print('换灯点在当前批次中, idx=', step_idx)
            # 换灯点在当前批次中
            if step_idx == 0:

                # print('换灯点在当前批次第一个点，使用上一个批次的数据')
                # 换灯点是当前批次的第一个点，需要用上一批次的数据
                last_few_y = cache.get_last_few_y()
                if len(last_few_y) >= 2:
                    # 使用上一批次最后几个点预测当前点应有的值
                    predicted_y = predict_next_y_simple(last_few_y)
                    offset = y[0] - predicted_y
                    cache.set_offset(offset)
                    y_corrected = y - offset
                else:
                    # 没有足够的上一批次数据，无法计算偏移
                    # 保持原样，可能需要记录警告
                    pass
            else:
                # 换灯点在批次中间，可以直接计算偏移
                # 使用换灯点前几个点预测换灯点应有的值
                # print('换灯点在当前批次中，可以直接计算偏移量')
                pre_step_y = y[:step_idx].tolist()
                if len(pre_step_y) >= 2:
                    predicted_y = predict_next_y_simple(pre_step_y)
                else:
                    # 点太少，直接用前一个点作为预测值
                    predicted_y = y[step_idx - 1]
                
                offset = y[step_idx] - predicted_y
                cache.set_offset(offset)
                # 从换灯点开始应用偏移
                y_corrected[step_idx:] = y[step_idx:] - offset
    
    # 更新缓存（保存当前批次尾部数据，供下一批次使用）
    cache.update(x.tolist(), y_corrected.tolist())
    
    # 如果是最后一批，清理缓存
    if is_last_batch:
        cache.clear()
    
    return {
        'code': 0,
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
    
    return {'code': 0, 'smoothed_data': [round(v, 4) for v in y]}


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