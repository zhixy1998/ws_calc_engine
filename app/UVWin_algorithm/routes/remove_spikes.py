
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

# 全局缓存，用于跨批次处理指定倒刺点
spike_cache = SpikeCorrectionCache()

@router.post('', response_model=OutSchema)
async def remove_spikes(data: InputSchema):
    # 【自动清空缓存机制】应对 Java 客户端中途断开连接的异常情况。
    # 正常的连续扫描批次中，波长永远是严格从高到低递减的。
    # 如果本次新批次的第一个 x_data >= 缓存中上一批次的末尾 x_data，
    # 说明 Java 重新开始了一次扫描，我们应当果断抛弃旧的脏缓存。
    if data.x_data:
        cached_tail_x = spike_cache.get_tail().get('x', [])
        if cached_tail_x and data.x_data[0] >= cached_tail_x[-1]:
            spike_cache.clear()

    result = process_targeted_spike_removal(
        x_data=data.x_data,
        y_data=data.y_data,
        spike_points=data.spinedot,
        wavelength_end=data.wavelength_end,
        cache=spike_cache,
    )
    return result