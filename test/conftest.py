import pytest
from fastapi.testclient import TestClient

from zjbs_tasker.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as client:
        yield client
