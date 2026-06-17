from fastapi import APIRouter
from fastapi import HTTPException
from pydantic import BaseModel, Field
from ..gmp_dog import GmpDog
import sys

router = APIRouter()

class InputSchema(BaseModel):
    bid: str


class OutputSchema(BaseModel):
    status_code: int = Field(..., description="状态码，200表示成功，400表示失败")
    message: str = Field(None, description="返回消息，成功时为空字符串，失败时包含错误信息")
    error: str = Field(None, description="错误详情，成功时为空字符串，失败时包含具体错误信息")
    

@router.post('/bind_dog', response_model=OutputSchema)
def bind_dog(input: InputSchema):
    if not sys.platform.startswith('win'):
        raise HTTPException(status_code=400, detail='当前环境不支持密码狗接口（仅 Windows）')

    bid = input.bid
    dog = GmpDog()
    if dog.findDog():
        if dog.setBindId(bid):
            return OutputSchema(status_code=200)
        else:
            return OutputSchema(status_code=400, message='绑定失败', error=dog.getLastError())
    else:
        return OutputSchema(status_code=400, message='未找到狗', error=dog.getLastError())