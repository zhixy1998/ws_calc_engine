import io
import base64
from decimal import Decimal

import matplotlib
matplotlib.use('Agg')
import numpy as np
import matplotlib.pyplot as plt
from numpy.polynomial import Polynomial
import statsmodels.api as sm
from utils.utils_data_format import convert_scientific_notation


def calculate_confidence_intervals(x, y, degree, force_zero=False, alpha=0.05):
    """使用 statsmodels 计算置信区间"""
    try:
        # 构造特征矩阵
        if force_zero:
            # 强制过零点，不包含常数项
            X = np.vander(x, degree + 1, increasing=True)[:, 1:]  # 去掉常数项
        else:
            # 正常拟合，包含常数项
            X = np.vander(x, degree + 1, increasing=True)
        
        # 检查数据点数量
        if len(x) <= X.shape[1]:
            # 数据点太少，无法计算置信区间
            return None
        
        # 拟合模型
        model = sm.OLS(y, X).fit()
        
        # 计算置信区间
        conf_int = model.conf_int(alpha=alpha)  # alpha=0.05 表示95%置信区间
        
        # 转换为列表格式，并四舍五入到合理精度
        conf_int_rounded = [[format_decimal_string(round(interval[0], 6)), format_decimal_string(round(interval[1], 6))] for interval in conf_int.tolist()]
        return conf_int_rounded
        
    except Exception as e:
        # 如果计算失败，返回 None
        return None

def handle_small_coefficients(coefficients):
    """处理非常小的系数，避免浮动误差"""
    # print(coefficients)
    l = []
    for coef in coefficients:
        # print(coef)
        if abs(coef) >= 1e-15:
            round_value = round(coef, 8)
            l.append(format_decimal_string(round_value))
        else:
            l.append('0')
    return l
            

