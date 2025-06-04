import pytest
from httpx import AsyncClient
from app.main import app
# 因为获取到app，其实不用启动服务器，所以设置的BASE_URL是一个假的URL就可以。
BASE_URL = "http://testserver"
"""
 pytest fixture, 意思是:在测试运行前自动提供一个资源(这里是一个 HTTP 客户端 AsyncClient)给测试函数用。
"""

@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        yield client

