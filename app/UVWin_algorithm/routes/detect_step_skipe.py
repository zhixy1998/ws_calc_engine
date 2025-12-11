"""
消除台阶或者倒刺
"""
from fastapi import APIRouter
from typing import Optional, List
from pydantic import BaseModel, Field

from utils.utils_detect_step_skipes import process_step_removal, process_spike_removal, StepCorrectionCache

router = APIRouter()

# 全局缓存，用于跨批次处理台阶
step_cache = StepCorrectionCache()

class InputSchema(BaseModel):
    x_data: List[float] = Field(..., description="波长数据，例如：1,2,3,4,5（从高波长到低波长）")
    y_data: List[float] = Field(..., description="吸光度数据，例如：2,4,6,8,10")
    k: float = Field(3.0, description='门限倍数（仅用于倒刺检测）')
    process_type: int = Field(1, description="处理类型：1: 台阶, 2: 倒刺")
    change_lamp_wavelength: Optional[float] = Field(None, description="换灯波长（仅台阶处理时需要，换灯后第一个点的波长）")
    wavelength_end: Optional[float] = Field(None, description="本次测量的结束波长（最低波长），用于判断是否最后一批")
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
    print(f'debug 台阶和倒刺: process_type={data.process_type}, x={data.x_data}, y={data.y_data}')
    
    if data.process_type == 1:
        # 台阶处理：使用换灯波长定位
        result = process_step_removal(
            x_data=data.x_data,
            y_data=data.y_data,
            change_lamp_wavelength=data.change_lamp_wavelength - 1,
            wavelength_end=data.wavelength_end,
            cache=step_cache
        )
    elif data.process_type == 2:
        # 倒刺处理：使用原有逻辑
        result = process_spike_removal(
            x_data=data.x_data,
            y_data=data.y_data,
            k=data.k
        )
    else:
        result = {'code': 400, 'smoothed_data': data.y_data, 'message': '无效的处理类型'}
    
    return result




