
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
    polyorder: Optional[int] = Field(..., description='系数')

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