"""Unit tests for the /health endpoint.

The app lifespan catches model-load failures so the API stays up even when
MLflow is unreachable (as in CI). /health must always answer 200 with the
expected shape.
"""


def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_payload_shape(client):
    body = client.get("/health").json()
    assert "status" in body
    assert "model_loaded" in body
    assert "model_version" in body
    assert "uptime_seconds" in body
    assert isinstance(body["model_loaded"], bool)
    assert isinstance(body["uptime_seconds"], (int, float))
