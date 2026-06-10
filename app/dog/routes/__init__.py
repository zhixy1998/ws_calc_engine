from fastapi import APIRouter
from .find_dog import router as find_dog_router
from .bind_dog import router as bind_dog_router

router = APIRouter()

router.include_router(find_dog_router, prefix='/dog', tags=['寻找狗和查询绑定ID'])
router.include_router(bind_dog_router, prefix='/dog', tags=['绑定ID'])
