TASKER_BASE_DIR: str = "/tasker"
TASK_BASE_DIR: str = f"{TASKER_BASE_DIR}/task"
TASK_TEMPLATE_BASE_DIR: str = f"{TASKER_BASE_DIR}/template"


def get_task_dir(task_id: int, task_name: str) -> str:
    return f"{TASK_BASE_DIR}/{task_id}_{task_name}"


def get_task_source_dir(task_id: int, task_name: str) -> str:
    task_dir = get_task_dir(task_id, task_name)
    return f"{task_dir}/source"


def get_task_run_dir(task_id: int, task_name: str, task_run_index: int) -> str:
    task_dir = get_task_dir(task_id, task_name)
    return f"{task_dir}/run_{task_run_index}"