def fit_data(x, y, degree, force_zero):
    """根据给定的多项式次数进行最小二乘拟合，支持强制过零点"""

    if force_zero:
        if degree == 1:
            # 一阶，强制过零点
            k1 = format_decimal_string(np.sum(x * y) / np.sum(x ** 2))
            y_pred = k1 * x
            r2 = calc_r2(y, y_pred)
            r = np.sqrt(r2)
            rmse = np.sqrt(np.mean((y - y_pred) ** 2))
            residual_std = np.std(y - y_pred)
            # 卡方计算，避免除零错误
            # 当 y_pred 为 0 时，跳过该项或使用小的替代值
            y_pred_safe = np.where(np.abs(y_pred) < 1e-10, np.nan, y_pred)
            chi_squared_terms = ((y - y_pred) ** 2) / y_pred_safe
            chi_squared = np.nansum(chi_squared_terms)  # 忽略 NaN 值
        
            # 使用 statsmodels 计算置信区间
            confidence_95 = calculate_confidence_intervals(x, y, degree, force_zero=True)
            return {
                "degree": degree,
                "R2": round(r2, 4),
                "R": round(r, 4),
                "k1": k1,
                "k0": 0.0,
                "coefficients": [0.0, k1],
                "equation": f"y = {k1}x",
                "image_base64": plot_fit(x, y, y_pred),
                "standard_error": rmse,
                "confidence_95": confidence_95,
                "rmse": rmse,
                "residual_std": residual_std,
                "chi_squared": chi_squared,
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
            # 卡方计算，避免除零错误
            # 当 y_pred 为 0 时，跳过该项或使用小的替代值
            y_pred_safe = np.where(np.abs(y_pred) < 1e-10, np.nan, y_pred)
            chi_squared_terms = ((y - y_pred) ** 2) / y_pred_safe
            chi_squared = np.nansum(chi_squared_terms)  # 忽略 NaN 值

            # 使用 statsmodels 计算置信区间
            confidence_95 = calculate_confidence_intervals(x, y, degree, force_zero=True)
            
            result = {
                "degree": degree,
                "R2": round(calc_r2(y, y_pred), 4),
                "R": round(np.sqrt(calc_r2(y, y_pred)), 4),
                "coefficients": cleaned_reversed,
                "equation": generate_equation(cleaned_reversed, force_zero=force_zero),
                "image_base64": plot_fit(x, y, y_pred),
                "standard_error": round(rmse, 4),
                "rmse": round(rmse, 4),
                "residual_std": round(residual_std, 4),
                "chi_squared": round(chi_squared, 4),
                "confidence_95": confidence_95,
            }
            result['k0'] = 0.0
            for i in range(1, len(cleaned_reversed)):
                result[f'k{i}'] = cleaned_reversed[i]
    else:
        # 不强制过零点，直接 polyfit
        p = Polynomial.fit(x, y, degree)
        coefficients = p.convert().coef  # 从低阶到高阶排列
        y_pred = p(x)
        cleaned = handle_small_coefficients(coefficients)
        
        # 计算统计指标
        r2 = calc_r2(y, y_pred)
        r = np.sqrt(r2)
        rmse = np.sqrt(np.mean((y - y_pred) ** 2))
        residual_std = np.std(y - y_pred)
        
        # 卡方计算，避免除零错误
        y_pred_safe = np.where(np.abs(y_pred) < 1e-10, np.nan, y_pred)
        chi_squared_terms = ((y - y_pred) ** 2) / y_pred_safe
        chi_squared = np.nansum(chi_squared_terms)  # 忽略 NaN 值
        
        # 使用 statsmodels 计算置信区间
        confidence_95 = calculate_confidence_intervals(x, y, degree, force_zero=False)
        
        result = {
            "degree": degree,
            "R2": r2,
            "R": r,
            "coefficients": cleaned,
            "equation": generate_equation(cleaned, force_zero=False),
            "image_base64": plot_fit(x, y, y_pred),
            "standard_error": rmse,
            "confidence_95": confidence_95,
            "rmse": rmse,
            "residual_std": residual_std,
            "chi_squared": chi_squared,
        }
        
        # 添加各项系数
        for i, c in enumerate(cleaned):
            result[f'k{i}'] = c
            
    for k, v in result.items():
        result[k] = format_decimal_string(v)
    return result

def calc_r2(y_true, y_pred):
    """计算决定系数 R²"""
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return 1 - (ss_res / ss_tot)

def format_decimal_string(num):
    """
    将浮点数转换为格式化后的普通小数（非科学记数法）字符串。
    如果遇到无法转换的非数字类型，则返回其字符串形式。
    """
    if not isinstance(num, (float, int)):
        return num

    try:
        # 1. 使用 str() 转换浮点数，确保 Decimal 获得精确值
        d = Decimal(str(num))
        
        # 2. .to_eng_string() 转换为工程字符串（非科学记数法）
        s = d.to_eng_string()
        
        # 3. 清理：去除尾随零和单独的小数点
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
            
        # 4. 处理 "0" 或 "-0"
        if s in ["0", "-0"]:
            return "0"
            
        return s
        
    except Exception:
        # 异常捕获，避免 Decimal 无法处理的值导致程序崩溃
        return num

def generate_equation(coefficients, force_zero=0):
    """
    生成方程字符串，并将系数格式化为普通小数形式。
    :param coefficients: 系数列表 [k0, k1, k2, ...]
    :param force_zero: 如果为 1，则常数项 k0 强制为 0 (拟合过零点)
    :return: 方程字符串 (e.g., "y = 1.23 + 0.00045x")
    """
    terms = []
    has_non_zero = False

    for i, coef in enumerate(coefficients):
        # 强制过零点，跳过常数项（k0）
        if force_zero and i == 0:
            continue

        coef_val = float(coef) # 确保系数是浮点数，便于进行数值比较
        
        # 使用容差判断，避免浮点误差
        if abs(coef_val) < 1e-12:
            continue

        has_non_zero = True
        
        # 核心：使用新的格式化函数获取系数的字符串表示
        coef_str = format_decimal_string(coef_val)
        
        # 确定系数项的符号 (仅用于添加 ' + ' 或 ' - ')
        # 默认将所有项视为正项，后续再处理连接符号
        
        if i == 0:
            # 常数项
            term_str = coef_str
        elif i == 1:
            # 一次项 (x)
            term_str = f"{coef_str}x"
        else:
            # 高次项 (x^i)
            term_str = f"{coef_str}x^{i}"
        
        # 将带有符号的项添加到列表中
        if coef_val < 0 and terms:
            # 如果是负数且不是第一个项，用 ' - ' 连接，并使用系数的绝对值
            # 注意：在 format_decimal_string 中已经处理了负号，这里不需要再取 abs
            terms.append(f" - {term_str.lstrip('-')}")
        elif coef_val < 0 and not terms:
             # 如果是负数且是第一个项，直接添加
             terms.append(term_str)
        elif terms:
            # 如果是正数且不是第一个项，用 ' + ' 连接
            terms.append(f" + {term_str}")
        else:
            # 如果是正数且是第一个项，直接添加
            terms.append(term_str)

    # 如果所有系数都是 0，返回 "y = 0"
    if not has_non_zero:
        return "y = 0"

    # 将所有项连接起来
    return "y = " + "".join(terms).lstrip(" + ").lstrip(" - ")


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