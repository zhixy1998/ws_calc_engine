from Crypto.PublicKey import RSA

# 生成 2048 位 RSA 密钥
key = RSA.generate(2048)

# 私钥字符串（直接放在 Python 文件里）
private_key_pem = key.export_key().decode('utf-8')

# 公钥字符串（发给 Java 端）
public_key_pem = key.publickey().export_key().decode('utf-8')

print("==== 私钥（放在 Python 里） ====")
print(private_key_pem)
print("==== 公钥（发给 Java 端） ====")
print(public_key_pem)