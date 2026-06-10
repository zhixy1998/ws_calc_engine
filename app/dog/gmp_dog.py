
import hashlib
import ctypes  # ctypes: Python 标准库，用于调用 C DLL 函数
import os      # os: 用于路径处理（可选，加 DLL 目录）
import sys
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import base64
import json
import wmi
from cryptography.hazmat.primitives.asymmetric import padding
from Crypto.Cipher import AES
import time
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.Random import get_random_bytes

PRIVATE_KEY_PEM = """
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA6KMIcq4zVaawVamXTpciXfLGl+lLWpagzqv8ViOYa9xgOOSO
HwegeGJSufNizsKaLE88VQ6u31QY/F2aW9/3PI28kvOsYZ2G14WGbzOOq+k0Uq/y
/aYN2E2Q7/sOfmhoIX2E6jLvsbgNzVgONI7meAH8MEczjJYcUFCx0p7sde3yv7P9
Wa6x94fdhI3xi2fv2APovwLE10Cr4mpM6CaZA3NSIunKPluMRKWASKTu34wRKkx+
S3tHcNbcDi7Ce8X7lf5yHRkNhx2c1Ahlo9C1r66smU4lbN2ARSTUJq+zZ7vtE1Je
DxjspxtIA0mC09UnyuGFuHXE6SXRvVq0RR0+SwIDAQABAoIBAC7HKZm1wYjFfcub
0FrzNOvjN1+wf4B1rVwhZRoFCk8V/xsxigpfRDswuiW99O5SXyHtxNntm+g4RtXo
FHPI8zPv5C1AZjcyr7yCkuelXFjhCa5exuOOElaeMjivKNjuMZIaZTGakGwR8GSM
Aj87RMh4zbb/ejQYsxTLRRZu8mk7z1tGauONMpi2J0MOb94mfvDbnAf1GNFHUVkJ
OVar/3Bb3lLZyu3pCMPROeyDNZVIs6pxo3/DVsjDfAlmSk5S0VJO77aiYac0VA0P
LHtExjN1VBZk3HJZYVVIf4cUTSJbK/T4vpzJqxYVIS7dKxzohpdlGE/unqKvwB5F
a7GL+6ECgYEA7qv1vebTwint4UO3O5bB4jAj85516jmrw3nyBwTPtTC3ktQ+Zk2a
ru/I7mbE+Sp8pqRqE0YnIflt6Na4N0ZJsh9uBTbqzolinGK41DcCGswin48QLWo0
oI/dI6y3jgmCE9YLbgN4o8Vf5lORut7UGGwx6StSi5pslRDOeSzwm0kCgYEA+Ybo
ILeBkqLjTQEgUYyOLTd2pk22wsql6cLUdoiXsahR3FD1pF0nJoNoQAZf0mtj3P/b
Oz5jDh0wXXYgQf+nHAXFG/BHzjXBnwMZ2AL8p9xyOQbN+qrvDEJbcxj1JnFzu6GA
1g/k+oVWEXSxpI+RIqRuu7rjTN0mW8F1nonTGPMCgYEA2zeg4Er6pzVh4+0RiK8A
6CM1cldSkM9lv4brUZ0OtqrHghpmMgsHj7R4hthoBUAL+/e54ngmC2ORmzJVQ5fQ
qsWJhUqawxeXNnLKt0jLKxfimVGLF1ucePmKsXC7q7959YQ9PU/859erLOAHU2/F
uaTu9u6uw8EUCJrGOrCXUtkCgYAD7t1vzpSrRAgDKbZhsq53Bf3Hx0fPMDSHR7vj
lmmVskqAB4KnsZQxZjbZc4BFJ84uKJZDC8ux6EHf50HA6I+wwGKH+zSWioBfykO5
BOsIlk/ymCnc/p6/+bfJS6ZpkbY6SeRm+18nl7xwj/9Q0bZ+7kqUiPCWQJIfNiBt
fEyogwKBgE1qHa8finyZulE/b3gwlh6yfsqH4rsS6T1zRVedopsPsERzbr8mW1lY
UkaVTxt5HygXq5pfVNIS9iQ9iPHcegaoVvETqZaG/L2Q55CThuzkLctzv44VKbo2
TtT+wPzSuZ7VzL4xvAUL4Hy6mAIqBRLRTVqz6/eu7Cq8gadnq6ak
-----END RSA PRIVATE KEY-----
"""

