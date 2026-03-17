
"""
消除台阶或者倒刺
"""
from fastapi import APIRouter
from typing import Optional, List
from pydantic import BaseModel, Field

from utils.utils_detect_step_skipes import process_targeted_spike_removal, SpikeCorrectionCache

router = APIRouter()

class InputSchema(BaseModel):
    x_data: List[float] = Field(..., description='x值列表')
    y_data: List[float] = Field(..., description='y值列表')
    spinedot: List[float] = Field(..., description='刺列表')
    wavelength_end: float = Field(..., description='结束点')

class OutSchema(BaseModel):
    code: int = Field(..., description='状态码')
    smoothed_data: List[float] = Field(..., description="平滑后的数据")
    message: Optional[str] = Field(None, description="附加消息，成功或错误信息")


@router.post('/', response_model=OutSchema)
async def remove_spikes(data: InputSchema):
    cache = SpikeCorrectionCache()
    result = process_targeted_spike_removal(
        x_data=data.x_data,
        y_data=data.y_data,
        spike_points=data.spinedot,
        wavelength_end=data.wavelength_end,
        cache=cache,
    )
    return result