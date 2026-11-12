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
from app.core.security import create_access_token, password_context
get_settings.cache_clear()
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.case import Case, CaseVersion, File, TeachingCopy
from app.models.practice import Submission, Task, TaskAssignment
from app.models.user import User
from app.seed import seed


def upgrade(revision="head"):
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(config, revision)


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    upgrade("head")
    password_context.update(bcrypt__rounds=4)
    seed()
    yield
    engine.dispose()
    _tmp.cleanup()


def token(client, name):
    token, _ = create_access_token(name)
    return {"Authorization": f"Bearer {token}"}


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
        version = CaseVersion(case_id=case.id, source_file_id=source.id, version_number=1, status="READY", viewer_manifest_key=f"cases/{case.id}/versions/pending/potree/metadata.json")
        db.add(version); db.flush()
        case_id, version_id = case.id, version.id
    potree = Path(os.environ["STORAGE_ROOT"]) / "cases" / case_id / "versions" / version_id / "potree"
    potree.mkdir(parents=True)
    (potree / "metadata.json").write_text("{}", encoding="utf-8")
    (potree / "hierarchy.bin").write_bytes(b"hierarchy")
    (potree / "octree.bin").write_bytes(b"octree")
    future = (datetime.now(UTC) + timedelta(days=3)).isoformat().replace("+00:00", "Z")
    auth = client.post(f"/api/v1/cases/{case_id}/authorizations", headers=admin, json={"reference": f"AUTH-{version_id}", "scope": "teaching", "validUntil": future})
    assert auth.status_code == 201
    authorization_id = auth.json()["data"]["id"]
    publication = {"authorizationId": authorization_id, "validUntil": future, "reviewConfirmed": True, "reviewNote": "reviewed"}
    assert client.post(f"/api/v1/case-versions/{version_id}/publish", headers=admin, json=publication).status_code == 200
    return client, admin, teacher, student, case_id, version_id, authorization_id, publication


def test_migrations_from_0011_to_0012():
    old_db = Path(_tmp.name, "from_0011.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{old_db.as_posix()}"; get_settings.cache_clear()
    upgrade("202611110011"); upgrade("head")
    migrated_engine = create_engine(os.environ["DATABASE_URL"])
    columns = {column["name"] for column in inspect(migrated_engine).get_columns("teaching_copies")}
    assert {"review_note", "case_version_id", "manifest_key"} <= columns
    measurement_columns = {column["name"] for column in inspect(migrated_engine).get_columns("measurements")}
    submission_measurement_columns = {column["name"] for column in inspect(migrated_engine).get_columns("submission_measurements")}
    assert {"title", "description"} <= measurement_columns
    assert {"title", "description"} <= submission_measurement_columns
    assert {"points", "perimeter", "area", "owner_id"} <= {column["name"] for column in inspect(migrated_engine).get_columns("area_measurements")}
    assert {"points", "perimeter", "area", "submission_id"} <= {column["name"] for column in inspect(migrated_engine).get_columns("submission_area_measurements")}
    assert {"points", "width", "path_length", "owner_id"} <= {column["name"] for column in inspect(migrated_engine).get_columns("profile_measurements")}
    assert {"points", "width", "path_length", "submission_id"} <= {column["name"] for column in inspect(migrated_engine).get_columns("submission_profiles")}
    migrated_engine.dispose()
    os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp.name, 'm5.db').as_posix()}"; get_settings.cache_clear()


