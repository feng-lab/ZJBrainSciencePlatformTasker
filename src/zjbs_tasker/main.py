import logging
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_crudrouter import OrmarCRUDRouter
from loguru import logger
from ormar import Model, NoMatch
from zjbs_file_client import close_client, init_client

from zjbs_tasker.api import router as api_router
from zjbs_tasker.api.interpreter import router as interpreter_router
from zjbs_tasker.db import Task, TaskRun, TaskTemplate, database
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
    await init_client(settings.FILE_SERVER_URL, timeout=60)


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
app.include_router(interpreter_router)


# CRUD Router
def crud_router(model: type[Model], *include: str) -> None:
    create_update_schema = model.get_pydantic(include=set(include))
    # noinspection PyTypeChecker
    app.include_router(
        OrmarCRUDRouter(
            model,
            prefix=model.__name__,
            create_schema=create_update_schema,
            update_schema=create_update_schema,
            tags=["CRUD"],
        )
    )


crud_router(TaskTemplate, "interpreter", "name", "description", "argument", "environment")
crud_router(Task, "template", "name", "argument", "environment", "retry_times")
crud_router(TaskRun, "task", "index", "status", "start_at", "end_at")


@app.exception_handler(NoMatch)
def handle_no_match(_request: Request, exception: NoMatch) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Not Found", "exception": str(exception)})
