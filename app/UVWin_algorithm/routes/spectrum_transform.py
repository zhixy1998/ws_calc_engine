from fastapi import APIRouter
from typing import List
from pydantic import BaseModel, Field
import numpy as np

from exceptions.error import ErrorCode
from exceptions.command_exception import APIException

router = APIRouter()

class SpectrumTransformRequest(BaseModel):
    y_data: List[float] = Field(..., description="谱图的 y 值")
    transform_type: int = Field(..., description="变换类型：0=Abs->T%，1=T%->Abs，2=Abs->R%，3=R%->Abs，4=log10，5=倒数", example=0)

class SpectrumTransformResponse(BaseModel):
    code: int
    message: str
    result_y: List[float]

"""
| 类型编号 | 转换       | 数学公式                    | 代码实现是否正确  |
| ----    | --------   | -------------------------- | --------- |
| 0       | Abs → T%   | $T = 10^{-Abs} \times 100$ | ✅ 正确      |
| 1       | T% → Abs   | $Abs = -\log_{10}(T/100)$  | ✅ 正确，且有检查 |
| 2       | Abs → R%   | 同上                       | ✅ 正确      |
| 3       | R% → Abs   | 同上                       | ✅ 正确，且有检查 |
| 4       | log10      | $\log_{10}(y)$             | ✅ 正确，且有检查 |
| 5       | 倒数       | $1 / y$                    | ✅ 正确，且有检查 |

"""

@router.post("/spectrum_transform", response_model=SpectrumTransformResponse)
async def spectrum_transform(data: SpectrumTransformRequest):
    try:
        y = np.array([float(val) for val in data.y_data])
        if data.transform_type == 0:
            result_y = (10 ** (-y)) * 100
        elif data.transform_type == 1:
            if np.any(y <= 0):
                raise APIException(ErrorCode.INVALID_ARGUMENT, "T%必须大于0")
            result_y = -np.log10(y / 100)
        elif data.transform_type == 2:
            result_y = (10 ** (-y)) * 100
        elif data.transform_type == 3:
            if np.any(y <= 0):
                raise APIException(ErrorCode.INVALID_ARGUMENT, "R%必须大于0")
            result_y = -np.log10(y / 100)
        elif data.transform_type == 4:
            if np.any(y <= 0):
                raise APIException(ErrorCode.INVALID_ARGUMENT, "log10 输入必须大于0")
            result_y = np.log10(y)
        elif data.transform_type == 5:
            if np.any(y == 0):
                raise APIException(ErrorCode.INVALID_ARGUMENT, "不能对0取倒数")
            result_y = 1 / y
        else:
            raise APIException(ErrorCode.INVALID_ARGUMENT)
    except APIException:
        raise
    except Exception as e:
        raise APIException(ErrorCode.OPERATION_FAILED, str(e))

    return SpectrumTransformResponse(
        code=0,
        message="Success",
        result_y=[round(i, 4) for i in result_y.tolist()]
    )
