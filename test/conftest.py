import pytest
from fastapi.testclient import TestClient
from rq import SimpleWorker, Worker
from rq.command import send_shutdown_command
from rq.timeouts import TimerDeathPenalty

from zjbs_tasker.main import app
from zjbs_tasker.server import queue


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as client:
        yield client


class WindowsWorker(SimpleWorker):
    death_penalty_class = TimerDeathPenalty


@pytest.fixture(scope="session")
def rq_worker() -> Worker:
    worker = WindowsWorker([queue], connection=queue.connection)
    yield worker
    send_shutdown_command(queue.connection, worker.name)
