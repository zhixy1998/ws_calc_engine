"""
谱图的四则运算
"""
from fastapi import APIRouter
from typing import List
from pydantic import BaseModel, Field

from exceptions.error import ErrorCode
from exceptions.command_exception import APIException

router = APIRouter()

class SpectrumMathRequest(BaseModel):
    x_data: List[float] = Field(..., description="x 轴数据，两个谱图必须一致")
    y1_data: List[float] = Field(..., description="第一个谱图的 y 值")
    y2_data: List[float] = Field(..., description="第二个谱图的 y 值")
    operation: int = Field(..., description="运算类型：0=加法，1=减法，2=乘法，3=除法", json_schema_extra={"example": 0})

class SpectrumMathResponse(BaseModel):
    code: int
    message: str
    x_data: List[float]
    result_y: List[float]

@router.post("/spectrum_math", response_model=SpectrumMathResponse)
def spectrum_math(data: SpectrumMathRequest):
    if len(data.x_data) != len(data.y1_data) or len(data.y1_data) != len(data.y2_data):
        raise APIException(ErrorCode.X_Y_LENGTH_MISMATCH)

    try:
        if data.operation == 0:
            result_y = [a + b for a, b in zip(data.y1_data, data.y2_data)]
        elif data.operation == 1:
            result_y = [a - b for a, b in zip(data.y1_data, data.y2_data)]
        elif data.operation == 2:
            result_y = [a * b for a, b in zip(data.y1_data, data.y2_data)]
        elif data.operation == 3:
            result_y = [a / b if b != 0 else 0 for a, b in zip(data.y1_data, data.y2_data)]
        else:
            raise APIException(ErrorCode.INVALID_ARGUMENT)
    except APIException:
        raise  # 保留自定义异常，原样抛出
    except Exception as e:
        raise APIException(ErrorCode.OPERATION_FAILED)

    return SpectrumMathResponse(
        code=0,
        message="Success",
        x_data=data.x_data,
        result_y=result_y
    )