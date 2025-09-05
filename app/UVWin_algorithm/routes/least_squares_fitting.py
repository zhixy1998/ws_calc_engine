"""
最小二乘拟合
"""
import sys
import numpy as np
import json
from fastapi import APIRouter
from typing import Optional, List
from pydantic import BaseModel, Field

from exceptions.error import ErrorCode
from exceptions.command_exception import APIException
from utils.utils_least_squares_fitting import fit_data

def clean_nan_values(obj):
    """递归处理数据中的 NaN 和 Infinity 值，将其转换为 None"""
    if isinstance(obj, dict):
        return {k: clean_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_values(item) for item in obj]
    elif isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    else:
        return obj

def validate_json_serializable(data):
    """检查数据是否可以JSON序列化"""
    try:
        # 使用 allow_nan=False 来禁止 inf 和 nan 值
        json.dumps(data, allow_nan=False)
        return True
    except (ValueError, TypeError):
        return False


router = APIRouter()

class InputSchema(BaseModel):
    x_data: List[float] = Field(..., description="自变量数据，例如：1,2,3,4,5")
    y_data: List[float] = Field(..., description="因变量数据，例如：2,4,6,8,10")
    degree: int = Field(..., ge=1, le=4, description="拟合的多项式次数：1：一次拟合，2:二次拟合，3：三次拟合，4：四次拟合")
    force_zero: int = Field(0, description="是否强制过零点，0=否，1=是")

class OutPutSchema(BaseModel):
    code: int = Field(..., description="状态码")
    degree: int = Field(..., description="拟合的多项式次数")
    R: Optional[float] = Field(None, description="R值 （标准差, 代表拟合准确率）")
    R2: Optional[float] = Field(None, description="R2值 （决定系数, 代表拟合准确率）")
    k0: Optional[float] = Field(None, description="常数项")
    k1: Optional[float] = Field(None, description="一次项")
    k2: Optional[float] = Field(None, description="二次项")
    k3: Optional[float] = Field(None, description="三次项")
    k4: Optional[float] = Field(None, description="四次项")
    coefficients: Optional[List[float]] = Field(None, description="所有系数列表，顺序为 k0, k1, ..., kn")
    equation: Optional[str] = Field(
        None, description="拟合公式字符串，例如 y = 2.3x² + 1.2x + 4.5"
    )
    image_base64: Optional[str] = Field(
        None, description="拟合图像（Base64 编码，可用于前端显示）"
    )
    standard_error: Optional[float] = Field(
        None, description="预测标准误差（S），表示拟合值对实际值的偏离程度"
    )
    confidence_95: Optional[List[List[float]]] = Field(
        None, description="95%置信区间（L），表示系数的统计置信区间"
    )
    r2_0: Optional[float] = Field(
        None, description="相关系数（r2_0），用于强调 Pearson 相关性"
    )
    r2_M: Optional[float] = Field(
        None, description="多变量相关系数（r2_M），与R2相同但强调多项式场景"
    )
    rmse: Optional[float] = Field(
        None, description="评估标准误差（D），与 standard_error 等价"
    )
    residual_std: Optional[float] = Field(
        None, description="残差标准偏差（R），表示残差的离散程度"
    )
    chi_squared: Optional[float] = Field(
        None, description="卡方（C），拟合优度检验统计值，越小越好"
    )


@router.post("", response_model=OutPutSchema, response_model_exclude_none=True)
def least_squares_fitting(
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

    # 先清理 NaN 值，然后检查结果是否可以JSON序列化
    result = {**coefficients, "code": 200}
    cleaned_result = clean_nan_values(result)
    
    # if not validate_json_serializable(cleaned_result):
    #     raise APIException(ErrorCode.IMPOSSIBLE_FITTING)

    
    # 输出拟合结果为JSON格式
    return cleaned_result
