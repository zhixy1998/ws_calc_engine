"""
同时寻峰寻谷测试
"""

import pytest
from exceptions.error import ErrorCode
BASE_URL = '/get_peaks_and_valleys'

@pytest.mark.asyncio
async def test_get_peaks_and_valleys(async_client):
    # 使用混合数据：既有明显的峰，也有明显的谷
    x_data = [0,   1,   2,   3,   4,   5,   6,   7,   8,   9]
    y_data = [1.0, 0.2, 2.5, 0.5, 3.0, 0.3, 2.3, 0.7, 2.8, 1.0]
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        'peak_height': 0.3,  # 峰的阈值
        'valley_height': 0.3,  # 谷的阈值
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    
    # 返回结果结构性测试
    print("peaks and valleys data========", data)
    
    # 基本结构验证
    assert data['code'] == 0
    assert 'peak_x' in data
    assert 'peak_y' in data
    assert 'peak_indices' in data
    assert 'peak_areas' in data
    assert 'peak_widths' in data
    assert 'num_peaks' in data
    
    assert 'valley_x' in data
    assert 'valley_y' in data
    assert 'valley_indices' in data
    assert 'valley_depths' in data
    assert 'valley_widths' in data
    assert 'num_valleys' in data
    
    assert 'smoothed_y' in data
    assert 'differentiated_y' in data
    
    # 数据一致性验证
    assert len(data['peak_x']) == len(data['peak_y']) == len(data['peak_indices']) == len(data['peak_areas']) == len(data['peak_widths']) == data['num_peaks']
    assert len(data['valley_x']) == len(data['valley_y']) == len(data['valley_indices']) == len(data['valley_depths']) == len(data['valley_widths']) == data['num_valleys']
    assert len(data['smoothed_y']) == len(y_data)
    assert len(data['differentiated_y']) == len(y_data)
    
    # 应该至少找到一些峰和谷
    assert data['num_peaks'] >= 1
    assert data['num_valleys'] >= 1

# 测试只设置峰阈值的情况
@pytest.mark.asyncio
async def test_peak_height_only(async_client):
    x_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    y_data = [1.0, 0.2, 2.5, 0.5, 3.0, 0.3, 2.3, 0.7, 2.8, 1.0]
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        'peak_height': 0.5,  # 只设置峰阈值
        # valley_height 不设置
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    
    assert data['code'] == 0
    # 峰应该被过滤
    assert isinstance(data['num_peaks'], int)
    # 谷不应该被过滤（找到所有谷）
    assert data['num_valleys'] >= 0

# 测试只设置谷阈值的情况
@pytest.mark.asyncio
async def test_valley_height_only(async_client):
    x_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    y_data = [1.0, 0.2, 2.5, 0.5, 3.0, 0.3, 2.3, 0.7, 2.8, 1.0]
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        # peak_height 不设置
        'valley_height': 0.5,  # 只设置谷阈值
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    
    assert data['code'] == 0
    # 峰不应该被过滤（找到所有峰）
    assert data['num_peaks'] >= 0
    # 谷应该被过滤
    assert isinstance(data['num_valleys'], int)

# 测试平滑功能
@pytest.mark.asyncio
async def test_smooth_feature(async_client):
    x_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    y_data = [1.0, 0.2, 2.5, 0.5, 3.0, 0.3, 2.3, 0.7, 2.8, 1.0]
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        'peak_height': 0.3,
        'valley_height': 0.3,
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