AES_KEY = "zKJrRM0FcmeDTWyBj0hxlg=="
# 厂商 DLL 文件名（根据你们实际文件改；假设是 FT_ET99_API.dll）
DLL_NAME = "FT_ET99_API.dll"  # DLL 文件必须在当前目录或系统 PATH 中

# 常量定义（从 C++ 复制，保持一致）
G_PID = b"FAFF72AD"           # 全局 PID (bytes 类型，C API 需要 bytes)
G_PIN = b"9E51F8C6BD343D56"   # 全局 User PIN (bytes 类型)
G_MAGIC = 0xEAEA3636          # 魔数，用于验证绑定 ID 是否已写

# 错误码常量（从头文件 FT_ET99_API.h 复制）
ET_SUCCESS = 0x00             # 操作成功
ET_ACCESS_DENY = 0x01         # 访问被拒，无权限
ET_COMMUNICATIONS_ERROR = 0x02 # 通讯错误，未检测到设备（狗未插）
ET_INVALID_PARAMETER = 0x03   # 无效参数
ET_NOT_SET_PID = 0x04         # 未设置 PID
ET_UNIT_NOT_FOUND = 0x05      # 指定设备未找到
ET_HARD_ERROR = 0x06          # 硬件错误
ET_UNKNOWN = 0x07             # 未知错误
ET_PIN_ERR_MASK = 0x0F        # PIN 错误掩码
ET_PIN_ERR_MAX = 0xFF         # PIN 错误次数超限（锁死）
SALT = '39fa239gsdfb98s8'

# PIN 类型常量（从头文件复制）
ET_VERIFY_USERPIN = 0         # User PIN 验证
ET_VERIFY_SOPIN = 1           # SO PIN 验证

# 加载 DLL（使用 windll，因为 API 是 __stdcall 约定，Windows 常见）
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))


def _resolve_dll_path():
    candidate_dirs = [project_root, script_dir]

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        candidate_dirs.insert(0, sys._MEIPASS)

    checked_paths = []
    for candidate_dir in candidate_dirs:
        candidate_path = os.path.join(candidate_dir, DLL_NAME)
        checked_paths.append(candidate_path)
        if os.path.exists(candidate_path):
            return candidate_path

    checked = ', '.join(checked_paths)
    raise RuntimeError(f"DLL 不存在: {checked}. 请确认文件已放到项目根目录或打包输出根目录")


dll_path = _resolve_dll_path()
dll_dir = os.path.dirname(dll_path)

print(f"调试: 当前 cwd = {os.getcwd()}")
print(f"调试: DLL 绝对路径 = {dll_path}")
print(f"调试: DLL 存在? = {os.path.exists(dll_path)}")

# 添加 DLL 目录到搜索路径（解决依赖）
os.add_dll_directory(dll_dir)

try:
    et_dll = ctypes.windll.LoadLibrary(dll_path)  # 用绝对路径
    print("调试: DLL 加载成功！")  # 成功提示
except OSError as e:
    raise RuntimeError(f"无法加载 DLL {DLL_NAME}: {e}. 可能依赖缺失（装 VC++ Redist），或驱动未装。cwd={os.getcwd()}, DLL={dll_path}")

# 为 et_Verify 函数定义 argtypes 和 restype（ctypes 必须指定参数/返回类型）
et_dll.et_Verify.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]  # HANDLE, Flags, PIN (bytes)
et_dll.et_Verify.restype = ctypes.c_ulong  # 返回 ET_STATUS (unsigned long)

# 为 et_OpenToken 定义（其他函数类似，按需加）
et_dll.et_OpenToken.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_char_p, ctypes.c_int]
et_dll.et_OpenToken.restype = ctypes.c_ulong

et_dll.et_CloseToken.argtypes = [ctypes.c_void_p]
et_dll.et_CloseToken.restype = ctypes.c_ulong



