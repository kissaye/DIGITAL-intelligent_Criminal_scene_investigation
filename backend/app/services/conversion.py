"""M1 point-cloud conversion worker executed by RQ."""
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.case import AuditLog, CaseVersion, Job


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
    count = reader.get("count") or reader.get("num_points")
    bounds = reader.get("bbox", {}).get("native") or reader.get("bounds")
    if not isinstance(count, int) or not isinstance(bounds, dict):
        raise RuntimeError("PDAL metadata did not contain point count and bounds")
    try:
        normalized_bounds = {"min": [bounds[axis]["min"] for axis in ("x", "y", "z")], "max": [bounds[axis]["max"] for axis in ("x", "y", "z")]}
    except (KeyError, TypeError) as exc:
        raise RuntimeError("PDAL metadata bounds format is unsupported") from exc
    return count, normalized_bounds


def run_conversion(job_id: str) -> None:
    """Update durable job/version state. Any tool error becomes FAILED, never READY."""
    settings = get_settings()
    with SessionLocal.begin() as db:
        job = db.scalar(select(Job).where(Job.id == job_id))
        if job is None:
            return
        version = job.case_version
        job.status, job.progress, job.started_at = "RUNNING", 5, datetime.now(UTC)
        version.status, version.error_message = "PROCESSING", None

    try:
        with SessionLocal.begin() as db:
            job = db.scalar(select(Job).where(Job.id == job_id))
            version = job.case_version
            raw_path = Path(settings.storage_root).resolve() / version.source_file.storage_key
            if not raw_path.is_file():
                raise RuntimeError("Raw point-cloud file is missing from controlled storage")
            point_count, bounds = _read_pdal_metadata(raw_path)
            job.progress = 45
            version.point_count, version.bounds = point_count, bounds
            unavailable = _tool_error("PotreeConverter", settings.potree_converter_path)
            if unavailable:
                raise RuntimeError(unavailable)
            output_dir = Path(settings.storage_root).resolve() / "cases" / version.case_id / "versions" / version.id / "potree"
            output_dir.mkdir(parents=True, exist_ok=True)
            result = subprocess.run([settings.potree_converter_path, str(raw_path), "-o", str(output_dir)], capture_output=True, text=True, timeout=settings.conversion_timeout_seconds, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"PotreeConverter failed: {result.stderr.strip() or result.stdout.strip()}")
            manifest = output_dir / "metadata.json"
            if not manifest.is_file():
                raise RuntimeError("PotreeConverter completed but metadata.json was not produced")
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
