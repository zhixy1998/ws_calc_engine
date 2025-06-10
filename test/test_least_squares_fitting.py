"""
最小二乘拟合
"""
import pytest

# URL = "http://127.0.0.1:8000/least_squares_fitting?x_data=1,2,3,4,5&y_data=2,4,6,8,10&degree=1&force_zero=0"
BASE_URL = "/least_squares_fitting"

# # 请求次数和间隔（毫秒）
# TOTAL_REQUESTS = 50
# INTERVAL_MS = 2

# # 请求处理函数
# async def send_request(client, index, results):
#     start = time.time()
#     try:
#         response = await client.get(URL)
#         duration = (time.time() - start) * 1000
#         results[index] = duration
#         print(f"[{index+1:02d}] 状态码: {response.status_code}, 用时: {duration:.2f} ms")
#     except Exception as e:
#         results[index] = -1
#         print(f"[{index+1:02d}] 请求失败: {e}")

# # 主函数
# async def main():
#     async with httpx.AsyncClient() as client:
#         tasks = []
#         results = [0] * TOTAL_REQUESTS

#         for i in range(TOTAL_REQUESTS):
#             task = asyncio.create_task(send_request(client, i, results))
#             tasks.append(task)
#             await asyncio.sleep(INTERVAL_MS / 1000.0)  # 每次间隔 2ms 发一个请求

#         await asyncio.gather(*tasks)

#         total_time = sum(r for r in results if r >= 0)
#         avg_time = total_time / len([r for r in results if r >= 0])
#         print(f"\n🔥 请求总数: {TOTAL_REQUESTS}")
#         print(f"✅ 成功数: {len([r for r in results if r >= 0])}")
#         print(f"⏱️ 平均响应时间: {avg_time:.2f} ms")
#         print(f"⏱️ 总响应时间:{total_time:.2f} ms")


# 测试用例
test_cases = [
    {
        "desc": "一次拟合 - 不强制过零点",
        "params": {"x_data": "1,2,3,4,5", "y_data": "2,4,6,8,10", "degree": 1, "force_zero": 0},
        "expected": {"degree": 1, "R2": 1.0, "R": 1.0, "coefficients": [0.0, 2.0], "k0": 0.0, "k1": 2.0}
    },
    {
        "desc": "一次拟合 - 强制过零点",
        "params": {"x_data": "1,2,3,4,5", "y_data": "2,4,6,8,10", "degree": 1, "force_zero": 1},
        "expected": {"degree": 1, "k1": 2.0, "k0": 0.0, "R2": 1.0, "R": 1.0, "coefficients": [0.0, 2.0]}
    },
    {
        "desc": "二次拟合 - 不强制过零点",
        "params": {"x_data": "1,2,3,4,5", "y_data": "3,7,13,21,31", "degree": 2, "force_zero": 0},
        "expected": {"degree": 2, "R2": 1.0, "R": 1.0, "coefficients": [1.0, 1.0, 1.0], "k0": 1.0, "k1": 1.0, "k2": 1.0}
    },
    {
        "desc": "二次拟合 - 强制过零点",
        "params": {"x_data": "1,2,3,4,5", "y_data": "3,7,13,21,31", "degree": 2, "force_zero": 1},
        "expected": {"degree": 2, "R2": 1.0, "R": 1.0, "coefficients": [1.0, 1.0, 1.0], "k0": 1.0, "k1": 1.0, "k2": 1.0}
    },
    {
        "desc": "三次拟合 - 不强制过零点",
        "params": {"x_data": "1,2,3,4", "y_data": "6,24,60,120", "degree": 3, "force_zero": 0},
        "expected": {"degree": 3, "R2": 1.0, "R": 1.0, "coefficients": [0.0, 2.0, 3.0, 1.0], "k0": 0.0, "k1": 2.0, "k2": 3.0, "k3": 1.0}
    },
    {
        "desc": "三次拟合 - 强制过零点",
        "params": {"x_data": "1,2,3,4", "y_data": "6,24,60,120", "degree": 3, "force_zero": 1},
        "expected": {"degree": 3, "R2": 1.0, "R": 1.0, "coefficients": [0.0, 2.0, 3.0, 1.0], "k0": 0.0, "k1": 2.0, "k2": 3.0, "k3": 1.0}
    },
    {
        "desc": "四次拟合 - 不强制过零点",
        "params": {"x_data": "1,2,3,4,5", "y_data": "30,130,330,650,1130", "degree": 4, "force_zero": 0},
        "expected": {"degree": 4, "R2": 1.0, "R": 1.0, "coefficients": [30.0, -55.0, 59.1667, -5.0, 0.8333], "k0": 30.0, "k1": -55.0, "k2": 59.1667, "k3": -5.0, "k4": 0.8333}
    },
    {
        "desc": "四次拟合 - 强制过零点",
        "params": {"x_data": "1,2,3,4,5", "y_data": "30,130,330,650,1130", "degree": 4, "force_zero": 1},
        "expected": {"degree": 4, "R2": 1.0, "R": 1.0, "coefficients": [30.0, -55.0, 59.1667, -5.0, 0.8333], "k0": 30.0, "k1": -55.0, "k2": 59.1667, "k3": -5.0, "k4": 0.8333}
    },
]


TOLERANCE = 0.01  # 误差容忍范围

def assert_approx_equal(value, expected, key):
    if isinstance(value, list) and isinstance(expected, list):
        if len(value) != len(expected):
            raise AssertionError(f"{key}: 长度不匹配，实际{len(value)} != 期望{len(expected)}")
        for i, (v, e) in enumerate(zip(value, expected)):
            if abs(v - e) > TOLERANCE:
                raise AssertionError(f"{key}[{i}]: {v} != {e} (±{TOLERANCE})")
    else:
        if abs(value - expected) > TOLERANCE:
            raise AssertionError(f"{key}: {value} != {expected} (±{TOLERANCE})")

@pytest.mark.asyncio 
async def test_run_all_case(async_client):
    for case in test_cases:
        param_str = case['params']
        post_json = {
            'x_data': param_str['x_data'].split(','),
            'y_data': param_str['y_data'].split(','),
            'degree': int(param_str['degree']),
            'force_zero': int(param_str['force_zero'])
        }
        response = await async_client.post(BASE_URL,  json=post_json)
        data = response.json()
        assert data['code'] == 0
        print(f"\n=== {case['desc']} ===")
        print("请求参数:", case["params"])
        print("返回结果:", data)

        for key, expected_val in case["expected"].items():
            actual_val = data.get(key)
            assert_approx_equal(actual_val, expected_val, key)

        print("✅ 断言通过")




# 运行
# asyncio.run(main())
