from pathlib import Path

from fastapi.testclient import TestClient


def test_worker(client: TestClient) -> int:
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

    # execute_task_run(task_run_id)
    return task_run_id
