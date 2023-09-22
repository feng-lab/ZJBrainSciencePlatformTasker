from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZJBS_TASKER_")

    # 调试模式
    DEBUG_MODE: bool = False

    # 日志目录
    LOG_DIR: Path = Path(__file__).parent.parent.parent / "debug_data"


settings: Settings = Settings()
