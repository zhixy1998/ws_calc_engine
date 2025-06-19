## ws_calc_engine

工作站算法引擎代码库

启动命令
docker build -t ws_calc_engine .
docker run -d --name ws_calc_engine --env-file .env -p 8002:8002 ws_calc_engine
