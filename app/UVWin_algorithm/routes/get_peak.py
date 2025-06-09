"""
寻峰，以及峰面积，半峰宽。
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional

import numpy as np
from scipy.signal import find_peaks, peak_widths, savgol_filter

from exceptions.error import ErrorCode
from exceptions.command_exception import APIException

router = APIRouter()

class PeakRequest(BaseModel):
    x_data: List[float] = Field(..., description="x 坐标数组，例如：[1.0, 2.0, 3.0, 4.0]", json_schema_extra={"example": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]})
    y_data: List[float] = Field(..., description="y 值数组，例如：[0.1, 0.8, 0.2, 1.1]", json_schema_extra={"example": [0.1, 1.2, 0.5, 2.5, 0.3, 3.0, 0.7, 1.5, 0.2, 0.0]})
    height: Optional[float] = Field(None, description="过滤峰值的最小高度", json_schema_extra={"example": 1.0})
    distance: Optional[int] = Field(None, description="两个峰之间的最小间距（索引）", json_schema_extra={"example": 2})
    smooth: Optional[int] = Field(0, description="是否平滑，0=否，1=是", json_schema_extra={"example": 1})
    round: Optional[int] = Field(3, description="小数点精度", json_schema_extra={"example": 3})

class PeakResponse(BaseModel):
    code: int = Field(..., description="状态码")
    message: Optional[str] = Field(None, description="消息")
    peak_x: List[float] = Field(..., description="峰值对应的 x 坐标")
    peak_y: List[float] = Field(..., description="峰值对应的 y 值")
    num_peaks: int = Field(..., description="检测到的峰数量")
    peak_indices: List[int] = Field(..., description="峰值在原始数组中的索引位置")
    peak_areas: Optional[List[float]] = Field(None, description="峰面积")
    peak_widths: Optional[List[float]] = Field(None, description="半峰宽")
    smoothed_y: Optional[List[float]] = Field(None, description="平滑后的Y值")
    differentiated_y: Optional[List[float]] = Field(None, description="微分后的Y值")


@router.post("/find_peaks", response_model=PeakResponse)
def find_peaks_post(data: PeakRequest):
    x = np.array(data.x_data)
    y = np.array(data.y_data)
    round_num = data.round

    if len(x) != len(y):
        raise APIException(ErrorCode.X_Y_LENGTH_MISMATCH)
    if data.height is not None and data.height > 1:
        raise APIException(ErrorCode.HEIGHT_MUST_BE_LESS_THAN_OR_EQUAL_1)

    # 先做平滑（可选）
    if data.smooth == 1:
        y_smooth = savgol_filter(y, 5, 3)  # window=5, polyorder=3
    else:
        y_smooth = y.copy()

    # 计算阈值
    height_threshold = None
    if data.height is not None:
        height_threshold = np.max(y_smooth) * data.height

    # 寻峰
    peaks, properties = find_peaks(y_smooth, height=height_threshold, distance=data.distance)

    # 计算半峰宽
    results_half = peak_widths(y_smooth, peaks, rel_height=0.5)

    # 计算峰面积（用半峰宽左右范围积分）
    peak_areas = []
    for i, peak in enumerate(peaks):
        left_ip = int(results_half[2][i])  # 半峰宽左边界索引（浮点数，取整）
        right_ip = int(results_half[3][i])  # 右边界索引
        area = round(np.trapz(y_smooth[left_ip:right_ip + 1], x[left_ip:right_ip + 1]), round_num)
        peak_areas.append(area)

    return {
        "code": 0,
        "message": "Success",
        "peak_indices": peaks.tolist(),
        "peak_x": x[peaks].tolist(),
        "peak_y": y_smooth[peaks].tolist(),
        "num_peaks": len(peaks),
        "peak_areas": peak_areas,
        "peak_widths": [round(i, round_num) for i in results_half[0].tolist()],  # 半峰宽对应x轴单位可以根据需求转换
        "smoothed_y": y_smooth.tolist(),  # 如果需要可返回
        "differentiated_y": [round(i, round_num) for i in np.gradient(y_smooth).tolist()]  # 如果需要可返回
    }