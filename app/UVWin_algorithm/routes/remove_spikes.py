
"""
消除台阶或者倒刺
"""
import json
import os
from datetime import datetime
from fastapi import APIRouter
from typing import Optional, List
from pydantic import BaseModel, Field

from utils.utils_detect_step_skipes import process_targeted_spike_removal_v2, SpikeCorrectionCache

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
DEFAULT_SEARCH_RADIUS = 5.0
DEFAULT_SPIKE_K = 2.0

# JSON 调试日志文件路径
DEBUG_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'debug_logs')
_current_log_file: Optional[str] = None


def _create_new_log_file():
    """新扫描开始时创建新的 JSONL 文件（每行一次请求）"""
    global _current_log_file
    os.makedirs(DEBUG_LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    _current_log_file = os.path.join(DEBUG_LOG_DIR, f'spike_removal_{timestamp}.jsonl')
    open(_current_log_file, 'w').close()  # 创建空文件


def _append_to_log(
    x_data: List[float],
    y_data_input: List[float],
    y_data_output: List[float],
    spike_points: List[float],
    wavelength_end: float,
    is_new_scan: bool,
):
    """将本次请求作为单行 JSON 追加到当前日志文件"""
    global _current_log_file
    if _current_log_file is None:
        _create_new_log_file()
    entry = {
        "logged_at": datetime.now().isoformat(),
        "is_new_scan": is_new_scan,
        "spinedot": spike_points,
        "wavelength_end": wavelength_end,
        "x": x_data,
        "y_in": y_data_input,
        "y_out": y_data_output,
    }
    with open(_current_log_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')


@router.post('', response_model=OutSchema)
async def remove_spikes(data: InputSchema):
    global _current_log_file
    # 【自动清空缓存机制】应对 Java 客户端中途断开连接的异常情况。
    # 正常的连续扫描批次中，波长永远是严格从高到低递减的。
    # 如果本次新批次的第一个 x_data >= 缓存中上一批次的末尾 x_data，
    # 说明 Java 重新开始了一次扫描，我们应当果断抛弃旧的脏缓存。
    is_new_scan = False
    if data.x_data:
        cached_tail_x = spike_cache.get_tail().get('x', [])
        if cached_tail_x and data.x_data[0] >= cached_tail_x[-1]:
            spike_cache.clear()
            is_new_scan = True
        elif not cached_tail_x:
            is_new_scan = True

    if is_new_scan:
        _create_new_log_file()

    print('data.spinedot: ', data.spinedot)
    
    result = process_targeted_spike_removal_v2(
        x_data=data.x_data,
        y_data=data.y_data,
        spike_points=data.spinedot,
        wavelength_end=data.wavelength_end,
        cache=spike_cache,
        search_radius=DEFAULT_SEARCH_RADIUS,
        spike_k=DEFAULT_SPIKE_K,
    )

    _append_to_log(
        data.x_data,
        data.y_data,
        result.get('smoothed_data', []),
        data.spinedot,
        data.wavelength_end,
        is_new_scan,
    )

    return result