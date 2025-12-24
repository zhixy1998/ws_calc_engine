"""
代数运算，用户自定义运算
"""
import numpy as np
import re
from pydantic import BaseModel, Field
from fastapi import APIRouter

import sympy as sp
from sympy import sympify
from sympy.parsing.latex import parse_latex

from exceptions.error import ErrorCode
from exceptions.command_exception import APIException


router = APIRouter()

class InputSchema(BaseModel):
    formula_string: str = Field(..., description="计算公式字符串，支持普通表达式和LaTeX格式", json_schema_extra={'example':'(体积+0.9)/重量*稀释倍数'})
    independent_variable_string: str = Field(..., description='自变量字符串集合：体积,重量,稀释倍数', json_schema_extra={'example':'体积,重量,稀释倍数'})
    independent_variable_value: str = Field(..., description='自变量依次对应的数值:2.0,3,1.5', json_schema_extra={'example':'2.0,3,1.5'})

class OutPutSchema(BaseModel):
    code: int
    result: float


@router.post('', response_model=OutPutSchema)
def algebraic_operations(data: InputSchema):
    independent_variable_string_list = [v.strip() for v in data.independent_variable_string.split(',')]
    independent_variable_value_list = [v.strip() for v in data.independent_variable_value.split(',')]
    
    print(f"原始公式: {data.formula_string}")
    print(f"变量列表: {independent_variable_string_list}")
    print(f"数值列表: {independent_variable_value_list}")

    # 检查变量和数值列表长度是否一致
    if len(independent_variable_string_list) != len(independent_variable_value_list):
        raise APIException(ErrorCode.INDEPENDENT_ARIABLE_STRING_VALUE_LENGTH_NOT_EQUAL)
    
    # 使用sympy解析公式，传递变量列表用于预处理
    try:
        expr = parse_formula_with_sympy(data.formula_string, independent_variable_string_list)
    except Exception as e:
        print(f"公式解析错误: {e}")
        raise APIException(ErrorCode.INVALID_ARGUMENT)
    
    # 从表达式中提取变量
    formula_variables = extract_variables_from_sympy_expr(expr)
    print(f"公式中的变量: {formula_variables}")
    
    # 检查所有提供的变量是否在公式中存在
    # for v in independent_variable_string_list:
    #     if v not in formula_variables:
    #         raise APIException(ErrorCode.VARIABLE_NOT_IN_FORMULA)

    # 检查变量值是否为数字
    for v in independent_variable_value_list:
        try:
            float(v)
        except ValueError:
            raise APIException(ErrorCode.VARIABLE_VALUE_NOT_NUMERIC)
    
    # 构建变量字典
    variable_dict = {}
    for i, var_name in enumerate(independent_variable_string_list):
        variable_dict[var_name] = independent_variable_value_list[i]
    
    # 使用sympy进行计算
    result = substitute_and_evaluate(expr, variable_dict)
    
    return OutPutSchema(code=200, result=result)


def is_latex_formula(formula_string):
    """
    判断是否为LaTeX公式
    """
    latex_patterns = [
        r'\\frac\{',
        r'\\left',
        r'\\right',
        r'\\cdot',
        r'\\times',
        r'\\sqrt\{',
        r'\^{',
        r'\\sum',
        r'\\int',
        r'\\alpha',
        r'\\beta',
        r'\\gamma'
    ]

    return any(re.search(pattern, formula_string) for pattern in latex_patterns)


def create_safe_variable_mapping(variable_list):
    """
    为带数字的变量创建安全的临时映射
    使用希腊字母和特殊符号作为临时变量，避免被sympy拆分
    """
    # 使用希腊字母作为临时变量（sympy认识这些符号）
    greek_letters = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta', 
                    'iota', 'kappa', 'lambda', 'mu', 'nu', 'xi', 'omicron', 'pi', 
                    'rho', 'sigma', 'tau', 'upsilon', 'phi', 'chi', 'psi', 'omega']
    
    variable_mapping = {}
    temp_to_original = {}
    
    for i, var in enumerate(variable_list):
        if re.match(r'^[A-Za-z]+\d+$', var):  # 匹配字母+数字的变量名
            if i < len(greek_letters):
                temp_var = greek_letters[i]
            else:
                # 如果希腊字母不够用，使用下标形式
                temp_var = f"x_{i}"
            
            variable_mapping[var] = temp_var
            temp_to_original[temp_var] = var
    
    return variable_mapping, temp_to_original

