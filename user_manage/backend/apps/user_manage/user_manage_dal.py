from utils.base_dal import BaseDal
from .models import TSysUser, TSysGroup, TSysUserGroup, TemporaryUserExtraInfo

class TSysUserDal(BaseDal):
    def __init__(self):
        super().__init__(TSysUser)


class TSysGroupDal(BaseDal):
    def __init__(self):
        super().__init__(TSysGroup)


class TSysUserGroupDal(BaseDal):
    def __init__(self):
        super().__init__(TSysUserGroup)

class TemporaryUserExtraInfoDal(BaseDal):
    def __init__(self):
        super().__init__(TemporaryUserExtraInfo)

t_s_user_dal = TSysUserDal()
t_s_group_dal = TSysGroupDal()
t_s_user_group_dal = TSysUserGroupDal()
temporary_user_extra_info_dal = TemporaryUserExtraInfoDal()