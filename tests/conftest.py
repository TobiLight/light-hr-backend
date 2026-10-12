import pytest
from app.bootstrap import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client
