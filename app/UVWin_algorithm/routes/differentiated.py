
from typing import List, Optional

import numpy as np
from simpleeval import simple_eval
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from scipy.signal import find_peaks, peak_widths, savgol_filter

from utils.utils_data_format import get_max_decimal_places
from exceptions.error import ErrorCode
from exceptions.command_exception import APIException


router = APIRouter()

class InputSchema(BaseModel):
    y_data: List[float] = Field(..., description='y值')
    round_num: int = Field(None, description='小数点后几位')
    window_length: Optional[int] = Field(..., description='点数')
    polyorder: Optional[int] = Field(..., description="""系数 polyorder 是 Savitzky-Golay 滤波器（savgol_filter）中的一个参数，表示拟合多项式（polynomial）的阶数。具体来说：
作用：它决定了用于局部多项式拟合的多项式的最高次幂。
常见值：通常设置为 2 或 3，表示二次或三次多项式。
影响：
较低的值（如 1）会使拟合更简单，可能欠拟合数据。
较高的值（如 4 或更高）可能对噪声更敏感，导致过拟合。
必须小于 window_length（窗口长度）。""")
    deriv: Optional[int] = Field(1, description='微分次数（1 表示一阶导，2 表示二阶导）默认值1')

class OutPutSchemaData(BaseModel):
    differentiated_y: Optional[List[str]] = Field(None, description="微分后的Y值")


class OutPutSchema(BaseModel):
    code: int = Field(..., description="状态码")
    message: Optional[str] = Field(..., description="消息")
    data: OutPutSchemaData = Field(..., description='返回数据')
    


@router.post('', response_model=OutPutSchema)
def smoothed_differentiated(data: InputSchema):
    y = data.y_data

    # 自动检测输入数据的最大小数点位

    window_length = data.window_length
    polyorder = data.polyorder
    if window_length %2 != 1:
        raise APIException(ErrorCode.WINDOWS_MUST_ODD)
    if polyorder >= window_length:
        raise APIException(ErrorCode.POLYORDER_MUST_LESS_THEN_WINDOWS_LENGTH)

    differentiated_y = savgol_filter(y, window_length=data.window_length, polyorder=data.polyorder, deriv=data.deriv)  # window=5, polyorder=3

    decimal_places = get_max_decimal_places(y)

    differentiated_round = [f"{i:.{decimal_places}f}" for i in differentiated_y.tolist()]

    return {
        'code': 200,
        'message': 'success',
        'data': {
            "differentiated_y": differentiated_round
        }
    }

