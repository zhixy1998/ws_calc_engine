"""
最小二乘拟合
"""
import sys
import numpy as np
from fastapi import APIRouter
from typing import Optional, List
from pydantic import BaseModel, Field

from exceptions.error import ErrorCode
from exceptions.command_exception import APIException
from utils.utils_least_squares_fitting import fit_data

router = APIRouter()

class InputSchema(BaseModel):
    x_data: List[float] = Field(..., description="自变量数据，例如：1,2,3,4,5")
    y_data: List[float] = Field(..., description="因变量数据，例如：2,4,6,8,10")
    degree: int = Field(..., ge=1, le=4, description="拟合的多项式次数：1：一次拟合，2:二次拟合，3：三次拟合，4：四次拟合")
    force_zero: int = Field(0, description="是否强制过零点，0=否，1=是")

class OutPutSchema(BaseModel):
    code: int = Field(..., description="状态码")
    degree: int = Field(..., description="拟合的多项式次数")
    R: float = Field(..., description="R值 （标准差, 代表拟合准确率）")
    R2: float = Field(..., description="R2值 （决定系数, 代表拟合准确率）")
    k0: Optional[float] = Field(None, description="常数项")
    k1: Optional[float] = Field(None, description="一次项")
    k2: Optional[float] = Field(None, description="二次项")
    k3: Optional[float] = Field(None, description="三次项")
    k4: Optional[float] = Field(None, description="四次项")
    coefficients: Optional[List[float]] = Field(None, description="所有系数列表，顺序为 k0, k1, ..., kn")

@router.post("", response_model=OutPutSchema, response_model_exclude_none=True)
async def least_squares_fitting(
    data: InputSchema
):

    # 解析x和y数据
    try:
        x = np.array([float(val) for val in data.x_data])
        y = np.array([float(val) for val in data.y_data])
    except ValueError:
        raise APIException(ErrorCode.X_Y_MUST_NUM)

    # 检查数据长度是否匹配
    if len(x) != len(y):
        raise APIException(ErrorCode.X_Y_LENGTH_MISMATCH)

    # 进行拟合
    try:
        coefficients = fit_data(x, y, data.degree, data.force_zero)
    except Exception as e:
        raise APIException(ErrorCode.OPERATION_FAILED)

    # 输出拟合结果为JSON格式
    return {**coefficients, "code": 0}
