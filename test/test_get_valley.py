"""
寻谷测试
"""

import pytest
from exceptions.error import ErrorCode
BASE_URL = '/get_valley'

@pytest.mark.asyncio
async def test_get_valley(async_client):
    # 使用与寻峰相反的数据模式：高-低-高，这样谷会更明显
    x_data = [0,   1,   2,   3,   4,   5,   6,   7,   8,   9]
    y_data = [3.0, 0.8, 2.5, 0.5, 2.7, 0.3, 2.3, 0.7, 2.8, 1.0]
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 0.3,  # 较低的阈值，能找到明显的谷
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    
    # 返回结果结构性测试
    print("valley data========", data)
    assert len(data['valley_x']) == len(data['valley_y']) == len(data['valley_indices']) == len(data['valley_depths']) == len(data['valley_widths'])
    
    # 返回结果正确性测试
    assert data['code'] == 0
    assert data['num_valleys'] >= 1  # 至少应该找到一个谷
    assert isinstance(data['valley_x'], list)
    assert isinstance(data['valley_y'], list)
    assert isinstance(data['valley_indices'], list)
    assert isinstance(data['valley_depths'], list)
    assert isinstance(data['valley_widths'], list)
    assert len(data['smoothed_y']) == len(y_data)
    assert len(data['differentiated_y']) == len(y_data)

# 测试平滑功能
@pytest.mark.asyncio
async def test_smooth_feature(async_client):
    x_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    y_data = [3.0, 0.8, 2.5, 0.5, 2.7, 0.3, 2.3, 0.7, 2.8, 1.0]
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 0.5,
        'distance': 2,
        'smooth': 1,  # 开启平滑
        'round': 3
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    
    # 验证平滑后的Y值（只进行结构性检查）
    assert len(data['smoothed_y']) == len(y_data)
    # 验证平滑后的Y值变化（简单检查值的平滑效果）
    assert data['smoothed_y'][0] != y_data[0] or data['smoothed_y'][2] != y_data[2]

# 此测试用例验证了不同的height参数对谷值检测的影响，确保height正确限制了检测的谷值深度。
@pytest.mark.asyncio
async def test_height_filter(async_client):
    x_data = [0,   1,   2,   3,   4,   5,   6,   7,   8,   9]
    y_data = [2.0, 0.8, 1.8, 0.2, 1.5, 0.1, 1.3, 0.5, 1.7, 0.9]
    
    # 测试较低的 height 阈值
    post_json_low = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 0.3,  # 较低阈值，应该能找到更多谷
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response_low = await async_client.post(BASE_URL, json=post_json_low)
    data_low = response_low.json()
    # 验证结果，期望找到多个谷
    low_count = data_low['num_valleys']
    assert low_count >= 1

    # 测试较高的 height 阈值
    post_json_high = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 0.8,  # 高阈值，应该找到更少的谷
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response_high = await async_client.post(BASE_URL, json=post_json_high)
    data_high = response_high.json()
    # 验证结果，期望找到更少的谷
    high_count = data_high['num_valleys']
    assert high_count <= low_count  # 高阈值找到的谷应该不多于低阈值

# 此测试用例验证了distance参数对谷值检测的影响，确保distance限制了两个谷之间的最小间距。
@pytest.mark.asyncio
async def test_distance_parameter(async_client):
    x_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    y_data = [2.0, 0.5, 1.8, 0.3, 1.5, 0.1, 1.3, 0.4, 1.7, 0.6]
    
    # 测试较短的距离阈值
    post_json_short = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 0.2,
        'distance': 1,  # 短距离，允许相邻的谷
        'smooth': 0,
        'round': 3
    }
    response_short = await async_client.post(BASE_URL, json=post_json_short)
    data_short = response_short.json()
    short_count = data_short['num_valleys']

    # 测试较长的距离阈值
    post_json_long = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 0.2,
        'distance': 4,  # 长距离，限制相邻谷
        'smooth': 0,
        'round': 3
    }
    response_long = await async_client.post(BASE_URL, json=post_json_long)
    data_long = response_long.json()
    long_count = data_long['num_valleys']
    
    # 验证距离参数的影响：长距离应该找到更少或相等的谷
    assert long_count <= short_count

# 此测试用例验证了当x_data和y_data长度不一致时，是否正确抛出APIException。
@pytest.mark.asyncio
async def test_x_y_length_mismatch(async_client):
    x_data = [0, 1, 2, 3, 4]  # 长度为5
    y_data = [2.0, 0.5, 1.8, 0.3]  # 长度为4，不匹配
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 0.5,
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    
    # 验证错误处理
    assert data['code'] == ErrorCode.X_Y_LENGTH_MISMATCH.value.code

# 此测试用例验证了height参数超出范围时的错误处理
@pytest.mark.asyncio
async def test_height_out_of_range(async_client):
    x_data = [0, 1, 2, 3, 4]
    y_data = [2.0, 0.5, 1.8, 0.3, 1.2]
    
    # 测试height > 1的情况
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 1.5,  # 超出范围
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    
    # 验证错误处理
    assert data['code'] == ErrorCode.HEIGHT_MUST_BE_BETWEEN_0_AND_1.value.code

# 测试无height参数的情况
@pytest.mark.asyncio
async def test_no_height_parameter(async_client):
    x_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    y_data = [2.0, 0.5, 1.8, 0.3, 1.5, 0.1, 1.3, 0.4, 1.7, 0.6]
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        # 不设置height参数
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    
    # 验证结果：没有height过滤时应该能找到所有谷
    assert data['code'] == 0
    assert data['num_valleys'] >= 0  # 至少不会出错