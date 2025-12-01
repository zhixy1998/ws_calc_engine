"""
数据格式化工具函数
"""
from typing import List
from decimal import Decimal

def convert_scientific_notation(values):
    """将科学记数法转换为普通小数格式"""
    converted = []
    for val in values:
        val_str = str(val)
        if isinstance(val, (int, float)):
            # 将数值转换为字符串，检查是否包含科学记数法标记
            if 'e' in val_str.lower():
                # 如果是科学记数法，用 Decimal 转换成字符串返回
                try:
                    decimal_val = Decimal(str(val))
                    # 直接转换为字符串，去除尾随零
                    decimal_str = str(decimal_val)
                    if '.' in decimal_str:
                        decimal_str = decimal_str.rstrip('0').rstrip('.')
                    converted.append(decimal_str)
                except:
                    converted.append(val_str)
            else:
                converted.append(val_str)
        else:
            converted.append(val_str)
    return converted


def get_max_decimal_places(y_data: List[float]) -> int:
    """
    检测 y_data 列表中所有浮点数的最大小数点位数。
    例如：[1.23, 4.567] 返回 3（因为 4.567 有 3 位小数）。
    如果都是整数，返回 0。
    """
    max_places = 0
    for val in y_data:
        # 将浮点数转换为字符串，去掉尾部零和小数点
        str_val = f"{val:.10f}".rstrip('0').rstrip('.')
        if '.' in str_val:
            places = len(str_val.split('.')[1])
            max_places = max(max_places, places)
    return max_places
