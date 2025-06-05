FROM python:3.8.6

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 并安装依赖
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
        -i https://mirrors.aliyun.com/pypi/simple \
        --trusted-host mirrors.aliyun.com \
    || pip install --no-cache-dir -r requirements.txt \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --trusted-host pypi.tuna.tsinghua.edu.cn \
    || pip install --no-cache-dir -r requirements.txt \
        -i https://pypi.doubanio.com/simple \
        --trusted-host pypi.doubanio.com \
    || pip install --no-cache-dir -r requirements.txt \
        -i https://pypi.org/simple

RUN pip install --no-cache-dir -r requirements.txt \
        -i https://mirrors.aliyun.com/pypi/simple \
        --trusted-host mirrors.aliyun.com \
    || pip install --no-cache-dir -r requirements.txt \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --trusted-host pypi.tuna.tsinghua.edu.cn \
    || pip install --no-cache-dir -r requirements.txt \
        -i https://pypi.doubanio.com/simple \
        --trusted-host pypi.doubanio.com \
    || pip install --no-cache-dir -r requirements.txt \
        -i https://pypi.org/simple


# 复制整个项目（除了 .dockerignore 过滤掉的）
COPY . .

# 设置环境变量（可选）
ENV PYTHONUNBUFFERED=1

# 启动 FastAPI 服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
