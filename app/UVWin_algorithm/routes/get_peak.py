"""
寻峰，以及峰面积，半峰宽。
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional, Union

import numpy as np
from scipy.signal import find_peaks, peak_widths, savgol_filter, argrelmin

from exceptions.error import ErrorCode
from exceptions.command_exception import APIException
from utils.utils_data_format import convert_scientific_notation

router = APIRouter()

class PeakRequest(BaseModel):
    x_data: List[float] = Field(..., description="x 坐标数组，例如：[1.0, 2.0, 3.0, 4.0]", json_schema_extra={"example": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]})
    y_data: List[float] = Field(..., description="y 值数组，例如：[0.1, 0.8, 0.2, 1.1]", json_schema_extra={"example": [0.1, 1.2, 0.5, 2.5, 0.3, 3.0, 0.7, 1.5, 0.2, 0.0]})
    height: Optional[float] = Field(None, description="峰谷差阈值（0-1之间的比例值）", json_schema_extra={"example": 0.3})
    distance: Optional[int] = Field(None, description="两个峰之间的最小间距（索引）", json_schema_extra={"example": 2})
    smooth: Optional[int] = Field(0, description="是否平滑，0=否，1=是", json_schema_extra={"example": 1})
    round: Optional[int] = Field(0, description="小数点精度", json_schema_extra={"example": 3})

class PeakResponse(BaseModel):
    code: int = Field(..., description="状态码")
    message: Optional[str] = Field(None, description="消息")

    # 峰数据
    peak_x: List[float] = Field(..., description="峰值对应的 x 坐标")
    peak_y: List[Union[float, str]] = Field(..., description="峰值对应的 y 值")
    num_peaks: int = Field(..., description="检测到的峰数量")
    peak_indices: List[int] = Field(..., description="峰值在原始数组中的索引位置")
    peak_areas: Optional[List[float]] = Field(None, description="峰面积")
    peak_widths: Optional[List[float]] = Field(None, description="半峰宽")

    smoothed_y: Optional[List[Union[float, str]]] = Field(None, description="平滑后的Y值")
    differentiated_y: Optional[List[float]] = Field(None, description="微分后的Y值")


def calculate_peak_valley_differences(y_data, peak_indices):
    """
    计算每个峰与其相邻谷的峰谷差
    
    Args:
        y_data: 平滑后的y值数组
        peak_indices: 峰的索引数组
    
    Returns:
        peak_valley_diffs: 每个峰的峰谷差列表
    """
    if len(peak_indices) == 0:
        return []
    
    # 找到所有局部最小值（谷）
    valleys = argrelmin(y_data, order=1)[0]
    
    # 如果没有找到谷，使用数组边界作为谷
    if len(valleys) == 0:
        valleys = np.array([0, len(y_data) - 1])
    else:
        # 确保边界也被考虑为潜在的谷
        valleys = np.concatenate([[0], valleys, [len(y_data) - 1]])
        valleys = np.unique(valleys)
    
    peak_valley_diffs = []
    
    for peak_idx in peak_indices:
        peak_value = y_data[peak_idx]
        
        # 找到峰左侧最近的谷
        left_valleys = valleys[valleys < peak_idx]
        if len(left_valleys) > 0:
            left_valley_idx = left_valleys[-1]  # 最近的左侧谷
            left_valley_value = y_data[left_valley_idx]
        else:
            left_valley_value = float('inf')  # 没有左侧谷
        
        # 找到峰右侧最近的谷
        right_valleys = valleys[valleys > peak_idx]
        if len(right_valleys) > 0:
            right_valley_idx = right_valleys[0]  # 最近的右侧谷
            right_valley_value = y_data[right_valley_idx]
        else:
            right_valley_value = float('inf')  # 没有右侧谷
        
        # 计算峰谷差：峰值减去相邻的最低谷值
        adjacent_valley_value = min(left_valley_value, right_valley_value)
        if adjacent_valley_value == float('inf'):
            # 如果没有相邻谷，使用全局最小值
            adjacent_valley_value = np.min(y_data)
        
        peak_valley_diff = peak_value - adjacent_valley_value
        peak_valley_diffs.append(peak_valley_diff)
    
    return peak_valley_diffs

@router.post("", response_model=PeakResponse)
def find_peaks_post(data: PeakRequest):
    x = np.array(data.x_data)
    y = np.array(data.y_data)
    round_num = data.round

    if len(x) != len(y):
        raise APIException(ErrorCode.X_Y_LENGTH_MISMATCH)
    if data.height is not None and (data.height < 0 or data.height > 1):
        raise APIException(ErrorCode.HEIGHT_MUST_BE_BETWEEN_0_AND_1)

    # 先做平滑（可选）
    if data.smooth == 1:
        y_smooth = savgol_filter(y, 5, 3)  # window=5, polyorder=3
    else:
        y_smooth = y.copy()

    # 首先找到所有可能的峰（不使用height过滤）
    all_peaks, properties = find_peaks(y_smooth, distance=data.distance)
    
    # 如果指定了height参数，使用峰谷差进行过滤
    if data.height is not None and len(all_peaks) > 0:
        # 计算每个峰的峰谷差
        peak_valley_diffs = calculate_peak_valley_differences(y_smooth, all_peaks)
        
        # 计算全局峰谷差范围作为参考
        global_range = np.max(y_smooth) - np.min(y_smooth)
        threshold = global_range * data.height
        
        # 根据峰谷差过滤峰
        valid_peak_mask = np.array(peak_valley_diffs) >= threshold
        peaks = all_peaks[valid_peak_mask]
    else:
        peaks = all_peaks

    # 计算半峰宽
    results_half = peak_widths(y_smooth, peaks, rel_height=0.5)

    # 计算峰面积（用半峰宽左右范围积分）
    peak_areas = []
    for i, peak in enumerate(peaks):
        left_ip = int(results_half[2][i])  # 半峰宽左边界索引（浮点数，取整）
        right_ip = int(results_half[3][i])  # 右边界索引
        area = round(np.trapz(y_smooth[left_ip:right_ip + 1], x[left_ip:right_ip + 1]), round_num)
        peak_areas.append(area)
    


    if round_num:
        peak_y_raw = y_smooth[peaks].tolist()
        peak_y_converted = convert_scientific_notation(peak_y_raw)
        peak_y = [round(i, round_num) for i in peak_y_converted]
        peak_width_list = [round(i, round_num) for i in results_half[0].tolist()]  # 半峰宽对应x轴单位可以根据需求转换
        smoothed_y = [round(i, round_num) for i in y_smooth.tolist()]  # 如果需要可返回
        differentiated_y = [round(i, round_num) for i in np.gradient(y_smooth).tolist()]  # 如果需要可返回
    else:
        peak_y_raw = y_smooth[peaks].tolist()
        peak_y = convert_scientific_notation(peak_y_raw)
        peak_width_list = results_half[0].tolist()
        smoothed_y = y_smooth.tolist()
        differentiated_y = np.gradient(y_smooth).tolist()
    print("peak_y", peak_y)
    return_data = {
        "code": 0,
        "message": "Success",

        # 峰数据
        "peak_indices": peaks.tolist(),
        "peak_x": x[peaks].tolist(),
        "peak_y": peak_y,
        "num_peaks": len(peaks),
        "peak_areas": peak_areas,
        "peak_widths": peak_width_list,

        "smoothed_y": convert_scientific_notation(smoothed_y),
        "differentiated_y": differentiated_y
    }
    # print("return_data", return_data)
    return return_data