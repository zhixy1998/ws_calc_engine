"""
消除台阶或者倒刺
"""
from fastapi import APIRouter
from typing import Optional, List
from pydantic import BaseModel, Field

from utils.utils_detect_step_skipes import fit_data

router = APIRouter()

class InputSchema(BaseModel):
    x_data: List[float] = Field(..., description="波长数据，例如：1,2,3,4,5")
    y_data: List[float] = Field(..., description="吸光度数据，例如：2,4,6,8,10")
    k: float = Field(..., description='门限倍数')
    # smoothing_method: Optional[str] = Field("gaussian", description="平滑方法：'moving_average', 'gaussian', 'median'")

class OutPutSchema(BaseModel):
    code: int = Field(..., description="状态码")
    smoothed_data: List[float] = Field(..., description="平滑后的数据")
    message: Optional[str] = Field(None, description="附加消息，成功或错误信息")
    plot_base64: Optional[str] = Field(None, description="对比图（base64 PNG）")

@router.post("", response_model=OutPutSchema, response_model_exclude_none=True)
async def process_data(
    data: InputSchema
):
    return fit_data(data.x_data, data.y_data, data.k)




