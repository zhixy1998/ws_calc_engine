"""
滤波算法模块

包含以下滤波算法：
1. SG滤波 (Savitzky-Golay滤波)
2. 滑动平均滤波
3. 中位平均滤波
4. 小波滤波
"""

import numpy as np
from scipy.signal import savgol_filter
from scipy.ndimage import uniform_filter1d
from scipy.stats import trim_mean
import pywt
from typing import List, Union


# ==================== SG滤波 (Savitzky-Golay滤波) ====================

def sg_smooth_manual(data: List[float], m: int) -> np.ndarray:
    """
    手动实现的SG滤波（与C++代码逻辑一致）
    
    Args:
        data: 输入数据列表
        m: 半步宽 (m > 0, m越大，平滑度越高)
    
    Returns:
        平滑后的数据数组
    """
    # 计算系数 (对应C++的SetCoefficient)
    w = m * 2 + 1
    w2 = w ** 2
    a1 = 15 / (w2 - 4)
    a2 = (w2 - 1) / 12
    coefficient = [(1 + a1 * (a2 - j ** 2)) / w for j in range(-m, m + 1)]
    
    data = np.array(data)
    result = np.copy(data)
    
    # 对每个点应用SG平滑
    for i in range(m, len(data) - m):
        window = data[i - m:i + m + 1]
        if len(window) == len(coefficient):
            result[i] = sum(c * v for c, v in zip(coefficient, window))
    
    return result


def sg_smooth(data: Union[List[float], np.ndarray], window_length: int = 5, polyorder: int = 2) -> np.ndarray:
    """
    使用scipy库的Savitzky-Golay滤波（推荐使用）
    
    Args:
        data: 输入数据
        window_length: 窗口长度（必须为奇数）
        polyorder: 多项式阶数
    
    Returns:
        平滑后的数据数组
    """
    data = np.array(data)
    # 确保window_length是奇数
    if window_length % 2 == 0:
        window_length += 1
    # 确保window_length大于polyorder
    if window_length <= polyorder:
        window_length = polyorder + 2
        if window_length % 2 == 0:
            window_length += 1
    return savgol_filter(data, window_length, polyorder)


# ==================== 滑动平均滤波 ====================

