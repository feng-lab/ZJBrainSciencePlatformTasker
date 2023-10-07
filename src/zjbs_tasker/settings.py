from pathlib import Path

from pydantic import BaseSettings


class Settings(BaseSettings):
    # 调试模式
    DEBUG_MODE: bool = False

    # 日志目录
    LOG_DIR: Path = Path(__file__).parent.parent.parent / "debug_data" / "log" / "tasker"

    # 数据库URL
    DATABASE_URL: str = "postgresql://zjlab:zjlab2023@localhost:7100/zjbs-tasker"
    # 文件服务器URL
    FILE_SERVICE_URL: str = "http://localhost:7200"
    # Redis服务IP和端口
    REDIS_HOST_PORT: str = "localhost:7300"

    # 工作进程目录
    WORKER_DIR: Path = Path(__file__).parent.parent.parent / "debug_data" / "worker"


settings: Settings = Settings()
