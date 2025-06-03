from fastapi import APIRouter
from .user import router

router = APIRouter()

router.include_router(router, prefix="/user", tags=["用户视图"])


