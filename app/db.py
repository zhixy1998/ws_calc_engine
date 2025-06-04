import os
from dotenv import load_dotenv
from tortoise import Tortoise
"""
# 第一次初始化
aerich init -t app.db.TORTOISE_ORM

# 初始建表
aerich init-db

# 修改模型后
aerich migrate 生成迁移文件
aerich upgrade 应用迁移文件

"""

load_dotenv(override=True)
TORTOISE_ORM = {
    "connections": {"default": os.getenv("DB_URL")},
    "apps": {
        "models": {  # ← 这个名字无所谓，aerich 要求必须叫 models 或 aerich
            "models": [
                "app.user.model",              # 你自己的 user 模型包
                "app.UVWin_algorithm.model",   # 你自己的算法模型包
                "aerich.models"                # Aerich 迁移系统必需
            ],
            "default_connection": "default"
        }
    }
}

async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()