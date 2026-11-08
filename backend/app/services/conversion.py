"""M1 point-cloud conversion worker executed by RQ."""
import json
import math
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.case import AuditLog, CaseVersion, Job
from app.models.practice import Task
from app.services.potree import validate_potree


def _tool_error(tool_name: str, configured_path: str) -> str | None:
    if Path(configured_path).is_file() or shutil.which(configured_path):
        return None
    return f"{tool_name} is unavailable: configured path '{configured_path}' was not found"


def _read_pdal_metadata(raw_path: Path) -> tuple[int, dict]:
    settings = get_settings()
    unavailable = _tool_error("PDAL", settings.pdal_path)
    if unavailable:
        raise RuntimeError(unavailable)
    result = subprocess.run([settings.pdal_path, "info", "--metadata", str(raw_path)], capture_output=True, text=True, timeout=settings.conversion_timeout_seconds, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"PDAL metadata failed: {result.stderr.strip() or result.stdout.strip()}")
    payload = json.loads(result.stdout)
    metadata = payload.get("metadata", {})
    reader = next((value for key, value in metadata.items() if key.startswith("readers.")), metadata)
    count = reader.get("count", reader.get("num_points"))
    bounds = reader.get("bbox", {}).get("native") or reader.get("bounds")
    if type(count) is not int or count < 0:
        raise RuntimeError("PDAL metadata did not contain a valid point count")
    try:
        if all(f"min{axis}" in reader for axis in ("x", "y", "z")):
            normalized_bounds = {"min": [reader[f"min{axis}"] for axis in ("x", "y", "z")], "max": [reader[f"max{axis}"] for axis in ("x", "y", "z")]}
        else:
            normalized_bounds = {"min": [bounds[axis]["min"] for axis in ("x", "y", "z")], "max": [bounds[axis]["max"] for axis in ("x", "y", "z")]}
        if not all(math.isfinite(value) for value in normalized_bounds["min"] + normalized_bounds["max"]) or any(a > b for a, b in zip(normalized_bounds["min"], normalized_bounds["max"])):
            raise ValueError("Non-finite or reversed bounds")
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("PDAL metadata bounds format is unsupported") from exc
    return count, normalized_bounds


def run_conversion(job_id: str) -> None:
    """Update durable job/version state. Any tool error becomes FAILED, never READY."""
    settings = get_settings()
    with SessionLocal.begin() as db:
        job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        if job is None:
            return
        if job.status == "SUCCEEDED":
            return
        version = job.case_version
        if version.status in {"PUBLISHED", "ARCHIVED"} or db.scalar(select(Task.id).where(Task.case_version_id == version.id)):
            job.status, job.error_message, job.finished_at = "FAILED", "Conversion is blocked for published, archived, or assigned versions", datetime.now(UTC)
            db.add(AuditLog(action="CONVERSION_FAILED", case_id=version.case_id, case_version_id=version.id, job_id=job.id, detail={"error": job.error_message}))
            return
        job.status, job.progress, job.started_at = "RUNNING", 5, datetime.now(UTC)
        version.status, version.error_message = "PROCESSING", None
        version.viewer_manifest_key = None
        job.error_message = None

    try:
        with SessionLocal.begin() as db:
            job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
            if job is None or job.status == "SUCCEEDED":
                return
            version = job.case_version
            root = Path(settings.storage_root).resolve()
            raw_path = (root / version.source_file.storage_key).resolve()
            if root not in raw_path.parents:
                raise RuntimeError("Source path escapes controlled storage")
            if not raw_path.is_file():
                raise RuntimeError("Raw point-cloud file is missing from controlled storage")
            point_count, bounds = _read_pdal_metadata(raw_path)
            if point_count == 0:
                raise RuntimeError("Point cloud contains no points after processing")
            job.progress = 45
            version.point_count, version.bounds = point_count, bounds
            unavailable = _tool_error("PotreeConverter", settings.potree_converter_path)
            if unavailable:
                raise RuntimeError(unavailable)
            output_dir = Path(settings.storage_root).resolve() / "cases" / version.case_id / "versions" / version.id / "potree"
            if root not in output_dir.resolve().parents or output_dir.is_symlink():
                raise RuntimeError("Output path escapes controlled storage")
            if output_dir.exists():
                raise RuntimeError("Potree output already exists; create a new conversion version")
            output_dir.mkdir(parents=True, exist_ok=True)
            result = subprocess.run([settings.potree_converter_path, str(raw_path), "-o", str(output_dir)], capture_output=True, text=True, timeout=settings.conversion_timeout_seconds, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"PotreeConverter failed: {result.stderr.strip() or result.stdout.strip()}")
            manifest = validate_potree(output_dir, point_count)
            version.viewer_manifest_key = str(manifest.relative_to(Path(settings.storage_root).resolve())).replace("\\", "/")
            version.status, job.status, job.progress, job.finished_at = "READY", "SUCCEEDED", 100, datetime.now(UTC)
            db.add(AuditLog(action="CONVERSION_SUCCEEDED", case_id=version.case_id, case_version_id=version.id, job_id=job.id))
    except Exception as exc:  # Persist tool/process failures for administrator diagnosis.
        message = str(exc)[:4000]
        with SessionLocal.begin() as db:
            job = db.scalar(select(Job).where(Job.id == job_id))
            if job is not None:
                version = job.case_version
                version.status, version.error_message = "FAILED", message
                job.status, job.error_message, job.finished_at = "FAILED", message, datetime.now(UTC)
                db.add(AuditLog(action="CONVERSION_FAILED", case_id=version.case_id, case_version_id=version.id, job_id=job.id, detail={"error": message}))
