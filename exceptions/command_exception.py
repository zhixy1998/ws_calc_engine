from .error import Error

class APIException(Exception):
    def __init__(self, error: Error):
        self.code = error.value.code
        self.message = error.value.zh