def preprocess_latex_with_safe_variables(latex_formula, variable_list):
    """
    使用安全的变量替换预处理LaTeX公式
    """
    variable_mapping, temp_to_original = create_safe_variable_mapping(variable_list)
    
    processed_formula = latex_formula
    for original_var, temp_var in variable_mapping.items():
        # 使用LaTeX希腊字母语法
        latex_temp_var = f"\\{temp_var}" if temp_var in ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta', 
                                                         'iota', 'kappa', 'lambda', 'mu', 'nu', 'xi', 'omicron', 'pi', 
                                                         'rho', 'sigma', 'tau', 'upsilon', 'phi', 'chi', 'psi', 'omega'] else temp_var
        processed_formula = processed_formula.replace(original_var, latex_temp_var)
    
    return processed_formula, temp_to_original

def postprocess_sympy_expression(expr, temp_to_original):
    """
    将sympy表达式中的临时变量替换回原始变量
    """
    # 创建符号替换字典
    substitutions = {}
    for temp_var, original_var in temp_to_original.items():
        temp_symbol = sp.Symbol(temp_var)
        original_symbol = sp.Symbol(original_var)
        substitutions[temp_symbol] = original_symbol
    
    # 进行符号替换
    return expr.subs(substitutions)

def parse_formula_with_sympy(formula_string, variable_list=None):
    """
    使用sympy解析公式（支持LaTeX和普通表达式）
    """
    try:
        if is_latex_formula(formula_string):
            print(f"检测到LaTeX公式: {formula_string}")
            
            if variable_list:
                # 使用安全的变量替换
                processed_formula, temp_to_original = preprocess_latex_with_safe_variables(formula_string, variable_list)
                print(f"安全替换后公式: {processed_formula}")
                
                # 使用sympy的LaTeX解析器
                expr = parse_latex(processed_formula)
                print(f"LaTeX解析结果: {expr}")
                
                # 恢复原始变量名
                expr = postprocess_sympy_expression(expr, temp_to_original)
                print(f"变量名恢复后: {expr}")
            else:
                # 直接解析
                expr = parse_latex(formula_string)
                print(f"LaTeX解析结果: {expr}")
        else:
            print(f"检测到普通表达式: {formula_string}")
            # 使用sympy的普通表达式解析器
            expr = sympify(formula_string)
            print(f"普通表达式解析结果: {expr}")
        
        return expr
    except Exception as e:
        print(f"公式解析失败: {e}")
        raise APIException(ErrorCode.INVALID_ARGUMENT)


def extract_variables_from_sympy_expr(expr):
    """
    从sympy表达式中提取变量
    """
    return [str(symbol) for symbol in expr.free_symbols]


def substitute_and_evaluate(expr, variable_dict):
    """
    使用sympy进行变量替换和计算，保留合理的小数精度
    """
    try:
        # 创建sympy符号
        sympy_subs = {}
        for var_name, var_value in variable_dict.items():
            symbol = sp.Symbol(var_name)
            # 使用 Decimal 来保持精度
            sympy_subs[symbol] = sp.Float(var_value)

        print(f"变量替换: {sympy_subs}")

        # 进行替换
        substituted_expr = expr.subs(sympy_subs)
        print(f"替换后表达式: {substituted_expr}")

        # 计算结果并使用 N 函数控制精度
        # 这里使用 15 位小数精度，可以根据需要调整
        result = float(sp.N(substituted_expr, 15))
        # print(f"计算结果: {result}")

        # 四舍五入到合理的小数位
        # 这里使用 10 位小数，可以根据需要调整
        return round(result, 10)
    except Exception as e:
        print(f"计算失败: {e}")
        raise APIException(ErrorCode.OPERATION_FAILED)
