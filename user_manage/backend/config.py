import os

class Config:

    @property
    def admin_password(self):
        admin_password = os.environ.get('admin_password')
        if not admin_password:
            return 'admin123'
        return admin_password
    
    @property
    def env(self):
        env = os.environ.get('user_manage_env') # produce
        if not env:
            return 'dev'
        return env
    

# 在 main.py 或其他入口文件中使用
config = Config()
