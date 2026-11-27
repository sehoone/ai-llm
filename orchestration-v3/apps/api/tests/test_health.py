from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_health_live() -> None:
    # liveness 별칭 — 의존성 미조회, 항상 200 (ADR-0032).
    res = client.get("/health/live")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_health_ready_reports_checks() -> None:
    # readiness — DB/스토리지 상태를 보고. 환경에 따라 200/503이나 checks 키는 항상 존재 (ADR-0032).
    res = client.get("/health/ready")
    assert res.status_code in (200, 503)
    body = res.json()
    assert "db" in body["checks"] and "storage" in body["checks"]