# 按你的 C 函数声明设置参数类型
et_dll.et_Read.argtypes = [
    ctypes.c_void_p,      # ET_HANDLE hHandle（多数 dongle 厂都是 pointer）
    ctypes.c_ushort,      # WORD offset
    ctypes.c_int,         # int Len
    ctypes.POINTER(ctypes.c_ubyte)  # unsigned char* pucReadBuf
]

et_dll.et_Read.restype = ctypes.c_int   # ET_STATUS 通常是 int

et_dll.et_Write.argtypes = [ctypes.c_void_p, ctypes.c_ushort, ctypes.c_int, ctypes.c_char_p]
et_dll.et_Write.restype = ctypes.c_ulong

et_dll.et_FindToken.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
et_dll.et_FindToken.restype = ctypes.c_ulong

class GmpDog:
    """
    GmpDog 类：封装加密狗（ET99）操作。
    - 查找狗、打开/关闭句柄、验证 PIN。
    - 读/写绑定 ID（存储在狗的 EEPROM 中，偏移 0 开始）。
    - 绑定逻辑：读 magic 验证是否已绑定；写时覆盖 magic + 长度 + ID。
    - 错误：通过 self.mLastError 存储，最后用 getLastError() 获取描述。
    """
    
    def __init__(self):
        """
        构造函数：初始化句柄为 None，最后错误码为 0。
        """
        self.mHandle = None  # ET_HANDLE (ctypes.c_void_p 类型，C 的 void*)
        self.mLastError = ET_SUCCESS  # 上次操作错误码
    
    def findDog(self):
        """
        查找加密狗：调用 et_FindToken，传入 PID，获取狗数量。
        - 返回 True 如果找到（count > 0 且无错）。
        - 错误：无狗插上 → ET_COMMUNICATIONS_ERROR。
        """
        count = ctypes.c_int(0)  # 输出参数：狗数量 (int*)
        self.mLastError = et_dll.et_FindToken(G_PID, ctypes.byref(count))  # 调用 DLL，byref 传引用
        return self.mLastError == ET_SUCCESS and count.value > 0  # 成功且至少 1 个狗
    
    def getBindId(self):
        """
        获取绑定 ID：打开狗 → 验证 PIN → 读 magic + 长度 + ID。
        - 如果 magic 不匹配，返回 "new_dog"（新狗，未绑定）。
        - 返回绑定 ID 字符串（str），或 None（失败）。
        - 存储格式：偏移 0: magic (4 bytes), 4: 长度 (2 bytes), 6: ID 数据。
        """
        # 1. 打开狗
        if not self.open():
            return None
        
        # 2. 验证 PIN（用 User PIN）
        if not self.verify(use_so=True):
            return None
        
        # 3. 读 magic (unsigned int, 4 bytes)
        buf_len = 4
        magic_buf = (ctypes.c_ubyte * buf_len)()
        self.mLastError = et_dll.et_Read(self.mHandle, 0, 4, magic_buf)  # offset=0, Len=4
        if self.mLastError != ET_SUCCESS:
            self.close()  # 失败时关闭
            return None
        magic_value = int.from_bytes(bytes(magic_buf), 'little') 
        if magic_value != G_MAGIC:
            self.close()
            return "new_dog"  # 未绑定，返回默认 ID
        
        # 4. 读长度 (short, 2 bytes)
        buf = (ctypes.c_ubyte * 2)()  # 创建 2 字节缓冲区
        self.mLastError = et_dll.et_Read(self.mHandle, 4, 2, buf)
        if self.mLastError != ET_SUCCESS:
            self.close()
            return None
        
        # 5读数据
        sn_length = int.from_bytes(bytes(buf), 'little', signed=False)
        sn_buffer = (ctypes.c_ubyte * sn_length)()
        self.mLastError = et_dll.et_Read(self.mHandle, 6, sn_length, sn_buffer)
        if self.mLastError != ET_SUCCESS:
            self.close()
            return None
        
        data_bytes = bytes(sn_buffer)
        self.close()
        return data_bytes.decode('ascii').rstrip('\x00')
    
    def setBindId(self, bid):
        """
        设置绑定 ID：打开狗 → 验证 PIN（用 SO PIN，可写）→ 写 magic + 长度 + ID。
        - bid: 绑定 ID 字符串 (str)，e.g., "SN123456"。
        - 返回 True（成功）。
        - 长度限制：bid 长度 <= 249（总 255 - 6）。
        """
        if not isinstance(bid, str) or len(bid) > 249:
            self.mLastError = ET_INVALID_PARAMETER
            return False
    
        # 1. 打开狗
        if not self.open():
            return False
    
        # 2. 验证 PIN（用 SO PIN，允许写）
        if not self.verify(use_so=True):
            return False
    
        try:
            # 3. 写 magic (4 bytes) - 修复类型问题
            magic_data = G_MAGIC.to_bytes(4, byteorder='little')  # 将整数转换为4字节
            self.mLastError = et_dll.et_Write(self.mHandle, 0, 4, magic_data)
            if self.mLastError != ET_SUCCESS:
                self.close()
                return False
        
            # 4. 写长度 (short, 2 bytes)
            sn_length = len(bid)
            length_data = sn_length.to_bytes(2, byteorder='little')  # 将长度转换为2字节
            self.mLastError = et_dll.et_Write(self.mHandle, 4, 2, length_data)
            if self.mLastError != ET_SUCCESS:
                self.close()
                return False
        
            # # 5. 写 ID (bytes)
            sn_bytes = bid.encode('ascii')  # str → bytes (ASCII 假设)
            self.mLastError = et_dll.et_Write(self.mHandle, 6, len(sn_bytes), sn_bytes)
            if self.mLastError != ET_SUCCESS:
                self.close()
                return False
            
            if self.mLastError != ET_SUCCESS:
                self.close()
                return False
        
            self.close()  # 成功后关闭
            return True
        
        except Exception as e:
            print(f"写入时发生错误: {e}")
            self.close()
            return False
    
    def reset(self):
        """
        重置狗：打开 → 验证 SO PIN → 写 50 bytes 零到偏移 0（清空绑定数据）。
        - 返回 True（成功）。
        """
        # 1. 打开狗
        if not self.open():
            return False
        
        # 2. 验证 SO PIN（可写）
        if not self.verify(use_so=True):
            return False
        
        # 3. 写 50 bytes 零
        buffer = (ctypes.c_char * 50)()  # 零初始化缓冲区
        self.mLastError = et_dll.et_Write(self.mHandle, 0, 50, buffer)
        if self.mLastError != ET_SUCCESS:
            self.close()
            return False
        
        self.close()
        return True
    
    def close(self):
        """
        关闭狗句柄：调用 et_CloseToken。
        - 返回 True（成功），句柄设为 None。
        """
        if self.mHandle is None:
            return True
        self.mLastError = et_dll.et_CloseToken(self.mHandle)
        self.mHandle = None
        return self.mLastError == ET_SUCCESS
    
    def open(self):
        """
        打开狗：调用 et_OpenToken，PID + index=1（第一个狗）。
        - 返回 True（成功），self.mHandle 更新。
        """
        if self.mHandle is not None:
            self.close()  # 先关闭旧句柄
        
        self.mHandle = ctypes.c_void_p()  # 创建 HANDLE 指针
        self.mLastError = et_dll.et_OpenToken(ctypes.byref(self.mHandle), G_PID, 1)  # index=1
        return self.mLastError == ET_SUCCESS
    
    def verify(self, use_so=False, bid=None):
        """
        验证 PIN：User PIN 或 SO PIN。
        - use_so=True: 用 SO PIN（可写操作）。
        - SO PIN 计算：sprintf("%ldDD%d7F%s", 576741, 21, "C401") → "576741DD217FC401"。
        - 返回 True（成功）。
        """
        if use_so:
            so_pin = b"576741DD217FC401"  # 硬编码计算结果 (bytes)
            self.mLastError = et_dll.et_Verify(self.mHandle, ET_VERIFY_SOPIN, G_PIN)
        else:
            self.mLastError = et_dll.et_Verify(self.mHandle, ET_VERIFY_USERPIN, G_PIN)
        return self.mLastError == ET_SUCCESS
    
    def verify_hardware(self):
        new_bid = self.generate_bid()
        old_bid = self.getBindId()
        return new_bid == old_bid
    
    def getLastError(self):
        """
        获取上次错误描述：根据 self.mLastError 返回字符串。
        - 支持特殊码如 0xF0 (PIN 锁死)。
        """
        if self.mLastError == ET_SUCCESS:
            return "Success!"
        elif self.mLastError == ET_ACCESS_DENY:
            return "Err: access denied, have not enough right!"
        elif self.mLastError == ET_COMMUNICATIONS_ERROR:
            return "Err: have not open the device"
        elif self.mLastError == ET_INVALID_PARAMETER:
            return "Err: invalid parameter!"
        elif self.mLastError == ET_NOT_SET_PID:
            return "Err: have not set PID!"
        elif self.mLastError == ET_UNIT_NOT_FOUND:
            return "Err: open the device fail!"
        elif self.mLastError == 0xF0:
            return "Err: PIN have been locked!"
        elif self.mLastError & ET_PIN_ERR_MASK == ET_PIN_ERR_MASK:  # PIN 错掩码
            return "Err: PIN is wrong!"
        else:
            return "Err: unknown error occured!"
        

    def get_hardware_info(self):
        """获取 Windows 硬件指纹（字典）"""
        """使用WMI获取硬件信息"""
        c = wmi.WMI()
        hardware_info = {}
    
        # 获取MAC地址（第一个启用网卡的地址）
        for interface in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
            hardware_info['mac_address'] = interface.MACAddress
            break
    
        # 获取主板序列号
        for board in c.Win32_BaseBoard():
            hardware_info['motherboard_id'] = board.SerialNumber.strip()
            break
    
        # 获取硬盘序列号（第一个物理硬盘）
        for disk in c.Win32_DiskDrive():
            hardware_info['disk_id'] = disk.SerialNumber.strip()
            break
    
        return hardware_info

    def short_hash(self, value: str, length: int = 4) -> str:
        """对单个硬件字段生成短哈希（默认 4 字符 hex）"""
        return hashlib.sha256(value.encode('utf-8')).hexdigest()[:length]

    def generate_bid(self, final_len: int = 18) -> str:
        """
        传入硬件字典 {field: value}
        输出固定长度的硬件指纹（默认 18字符）
        """
        # 1. 按键排序，确保稳定
        hw_info = self.get_hardware_info()
        items = []

        for key in sorted(hw_info.keys()):
            value = str(hw_info[key])
            h = self.short_hash(value, length=4)   # 每个字段短哈希 4 字符
            items.append(f"{key}:{h}")

        # 2. 拼接所有短哈希形成 fingerprint base
        base = "|".join(items)

        # 3. 再做一次强哈希，确保所有字段都影响最终结果
        full_digest = hashlib.sha256(base.encode("utf-8")).hexdigest()

        return full_digest[:final_len]     # 输出固定长度 18 字符

    def validate_bid(self, stored_bid):
        """
        验证 BID：重新计算，检查哈希值是否 100% 匹配。
        (此版本不包含容错)

        :param stored_bid: 从加密狗中读出的哈希字符串。
        :return: True (匹配) 或 False (不匹配)
        """
        try:
            current_bid = self.generate_bid()
        except ValueError:
            # 如果当前电脑无法获取硬件信息（例如 WMI 损坏），则验证失败
            print("错误：无法在当前机器上生成 BID。")
            return False

        # 严格的字符串比较
        return current_bid == stored_bid
    
    def aes_decrypt(self, iv_and_cipher, aes_key):
        try:
            iv_b64, cipher_b64 = iv_and_cipher.split(":")
        except ValueError:
            raise ValueError("Invalid encrypted data format")

        iv = base64.b64decode(iv_b64)
        cipher = base64.b64decode(cipher_b64)

        aes = AES.new(aes_key, AES.MODE_CBC, iv)
        decrypted = aes.decrypt(cipher)

        # PKCS7 unpad
        decrypted = self.unpad(decrypted)
        return decrypted.decode()

    def unpad(self, data):
        pad_len = data[-1]
        if pad_len < 1 or pad_len > 16:
            raise ValueError("Invalid padding")

        if data[-pad_len:] != bytes([pad_len]) * pad_len:
            raise ValueError("Padding mismatch")

        return data[:-pad_len]

    def validate_ts(self, ts):
        now = time.time()

        # 自动识别毫秒
        if ts > 1e12:
            ts = ts / 1000.0

        return abs(now - ts) <= 5

    def verify_and_get_data(self, encrypted_key_base64, encrypted_data):
        private_key = RSA.import_key(PRIVATE_KEY_PEM)

        encrypted_key = base64.b64decode(encrypted_key_base64)

        # RSA PKCS1_v1_5 解密
        cipher = PKCS1_v1_5.new(private_key)
        aes_key = cipher.decrypt(encrypted_key, None)
        if aes_key is None:
            print("RSA 解密失败")
            return False

        # AES 解密
        try:
            json_str = self.aes_decrypt(encrypted_data, aes_key)
        except Exception as e:
            print("AES 解密失败:", str(e))
            return False

        obj = json.loads(json_str)
        print("解密结果：", obj)

        # 校验时间戳
        if not self.validate_ts(obj.get("ts", 0)):
            print("时间戳验证失败")
            return False

        # 校验操作类型
        return aes_key, obj
        # try:
        #     if int(obj.get("operation")) == 1:
        #         return self.verify_hardware()
        # except:
        #     return False

        # return False
    
    def pad(self, data):
        """PKCS7 填充"""
        pad_len = 16 - (len(data) % 16)
        # 将字节数据转换为可变的 bytearray
        data_array = bytearray(data)
        # 添加填充
        data_array.extend(bytes([pad_len]) * pad_len)
        return bytes(data_array)

    def aes_encrypt(self, json_str, aes_key):
        """
        使用共享的 AES 密钥加密返回数据
        """
        # 1. 生成一个*新的*、*随机的* IV (初始化向量)
        iv = get_random_bytes(16)
    
        # 2. 准备 AES 加密器
        aes = AES.new(aes_key, AES.MODE_CBC, iv)
    
        # 3. 填充数据
        data_bytes = self.pad(json_str.encode('utf-8'))
    
        # 4. 加密
        encrypted_bytes = aes.encrypt(data_bytes)
    
        # 5. 组合成 "iv:cipher" 格式返回
        iv_b64 = base64.b64encode(iv).decode('utf-8')
        cipher_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
    
        return f"{iv_b64}:{cipher_b64}"

    def verify_dog_handle_request(self, encrypted_key, encrypted_data):
        """
        完整的请求 -> 处理 -> 响应 流程
        """
    
        # --- 接收和解密 (Client -> Server) ---
        aes_key, request_obj = self.verify_and_get_data(encrypted_key, encrypted_data)
    
        if aes_key is None or request_obj is None:
            # 解密或验证失败
            # 注意：这里我们不能加密返回，因为我们没有aes_key
            # 最好直接返回一个HTTP错误，例如 401 Unauthorized
            return "ERROR: Authentication Failed" 

        # --- 业务逻辑 ---
        response_data = {}
        try:
            if int(request_obj.get("operation")) == 1:
                # 假设 verify_hardware() 返回 True/False
                success = self.verify_hardware() 
                if success:
                    response_data = {"status": "OK", "message": "Hardware verified."}
                else:
                    response_data = {"status": "FAILED", "message": "Hardware mismatch."}
            else:
                response_data = {"status": "ERROR", "message": "Unknown operation."}

        except Exception as e:
            response_data = {"status": "ERROR", "message": f"Server logic error: {e}"}

        # --- 加密并返回 (Server -> Client) ---
    
        # 同样加入时间戳，防止对服务器的返回进行重放
        response_data["ts"] = int(time.time()) 
        response_json = json.dumps(response_data)
    
        # 使用刚才解密得到的 aes_key 加密回去！
        encrypted_response = self.aes_encrypt(response_json, aes_key)
    
        print(f"加密的返回: {encrypted_response}")
        return encrypted_response