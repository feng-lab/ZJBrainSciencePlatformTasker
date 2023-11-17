from pathlib import Path

from fastapi.testclient import TestClient
from rq import Worker
from rq.job import JobStatus

from zjbs_tasker.db import TaskInterpreter
from zjbs_tasker.server import queue
from zjbs_tasker.worker import execute_task_run

cwd = Path(__file__).parent
data_dir = cwd / "data"


def test_create_task_run(client: TestClient) -> None:
    response = client.post(
        "/taskinterpreter",
        json={
            "name": "test",
            "is_external": False,
            "type": "executable",
            "executable": '["copy.exe"]',
            "environment": "{}",
        },
    )
    assert response.is_success
    task_interpreter = TaskInterpreter(**response.json())
    assert task_interpreter.id > 0

    with open(data_dir / "copy.zip", "rb") as file:
        response = client.post(
            "/UploadTaskInterpreterPack",
            files={"file": ("copy.zip", file)},
            data={"task_interpreter_id": task_interpreter.id, "compress_method": "zip"},
        )
        assert response.is_success


def test_worker(client: TestClient, rq_worker: Worker) -> None:
    response = client.post(
        "/CreateTaskTemplate",
        json={"name": "test-worker", "type": "executable", "executable": ["copy.exe"], "environment": {}},
    )
    assert response.is_success
    task_template_id = int(response.json())

    test_data_dir = Path(__file__).parent / "data"
    with open(test_data_dir / "copy.zip", "rb") as file:
        response = client.post(
            "/UploadTaskTemplateExecutable",
            files={"file": ("copy.zip", file)},
            data={"task_template_id": task_template_id, "compress_method": "zip"},
        )
    assert response.is_success

    response = client.post(
        "/CreateTask",
        json={"template": task_template_id, "name": "test-worker-task", "argument": ["test.txt"], "environment": {}},
    )
    assert response.is_success
    task_id = int(response.json())

    with open(test_data_dir / "test.zip", "rb") as file:
        response = client.post(
            "/UploadTaskSourceFile",
            files={"file": ("test.zip", file)},
            data={"task_id": task_id, "compress_method": "zip"},
        )
    assert response.is_success

    response = client.post("/task_run", json={"task": task_id, "status": "pending", "index": 0})
    assert response.is_success
    task_run_id = response.json()["id"]
    print(f"{task_run_id=}")

    job = queue.enqueue_call(execute_task_run, [task_run_id], timeout=10)
    rq_worker.work(burst=True)
    assert job.get_status(refresh=True) == JobStatus.FINISHED
