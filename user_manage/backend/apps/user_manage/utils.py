import hmac
import hashlib

KEY = "3cdb0c5c984e85e9dfb259425fc00a8c"

def hash_password(data: str) -> str:
    mac = hmac.new(KEY.encode(), data.encode(), hashlib.md5)
    return mac.hexdigest()