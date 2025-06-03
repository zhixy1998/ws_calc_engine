
import numpy as np
from numpy.polynomial import Polynomial

def handle_small_coefficients(coefficients):
    """处理非常小的系数，避免浮动误差"""
    # print(coefficients)
    l = []
    for coef in coefficients:
        # print(coef)
        if abs(coef) >= 1e-15:
            round_value = round(coef, 8)
            if round_value.is_integer():
                l.append(str(int(round_value)))
            else:
                l.append(round_value)
        else:
            l.append('0')
    return l
            

def fit_data(x, y, degree, force_zero):
    """根据给定的多项式次数进行最小二乘拟合，支持强制过零点"""

    if force_zero:
        if degree == 1:
            # 一阶，强制过零点
            k1 = np.sum(x * y) / np.sum(x ** 2)
            y_pred = k1 * x
            r2 = calc_r2(y, y_pred)
            r = np.sqrt(r2)
            return {
                "degree": degree,
                "R2": round(r2, 4),
                "R": round(r, 4),
                "k1": k1,
                "k0": 0.0,
                "coefficients": [0.0, k1]
            }

        elif degree in [2, 3, 4]:
            # 高阶，强制过零点，构造 A 矩阵，不含 k0
            powers = [x ** d for d in range(degree, 0, -1)]
            A = np.vstack(powers + [np.ones_like(x)]).T
            coeffs = np.linalg.lstsq(A, y, rcond=None)[0]  # 高 -> 低
            y_pred = A @ coeffs
            cleaned = handle_small_coefficients(coeffs)
            cleaned_reversed = cleaned[::-1]  # 低 -> 高
            result = {
                "degree": degree,
                "R2": round(calc_r2(y, y_pred), 4),
                "R": round(np.sqrt(calc_r2(y, y_pred)), 4),
                "coefficients": cleaned_reversed,
            }
            for i, c in enumerate(cleaned_reversed):
                result[f'k{i}'] = c
            return result
    else:
        # 不强制过零点，直接 polyfit
        p = Polynomial.fit(x, y, degree)
        coefficients = p.convert().coef  # 从低阶到高阶排列
        y_pred = p(x)
        cleaned = handle_small_coefficients(coefficients)
        result = {
            "degree": degree,
            "R2": round(calc_r2(y, y_pred), 4),
            "R": round(np.sqrt(calc_r2(y, y_pred)), 4),
            "coefficients": cleaned,
        }
        for i, c in enumerate(cleaned):
            result[f'k{i}'] = c
        return result

def calc_r2(y_true, y_pred):
    """计算决定系数 R²"""
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return 1 - (ss_res / ss_tot)