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
    peak_end_x: List[float] = Field(..., description="每个峰结束的 x 坐标（基线=max(左右谷高度)，峰右侧首次回落至基线处的 x，线性插值）")

    smoothed_y: Optional[List[Union[float, str]]] = Field(None, description="平滑后的Y值")
    differentiated_y: Optional[List[float]] = Field(None, description="微分后的Y值")

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
        y_smooth = y.copy()
    else:
        y_smooth = y.copy()
    
    global_range = np.max(y_smooth) - np.min(y_smooth)
    prominence_threshold = global_range * data.height if data.height is not None else None
    
    # 使用 prominence 过滤峰（突出度阈值）
    peaks, properties = find_peaks(y_smooth, distance=data.distance, prominence=prominence_threshold)

    # 计算半峰宽
    results_half = peak_widths(y_smooth, peaks, rel_height=0.5)

    # 计算峰面积（用半峰宽左右范围积分）
    peak_areas = []
    for i, peak in enumerate(peaks):
        left_ip = int(results_half[2][i])  # 半峰宽左边界索引（浮点数，取整）
        right_ip = int(results_half[3][i])  # 右边界索引
        area = round(np.trapz(y_smooth[left_ip:right_ip + 1], x[left_ip:right_ip + 1]), round_num)
        peak_areas.append(area)

    # 计算每个峰的结束 x 坐标（peak_end_x）
    # 标准：基线 = max(左侧谷高度, 右侧谷高度)，即 prominence 的基底高度。
    #      峰右侧首次回落到该基线即为峰的结束点，线性插值精确计算 x。
    #      若无左侧谷，则以第一个数据点的 y 值代替。
    #      若无右侧谷，则以左侧谷高度代替（退化为单侧基线）。
    #      若始终未回落到基线，则取最后一个数据点。
    # 原理：prominence（峰谷差）的基底是左右两侧谷中较高的那个。
    #      基线移动时（右侧谷更高），峰结束于回落到新基线的第一个点。
    #      基线不移动时（左右谷相等），与原来行为一致。
    local_minima = argrelmin(y_smooth, order=1)[0]  # 一阶局部极小值（谷）
    peak_end_x_list = []
    for p in peaks:
        # 左侧谷高度
        left_valleys = local_minima[local_minima < p]
        left_h = float(y_smooth[left_valleys[-1]]) if len(left_valleys) > 0 else float(y_smooth[0])
        # 右侧谷高度
        right_valleys = local_minima[local_minima > p]
        right_h = float(y_smooth[right_valleys[0]]) if len(right_valleys) > 0 else left_h
        # 基线 = prominence 基底 = max(左谷, 右谷)
        baseline_y = max(left_h, right_h)
        # 从峰右侧开始，找第一个 y <= baseline_y 的点
        found = False
        for i in range(int(p) + 1, len(x)):
            if float(y_smooth[i]) <= baseline_y:
                # 线性插值：在 (i-1, y[i-1]) 和 (i, y[i]) 之间找 y=baseline_y 的 x
                if i > int(p) + 1 and float(y_smooth[i - 1]) > baseline_y:
                    x1, x2 = float(x[i - 1]), float(x[i])
                    y1, y2 = float(y_smooth[i - 1]), float(y_smooth[i])
                    if y1 != y2:
                        end_x = x1 + (x2 - x1) * (baseline_y - y1) / (y2 - y1)
                    else:
                        end_x = x2
                else:
                    end_x = float(x[i])
                peak_end_x_list.append(end_x)
                found = True
                break
        if not found:
            # 始终未回落到基线，取最后一个数据点
            peak_end_x_list.append(float(x[-1]))

    # 确保 peak_x 与 peak_end_x 一一对应
    assert len(peak_end_x_list) == len(peaks), f"peak_end_x({len(peak_end_x_list)}) != peaks({len(peaks)})"

    if round_num:
        peak_y_raw = y_smooth[peaks].tolist()
        peak_y_converted = convert_scientific_notation(peak_y_raw)
        peak_y = [round(float(i), round_num) for i in peak_y_converted]
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
        "code": 200,
        "message": "Success",

        # 峰数据
        "peak_indices": peaks.tolist(),
        "peak_x": x[peaks].tolist(),
        "peak_y": peak_y,
        "num_peaks": len(peaks),
        "peak_areas": peak_areas,
        "peak_widths": peak_width_list,
        "peak_end_x": peak_end_x_list,

        "smoothed_y": convert_scientific_notation(smoothed_y),
        "differentiated_y": differentiated_y
    }
    # print("return_data", return_data)
    return return_data