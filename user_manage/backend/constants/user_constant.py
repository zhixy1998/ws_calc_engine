from .base_constant import StorageInfo, MessageType

class TemplateBookMarkType(StorageInfo):
    text = MessageType(decs='文字', value=0, name='text')
    sheet = MessageType(decs='表格', value=1, name='sheet')
    img = MessageType(decs='图片', value=2, name='img')

class UserStatusConstant(StorageInfo):
    active = MessageType(decs='激活', value=1, name='active')
    inactive = MessageType(decs='未激活', value=0, name='inactive')