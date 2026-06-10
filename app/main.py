from fastapi import FastAPI
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.db import init_db
from app.user.routes import router as user_router
from app.UVWin_algorithm.routes import router as UVWin_algorithm_router
from app.dog.routes import router as dog_router
from exceptions.command_exception import APIException

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

# app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(UVWin_algorithm_router, prefix='')
app.include_router(user_router, prefix='')
app.include_router(dog_router, prefix='')


@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=200,  # 固定返回 200
        content={
            "code": exc.code,
            "message": exc.message
        }
    )