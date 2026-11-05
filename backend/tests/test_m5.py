"""M5 integration coverage against isolated SQLite and controlled local storage."""
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_tmp = TemporaryDirectory()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp.name, 'm5.db').as_posix()}"
os.environ["STORAGE_ROOT"] = str(Path(_tmp.name, "storage"))

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select

from app.core.config import get_settings
get_settings.cache_clear()
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.case import Case, CaseVersion, File, TeachingCopy
from app.models.practice import Task, TaskAssignment
from app.models.user import User
from app.seed import seed


def upgrade(revision="head"):
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(config, revision)


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    upgrade("head")
    seed()
    yield
    engine.dispose()
    _tmp.cleanup()


def token(client, name):
    response = client.post("/api/v1/auth/login", json={"username": name, "password": "M0DemoPass!2026"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['accessToken']}"}


@pytest.fixture
def published():
    client = TestClient(app)
    admin, teacher, student = token(client, "admin"), token(client, "teacher"), token(client, "student")
    with SessionLocal.begin() as db:
        admin_user = db.scalar(select(User).where(User.username == "admin"))
        case = Case(title="M5", internal_code=f"M5-{datetime.now().timestamp()}", teaching_title="M5 教学案例", case_type="室内", difficulty="基础", course_tags=[], desensitization_level="二级", created_by_id=admin_user.id)
        db.add(case); db.flush()
        source = File(case_id=case.id, storage_key=f"cases/{case.id}/raw/test.las", original_name="test.las", mime_type="application/octet-stream", size_bytes=1, checksum_sha256="0" * 64)
        db.add(source); db.flush()
        version = CaseVersion(case_id=case.id, source_file_id=source.id, version_number=1, status="READY")
        db.add(version); db.flush()
        case_id, version_id = case.id, version.id
    potree = Path(os.environ["STORAGE_ROOT"]) / "cases" / case_id / "versions" / version_id / "potree"
    potree.mkdir(parents=True); (potree / "metadata.json").write_text("{}", encoding="utf-8"); (potree / "node.bin").write_bytes(b"bin")
    future = (datetime.now(UTC) + timedelta(days=3)).isoformat().replace("+00:00", "Z")
    auth = client.post(f"/api/v1/cases/{case_id}/authorizations", headers=admin, json={"reference": f"AUTH-{version_id}", "scope": "teaching", "validUntil": future})
    assert auth.status_code == 201
    authorization_id = auth.json()["data"]["id"]
    publication = {"authorizationId": authorization_id, "validUntil": future, "reviewConfirmed": True, "reviewNote": "reviewed"}
    assert client.post(f"/api/v1/case-versions/{version_id}/publish", headers=admin, json=publication).status_code == 200
    return client, admin, teacher, student, case_id, version_id, authorization_id, publication


def test_migrations_from_empty_and_0007():
    # The test database was upgraded from empty. A separate file proves 0007 -> 0008.
    old_db = Path(_tmp.name, "from_0007.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{old_db.as_posix()}"; get_settings.cache_clear()
    upgrade("202610300007"); upgrade("head")
    columns = {column["name"] for column in inspect(create_engine(os.environ["DATABASE_URL"])).get_columns("teaching_copies")}
    assert {"review_note", "case_version_id", "manifest_key"} <= columns
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp.name, 'm5.db').as_posix()}"; get_settings.cache_clear()


