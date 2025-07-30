"""
寻峰测试
"""

import pytest
from exceptions.error import ErrorCode
BASE_URL = '/get_peak'

@pytest.mark.asyncio
async def test_get_peak(async_client):
    x_data = [0,   1,   2,   3,   4,   5,   6, 7,   8,   9]
    y_data = [0.1, 1.2, 0.5, 2.5, 0.3, 3, 0.7, 1.5, 0.2, 0]
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 0.9,
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response = await async_client.post(BASE_URL,  json=post_json)
    data = response.json()
    # 返回结果结构性测试
    print("data========", data)
    assert len(data['peak_x']) == len(data['peak_y']) == len(data['peak_indices']) == len(data['peak_areas']) == len(data['peak_widths'])
    # 返回结果正确性测试
    assert data['code'] == 0
    assert data['peak_x'] == [5]
    assert data['peak_y'] == [3]
    assert data['num_peaks'] == 1
    assert data['peak_indices'] == [5]
    assert data['peak_areas'] == [1.65]
    assert data['peak_widths'] == [1.167]
    assert data['smoothed_y'] == [0.1,1.2,0.5,2.5,0.3,3,0.7,1.5,0.2,0]
    assert data['differentiated_y'] == [1.1,0.2,0.65,-0.1,0.25,0.2,-0.75,-0.25,-0.75,-0.2]

# 测试平滑
@pytest.mark.asyncio
async def test_smooth_feature(async_client):
    x_data = [0,1,2,3,4,5,6,7,8,9]
    y_data = [0.1, 0.8, 0.2, 1.1, 0.3, 3.0, 0.7, 1.5, 0.2, 0.0]
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 1,
        'distance': 2,
        'smooth': 1,  # 开启平滑
        'round': 3
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    
    # 验证平滑后的Y值（只进行结构性检查）
    assert len(data['smoothed_y']) == len(y_data)
    # 验证平滑后的Y值变化（简单检查值的平滑效果）
    assert data['smoothed_y'][0] != y_data[0]
    assert data['smoothed_y'][2] != y_data[2]

# 此测试用例验证了不同的height参数对峰值检测的影响，确保height正确限制了检测的峰值高度。
@pytest.mark.asyncio
async def test_height_filter(async_client):
    x_data = [0,     1,    2,   3,   4,    5,   6,   7,   8, 9]
    y_data = [0.1, 0.8,  0.2, 1.1, 0.3,  1.8, 0.7, 1.5, 0.2, 0.0]
    
    # 测试较低的 height 阈值
    post_json_low = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 0.6,
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response_low = await async_client.post(BASE_URL, json=post_json_low)
    data_low = response_low.json()
    # 验证结果，期望峰值发生变化
    assert data_low['num_peaks'] == 2  # 可能找到更多的峰

    # 测试较高的 height 阈值
    post_json_high = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 0.9,  # 高度过滤阈值设置为0.8
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response_high = await async_client.post(BASE_URL, json=post_json_high)
    data_high = response_high.json()
    # 验证结果，期望只有1个峰
    assert data_high['num_peaks'] == 0

# 此测试用例验证了distance参数对峰值检测的影响，确保distance限制了两个峰之间的最小间距。
@pytest.mark.asyncio
async def test_distance_parameter(async_client):
    x_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    y_data = [0.1, 1.2, 2.5, 0.5, 0.3, 3.0, 0.7, 1.5, 0.2, 0.0]
    
    # 测试较短的距离阈值
    post_json_short = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 0.5, # 百分比
        'distance': 1,  # 两个峰之间的最小间距为1
        'smooth': 0,
        'round': 3
    }
    response_short = await async_client.post(BASE_URL, json=post_json_short)
    data_short = response_short.json()
    assert data_short['num_peaks'] == 3  # 可能检测到更多的峰

    # 测试较长的距离阈值
    post_json_long = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 0.5,
        'distance': 3,  # 两个峰之间的最小间距为3
        'smooth': 0,
        'round': 3
    }
    response_long = await async_client.post(BASE_URL, json=post_json_long)
    data_long = response_long.json()
    assert data_long['num_peaks'] == 2  # 可能只检测到1个峰

# 此测试用例验证了当x_data和y_data长度不一致时，是否正确抛出APIException。
@pytest.mark.asyncio
async def test_x_y_length_mismatch(async_client):
    x_data = [0, 1, 2, 3, 4]
    y_data = [0.1, 0.8, 0.5, 1.1]  # y_data 少了一个元素
    
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        'height': 1,
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    
    # 应该抛出 X_Y_LENGTH_MISMATCH 异常
    response = await async_client.post(BASE_URL, json=post_json)
    assert response.status_code == 200  # 预期返回400错误
    assert response.json()['code'] == ErrorCode.X_Y_LENGTH_MISMATCH.value.code