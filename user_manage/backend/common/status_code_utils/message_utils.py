# -*- coding: utf-8 -*-
# @Time    : 2022/1/11 下午5:42
# @Author  : huanghaohao
# @Email   : haohao.huang@easytransfer.cn
# @File    : message_utils.py
# @Software: PyCharm


class MessageUtils(object):
    common_success_message = 'submitted successfully' # 通用语言成功提示语
    common_error_message = "network error"   # 通用失败提示语

    def __init__(self, status_code, message_dict, is_format=False, **kwargs):
        self.status_code = status_code
        for message, language_list in message_dict.items():
            for language in language_list:
                setattr(self, f'{language}_message', message)
        self.is_format = is_format  # 是否需要填充字符串

    def get_message(self, language, common_message_type='success', format_message=None):
        language_key = f"{language}_message"
        common_message = self.common_success_message if common_message_type == 'success' else self.common_error_message
        message = getattr(self, language_key, common_message)
        if self.is_format:
            message = message.format(**format_message)
        return message

    def as_dict(self, language: str = 'zh', common_message_type: str = 'error', code_field: str = 'code', message_field: str = 'message') -> dict:
        """返回一个可直接用于 Schema 解包的字典。

        例: `LoginOutSchema(**FailCode.password_error.as_dict('zh'))`
        返回: {'code': 410, 'message': '密码错误'}
        """
        return {
            code_field: self.status_code,
            message_field: self.get_message(language, common_message_type=common_message_type),
        }

    def __call__(self, language: str = 'zh', common_message_type: str = 'error', code_field: str = 'code', message_field: str = 'message') -> dict:
        """允许直接通过调用 MessageUtils 实例生成字典：

        例如: `FailCode.password_error('en')` 或 `FailCode.password_error()`
        """
        return self.as_dict(language=language, common_message_type=common_message_type, code_field=code_field, message_field=message_field)

