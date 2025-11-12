from config import config

bind = f"0.0.0.0:{config.port}"  # 内部绑定端口
loglevel = config.log_level
workers = 4
worker_class = 'uvicorn.workers.UvicornWorker'