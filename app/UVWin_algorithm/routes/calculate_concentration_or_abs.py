
"""
吸光率和浓度计算
"""
import numpy as np
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from fastapi import APIRouter, Query
from utils.utils_calculate_concentration_or_abs import fit_data
from exceptions.command_exception import APIException
from exceptions.error import ErrorCode

router = APIRouter()

class InputSchema(BaseModel):
    coeffs: List[float] = Field(..., description='拟合模型，k0-k4, 传递数组 比如[0,2,3,1,2], 分别对应[k0,k1,k2,k3,k4]')
    value: float = Field(..., description='吸光度或者浓度的值')
    mode: int = Field(..., description='0: 吸光度求浓度 1: 浓度求吸光度')

class OutPutSchema(BaseModel):
    code: int
    value: float

@router.post("", response_model=OutPutSchema)
def calculate_concentration_or_abs(
    input_data: InputSchema,
):
    """
    abs = f(x) * c
    f(x): 最小二次拟合
    abs: 吸光度
    c: 浓度
    """
    if input_data.mode not in (0, 1):
        raise APIException(ErrorCode.INVALID_MODE)
    return OutPutSchema(code=200, value=fit_data(input_data.coeffs, input_data.value, input_data.mode))
  