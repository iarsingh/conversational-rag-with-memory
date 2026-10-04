from fastapi.testclient import TestClient
from convrag.main import app
from convrag import memory

client = TestClient(app)


def setup_function():
    memory.SESSIONS.clear()


def test_second_turn_uses_memory():
    first = client.post("/ask", json={"session_id": "s1", "question": 'What is the error budget minutes?'}).json()
    assert first["answered"] is True
    second = client.post("/ask", json={"session_id": "s1", "question": 'Who cares about it during rollback?'}).json()
    assert second["turns"] == 2
    assert second["citation"] == "budget.md"
