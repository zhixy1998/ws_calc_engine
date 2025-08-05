import io
import base64

import matplotlib
matplotlib.use('Agg')
import numpy as np
import matplotlib.pyplot as plt
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
            rmse = np.sqrt(np.mean((y - y_pred) ** 2))
            residual_std = np.std(y - y_pred)
            chi_squared = np.sum(((y - y_pred) ** 2) / y_pred)
        
            # 置信区间估算（近似，仅适用于一元线性回归）
            n = len(x)
            x_mean = np.mean(x)
            s_err = np.sum((y - y_pred)**2)
            t = 2.131  # 95% confidence for small n (e.g. df=10)
            conf = t * np.sqrt((s_err / (n - 2)) * (1 / np.sum((x - x_mean)**2)))
            return {
                "degree": degree,
                "R2": round(r2, 4),
                "R": round(r, 4),
                "k1": k1,
                "k0": 0.0,
                "coefficients": [0.0, k1],
                "equation": f"y = {round(k1, 4)}x",
                "image_base64": plot_fit(x, y, y_pred),
                "standard_error": round(rmse, 4),
                "confidence_95": [[round(0.0, 4), round(0.0, 4)], [round(k1 - conf, 4), round(k1 + conf, 4)]],
                "rmse": round(rmse, 4),
                "residual_std": round(residual_std, 4),
                "chi_squared": round(chi_squared, 4),
            }

        elif degree in [2, 3, 4]:
            # 高阶，强制过零点，构造 A 矩阵，不含 k0
            powers = [x ** d for d in range(degree, 0, -1)]
            A = np.vstack(powers + [np.ones_like(x)]).T
            coefficients = np.linalg.lstsq(A, y, rcond=None)[0]  # 高 -> 低
            y_pred = A @ coefficients

            # p = Polynomial.fit(x, y, degree)
            # coefficients = p.convert().coef  # 从低阶到高阶
            # y_pred = p(x)

            cleaned = handle_small_coefficients(coefficients)
            cleaned_reversed = cleaned[::-1]  # 低 -> 高

            r2 = calc_r2(y, y_pred)
            r = np.sqrt(r2)
            rmse = np.sqrt(np.mean((y - y_pred) ** 2))
            residual_std = np.std(y - y_pred)
            chi_squared = np.sum(((y - y_pred) ** 2) / y_pred)

            result = {
                "degree": degree,
                "R2": round(calc_r2(y, y_pred), 4),
                "R": round(np.sqrt(calc_r2(y, y_pred)), 4),
                "coefficients": cleaned_reversed,
                "equation": generate_equation(coefficients),
                "image_base64": plot_fit(x, y, y_pred),
                "standard_error": round(rmse, 4),
                "rmse": round(rmse, 4),
                "residual_std": round(residual_std, 4),
                "chi_squared": round(chi_squared, 4),
            }
            result['k0'] = 0.0
            for i in range(1, len(cleaned_reversed)):
                result[f'k{i}'] = cleaned_reversed[i]
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

def generate_equation(coefficients):
    """生成方程字符串"""
    terms = []
    for i, coef in enumerate(coefficients):
        coef_val = round(float(coef), 4)
        if coef_val == 0:
            continue
        if i == 0:
            terms.append(f"{coef_val}")
        elif i == 1:
            terms.append(f"{coef_val}x")
        else:
            terms.append(f"{coef_val}x^{i}")
    return "y = " + " + ".join(terms)

def plot_fit(x, y, y_pred):
    """绘制拟合图像并返回 base64 编码"""
    plt.figure()
    plt.plot(x, y, 'bo', label='Original data')
    plt.plot(x, y_pred, 'r-', label='Fitted curve')
    plt.legend()
    plt.xlabel("X")
    plt.ylabel("Y")
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")