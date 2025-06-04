from .error import Error

class APIException(Exception):
    def __init__(self, error: Error, message: str = None):
        self.code = error.value.code
        self.message = message or error.value.zh
        super().__init__(self.message)
