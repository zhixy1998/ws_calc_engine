# -*- coding: utf-8 -*-
# @Time    : 2022/1/11 下午5:41
# @Author  : huanghaohao
# @Email   : haohao.huang@easytransfer.cn
# @File    : success_code.py
# @Software: PyCharm
"""成功的状态码, 返回码大于400为错误, 小于400为成功  """
from common.status_code_utils.message_utils import MessageUtils


class SuccessCode(object):
    
    @property
    def success(self, request=None):
        return {'code':200, 'message': '成功'}

success_code = SuccessCode()