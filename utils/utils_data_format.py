"""
数据格式化工具函数
"""
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
