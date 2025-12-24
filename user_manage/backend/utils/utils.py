import time

import jwt
from django.conf import settings

def generation_token(user_id: int) -> str:
    expire_time = int(time.time()) + 600 # 10分钟后过期
    token = jwt.encode(
        payload={'user_id': user_id, 'exp_time': expire_time},
        key = settings.SECRET_KEY,
        algorithm='HS256'
    )
    return token