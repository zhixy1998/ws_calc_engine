import secrets
import base64

# 生成 AES-128 密钥（16 字节）
aes_key = secrets.token_bytes(16)
print("AES Key (base64):", base64.b64encode(aes_key).decode())