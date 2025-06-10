"""
谱图变换
"""
import pytest

"""
这是 pytest-asyncio 提供的标记，它告诉 pytest：

“这个测试函数是 异步的，需要用 asyncio event loop 来运行。”
"""
@pytest.mark.asyncio
async def test_transform_abs_to_t(async_client):
    payload = {
        'y_data': [0.3, 0.5],
        'transform_type': 0 # Abs->T%
    }
    response = await async_client.post('/spectrum_transform', json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 0
    assert data['result_y'] == pytest.approx([50.1187, 31.6227], rel=1e-3)


@pytest.mark.asyncio
async def test_transform_invalid_type(async_client):
    payload = {
        'y_data': [0.3, 0.5],
        'transform_type': 999  # 非法类型
    }
    response = await async_client.post('/spectrum_transform', json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data['code'] != 0