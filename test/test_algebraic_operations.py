"""
测试代数运算，用户自定义运算
"""


import pytest
from exceptions.error import ErrorCode
BASE_URL = '/algebraic_operations'

@pytest.mark.asyncio
async def test_algebraic_operations(async_client):
    post_json = {
    "formula_string": "(体积+0.9)/重量*稀释倍数",
    "independent_ariable_string": "体积,重量,稀释倍数",
    "independent_ariable_value": "2.0,3,1.5"
    }

    response = await async_client.post(BASE_URL,  json=post_json)
    data = response.json()
    assert data['code'] == 0
    assert data['result'] == 1.45
