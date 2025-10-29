from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field
from scipy.signal import savgol_filter

from exceptions.error import ErrorCode
from exceptions.command_exception import APIException


router = APIRouter()

class InputSchema(BaseModel):
    y_data: List[float] = Field(..., description='y值')
    round_num: int = Field(4, description='小数点后几位')
    window_length: Optional[int] = Field(..., description='点数')
    polyorder: Optional[int] = Field(..., description="""系数 polyorder 是 Savitzky-Golay 滤波器（savgol_filter）中的一个参数，表示拟合多项式（polynomial）的阶数。具体来说：
作用：它决定了用于局部多项式拟合的多项式的最高次幂。
常见值：通常设置为 2 或 3，表示二次或三次多项式。
影响：
较低的值（如 1）会使拟合更简单，可能欠拟合数据。
较高的值（如 4 或更高）可能对噪声更敏感，导致过拟合。
必须小于 window_length（窗口长度）。""")

class OutPutSchemaData(BaseModel):
    smoothed_y: Optional[List[float]] = Field(None, description="平滑后的Y值")


class OutPutSchema(BaseModel):
    code: int = Field(..., description="状态码")
    message: Optional[str] = Field(..., description="消息")
    data: OutPutSchemaData = Field(..., description='返回数据')
    


@router.post('', response_model=OutPutSchema)
def smoothed_differentiated(data: InputSchema):
    y = data.y_data
    round_num = data.round_num
    y_smooth = savgol_filter(y, window_length=data.window_length, polyorder=data.polyorder)  # window=5, polyorder=3


    return {
        'code': 200,
        'message': 'success',
        'data': {
            "smoothed_y": [round(i, round_num) for i in y_smooth.tolist()]
        }
    }