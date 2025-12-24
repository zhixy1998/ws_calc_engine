import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scripts_manage import *
from datetime import datetime, timedelta

from constants.user_constant import UserStatusConstant
from apps.user_manage.user_manage_dal import t_s_user_dal, temporary_user_extra_info_dal

def sync_t_800_user_status():
    now = datetime.now()
    sql_text = """
    select temporary_user_extra_info.use_time, t_sys_user.id, t_sys_user.status, t_sys_user.last_login_time, t_sys_user.username
    from temporary_user_extra_info 
    inner join t_sys_user on 
    temporary_user_extra_info.user_id = t_sys_user.id where t_sys_user.status = %(status)s
    """
    user_infos = t_s_user_dal.execute_prevent_injection_raw_sql(sql_text=sql_text, sql_param={'status': UserStatusConstant.active.value})
    for user_info in user_infos:
        # print(user_info)
        use_time = user_info.get('use_time')
        user_id = user_info.get('id')
        username = user_info.get('username')
        last_login_time = user_info.get('last_login_time')
        if last_login_time:
            expire_time = last_login_time + timedelta(minutes=use_time)
            if now >= expire_time:
                print('用户id:{} 名称: {} 已过期，更新状态为未激活'.format(user_id, username), '过期时间:{}'.format(expire_time))
                t_s_user_dal.update_by_id(o_id=user_id, update_info={'status': UserStatusConstant.inactive.value})
            else:
                print('用户id:{}, 名称: {} 未过期，继续保持激活状态'.format(user_id, username), '过期时间:{}'.format(expire_time))
        else:
            print('用户id:{}, 名称: {} 未登录过，继续保持激活状态'.format(user_id, username))


if __name__ == "__main__":
    sync_t_800_user_status()