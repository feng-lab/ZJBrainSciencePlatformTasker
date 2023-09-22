import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse
from loguru import logger

from zjbs_tasker.settings import settings

app: FastAPI = FastAPI(title="ZJBrainSciencePlatform Tasker", description="之江实验室 Brain Science 平台任务平台")

# 中间件
app.add_middleware(GZipMiddleware, minimum_size=1024)

# 配置日志
logger.remove()
LOG_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss.SSS}|{level}|{name}:{function}:{line}|{message}"
logger.add(
    settings.LOG_DIR / "app.log", level="INFO", format=LOG_FORMAT, rotation="1 day", retention="14 days", enqueue=True
)
if settings.DEBUG_MODE:
    logger.add(sys.stdout, level="DEBUG", format=LOG_FORMAT, diagnose=True, enqueue=True)


# 根目录
@app.get("/")
async def index() -> RedirectResponse:
    if settings.DEBUG_MODE:
        return RedirectResponse("/docs")
    raise HTTPException(status_code=404, detail="/ Not Found")