def test_migrations_from_0001_to_0012():
    old_db = Path(_tmp.name, "from_0001.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{old_db.as_posix()}"; get_settings.cache_clear()
    upgrade("202610280001"); upgrade("head")
    migrated_engine = create_engine(os.environ["DATABASE_URL"])
    inspector = inspect(migrated_engine)
    assert {"title", "description"} <= {column["name"] for column in inspector.get_columns("measurements")}
    assert {"title", "description"} <= {column["name"] for column in inspector.get_columns("submission_measurements")}
    assert inspector.has_table("area_measurements") and inspector.has_table("submission_area_measurements")
    assert inspector.has_table("profile_measurements") and inspector.has_table("submission_profiles")
    migrated_engine.dispose()
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
    assert client.get(f"/api/v1/viewer-assets/{version_id}/hierarchy.bin").content == b"hierarchy"
    # URL normalization may remove the version-bound Cookie path first; neither result exposes an asset.
    assert client.get(f"/api/v1/viewer-assets/{version_id}/../metadata.json").status_code in {401, 404}
    assert client.get(f"/api/v1/viewer-assets/{version_id}/test.txt").status_code == 404
    payload = {"reportContent": {"overview": "x", "process": "", "evidenceDescription": "", "preliminaryConclusion": ""}, "marks": [], "measurements": []}
    assert client.put(f"/api/v1/student/tasks/{task_id}/draft", headers=student, json=payload).status_code == 200
    assert client.post(f"/api/v1/student/tasks/{task_id}/submissions", headers=student, json=payload).status_code == 200
    assert client.post(f"/api/v1/authorizations/{authorization_id}/revoke", headers=admin).status_code == 200
    for method, url in [(client.get, f"/api/v1/student/tasks/{task_id}/workspace"), (client.put, f"/api/v1/student/tasks/{task_id}/draft"), (client.post, f"/api/v1/student/tasks/{task_id}/submissions"), (client.get, asset)]:
        kwargs = {"headers": student}
        if method in (client.put, client.post): kwargs["json"] = payload
        assert method(url, **kwargs).status_code == 409


def test_m8_m9_measurement_http_contract(published):
    client, admin, teacher, student, _, version_id, _, _ = published
    measurement = {"startPoint": {"x": 0, "y": 0, "z": 9}, "endPoint": {"x": 9, "y": 9, "z": 0}, "title": "门窗空间测量", "description": "M9.1 教学测量", "viewerState": {}}
    created = client.post(f"/api/v1/case-versions/{version_id}/measurements", headers=admin, json=measurement)
    assert created.status_code == 201, created.text
    data = created.json()["data"]
    assert data["deltaX"] == 9 and data["deltaY"] == 9 and data["deltaZ"] == -9
    assert data["horizontalDistance"] == pytest.approx(12.7279220614) and data["verticalDistance"] == 9
    assert data["distance"] == pytest.approx(15.5884572681) and data["title"] == "门窗空间测量"
    assert client.get(f"/api/v1/case-versions/{version_id}/measurements", headers=admin).json()["data"][0]["distance"] == pytest.approx(15.5884572681)
    assert client.delete(f"/api/v1/measurements/{data['id']}", headers=admin).status_code == 200
    assert client.post(f"/api/v1/case-versions/{version_id}/measurements", headers=admin, json={**measurement, "distance": 1}).status_code == 422
    area = {"points": [{"x": 0, "y": 0, "z": 0}, {"x": 3, "y": 0, "z": 0}, {"x": 3, "y": 4, "z": 0}], "title": "现场区域 A", "description": "M9.2 教学区域测量", "viewerState": {}}
    created_area = client.post(f"/api/v1/case-versions/{version_id}/area-measurements", headers=admin, json=area)
    assert created_area.status_code == 201 and created_area.json()["data"]["area"] == pytest.approx(6)
    assert client.get(f"/api/v1/case-versions/{version_id}/area-measurements", headers=admin).json()["data"][0]["perimeter"] == pytest.approx(12)
    assert client.delete(f"/api/v1/area-measurements/{created_area.json()['data']['id']}", headers=admin).status_code == 200
    assert client.post(f"/api/v1/case-versions/{version_id}/area-measurements", headers=admin, json={**area, "area": 999}).status_code == 422
    profile = {"points": [{"x": 0, "y": 0, "z": 9}, {"x": 5, "y": 5, "z": 5}, {"x": 9, "y": 9, "z": 0}], "width": 1.0, "title": "房间纵向剖面", "description": "M9.3 教学剖面", "viewerState": {}}
    created_profile = client.post(f"/api/v1/case-versions/{version_id}/profiles", headers=admin, json=profile)
    assert created_profile.status_code == 201 and created_profile.json()["data"]["pathLength"] > 0
    assert client.get(f"/api/v1/case-versions/{version_id}/profiles", headers=admin).status_code == 200
    assert client.delete(f"/api/v1/profiles/{created_profile.json()['data']['id']}", headers=admin).status_code == 200
    assert client.post(f"/api/v1/case-versions/{version_id}/profiles", headers=admin, json={**profile, "pathLength": 999}).status_code == 422

    course = client.post("/api/v1/teacher/courses", headers=teacher, json={"title": "M8.3"}).json()["data"]
    student_id = client.get("/api/v1/teacher/students", headers=teacher).json()["data"][0]["id"]
    klass = client.post("/api/v1/teacher/classes", headers=teacher, json={"courseId": course["id"], "name": "M9.1", "studentIds": [student_id]}).json()["data"]
    task = client.post("/api/v1/teacher/tasks", headers=teacher, json={"classId": klass["id"], "title": "报告", "instructions": "", "caseVersionId": version_id, "allowLate": False, "reportTemplate": {}})
    assert task.status_code == 201
    task_id = task.json()["data"]["id"]
    report = {"overview": "现场概况", "process": "勘验过程", "evidenceDescription": "物证描述", "preliminaryConclusion": "初步结论"}
    payload = {"reportContent": report, "marks": [], "measurements": [measurement], "areaMeasurements": [area], "profiles": [profile]}
    for bad in ({"reportContent": {"overview": ""}, "marks": [], "measurements": []}, {"reportContent": {**report, "unknown": "x"}, "marks": [], "measurements": []}):
        assert client.put(f"/api/v1/student/tasks/{task_id}/draft", headers=student, json=bad).status_code == 422
    zero = {"reportContent": report, "marks": [], "measurements": [{"startPoint": {"x": 0, "y": 0, "z": 0}, "endPoint": {"x": 0, "y": 0, "z": 0}}]}
    assert client.put(f"/api/v1/student/tasks/{task_id}/draft", headers=student, json=zero).status_code == 422
    saved = client.put(f"/api/v1/student/tasks/{task_id}/draft", headers=student, json=payload)
    assert saved.status_code == 200 and saved.json()["data"]["reportContent"] == report
    assert saved.json()["data"]["measurements"][0]["deltaZ"] == -9
    assert saved.json()["data"]["areaMeasurements"][0]["area"] == pytest.approx(6)
    assert saved.json()["data"]["profiles"][0]["pathLength"] > 0
    submitted = client.post(f"/api/v1/student/tasks/{task_id}/submissions", headers=student, json=payload)
    assert submitted.status_code == 200
    assert client.put(f"/api/v1/student/tasks/{task_id}/draft", headers=student, json=payload).status_code == 409
    assert client.post(f"/api/v1/student/tasks/{task_id}/submissions", headers=student, json=payload).status_code == 409
    detail = client.get(f"/api/v1/teacher/submissions/{submitted.json()['data']['id']}", headers=teacher)
    assert detail.status_code == 200 and detail.json()["data"]["reportContent"] == report
    assert detail.json()["data"]["areaMeasurements"][0]["pointCount"] == 3
    assert detail.json()["data"]["profiles"][0]["pointCount"] == 3
    submission_id = submitted.json()["data"]["id"]
    with SessionLocal.begin() as db:
        row = db.get(Submission, submission_id)
        row.report_content = {"overview": None, "process": ["old"], "evidence": "旧物证", "conclusion": "旧结论"}
    legacy = client.get(f"/api/v1/student/submissions/{submission_id}", headers=student)
    assert legacy.status_code == 200
    assert legacy.json()["data"]["reportContent"] == {"overview": "", "process": "", "evidenceDescription": "旧物证", "preliminaryConclusion": "旧结论"}


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
