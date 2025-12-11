import base64
from datetime import datetime

from django.db.models.deletion import sql
from ninja import Router, Schema
from django.db import transaction

from config import config
from utils.utils import generation_token
from apps.user_manage.user_manage_dal import t_s_group_dal, t_s_user_dal, t_s_user_group_dal, temporary_user_extra_info_dal
from apps.user_manage.utils import hash_password
from constants.user_constant import UserStatusConstant
from common.status_code_utils.fail_code import fail_code
from common.status_code_utils.success_code import success_code
from common.status_code_utils.message_utils import MessageUtils

router = Router()

class LoginInputSchema(Schema):
    password: str


class LoginOutSchema(Schema):
    code: int
    token: str = None


@router.post('/verify', response=LoginOutSchema)
def login(request, payload: LoginInputSchema):

    password = payload.password
    if password == config.admin_password:
        return {'code': 200, 'token': generation_token(user_id='admin')}
    # 直接把 FailCode 对象转成 dict 并解包给 LoginOutSchema
    return {'code': 410 }



class CreateUserInputSchema(Schema):
    username: str
    password: str
    use_time: str = None

class CreateUserOutSchema(Schema):
    code: int

@router.post('/create_user', response=CreateUserOutSchema)
def create_user(request, payload: CreateUserInputSchema):
    try:
        username = payload.username
        password = payload.password
        use_time = payload.use_time if payload.use_time else 60
        if t_s_user_dal.get_info_filters(filters={'username': username}):
            return {'code': 512}  # 用户已存在
        with transaction.atomic():
            temporary_group = t_s_group_dal.get_one_by_condition(condition={'group_name': '临时组'})
            temporary_group_id = temporary_group.get('id') if temporary_group else None
            if temporary_group_id:
                user_create_info = dict(
                    username=username,
                    password=hash_password(password),
                    status=UserStatusConstant.active.value,
                    real_name = username
                )
                created_user_info = t_s_user_dal.create_one_obj(create_info=user_create_info)
                create_user_id = created_user_info.get('id')
                if create_user_id:
                    user_group_instance = t_s_user_group_dal.create_one_obj(
                        create_info=dict(
                            user_id=create_user_id,
                            group_id=temporary_group_id,
                            create_time=datetime.now()
                        )
                    )
                    if not user_group_instance:
                        raise Exception('用户组创建失败')
                user_extra_create_info = {
                    'user_id': create_user_id,
                    'use_time': use_time,
                    'password': base64.b64encode(password.encode("utf-8")).decode("utf-8"),
                    'create_datetime': datetime.now()
                }
                if not temporary_user_extra_info_dal.create_one_obj(create_info=user_extra_create_info):
                    raise Exception('用户扩展信息创建失败')
        return  {'code': 200}
    except Exception as e:
        # 可以根据需要记录日志: logger.error(str(e))
        return {'code': 500}


class DeleteUserInputSchema(Schema):
    user_id: int

@router.post('/delete_user')
def delete_user(request, payload: DeleteUserInputSchema):
    try:
        with transaction.atomic():
            t_s_user_dal.update_by_id(o_id=payload.user_id, update_info={'status': UserStatusConstant.inactive.value})
            return {'code': 200}
    except Exception as e:
        return {'code': 511}


@router.get('/users')
def list_users(request, status: int):
    """
    status: 0-未激活，1-激活
    """
    user_infos = []
    temporary_group = t_s_group_dal.get_one_by_condition(condition={'group_name': '临时组'})
    temporary_group_id = temporary_group.get('id') if temporary_group else None
    if temporary_group_id:
        all_temporary_groups = t_s_user_group_dal.get_info_filters(filters={'group_id': temporary_group_id})
        user_ids = [group_info.get('user_id') for group_info in all_temporary_groups]
        if status == -1:
            sql_text = """
            select temporary_user_extra_info.*, t_sys_user.status, t_sys_user.username, t_sys_user.last_login_time from temporary_user_extra_info
            left join t_sys_user on temporary_user_extra_info.user_id = t_sys_user.id
            where temporary_user_extra_info.user_id in %(user_ids)s
            """
            user_infos = temporary_user_extra_info_dal.execute_prevent_injection_raw_sql(sql_text=sql_text, sql_param={'user_ids': tuple(user_ids)})
        else:
            sql_text = """
            select temporary_user_extra_info.*, t_sys_user.status, t_sys_user.username, t_sys_user.last_login_time from temporary_user_extra_info
            left join t_sys_user on temporary_user_extra_info.user_id = t_sys_user.id
            where temporary_user_extra_info.user_id in %(user_ids)s and t_sys_user.status = %(status)s
            """
            user_infos = temporary_user_extra_info_dal.execute_prevent_injection_raw_sql(sql_text=sql_text, sql_param={'user_ids': tuple(user_ids), 'status': status})
#   {
#     key: "1",
#     name: "John Brown",
#     password: 32,
#     login_time: "2025-12-01 10:00:00",
#     status: "删除",
#     allowed_time: "120 分钟",
#   },
    new_user_infos = []
    for user_info in user_infos:
        allowed_time_str = f"{user_info.get('use_time')} 分钟"
        new_user_info = {
            'key': str(user_info.get('user_id')),
            'name': user_info.get('username'),
            'password': base64.b64decode(user_info.get('password').encode("utf-8")).decode("utf-8"),
            'login_time': user_info.get('last_login_time').strftime("%Y-%m-%d %H:%M:%S") if user_info.get('last_login_time') else '未登录',
            'status': user_info.get('status'),
            'allowed_time': allowed_time_str,
        }
        new_user_infos.append(new_user_info)
    return {'code': 200, 'user_infos': new_user_infos}

