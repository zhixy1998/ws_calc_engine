from ninja import NinjaAPI, Schema, Router
from apps.user_manage.router import user_manage_router

api = NinjaAPI()

# @api.get('/hello')
# def hello(request):
#     return "hello world"


# @api.get('hello_name')
# def hello_name(request, name='world'):
#     return f"hello {name}"

# # 输入类型
# @api.get('/math')
# def math(request, a:int, b:int):
#     return {'add': a+b, 'multiply': a*b}

# # 通过路径字符串传参 /api/math/2and3
# @api.get('/math/{a}and{b}')
# def math(request, a:int, b:int):
#     return {'add': a+b, 'multiply': a*b}

# # post 请求
# class HelloSchema(Schema):
#     name: str = 'world'

# @api.post('/hello')
# def hello2(request, data: HelloSchema):
#     return f'hello {data.name}'

api.add_router('', user_manage_router)
