from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field
from scipy.signal import savgol_filter, medfilt

from utils.utils_data_format import get_max_decimal_places
from exceptions.error import Error, ErrorCode
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
    # strength_level: int = Field(...)

class OutPutSchemaData(BaseModel):
    smoothed_y: Optional[List[str]] = Field(None, description="平滑后的Y值")


class OutPutSchema(BaseModel):
    code: int = Field(..., description="状态码")
    message: Optional[str] = Field(..., description="消息")
    data: OutPutSchemaData = Field(..., description='返回数据')
    


@router.post('', response_model=OutPutSchema)
def smoothed_differentiated(data: InputSchema):
    y = data.y_data
    round_num = data.round_num
    window_length = data.window_length
    polyorder = data.polyorder
    if window_length %2 != 1:
        raise APIException(ErrorCode.WINDOWS_MUST_ODD)
    if polyorder >= window_length:
        raise APIException(ErrorCode.POLYORDER_MUST_LESS_THEN_WINDOWS_LENGTH)

    y_smooth = savgol_filter(y, window_length=window_length, polyorder=polyorder)  # window=5, polyorder=3

    decimal_places = get_max_decimal_places(y)

    smoothed_y_formatted = [f"{i:.{decimal_places}f}" for i in y_smooth.tolist()]
    return {
        'code': 200,
        'message': 'success',
        'data': {
            "smoothed_y": smoothed_y_formatted
        }
    }


def despike_spectroscopy(y_in, strength_level):
    """
    使用“中位数滤波”去除光谱尖刺 (如宇宙射线)
    
    :param y_in: 原始光谱 y 轴数据 (numpy array)
    :param strength_level: “力度” (e.g., 1, 2, 3...)
                         将被映射为窗口大小 (3, 5, 7...)
    :return: 去除尖刺后的 y 轴数据 (numpy array)
    """
    
    # 将“力度”映射为奇数的窗口大小
    # 比如 力度 1 -> 窗口 3; 力度 2 -> 窗口 5
    window_size = (strength_level * 2) + 1
    
    if window_size < 3:
        window_size = 3 # 最小窗口必须为 3
        
    print(f"中位数滤波: 力度 {strength_level} -> 窗口大小 {window_size}")
    
    # kernel_size 就是窗口大小
    y_out = medfilt(y_in, kernel_size=window_size)
    return y_out