# 测试不同阈值对峰谷检测的影响
@pytest.mark.asyncio
async def test_different_thresholds(async_client):
    x_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    y_data = [1.0, 0.2, 2.5, 0.5, 3.0, 0.3, 2.3, 0.7, 2.8, 1.0]
    
    # 测试较低的阈值
    post_json_low = {
        'x_data': x_data,
        'y_data': y_data,
        'peak_height': 0.2,
        'valley_height': 0.2,
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response_low = await async_client.post(BASE_URL, json=post_json_low)
    data_low = response_low.json()
    
    # 测试较高的阈值
    post_json_high = {
        'x_data': x_data,
        'y_data': y_data,
        'peak_height': 0.8,
        'valley_height': 0.8,
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response_high = await async_client.post(BASE_URL, json=post_json_high)
    data_high = response_high.json()
    
    # 验证阈值的影响：高阈值应该找到更少或相等的峰谷
    assert data_high['num_peaks'] <= data_low['num_peaks']
    assert data_high['num_valleys'] <= data_low['num_valleys']

# 测试distance参数的影响
@pytest.mark.asyncio
async def test_distance_parameter(async_client):
    x_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    y_data = [1.0, 0.2, 2.5, 0.5, 3.0, 0.3, 2.3, 0.7, 2.8, 1.0]
    
    # 测试较短的距离阈值
    post_json_short = {
        'x_data': x_data,
        'y_data': y_data,
        'peak_height': 0.2,
        'valley_height': 0.2,
        'distance': 1,  # 短距离
        'smooth': 0,
        'round': 3
    }
    response_short = await async_client.post(BASE_URL, json=post_json_short)
    data_short = response_short.json()
    
    # 测试较长的距离阈值
    post_json_long = {
        'x_data': x_data,
        'y_data': y_data,
        'peak_height': 0.2,
        'valley_height': 0.2,
        'distance': 4,  # 长距离
        'smooth': 0,
        'round': 3
    }
    response_long = await async_client.post(BASE_URL, json=post_json_long)
    data_long = response_long.json()
    
    # 验证距离参数的影响：长距离应该找到更少或相等的峰谷
    assert data_long['num_peaks'] <= data_short['num_peaks']
    assert data_long['num_valleys'] <= data_short['num_valleys']

# 测试错误处理：x_data和y_data长度不匹配
@pytest.mark.asyncio
async def test_x_y_length_mismatch(async_client):
    x_data = [0, 1, 2, 3, 4]  # 长度为5
    y_data = [1.0, 0.2, 2.5, 0.5]  # 长度为4，不匹配
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        'peak_height': 0.3,
        'valley_height': 0.3,
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    
    # 验证错误处理
    assert data['code'] == ErrorCode.X_Y_LENGTH_MISMATCH.value.code

# 测试错误处理：peak_height超出范围
@pytest.mark.asyncio
async def test_peak_height_out_of_range(async_client):
    x_data = [0, 1, 2, 3, 4]
    y_data = [1.0, 0.2, 2.5, 0.5, 3.0]
    
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        'peak_height': 1.5,  # 超出范围
        'valley_height': 0.3,
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    
    # 验证错误处理
    assert data['code'] == ErrorCode.HEIGHT_MUST_BE_BETWEEN_0_AND_1.value.code

# 测试错误处理：valley_height超出范围
@pytest.mark.asyncio
async def test_valley_height_out_of_range(async_client):
    x_data = [0, 1, 2, 3, 4]
    y_data = [1.0, 0.2, 2.5, 0.5, 3.0]
    
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        'peak_height': 0.3,
        'valley_height': -0.1,  # 超出范围
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    
    # 验证错误处理
    assert data['code'] == ErrorCode.HEIGHT_MUST_BE_BETWEEN_0_AND_1.value.code

# 测试无阈值参数的情况
@pytest.mark.asyncio
async def test_no_height_parameters(async_client):
    x_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    y_data = [1.0, 0.2, 2.5, 0.5, 3.0, 0.3, 2.3, 0.7, 2.8, 1.0]
    post_json = {
        'x_data': x_data,
        'y_data': y_data,
        # 不设置peak_height和valley_height参数
        'distance': 2,
        'smooth': 0,
        'round': 3
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    
    # 验证结果：没有height过滤时应该能找到所有峰谷
    assert data['code'] == 0
    assert data['num_peaks'] >= 0
    assert data['num_valleys'] >= 0
