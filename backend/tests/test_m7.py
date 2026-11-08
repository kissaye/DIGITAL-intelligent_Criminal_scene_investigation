"""Regression checks for real-tool metadata and incomplete Potree products."""
import json
import struct
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services import conversion
from app.services.potree import validate_potree
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.models.case import AuditLog, Case, CaseVersion, File, Job
import app.models  # Register all tables and relationships for isolated worker tests.


@pytest.fixture
def potree(tmp_path):
    metadata = {"version": "2.0", "points": 2, "hierarchy": {"firstChunkSize": 22},
                "encoding": "DEFAULT", "attributes": [{"size": 12}]}
    (tmp_path / "metadata.json").write_text(json.dumps(metadata))
    (tmp_path / "hierarchy.bin").write_bytes(struct.pack("<BBIQQ", 1, 0, 2, 0, 24))
    (tmp_path / "octree.bin").write_bytes(bytes(24))
    return tmp_path


def test_complete_potree(potree):
    assert validate_potree(potree, 2).name == "metadata.json"


def test_leaf_with_children_matches_real_potree_output(potree):
    (potree / "metadata.json").write_text(json.dumps({
        "version": "2.0", "points": 2, "hierarchy": {"firstChunkSize": 44},
        "encoding": "DEFAULT", "attributes": [{"size": 12}],
    }))
    (potree / "hierarchy.bin").write_bytes(
        struct.pack("<BBIQQ", 1, 1, 2, 0, 24)
        + struct.pack("<BBIQQ", 1, 0, 0, 0, 0)
    )
    assert validate_potree(potree, 2).name == "metadata.json"


@pytest.mark.parametrize("damage", ["missing", "truncated", "points", "children", "range", "json"])
def test_incomplete_products_rejected(potree, damage):
    if damage == "missing":
        (potree / "octree.bin").unlink()
    elif damage == "truncated":
        (potree / "octree.bin").write_bytes(bytes(23))
    elif damage == "points":
        (potree / "hierarchy.bin").write_bytes(struct.pack("<BBIQQ", 1, 0, 1, 0, 12))
    elif damage == "children":
        (potree / "hierarchy.bin").write_bytes(struct.pack("<BBIQQ", 0, 1, 2, 0, 24))
    elif damage == "range":
        (potree / "hierarchy.bin").write_bytes(struct.pack("<BBIQQ", 1, 0, 2, 10, 24))
    else:
        (potree / "metadata.json").write_text("{")
    with pytest.raises((RuntimeError, ValueError)):
        validate_potree(potree, 2)


def test_proxy_hierarchy_chunk(potree):
    (potree / "hierarchy.bin").write_bytes(
        struct.pack("<BBIQQ", 2, 0, 2, 22, 22) + struct.pack("<BBIQQ", 1, 0, 2, 0, 24))
    validate_potree(potree, 2)


def test_proxy_cycle_rejected(potree):
    (potree / "hierarchy.bin").write_bytes(struct.pack("<BBIQQ", 2, 0, 2, 0, 22))
    with pytest.raises(RuntimeError, match="repeated"):
        validate_potree(potree, 2)


@pytest.mark.parametrize("nested", [False, True])
def test_pdal_las_metadata_formats(monkeypatch, nested):
    reader = {"count": 1000}
    if nested:
        reader["bounds"] = {axis: {"min": 0, "max": 9} for axis in "xyz"}
    else:
        reader.update({f"{prefix}{axis}": value for prefix, value in [("min", 0), ("max", 9)] for axis in "xyz"})
    monkeypatch.setattr(conversion, "_tool_error", lambda *args: None)
    monkeypatch.setattr(conversion.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout=json.dumps({"metadata": reader}), stderr=""))
    assert conversion._read_pdal_metadata(Path("demo.las")) == (1000, {"min": [0, 0, 0], "max": [9, 9, 9]})


def test_pdal_missing_has_explicit_error(monkeypatch):
    monkeypatch.setattr(conversion, "_tool_error", lambda *args: "PDAL is unavailable")
    with pytest.raises(RuntimeError, match="PDAL is unavailable"):
        conversion._read_pdal_metadata(Path("demo.las"))


@pytest.mark.parametrize("outcome", ["missing_tool", "metadata_only", "truncated", "complete"])
def test_worker_persists_verified_outcome(tmp_path, monkeypatch, outcome):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    settings = conversion.get_settings().model_copy(update={"storage_root": str(tmp_path)})
    monkeypatch.setattr(conversion, "get_settings", lambda: settings)
    monkeypatch.setattr(conversion, "SessionLocal", sessions)
    with sessions.begin() as db:
        case = Case(title="synthetic", created_by_id=1)
        db.add(case)
        db.flush()
        source = File(case_id=case.id, storage_key="raw/demo.las", original_name="demo.las",
                      mime_type="application/vnd.las", size_bytes=1, checksum_sha256="0" * 64)
        db.add(source)
        db.flush()
        version = CaseVersion(case_id=case.id, source_file_id=source.id, version_number=1, status="PROCESSING")
        db.add(version)
        db.flush()
        job = Job(case_version_id=version.id)
        db.add(job)
        db.flush()
        job_id, version_id = job.id, version.id
    raw = tmp_path / "raw/demo.las"
    raw.parent.mkdir()
    raw.write_bytes(b"synthetic test input")
    monkeypatch.setattr(conversion, "_read_pdal_metadata", lambda path: (2, {"min": [0, 0, 0], "max": [1, 1, 1]}))
    monkeypatch.setattr(conversion, "_tool_error", lambda *args: "PotreeConverter is unavailable" if outcome == "missing_tool" else None)

    def convert(command, **kwargs):
        output = Path(command[-1])
        (output / "metadata.json").write_text(json.dumps({"version": "2.0", "points": 2,
            "hierarchy": {"firstChunkSize": 22}, "attributes": [{"size": 12}]}))
        if outcome != "metadata_only":
            (output / "hierarchy.bin").write_bytes(struct.pack("<BBIQQ", 1, 0, 2, 0, 24))
            (output / "octree.bin").write_bytes(bytes(23 if outcome == "truncated" else 24))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(conversion.subprocess, "run", convert)
    conversion.run_conversion(job_id)
    with sessions() as db:
        version, job = db.get(CaseVersion, version_id), db.get(Job, job_id)
        expected = "READY" if outcome == "complete" else "FAILED"
        assert version.status == expected
        assert job.status == ("SUCCEEDED" if outcome == "complete" else "FAILED")
        assert bool(version.viewer_manifest_key) == (outcome == "complete")
        assert db.scalar(select(AuditLog).where(AuditLog.job_id == job_id)).action == (
            "CONVERSION_SUCCEEDED" if outcome == "complete" else "CONVERSION_FAILED")
    engine.dispose()
