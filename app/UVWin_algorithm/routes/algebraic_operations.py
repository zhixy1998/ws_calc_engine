
"""
代数运算，用户自定义运算
"""
import numpy as np
from pydantic import BaseModel
from fastapi import APIRouter, Query
from simpleeval import simple_eval

from exceptions.error import ErrorCode
from exceptions.command_exception import APIException


router = APIRouter()

class OutPutSchema(BaseModel):
    code: int
    result: float

@router.get('', response_model=OutPutSchema)
def algebraic_operations(
    formula_string: str = Query(..., description="计算公式字符串，例如: (体积+0.9)/重量*稀释倍数"),
    independent_ariable_string: str = Query(..., description='自变量字符串集合：体积,重量,稀释倍数'),
    independent_ariable_value: str = Query(..., description='自变量依次对应的数值:2.0,3,1.5'),
):
    independent_ariable_string_list = independent_ariable_string.split(',')
    independent_ariable_value_list = independent_ariable_value.split(',')
    if len(independent_ariable_string_list) != len(independent_ariable_value_list):
        raise APIException(ErrorCode.INDEPENDENT_ARIABLE_STRING_VALUE_LENGTH_NOT_EQUAL)
    
    for v in independent_ariable_string_list:
        if v not in formula_string:
            raise APIException(ErrorCode.VARIABLE_NOT_IN_FORMULA)

    for v in independent_ariable_value_list:
        try:
            float(v)
        except APIException:
            raise APIException(ErrorCode.VARIABLE_VALUE_NOT_NUMERIC)
    
    variables = {}
    for i, v in enumerate(independent_ariable_string_list):
        variables[independent_ariable_string_list[i]] = independent_ariable_value_list[i]
    for var, val in variables.items():
        formula_string = formula_string.replace(var, str(val))
        
    # 计算表达式结果
    result = simple_eval(formula_string)
    return OutPutSchema(code=0, result=result)