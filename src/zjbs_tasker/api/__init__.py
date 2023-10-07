from zjbs_tasker.db import Task, TaskTemplate

TASKER_BASE_DIR: str = "/tasker"
TASK_BASE_DIR: str = f"{TASKER_BASE_DIR}/task"
TASK_TEMPLATE_BASE_DIR: str = f"{TASKER_BASE_DIR}/template"


def get_task_dir(*, task: Task | None = None, task_id: int | None = None, task_name: str | None = None) -> str:
    if task:
        task_id, task_name = task.id, task.name
    return f"{TASK_BASE_DIR}/{task_id}_{task_name}"


def get_task_source_dir(*, task: Task | None = None, task_id: int | None = None, task_name: str | None = None) -> str:
    task_dir = get_task_dir(task=task, task_id=task_id, task_name=task_name)
    return f"{task_dir}/source"


def get_task_template_dir(
    *,
    task_template: TaskTemplate | None = None,
    task_template_id: int | None = None,
    task_template_name: str | None = None,
) -> str:
    if task_template:
        task_template_id, task_template_name = task_template.id, task_template.name
    return f"{TASK_TEMPLATE_BASE_DIR}/{task_template_id}_{task_template_name}"
