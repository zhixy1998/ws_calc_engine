# -*- coding: utf-8 -*-
# @Time    : 2022/1/11 下午6:30
# @Author  : huanghaohao
# @Email   : haohao.huang@easytransfer.cn
# @File    : fail_code.py
# @Software: PyCharm
"""失败的状态码, 返回码大于400为错误, 小于400为成功  """
from django.db.models import F
from common.status_code_utils.message_utils import MessageUtils


class FailCode(object):

    @property
    def password_error(self, request):
        return {'code':410, 'message': '密码错误'}

fail_code = FailCode()