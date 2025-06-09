import io
import base64
import numpy as np
from typing import List, Optional
import matplotlib.pyplot as plt
from exceptions.error import ErrorCode
from exceptions.command_exception import APIException
from scipy.signal import medfilt
from scipy.ndimage import gaussian_filter

def fit_data(x_data: List[float], y_data: List[float], k: float):
    # 解析x和y数据
    # x_data = x_data[::-1]
    # y_data = y_data[::-1]
    try:
        x = np.array([float(val) for val in x_data])
        y = np.array([float(val) for val in y_data])
    except ValueError:
        raise APIException(ErrorCode.X_Y_MUST_NUM)

    # 检查数据长度是否匹配
    if len(x) != len(y):
        raise APIException(ErrorCode.X_Y_LENGTH_MISMATCH)

    # 自动检测台阶和倒刺
    steps = detect_steps_adaptive(y, k)
    spikes = detect_spikes_adaptive(y, k)

    # 根据检测结果决定是否需要去除台阶和倒刺
    if len(steps) > 0:
        try:
            y, steps = remove_steps(y, steps)  # 调用台阶去除函数
        except Exception as e:
            raise APIException(ErrorCode.OPERATION_FAILED)

    if len(spikes) > 0:
        try:
            y = remove_spikes(y, spike_indices=spikes)  # 调用倒刺去除函数
        except Exception as e:
            raise APIException(ErrorCode.OPERATION_FAILED)

    # 平滑处理
    # try:
    #     smoothed_data = smooth_data(y)  # 调用平滑函数
    # except Exception as e:
    #     raise APIException(ErrorCode.OPERATION_FAILED)
    
    return {'code': 0, 'smoothed_data': [round(v, 4) for v in y]}

    # fig, ax = plt.subplots(figsize=(10, 6))
    # ax.plot(x, y_data, label="原始数据", linestyle="--", color='gray')
    # ax.plot(x, y, label="去台阶或者倒刺的数据", linestyle="-.", color='orange')
    # ax.legend()
    # ax.set_title("数据处理过程可视化")
    # ax.set_xlabel("波长")
    # ax.set_ylabel("吸光度")
    # fig.tight_layout()

    # buf = io.BytesIO()
    # plt.savefig(buf, format='png')
    # buf.seek(0)
    # base64_img = base64.b64encode(buf.read()).decode('utf-8')
    # plt.close()

    # return {
    #     'code': 0,
    #     'smoothed_data': [round(v, 4) for v in y],
    #     'image_base64': base64_img
    # }

# 自动检测台阶
def detect_steps_adaptive(data: List[float], k: int) -> Optional[List[int]]:
    """
    基于相邻点的平均波动 × k 倍数门限，检测最大的台阶点。
    """
    data = np.array(data)
    diffs = np.abs(np.diff(data))
    avg_deviation = np.mean(diffs)
    threshold = k * avg_deviation
    sustain_window = max(3, len(data) // 100)
    candidate_indices = []
    for i in range(len(data) - sustain_window - 1):
        step_jump = abs(data[i + 1] - data[i])
        if step_jump > threshold:
            # 检查后面 sustain_window 个点是否维持在新的水平附近
            post_mean = np.mean(data[i+2:i+2+sustain_window])
            if abs(post_mean - data[i+1]) < avg_deviation:
                candidate_indices.append((i, step_jump))

    if not candidate_indices:
        return []

    max_idx = max(candidate_indices, key=lambda x: x[1])[0]
    return [max_idx]


# 自动检测倒刺
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

# 新增：计算台阶偏移量（整体校正的关键）
def calc_step_offset(data, step_idx):
    """
    计算台阶的偏移量（台阶前和台阶后的均值差）
    窗口大小确保使用稳定的数据段
    """
    y_next, curvature = predict_next_point_by_curvature(data[step_idx-1:])
    # now_y = data[step_idx]
    # offset = data[step_idx+1]  - data[step_idx]
    # return offset

    if step_idx + 1 >= len(data):
        # 防止越界，无法计算偏移，返回0或抛异常
        return 0  
    offset = data[step_idx + 1] - data[step_idx]
    return y_next, offset

# 台阶去除函数
def remove_steps(data, step_indices):
    """
    整体偏移校正方案：
    1. 计算每个台阶点的偏移量
    2. 从台阶点开始，将后面的所有数据减去偏移量
    3. 在台阶点周围做过渡平滑
    """
    data = data.copy()
    step_infos = []
    
    # 按台阶点位置排序（从前到后）
    sorted_indices = np.sort(step_indices)
    
    # 计算每个台阶点的偏移量
    offsets = []
    for idx in sorted_indices:
        y_next, offset = calc_step_offset(data, idx)
        offsets.append(offset)
        step_infos.append({"position": idx, "offset": offset})
    for step_info in step_infos:
        idx = step_info["position"]
        offset = step_info["offset"]
        for i in range(idx+1, len(data)):
            # print('下标:', i)
            # print('当前y:', data[i])
            # print('处理后y', data[i] - offset)
            # print('------------')
            data[i] -= offset
    return data, step_info

# 倒刺去除函数
def remove_spikes(data, spike_indices):
    """倒刺修复：中值滤波替换尖点"""
    data = data.copy()
    for idx in spike_indices:
        window = data[max(0, idx - 2): min(len(data), idx + 3)]
        data[idx] = np.median(window)
    return data

# 平滑函数（多种方法）
def smooth_data(data, method="gaussian"):
    # if method == "moving_average":
    #     return moving_average(data)
    # elif method == "gaussian":
    return gaussian_filter(data, sigma=2)
    # elif method == "median":
    #     return medfilt(data, kernel_size=5)
    # else:
        # raise ValueError("Invalid smoothing method")

# 移动平均平滑
def moving_average(data, window_size=5):
    return np.convolve(data, np.ones(window_size)/window_size, mode='valid')


# 中值滤波平滑
def medfilt(data, kernel_size=5):
    return medfilt(data, kernel_size=kernel_size)


def predict_next_point_by_curvature(y: List[float]) -> float:
    """
    使用局部曲率预测下一个 y 值
    """
    if len(y) < 3:
        raise ValueError("至少需要3个点来计算曲率")
    
    y = np.array(y)
    x = np.arange(len(y))  # 假设等间距

    # 取最后三个点计算曲率
    x1, x2, x3 = x[-3], x[-2], x[-1]
    y1, y2, y3 = y[-3], y[-2], y[-1]

    # 使用有限差分法计算一阶导和二阶导
    dy_dx = (y3 - y1) / (x3 - x1)
    d2y_dx2 = (y3 - 2 * y2 + y1) / ((x3 - x2) ** 2)

    # 曲率计算公式（简化版本）
    curvature = np.abs(d2y_dx2) / (1 + dy_dx ** 2) ** 1.5

    # 预测下一个点（简单外推：延续曲率趋势）
    # 用二阶泰勒展开：y_next = y3 + dy + 0.5 * ddy
    dx = 1  # 假设等间距
    y_next = y3 + dy_dx * dx + 0.5 * d2y_dx2 * dx ** 2

    return round(y_next, 4), round(curvature, 6)