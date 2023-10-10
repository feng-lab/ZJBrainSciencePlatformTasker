import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_crudrouter import OrmarCRUDRouter
from loguru import logger
from ormar import NoMatch
from zjbs_file_client import close_client, init_client

from zjbs_tasker.api import router as api_router
from zjbs_tasker.db import Task, TaskRun, TaskTemplate, database
from zjbs_tasker.model import BaseTaskRun, CreateTask, CreateTaskTemplate
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


# 数据库
@app.on_event("startup")
async def connect_database() -> None:
    if not database.is_connected:
        await database.connect()


@app.on_event("shutdown")
async def disconnect_database() -> None:
    if database.is_connected:
        await database.disconnect()


# 文件服务客户端
@app.on_event("startup")
async def start_file_client() -> None:
    await init_client(settings.FILE_SERVICE_URL, timeout=60)


@app.on_event("shutdown")
async def close_file_client() -> None:
    await close_client()


# API 定义
@app.get("/")
async def index() -> RedirectResponse:
    if settings.DEBUG_MODE:
        return RedirectResponse("/docs")
    raise HTTPException(status_code=404, detail="/ Not Found")


app.include_router(api_router)

# CRUD Router
app.include_router(OrmarCRUDRouter(Task, create_schema=CreateTask, tags=["crud"]))
app.include_router(OrmarCRUDRouter(TaskTemplate, create_schema=CreateTaskTemplate, tags=["crud"]))
app.include_router(OrmarCRUDRouter(TaskRun, create_schema=BaseTaskRun, tags=["crud"]))


@app.exception_handler(NoMatch)
def handle_no_match(_request: Request, exception: NoMatch) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Not Found", "exception": str(exception)})
