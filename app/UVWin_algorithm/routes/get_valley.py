from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional, Union

import numpy as np
from scipy.signal import find_peaks, peak_widths, savgol_filter, argrelmax

from exceptions.error import ErrorCode
from exceptions.command_exception import APIException
from utils.utils_data_format import convert_scientific_notation

router = APIRouter()

class PeakRequest(BaseModel):
    x_data: List[float] = Field(..., description="x 坐标数组，例如：[1.0, 2.0, 3.0, 4.0]", json_schema_extra={"example": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]})
    y_data: List[float] = Field(..., description="y 值数组，例如：[0.1, 0.8, 0.2, 1.1]", json_schema_extra={"example": [0.1, 1.2, 0.5, 2.5, 0.3, 3.0, 0.7, 1.5, 0.2, 0.0]})
    height: Optional[float] = Field(None, description="谷峰差阈值（0-1之间的比例值）", json_schema_extra={"example": 0.3})
    distance: Optional[int] = Field(None, description="两个峰之间的最小间距（索引）", json_schema_extra={"example": 2})
    smooth: Optional[int] = Field(0, description="是否平滑，0=否，1=是", json_schema_extra={"example": 1})
    round: Optional[int] = Field(0, description="小数点精度", json_schema_extra={"example": 3})

class OutSchema(BaseModel):
    code: int = Field(..., description="状态码")
    message: Optional[str] = Field(None, description="消息")


    # 谷数据
    valley_x: List[float] = Field(..., description="谷值对应的 x 坐标")
    valley_y: List[Union[float, str]] = Field(..., description="谷值对应的 y 值")
    num_valleys: int = Field(..., description="检测到的谷数量")
    valley_indices: List[int] = Field(..., description="谷值在原始数组中的索引位置")
    valley_depths: Optional[List[float]] = Field(None, description="谷深度") # 对应半峰宽，可以是半谷宽或谷深度
    valley_widths: Optional[List[float]] = Field(None, description="半谷宽") # 对应半峰宽

    smoothed_y: Optional[List[Union[float, str]]] = Field(None, description="平滑后的Y值")
    differentiated_y: Optional[List[float]] = Field(None, description="微分后的Y值")


def calculate_valley_peak_differences(y_data, valley_indices):
    """
    计算每个谷与其相邻峰的谷峰差
    
    Args:
        y_data: 平滑后的y值数组
        valley_indices: 谷的索引数组
    
    Returns:
        valley_peak_diffs: 每个谷的谷峰差列表
    """
    if len(valley_indices) == 0:
        return []
    
    # 找到所有局部最大值（峰）
    peaks = argrelmax(y_data, order=1)[0]
    
    # 如果没有找到峰，使用数组边界作为峰
    if len(peaks) == 0:
        peaks = np.array([0, len(y_data) - 1])
    else:
        # 确保边界也被考虑为潜在的峰
        peaks = np.concatenate([[0], peaks, [len(y_data) - 1]])
        peaks = np.unique(peaks)
    
    valley_peak_diffs = []
    
    for valley_idx in valley_indices:
        valley_value = y_data[valley_idx]
        
        # 找到谷左侧最近的峰
        left_peaks = peaks[peaks < valley_idx]
        if len(left_peaks) > 0:
            left_peak_idx = left_peaks[-1]  # 最近的左侧峰
            left_peak_value = y_data[left_peak_idx]
        else:
            left_peak_value = float('-inf')  # 没有左侧峰
        
        # 找到谷右侧最近的峰
        right_peaks = peaks[peaks > valley_idx]
        if len(right_peaks) > 0:
            right_peak_idx = right_peaks[0]  # 最近的右侧峰
            right_peak_value = y_data[right_peak_idx]
        else:
            right_peak_value = float('-inf')  # 没有右侧峰
        
        # 计算谷峰差：相邻的最高峰值减去谷值
        adjacent_peak_value = max(left_peak_value, right_peak_value)
        if adjacent_peak_value == float('-inf'):
            # 如果没有相邻峰，使用全局最大值
            adjacent_peak_value = np.max(y_data)
        
        valley_peak_diff = adjacent_peak_value - valley_value
        valley_peak_diffs.append(valley_peak_diff)
    
    return valley_peak_diffs

@router.post("", response_model=OutSchema)
def find_valley_post(data: PeakRequest):
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

    # 将Y值取反以寻谷
    y_inverted = -y_smooth

    # 首先找到所有可能的谷（不使用height过滤）
    all_valleys, valley_properties = find_peaks(y_inverted, distance=data.distance)
    
    # 如果指定了height参数，使用谷峰差进行过滤
    if data.height is not None and len(all_valleys) > 0:
        # 计算每个谷的谷峰差
        valley_peak_diffs = calculate_valley_peak_differences(y_smooth, all_valleys)
        
        # 计算全局峰谷差范围作为参考
        global_range = np.max(y_smooth) - np.min(y_smooth)
        threshold = global_range * data.height
        
        # 根据谷峰差过滤谷
        valid_valley_mask = np.array(valley_peak_diffs) >= threshold
        valleys = all_valleys[valid_valley_mask]
    else:
        valleys = all_valleys

    # 计算半谷宽 (对取反后的数据计算半峰宽，rel_height 0.5 依然有效)
    valley_widths_results = peak_widths(y_inverted, valleys, rel_height=0.5)

    # 计算谷深度：直接使用y_inverted在valleys索引位置的值
    if len(valleys) > 0:
        valley_depths = [round(y_inverted[v], round_num) for v in valleys]
    else:
        valley_depths = []

    # 计算谷深度 (即取反后峰的高度) 和 半谷宽 (x轴上的宽度)
    valley_widths_at_half = [round(i, round_num) for i in valley_widths_results[0].tolist()]

    if round_num:
        valley_y_raw = y_smooth[valleys].tolist() # 谷的y值是原始平滑后的y值
        valley_y_converted = convert_scientific_notation(valley_y_raw)
        valley_y = [round(i, round_num) for i in valley_y_converted]
        smoothed_y = [round(i, round_num) for i in y_smooth.tolist()]  # 如果需要可返回
        differentiated_y = [round(i, round_num) for i in np.gradient(y_smooth).tolist()]  # 如果需要可返回
    else:
        valley_y_raw = y_smooth[valleys].tolist()
        valley_y = convert_scientific_notation(valley_y_raw)
        smoothed_y = y_smooth.tolist()
        differentiated_y = np.gradient(y_smooth).tolist()

    return_data =  {
        "code": 0,
        "message": "Success",

        # 谷数据
        "valley_indices": valleys.tolist(),
        "valley_x": x[valleys].tolist(),
        "valley_y": valley_y,
        "num_valleys": len(valleys),
        "valley_depths": valley_depths,
        "valley_widths": valley_widths_at_half,

        "smoothed_y": convert_scientific_notation(smoothed_y),
        "differentiated_y": differentiated_y
    }
    # print("return_data", return_data)
    return return_data