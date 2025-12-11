import base64
import datetime
import json, time
import jwt
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from common.message_info import MESSAGE_DICT

class Middleware(MiddlewareMixin):

    def __call__(self, request, **kwargs):
        login_verify_status = self.verify_login_validity(request)
        request.user_id = login_verify_status['user_id']  # 成功就返回用户的user 否则返回用户的
        if login_verify_status['result'] is False:
            return JsonResponse({'code': 401})
        response = self.get_response(request)
        return self.process_response(request, response)

    
    def verify_login_validity(self, request):
        token_key = request.META.get('HTTP_AUTHORIZATION', None)
        request_path = request.path
        url_info = settings.AUTHENTICATION_SKIP_URL.get(request_path)
        status = self.verify_bearer_token(token_key=token_key)
        if url_info and request.method in url_info:
            # 如果url在忽略token验证的路由和方法里，就不进行token验证
            status['result'] = True
        
        return status
    
    def verify_bearer_token(self, token_key):
        if not token_key:
            return {'user_id': None, 'result': False}
        token = token_key.split(' ')[1]
        result = self.verify_token(token=token)
        if result:
            is_expire = self.checkout_token_time(result.get('exp_time'))
            if not is_expire:  # 没过期
                return {'user_id': result.get('user_id'), 'result': True}
            return {'user_id': None, 'result': False}
        else:
            return {'user_id': None, 'result': False}
    
    def verify_token(self, token):
        result = jwt.decode(token, settings.SECRET_KEY, algorithms='HS256')
        return result

    def checkout_token_time(self, exp_time):
        if exp_time > (time.time()):
            return False
        return True
    
    def process_response(self, request, response):
        # 仅处理 JsonResponse
        try:
            data = json.loads(response.content)
        except json.JSONDecodeError:
            return response

        # 获取语言类型
        lang = self._get_request_language(request)
        # 根据 code 添加或覆盖 message
        code = data.get('code')
        if code is not None:
            message = self._get_message(code, lang)
            data['message'] = message
            response.content = json.dumps(data)
        return response

    def _get_request_language(self, request):
        """从请求参数或头中解析语言类型"""
        # 优先级：请求参数 > Accept-Language 头
        lang = request.GET.get('lang')
        if not lang:
            accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', 'en')
            lang = accept_language.split(',')[0].split(';')[0].strip().lower()
        # 简化为支持 'en' 或 'zh'
        return 'zh' if lang.startswith('zh') else 'en'

    def _get_message(self, code, lang):
        """根据错误码和语言返回文案"""
        try:
            return MESSAGE_DICT.get(code, 'Unknown error').get(lang)
        except Exception as e:
            return 'success' if lang == 'en' else '操作成功'
