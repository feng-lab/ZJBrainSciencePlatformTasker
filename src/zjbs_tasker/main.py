import logging
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from loguru import logger
from ormar import NoMatch
from zjbs_file_client import close_client, init_client

from zjbs_tasker.api.interpreter import router as interpreter_router
from zjbs_tasker.api.task import router as task_router
from zjbs_tasker.api.template import router as template_router
from zjbs_tasker.db import database
from zjbs_tasker.settings import settings

app: FastAPI = FastAPI(title="ZJBrainSciencePlatform Tasker", description="之江实验室 Brain Science 平台任务平台")

# 中间件
app.add_middleware(GZipMiddleware, minimum_size=1024)

# 日志
logger.remove()
LOG_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss.SSS}|{level}|{name}:{function}:{line}|{message}"
logger.add(
    settings.LOG_DIR / "app.log", level="INFO", format=LOG_FORMAT, rotation="1 day", retention="14 days", enqueue=True
)
if settings.DEBUG_MODE:
    logger.add(sys.stdout, level="DEBUG", format=LOG_FORMAT, diagnose=True, enqueue=True)
    logging.basicConfig()
    logging.getLogger("databases").setLevel(logging.DEBUG)


# 初始化
@app.on_event("startup")
async def startup() -> None:
    if not database.is_connected:
        await database.connect()

    await init_client(settings.FILE_SERVER_URL, timeout=60)


# 释放资源
@app.on_event("shutdown")
async def shutdown() -> None:
    if database.is_connected:
        await database.disconnect()

    await close_client()


# API 定义
@app.get("/")
async def index() -> RedirectResponse:
    if settings.DEBUG_MODE:
        return RedirectResponse("/docs")
    raise HTTPException(status_code=404, detail="/ Not Found")


app.include_router(task_router)
app.include_router(interpreter_router)
app.include_router(template_router)


@app.exception_handler(NoMatch)
def handle_no_match(_request: Request, exception: NoMatch) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Not Found", "exception": str(exception)})


@app.exception_handler(Exception)
def handle_exception(_request: Request, exception: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "exception": str(exception)})
