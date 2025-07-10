
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
    round: Optional[int] = Field(0, description="小数点精度", json_schema_extra={"example": 3})

class OutSchema(BaseModel):
    code: int = Field(..., description="状态码")
    message: Optional[str] = Field(None, description="消息")


    # 谷数据
    valley_x: List[float] = Field(..., description="谷值对应的 x 坐标")
    valley_y: List[float] = Field(..., description="谷值对应的 y 值")
    num_valleys: int = Field(..., description="检测到的谷数量")
    valley_indices: List[int] = Field(..., description="谷值在原始数组中的索引位置")
    valley_depths: Optional[List[float]] = Field(None, description="谷深度") # 对应半峰宽，可以是半谷宽或谷深度
    valley_widths: Optional[List[float]] = Field(None, description="半谷宽") # 对应半峰宽

    smoothed_y: Optional[List[float]] = Field(None, description="平滑后的Y值")
    differentiated_y: Optional[List[float]] = Field(None, description="微分后的Y值")


@router.post("", response_model=OutSchema)
def find_valley_post(data: PeakRequest):
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

    # 将Y值取反以寻谷
    y_inverted = -y_smooth

    # 谷的深度阈值 (相对于取反后Y值的最大值)
    # 例如，如果原始最小值是0.1，取反是-0.1。如果原始最小值是-5，取反是5。
    # 我们用 np.max(y_inverted) * data.height 来设置阈值，找到“最深”的谷（取反后是最高的峰）
    valley_depth_threshold = None
    if data.height is not None:
        valley_depth_threshold = np.min(y_inverted) * data.height

    valleys, valley_properties = find_peaks(y_inverted, height=valley_depth_threshold, distance=data.distance)

    # 计算半谷宽 (对取反后的数据计算半峰宽，rel_height 0.5 依然有效)
    valley_widths_results = peak_widths(y_inverted, valleys, rel_height=0.5)

    # 计算谷深度 (即取反后峰的高度) 和 半谷宽 (x轴上的宽度)
    if 'peak_heights' in valley_properties and valley_properties['peak_heights'].size > 0:
        valley_depths = [round(h, round_num) for h in valley_properties['peak_heights'].tolist()]
    else:
        valley_depths = []
    valley_widths_at_half = [round(i, round_num) for i in valley_widths_results[0].tolist()]

    if round_num:
        valley_y = [round(i, round_num) for i in y_smooth[valleys].tolist()] # 谷的y值是原始平滑后的y值
        smoothed_y = [round(i, round_num) for i in y_smooth.tolist()]  # 如果需要可返回
        differentiated_y = [round(i, round_num) for i in np.gradient(y_smooth).tolist()]  # 如果需要可返回
    else:
        valley_y = y_smooth[valleys].tolist()
        smoothed_y = y_smooth.tolist()
        differentiated_y = np.gradient(y_smooth).tolist()

    return {
        "code": 0,
        "message": "Success",

        # 谷数据
        "valley_indices": valleys.tolist(),
        "valley_x": x[valleys].tolist(),
        "valley_y": valley_y,
        "num_valleys": len(valleys),
        "valley_depths": valley_depths,
        "valley_widths": valley_widths_at_half,

        "smoothed_y": smoothed_y,
        "differentiated_y": differentiated_y
    }