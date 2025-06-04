FROM python:3.8.6

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制整个项目（除了 .dockerignore 过滤掉的）
COPY . .

# 设置环境变量（可选）
ENV PYTHONUNBUFFERED=1

# 启动 FastAPI 服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
