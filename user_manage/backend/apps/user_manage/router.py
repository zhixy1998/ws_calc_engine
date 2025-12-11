from ninja import Router
# from .apis.login_view import login_view
from .apis.user_manage_view import router

user_manage_router = Router()

# user_manage_router.add_router('/login', login_view)
user_manage_router.add_router('', router)
