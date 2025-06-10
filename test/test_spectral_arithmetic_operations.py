"""
谱图的四则运算
"""
import math

import pytest


BASE_URL = '/spectral_arithmetic_operations'

@pytest.mark.asyncio
async def test_spectral_arithmetic_operations(async_client):
    # 0=加法，1=减法，2=乘法，3=除法
    # 加法
    post_json = {
        'x_data': [1,2,3,4,5,6],
        'y1_data': [2,4,6,8,10,12],
        'y2_data': [3,4,5,6,7,8],
        'operation': 0
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    print(data)
    assert data['code'] == 0
    assert data['x_data'] == [1,2,3,4,5,6]
    assert data['y_data'] == [5,8,11,14,17,20]

    # 减法
    post_json = {
        'x_data': [1,2,3,4,5,6],
        'y1_data': [2,4,6,8,10,12],
        'y2_data': [3,4,5,6,7,8],
        'operation': 1
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    assert data['code'] == 0
    assert data['y_data'] == [-1, 0, 1, 2, 3, 4]

    # 乘法
    post_json = {
        'x_data': [1,2,3,4,5,6],
        'y1_data':  [2,4,6,8,10,12],
        'y2_data': [3,4,5,6,7,8],
        'operation': 2
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    assert data['code'] == 0
    assert data['y_data'] == [6, 16, 30, 48, 70, 96]

    # 除法
    post_json = {
        'x_data': [1,2,3,4,5,6],
        'y1_data':  [2,4,6,8,10,12],
        'y2_data': [3,4,5,6,7,8],
        'operation': 3
    }
    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()
    assert data['code'] == 0
    for i, v in enumerate(data['y_data']):
        assert_v_list = [0.6666, 1, 1.2, 1.3333, 1.4285714, 1.5]
        assert math.isclose(v, assert_v_list[i], rel_tol=1e-4) is True

