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
    "independent_variable_string": "体积,重量,稀释倍数",
    "independent_variable_value": "2.0,3,1.5"
    }

    response = await async_client.post(BASE_URL,  json=post_json)
    data = response.json()
    # print('data:', data)
    assert data['code'] == 0
    assert data['result'] == 1.45


@pytest.mark.asyncio
async def test_algebraic_operations_keeps_letter_digit_variable(async_client):
    post_json = {
        "formula_string": "A+C1",
        "independent_variable_string": "A,C1",
        "independent_variable_value": "1.9427,1.0000"
    }

    response = await async_client.post(BASE_URL, json=post_json)
    data = response.json()

    assert data['code'] == 200
    assert data['result'] == 2.9427
