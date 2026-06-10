from fastapi import APIRouter
from ..gmp_dog import GmpDog
from pydantic import BaseModel, Field

router = APIRouter()

class OutputSchema(BaseModel):
    status_code: int = Field(..., description="状态码，200表示成功，400表示失败")
    message: str = Field(None, description="返回消息，成功时为空字符串，失败时包含错误信息")
    has_dog: bool = Field(..., description="是否找到狗")
    bid: str = Field('', description="绑定ID，如果没有找到狗或绑定ID为new_dog，则返回空字符串")

@router.get('/find_dog', response_model=OutputSchema)
def find_dog():
    dog = GmpDog()
    has_dog = False
    bid = ''
    if dog.findDog():
        has_dog = True
        bid = dog.getBindId()
        if bid == 'new_dog':
            bid = ''
        return OutputSchema(status_code=200, message='', has_dog=has_dog, bid=bid)
    return OutputSchema(status_code=400, message='未找到狗', has_dog=has_dog, bid=bid)