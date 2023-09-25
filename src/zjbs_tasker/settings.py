from pathlib import Path

from pydantic import BaseSettings


class Settings(BaseSettings):
    # 调试模式
    DEBUG_MODE: bool = False

    # 日志目录
    LOG_DIR: Path = Path(__file__).parent.parent.parent / "debug_data"

    # 数据库URL
    DATABASE_URL: str = "sqlite:///debug_data/data.sqlite"


settings: Settings = Settings()
