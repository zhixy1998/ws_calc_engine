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
    change_lamp_wavelength: Optional[float] = Field(None, description="换灯波长（跳变前的点）")
    wavelength_end: Optional[float] = Field(None, description="本次测量的结束波长（最低波长），用于判断是否最后一批")
    change_filter_point_list: Optional[List[float]] = Field(None, description="换滤光片点列表（跳变前的点，按从长波长到低波长排序）")
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
        # 台阶处理：将换灯点与滤光片换片点合并为统一的跳变前点列表
        break_points = list(data.change_filter_point_list or [])
        if data.change_lamp_wavelength is not None:
            break_points.append(data.change_lamp_wavelength)
        # 按从高到低波长排序，去重
        break_points = sorted(set(break_points), reverse=True)
        # 消除台阶
        result = process_step_removal(
            x_data=data.x_data,
            y_data=data.y_data,
            break_points=break_points,
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




