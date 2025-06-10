"""
测试：
吸光率和浓度计算
"""

import pytest
BASE_URL = '/calculate_concentration_or_abs'

@pytest.mark.asyncio
async def test_calculate_concentration_or_abs(async_client):
    """
    abs = f(x) * c
    f(x): 最小二次拟合
    abs: 吸光度
    c: 浓度
    """
    # 输入浓度求吸光度
    post_json = {
    "coeffs": [0,2,3,1,2],
    "value": 10,
    "mode": 1  # 浓度求吸光度
    }
    response = await async_client.post(BASE_URL,  json=post_json)
    data = response.json()
    assert data['code'] == 0
    assert data['value'] == 21320

    # 输入吸光度求浓度

    post_json = {
    "coeffs": [0,2,3,1,2],
    "value": 10,
    "mode": 0  # 吸光率求浓度
    }
    response = await async_client.post(BASE_URL,  json=post_json)
    data = response.json()
    assert data['code'] == 0
    assert data['value'] == 1.0961
