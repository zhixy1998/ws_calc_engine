# exceptions/error_codes.py
from enum import Enum

class Error:
    def __init__(self, code: int, zh: str, en: str = None) -> None:
        self._code = code
        self._zh = zh
        self._en = en

    @property
    def code(self):
        return self._code

    @property
    def zh(self):
        return self._zh

    @property
    def en(self):
        return self._en or self._zh  # 如果英文没填，用中文代替

class ErrorCode(Enum):
    OPERATION_FAILED = Error(1001, zh="操作失败, 系统内部错误")
    INVALID_ARGUMENT = Error(1002, zh="无效的参数")
    INDEPENDENT_ARIABLE_STRING_VALUE_LENGTH_NOT_EQUAL = Error(1003, zh="独立变量字符串值长度不等")
    VARIABLE_NOT_IN_FORMULA = Error(1004, zh="自变量字符串集合中包含了未在计算公式字符串中出现的变量")
    VARIABLE_VALUE_NOT_NUMERIC = Error(1005, zh="自变量依次对应的数值中包含了非数字")
    INVALID_MODE = Error(1006, zh="无效的 mode，请使用 0 或 1")
    X_Y_LENGTH_MISMATCH = Error(1007, zh="横轴和纵轴长度必须一致")
    HEIGHT_MUST_BE_LESS_THAN_OR_EQUAL_1 = Error(1008, zh="height 必须小于等于 1")
    X_Y_MUST_NUM = Error(1009, zh='x y 必须为数字')