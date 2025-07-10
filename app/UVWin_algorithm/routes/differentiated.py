
from typing import List, Optional

import numpy as np
from simpleeval import simple_eval
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from scipy.signal import find_peaks, peak_widths, savgol_filter

from exceptions.error import ErrorCode
from exceptions.command_exception import APIException


router = APIRouter()

class InputSchema(BaseModel):
    y_data: List[float] = Field(..., description='y值')
    round_num: int = Field(4, description='小数点后几位')
    window_length: Optional[int] = Field(..., description='点数')
    polyorder: Optional[int] = Field(..., description='系数')
    deriv: Optional[int] = Field(1, description='微分次数（1 表示一阶导，2 表示二阶导）默认值1')

class OutPutSchemaData(BaseModel):
    differentiated_y: Optional[List[float]] = Field(None, description="微分后的Y值")


class OutPutSchema(BaseModel):
    code: int = Field(..., description="状态码")
    message: Optional[str] = Field(..., description="消息")
    data: OutPutSchemaData = Field(..., description='返回数据')
    


@router.post('', response_model=OutPutSchema)
def smoothed_differentiated(data: InputSchema):
    y = data.y_data
    round_num = data.round_num

    differentiated_y = savgol_filter(y, window_length=data.window_length, polyorder=data.polyorder, deriv=data.deriv)  # window=5, polyorder=3
    return {
        'code': 200,
        'message': 'success',
        'data': {
            "differentiated_y": [round(i, round_num) for i in differentiated_y.tolist()] # 基于平滑后的数据进行微分
        }
    }