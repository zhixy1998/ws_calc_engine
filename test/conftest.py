import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pytest_asyncio  # 导入pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app
# 因为获取到app，其实不用启动服务器，所以设置的BASE_URL是一个假的URL就可以。
BASE_URL = "http://testserver"
"""
 pytest fixture, 意思是:在测试运行前自动提供一个资源(这里是一个 HTTP 客户端 AsyncClient)给测试函数用。
"""

@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app),  # 关键修改
        base_url="http://test"
    ) as client:
        yield client