def slide_filter_manual(data: List[float], window_size: int, num_iterations: int = 1) -> float:
    """
    手动实现的滑动平均滤波（与C++代码逻辑一致）
    
    Args:
        data: 输入数据列表
        window_size: 窗口大小
        num_iterations: 迭代次数
    
    Returns:
        滤波后的单个值（最后10个点之后的平均值）
    """
    filtered_data = np.array(data, dtype=float)
    
    for _ in range(num_iterations):
        temp_data = []
        for i in range(len(filtered_data)):
            start_index = max(0, i - window_size // 2)
            end_index = min(len(filtered_data) - 1, i + window_size // 2)
            window = filtered_data[start_index:end_index + 1]
            temp_data.append(np.mean(window))
        filtered_data = np.array(temp_data)
    
    # 返回第10个点之后的平均值
    if len(filtered_data) > 10:
        return np.mean(filtered_data[10:])
    return np.mean(filtered_data)


def slide_filter(data: Union[List[float], np.ndarray], window_size: int, num_iterations: int = 1) -> np.ndarray:
    """
    使用scipy库的滑动平均滤波（推荐使用）
    
    Args:
        data: 输入数据
        window_size: 窗口大小
        num_iterations: 迭代次数
    
    Returns:
        滤波后的完整数据数组
    """
    filtered_data = np.array(data, dtype=float)
    
    for _ in range(num_iterations):
        filtered_data = uniform_filter1d(filtered_data, size=window_size, mode='nearest')
    
    return filtered_data


# ==================== 中位平均滤波 ====================

def mid_filter_manual(data: List[float]) -> float:
    """
    手动实现的中位平均滤波（与C++代码逻辑一致）
    去掉最大值和最小值后求平均
    
    Args:
        data: 输入数据列表
    
    Returns:
        滤波后的单个值
    """
    if len(data) <= 2:
        return np.mean(data)
    
    sorted_data = sorted(data)
    # 去掉最大和最小值后求平均
    trimmed_data = sorted_data[1:-1]
    return np.mean(trimmed_data)


def mid_filter(data: Union[List[float], np.ndarray], proportiontocut: float = 0.1) -> float:
    """
    使用scipy库的修剪平均滤波（推荐使用）
    
    Args:
        data: 输入数据
        proportiontocut: 两端各去掉的比例 (0-0.5)
    
    Returns:
        修剪后的平均值
    """
    return trim_mean(data, proportiontocut)


def mid_filter_window(data: Union[List[float], np.ndarray], window_size: int) -> np.ndarray:
    """
    滑动窗口中位平均滤波
    
    Args:
        data: 输入数据
        window_size: 窗口大小
    
    Returns:
        滤波后的完整数据数组
    """
    data = np.array(data, dtype=float)
    result = np.copy(data)
    half_window = window_size // 2
    
    for i in range(len(data)):
        start = max(0, i - half_window)
        end = min(len(data), i + half_window + 1)
        window = data[start:end]
        if len(window) > 2:
            sorted_window = np.sort(window)
            result[i] = np.mean(sorted_window[1:-1])
        else:
            result[i] = np.mean(window)
    
    return result


# ==================== 小波滤波 ====================

def wavelet_filter(data: Union[List[float], np.ndarray], 
                   wavelet: str = 'db4', 
                   level: int = None, 
                   threshold_mode: str = 'soft',
                   threshold_method: str = 'universal') -> np.ndarray:
    """
    小波滤波（去噪）
    
    Args:
        data: 输入数据
        wavelet: 小波类型，常用的有：
                 - 'db1'-'db20': Daubechies小波
                 - 'sym2'-'sym20': Symlet小波
                 - 'coif1'-'coif5': Coiflet小波
                 - 'haar': Haar小波
        level: 分解层数，None表示自动计算最大层数
        threshold_mode: 阈值模式，'soft'（软阈值）或'hard'（硬阈值）
        threshold_method: 阈值计算方法：
                         - 'universal': 通用阈值 (VisuShrink)
                         - 'sqtwolog': sqrt(2*log(n))
    
    Returns:
        滤波后的数据数组
    """
    data = np.array(data, dtype=float)
    
    # 自动计算分解层数
    if level is None:
        level = pywt.dwt_max_level(len(data), wavelet)
        level = min(level, 5)  # 限制最大层数为5
    
    # 小波分解
    coeffs = pywt.wavedec(data, wavelet, level=level)
    
    # 计算阈值
    # 使用第一层细节系数估计噪声标准差
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    
    if threshold_method == 'universal':
        # 通用阈值 (VisuShrink)
        threshold = sigma * np.sqrt(2 * np.log(len(data)))
    else:
        threshold = sigma * np.sqrt(2 * np.log(len(data)))
    
    # 对细节系数应用阈值
    new_coeffs = [coeffs[0]]  # 保留近似系数
    for i in range(1, len(coeffs)):
        if threshold_mode == 'soft':
            # 软阈值
            new_coeffs.append(pywt.threshold(coeffs[i], threshold, mode='soft'))
        else:
            # 硬阈值
            new_coeffs.append(pywt.threshold(coeffs[i], threshold, mode='hard'))
    
    # 小波重构
    filtered_data = pywt.waverec(new_coeffs, wavelet)
    
    # 确保输出长度与输入一致
    if len(filtered_data) > len(data):
        filtered_data = filtered_data[:len(data)]
    
    return filtered_data


def wavelet_filter_simple(data: Union[List[float], np.ndarray], 
                          wavelet: str = 'db4', 
                          level: int = 3) -> np.ndarray:
    """
    简化版小波滤波
    只保留低频近似系数，去除高频细节
    
    Args:
        data: 输入数据
        wavelet: 小波类型
        level: 分解层数
    
    Returns:
        滤波后的数据数组
    """
    data = np.array(data, dtype=float)
    
    # 小波分解
    coeffs = pywt.wavedec(data, wavelet, level=level)
    
    # 将所有细节系数置零
    for i in range(1, len(coeffs)):
        coeffs[i] = np.zeros_like(coeffs[i])
    
    # 小波重构
    filtered_data = pywt.waverec(coeffs, wavelet)
    
    # 确保输出长度与输入一致
    if len(filtered_data) > len(data):
        filtered_data = filtered_data[:len(data)]
    
    return filtered_data


# ==================== 示例使用 ====================

if __name__ == "__main__":
    # 生成测试数据（带噪声的正弦波）
    np.random.seed(42)
    x = np.linspace(0, 4 * np.pi, 200)
    clean_signal = np.sin(x)
    noise = np.random.normal(0, 0.1, len(x))
    noisy_signal = clean_signal + noise
    
    print("=" * 50)
    print("滤波算法测试")
    print("=" * 50)
    
    # 1. SG滤波
    sg_result = sg_smooth(noisy_signal, window_length=11, polyorder=2)
    print(f"\n1. SG滤波 (scipy): 前5个值 = {sg_result[:5]}")
    
    sg_manual_result = sg_smooth_manual(noisy_signal.tolist(), m=5)
    print(f"   SG滤波 (手动): 前5个值 = {sg_manual_result[:5]}")
    
    # 2. 滑动平均滤波
    slide_result = slide_filter(noisy_signal, window_size=5, num_iterations=2)
    print(f"\n2. 滑动平均滤波: 前5个值 = {slide_result[:5]}")
    
    # 3. 中位平均滤波
    mid_result = mid_filter_window(noisy_signal, window_size=5)
    print(f"\n3. 中位平均滤波: 前5个值 = {mid_result[:5]}")
    
    # 4. 小波滤波
    wavelet_result = wavelet_filter(noisy_signal, wavelet='db4', level=3)
    print(f"\n4. 小波滤波 (阈值): 前5个值 = {wavelet_result[:5]}")
    
    wavelet_simple_result = wavelet_filter_simple(noisy_signal, wavelet='db4', level=3)
    print(f"   小波滤波 (简化): 前5个值 = {wavelet_simple_result[:5]}")
    
    print("\n" + "=" * 50)
    print("测试完成!")