def test_authorization_contract_validation_and_publication(published):
    client, admin, _, _, case_id, version_id, _, publication = published
    assert client.post(f"/api/v1/cases/{case_id}/authorizations", headers=admin, json={"reference": "naive", "scope": "x", "validUntil": "2030-01-01T00:00:00"}).status_code == 422
    expired = (datetime.now(UTC) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    assert client.post(f"/api/v1/cases/{case_id}/authorizations", headers=admin, json={"reference": "past", "scope": "x", "validUntil": expired}).status_code == 422
    assert client.post(f"/api/v1/case-versions/{version_id}/publish", headers=admin, json=publication).status_code == 409
    row = client.get(f"/api/v1/cases/{case_id}/versions", headers=admin).json()["data"][0]
    assert row["publication"]["reviewNote"] == "reviewed" and row["createdAt"]


def test_student_teaching_assets_and_revocation(published):
    client, admin, teacher, student, case_id, version_id, authorization_id, _ = published
    course = client.post("/api/v1/teacher/courses", headers=teacher, json={"title": "课程", "description": ""}).json()["data"]
    student_id = client.get("/api/v1/teacher/students", headers=teacher).json()["data"][0]["id"]
    klass = client.post("/api/v1/teacher/classes", headers=teacher, json={"courseId": course["id"], "name": "班级", "studentIds": [student_id]}).json()["data"]
    task = client.post("/api/v1/teacher/tasks", headers=teacher, json={"classId": klass["id"], "title": "任务", "instructions": "", "caseVersionId": version_id, "allowLate": False, "reportTemplate": {}})
    assert task.status_code == 201
    task_id = task.json()["data"]["id"]
    asset = f"/api/v1/viewer-assets/{version_id}/metadata.json"
    assert client.get(asset).status_code == 401
    assert client.get(f"/api/v1/student/tasks/{task_id}/workspace", headers=student).status_code == 200
    asset_response = client.get(asset)
    assert asset_response.status_code == 200, asset_response.text
    assert client.get(f"/api/v1/viewer-assets/{version_id}/node.bin").content == b"bin"
    # URL normalization may remove the version-bound Cookie path first; neither result exposes an asset.
    assert client.get(f"/api/v1/viewer-assets/{version_id}/../metadata.json").status_code in {401, 404}
    assert client.get(f"/api/v1/viewer-assets/{version_id}/test.txt").status_code == 404
    payload = {"reportContent": {"overview": "x"}, "marks": [], "measurements": []}
    assert client.put(f"/api/v1/student/tasks/{task_id}/draft", headers=student, json=payload).status_code == 200
    assert client.post(f"/api/v1/student/tasks/{task_id}/submissions", headers=student, json=payload).status_code == 200
    assert client.post(f"/api/v1/authorizations/{authorization_id}/revoke", headers=admin).status_code == 200
    for method, url in [(client.get, f"/api/v1/student/tasks/{task_id}/workspace"), (client.put, f"/api/v1/student/tasks/{task_id}/draft"), (client.post, f"/api/v1/student/tasks/{task_id}/submissions"), (client.get, asset)]:
        kwargs = {"headers": student}
        if method in (client.put, client.post): kwargs["json"] = payload
        assert method(url, **kwargs).status_code == 409


def test_parent_validation_audit_and_permissions(published):
    client, admin, teacher, student, case_id, version_id, _, _ = published
    assert client.get("/api/v1/audit-logs?offset=0&limit=1", headers=admin).status_code == 200
    audit = client.get(f"/api/v1/audit-logs?caseId={case_id}&action=VERSION_PUBLISHED&offset=0&limit=1", headers=admin).json()["data"]
    assert audit["total"] >= 1 and len(audit["items"]) == 1
    assert client.get("/api/v1/audit-logs", headers=teacher).status_code == 403
    assert client.get("/api/v1/teacher/case-versions/ready", headers=teacher).status_code == 200
    assert client.get("/api/v1/teacher/case-versions/ready", headers=student).status_code == 403


def test_publication_and_case_expiry_and_archive_block_access(published):
    client, admin, teacher, student, case_id, version_id, _, _ = published
    # Expired teaching copy and expired case are both checked at request time.
    with SessionLocal.begin() as db:
        copy = db.scalar(select(TeachingCopy).where(TeachingCopy.case_version_id == version_id))
        copy.valid_until = datetime.now(UTC) - timedelta(seconds=1)
    assert version_id not in {item["id"] for item in client.get("/api/v1/teacher/case-versions/ready", headers=teacher).json()["data"]}
    with SessionLocal.begin() as db:
        copy = db.scalar(select(TeachingCopy).where(TeachingCopy.case_version_id == version_id))
        copy.valid_until = datetime.now(UTC) + timedelta(days=1)
        case = db.get(Case, case_id); case.valid_until = datetime.now(UTC) - timedelta(seconds=1)
    assert version_id not in {item["id"] for item in client.get("/api/v1/teacher/case-versions/ready", headers=teacher).json()["data"]}
    with SessionLocal.begin() as db:
        db.get(Case, case_id).valid_until = None
    assert client.post(f"/api/v1/case-versions/{version_id}/archive", headers=admin).status_code == 200
    assert client.post(f"/api/v1/case-versions/{version_id}/archive", headers=admin).status_code == 409
    assert version_id not in {item["id"] for item in client.get("/api/v1/teacher/case-versions/ready", headers=teacher).json()["data"]}


def test_task_schedule_identity_and_parent_version_validation(published):
    client, admin, _, student, case_id, version_id, _, _ = published
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.username == "student"))
        task = Task(title="schedule", instructions="", case_version_id=version_id, start_at=datetime.now(UTC) + timedelta(hours=1), allow_late=False, status="PUBLISHED", created_by=user.id)
        db.add(task); db.flush(); db.add(TaskAssignment(task_id=task.id, student_id=user.id)); task_id = task.id
    assert client.get(f"/api/v1/student/tasks/{task_id}/workspace", headers=student).status_code == 409
    with SessionLocal.begin() as db:
        task = db.get(Task, task_id); task.start_at = datetime.now(UTC) - timedelta(hours=2); task.due_at = datetime.now(UTC) - timedelta(hours=1)
    assert client.get(f"/api/v1/student/tasks/{task_id}/workspace", headers=student).status_code == 409
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.username == "student")); user.is_active = False
    assert client.get(f"/api/v1/student/tasks/{task_id}/workspace", headers=student).status_code == 401
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.username == "student")); user.is_active = True
        source = db.scalar(select(File).where(File.case_id == case_id))
        parent = db.get(CaseVersion, version_id)
        same_file = File(case_id=case_id, storage_key=f"cases/{case_id}/raw/second.las", original_name="second.las", mime_type="x", size_bytes=1, checksum_sha256="1" * 64)
        db.add(same_file); db.flush(); same_file_id = same_file.id
        other = Case(title="other", internal_code=f"OTHER-{datetime.now().timestamp()}", teaching_title="other", case_type="x", difficulty="x", course_tags=[], desensitization_level="x", created_by_id=user.id)
        db.add(other); db.flush()
        other_file = File(case_id=other.id, storage_key=f"cases/{other.id}/raw/other.las", original_name="other.las", mime_type="x", size_bytes=1, checksum_sha256="2" * 64)
        db.add(other_file); db.flush()
        other_version = CaseVersion(case_id=other.id, source_file_id=other_file.id, version_number=1, status="READY")
        db.add(other_version); db.flush(); other_parent_id = other_version.id
    same = client.post(f"/api/v1/cases/{case_id}/versions", headers=admin, json={"fileId": same_file_id, "parentVersionId": version_id})
    assert same.status_code == 202
    cross = client.post(f"/api/v1/cases/{case_id}/versions", headers=admin, json={"fileId": same_file_id, "parentVersionId": other_parent_id})
    assert cross.status_code == 422
