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
    FILE_SERVER_URL: str = "http://localhost:7200"
    # Redis服务IP和端口
    REDIS_HOST_PORT: str = "localhost:7300"

    # 服务器工作目录
    SERVER_WORKING_DIR: Path = Path(__file__).parent.parent.parent / "debug_data" / "server"
    # 工作进程目录
    WORKER_WORKING_DIR: Path = Path(__file__).parent.parent.parent / "debug_data" / "worker"


settings: Settings = Settings()


# 文件服务器路径
class FileServerPath:
    # 基本路径
    BASE_DIR: str = "/tasker"
    # 任务解释器
    TASK_INTERPRETER_DIR: str = f"{BASE_DIR}/interpreter"
    # 任务模板
    TASK_TEMPLATE_DIR: str = f"{BASE_DIR}/template"
    # 任务
    TASK_DIR: str = f"{BASE_DIR}/task"

    @staticmethod
    def task_interpreter_path(interpreter_id: int, interpreter_name: str) -> str:
        return f"{FileServerPath.TASK_INTERPRETER_DIR}/{interpreter_id}_{interpreter_name}.txz"

    @staticmethod
    def task_template_path(template_id: int, template_name: str) -> str:
        return f"{FileServerPath.TASK_TEMPLATE_DIR}/{template_id}_{template_name}.txz"

    @staticmethod
    def task_dir(task_id: int, task_name: str) -> str:
        return f"{FileServerPath.TASK_DIR}/{task_id}_{task_name}"

    @staticmethod
    def task_source_path(task_id: int, task_name: str) -> str:
        return f"{FileServerPath.task_dir(task_id, task_name)}/source.txz"

    @staticmethod
    def task_run_dir(task_id: int, task_name: str, task_run_index: int) -> str:
        return f"{FileServerPath.task_dir(task_id, task_name)}/run_{task_run_index}"
