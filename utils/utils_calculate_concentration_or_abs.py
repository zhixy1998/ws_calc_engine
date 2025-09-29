
import numpy as np
from typing import Optional, List, Literal
from pydantic import BaseModel, Field




def fit_data(coeffs, value, mode):
    coeffs = coeffs[::-1]
    value = float(value)
    if mode == 1: # 浓度求吸光度
        # 多项式直接代入
        y = np.polyval(coeffs, value)
        return round(y, 4)

    if mode == 0: # 吸光度求浓度
        coeffs_copy = coeffs.copy()
        coeffs_copy[-1] -= value  # 多项式减去 y
        roots = np.roots(coeffs_copy)
        # 找所有实根（包括负值）
        candidates = [r.real for r in roots if np.isreal(r)]
        if not candidates:
            raise ValueError("没有实数根，无法计算浓度")
        # 选出最接近 value 的那个解
        best_x = min(candidates, key=lambda x: abs(np.polyval(coeffs, x) - value))
        return round(best_x, 4)
    return []



def poly_to_string(coeffs: list):
    """
    将系数列表转为人可读的方程字符串
    例如 [1.2, 0.5, 0.1] -> '1.2*x^2 + 0.5*x + 0.1'
    """
    terms = []
    degree = len(coeffs) - 1
    for i, c in enumerate(coeffs):
        power = degree - i
        if abs(c) < 1e-10:
            continue
        if power == 0:
            terms.append(f"{c:.4f}")
        elif power == 1:
            terms.append(f"{c:.4f}*x")
        else:
            terms.append(f"{c:.4f}*x^{power}")
    return ' + '.join(terms) if terms else "0"