class MessageType(object):
    def __init__(self, decs, value, name, group=None, order=0,database_name=None,number=None):
        self.decs = decs
        self.value = value
        self.name = name
        self.group = group if group else list()
        self.order = order or 0
        self.database_name = database_name
        self.number = number

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        return None

class MetaStorageInfo(type):
    """
    meta class
    """

    def __new__(mcl, name, base, cdt):
        """
        生成类的时候添加俩个属性 get_message_info， message_list
        :param name:
        :param base:
        :param cdt:
        :return:
        """
        get_message_info = dict()
        message_list = list()
        for key, val in cdt.items():
            if isinstance(val, (MessageType,)):
                get_message_info[val.value] = val
                message_list.append(val)
        cdt['get_message_info'] = get_message_info
        cdt['message_list'] = message_list
        return super(MetaStorageInfo, mcl).__new__(mcl, name, base, cdt)

class StorageInfo(metaclass=MetaStorageInfo):
    @classmethod
    def get_message_by_attr(cls, attr):
        """
        返回所有属性的值
        :param attr:
        :return: list
        """
        if not isinstance(attr, str) or attr not in ['name', 'decs', 'value']:
            return []
        return [i[attr] for i in cls.message_list]

    @classmethod
    def get_name_desc_by_value(cls, value):
        """
        根据数据库保存的value返回desc
        :param value:
        :return:
        """
        if type(value) != int:
            return ''

        if value not in cls.get_message_by_attr('value'):
            return ''
        return cls.get_message_info[value].decs

    @classmethod
    def generate_decs_value_map(cls):
        """
        根据数据库保存的value返回desc
        :param value:
        :return:
        """
        return {mess.decs: mess.value for mess in cls.message_list}

    @classmethod
    def generate_name_value_map(cls):
        """
        根据数据库保存的value返回desc
        :param value:
        :return:
        """
        return {mess.name: mess.value for mess in cls.message_list}
    @classmethod
    def generate_value_desc_map(cls):
        """
        根据数据库保存的value返回desc
        :param value:
        :return:
        """
        return {mess.value: mess.decs for mess in cls.message_list}
    @classmethod
    def get_message_by_desc(cls, decs):
        """
        根据desc获取value
        :param value:
        :return:
        """
        mess = ''
        for mess in cls.message_list:
            if decs == mess.decs:
                mess = mess
                break

        return mess

    @classmethod
    def get_name_by_value(cls, value):
        """
        根据数据库保存的value返回name
        :param value:
        :return:
        """
        if type(value) != int:
            return ''

        if value not in cls.get_message_by_attr('value'):
            return ''
        return cls.get_message_info[value].name
    @classmethod
    def get_value_by_name(cls, name):
        """
        根据数据库保存的value返回name
        :param value:
        :return:
        """

        if name not in cls.get_message_by_attr('name'):
            return ''
        return { i.name:i.value for i in  cls.message_list}.get(name)

    @classmethod
    def get_database_name_by_name(cls, name):
        """
        根据数据库保存的name返回database_name
        :param name:
        :return:
        """
        if type(name) != str:
            return ''

        if name not in cls.get_message_by_attr('name'):
            return ''
        return cls.get_message_info[name].database_name
    @classmethod
    def get_group(cls, group_name, attr, all=False):
        """
        获取组的常量信息
        :param group_name: 组名
        :param attr: 属性
        :param all: 返回类型
        :return: 列表
        """
        if not isinstance(attr, str) or attr not in ['name', 'decs', 'value']:
            return []
        return [i[attr] for i in cls.message_list if group_name in i.group] if not all else [i for i in cls.message_list
                                                                                             if group_name in i.group]

    @classmethod
    def get_group_key_val(cls, group_name, key, value):
        """
        获取组的常量信息
        :param group_name: 组名
        :param key: key
        :param val: val
        :return: dict
        """
        if not isinstance(key, str) or key not in ['name', 'decs', 'value']:
            return []
        return {i[key]: i[value] for i in cls.message_list if group_name in i.group}

    @classmethod
    def get_dict(cls, key='name', value='value'):
        return {info[key]:info[value] for info in sorted(cls.message_list, key=lambda x:x.order)}

    @classmethod
    def get_dict_list(cls):
        data_list = list()
        for info in cls.message_list:
            data = {'value': info['value'], 'text': info['name']}
            data_list.append(data)
        return data_list

    @classmethod
    def name_query_number(cls,name):
        """
        根据数据库保存的value返回desc
        :param value:
        :return:
        """
        data={mess.name: mess.number for mess in cls.message_list}
        number=data.get(name)
        number=number if number else ""
        return number