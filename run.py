# run.py
import uvicorn
from app.main import app
from config import config

if __name__ == '__main__':
    print('hello')
    uvicorn.run(app, host='0.0.0.0', port=config.port, log_level=config.log_level, workers=config.calc_worker)