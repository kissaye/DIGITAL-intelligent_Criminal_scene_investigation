"""Real HTTP + RQ + PDAL + Potree acceptance check, run inside backend.

Exits nonzero on any failure and writes observations, never synthesizes READY.
"""
import argparse
import hashlib
import http.cookiejar
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo_las import create_demo
from sqlalchemy import select
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.case import AuditLog, CaseVersion
from app.services.potree import validate_potree


def verify(base_url: str, report: dict, password: str) -> None:
    settings = get_settings()
    root = Path(settings.storage_root).resolve()
    scratch = root / "verification" / str(uuid4())
    scratch.mkdir(parents=True)
    report["scratch"] = str(scratch)
    report["pdal"] = subprocess.check_output([settings.pdal_path, "--version"], text=True).strip()
    report["potree_revision"] = Path("/usr/local/bin/POTREE_REVISION").read_text().strip()
    report["potree_help"] = subprocess.check_output([settings.potree_converter_path, "--help"], text=True)[:2000]
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    token = None

    def request(method, path, payload=None, upload=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        body = None
        if upload:
            boundary = uuid4().hex
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
            body = (f'--{boundary}\r\nContent-Disposition: form-data; name="upload"; filename="{upload.name}"\r\n'
                    'Content-Type: application/octet-stream\r\n\r\n').encode() + upload.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        elif payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode()
        req = urllib.request.Request(base_url + "/api/v1" + path, data=body, headers=headers, method=method)
        with opener.open(req, timeout=30) as response:
            return json.load(response)["data"]

    token = request("POST", "/auth/login", {"username": "admin", "password": password})["accessToken"]
    case = request("POST", "/cases", {"internalCode": "M7-" + uuid4().hex[:16], "teachingTitle": "M7 synthetic CC0 grid",
                   "caseType": "synthetic", "difficulty": "basic", "desensitizationLevel": "synthetic"})
    report["case_id"] = case["id"]
    report["versions"] = []

    def wait(version_id):
        observations = []
        report.setdefault("states", {})[version_id] = observations
        deadline = time.monotonic() + settings.conversion_timeout_seconds * 3 + 90
        while time.monotonic() < deadline:
            version = request("GET", f"/case-versions/{version_id}")
            job = request("GET", f"/jobs/{version['jobId']}")
            observation = {"version": version["status"], "job": job["status"], "progress": job["progress"]}
            if not observations or observations[-1] != observation:
                observations.append(observation)
                print(version_id, json.dumps(observation), flush=True)
            if version["status"] == "FAILED":
                raise RuntimeError(version["failureReason"])
            if version["status"] == "READY":
                assert job["status"] == "SUCCEEDED"
                return version
            time.sleep(1)
        raise TimeoutError(f"Version {version_id} did not finish")

    las = scratch / "grid.las"
    create_demo(las)
    laz = scratch / "grid.laz"
    subprocess.run([settings.pdal_path, "translate", str(las), str(laz)], check=True)
    parent_id = None
    for sample in (las, laz):
        file = request("POST", f"/cases/{case['id']}/files", upload=sample)
        queued = request("POST", f"/cases/{case['id']}/versions", {"fileId": file["id"]})
        ready = wait(queued["id"])
        assert ready["pointCount"] == 1000
        with SessionLocal() as db:
            version = db.get(CaseVersion, ready["id"])
            manifest = root / version.viewer_manifest_key
            validate_potree(manifest.parent, 1000)
            source_key = version.source_file.storage_key
            report["versions"].append({"id": version.id, "format": sample.suffix, "points": version.point_count,
                                       "files": {p.name: p.stat().st_size for p in manifest.parent.iterdir() if p.is_file()}})
        # Probe public raw paths without any cookie or Authorization header.
        for prefix in ("/storage/", "/api/v1/files/", "/"):
            try:
                urllib.request.urlopen(base_url + prefix + source_key, timeout=10)
            except urllib.error.HTTPError as error:
                assert error.code in (401, 403, 404), error.code
            else:
                raise AssertionError("Raw source was publicly accessible")
        request("GET", f"/case-versions/{ready['id']}/viewer-config")
        for asset in ("metadata.json", "hierarchy.bin", "octree.bin"):
            url = base_url + f"/api/v1/viewer-assets/{ready['id']}/{asset}"
            with opener.open(url, timeout=30) as response:
                received = response.read()
            assert hashlib.sha256(received).digest() == hashlib.sha256((manifest.parent / asset).read_bytes()).digest()
        for asset in ("grid.las", "grid.laz", "../../../raw/" + Path(source_key).name):
            try:
                request("GET", f"/viewer-assets/{ready['id']}/{asset}")
            except urllib.error.HTTPError as error:
                assert error.code == 404
            else:
                raise AssertionError("Viewer exposed raw source")
        if sample == las:
            parent_id = ready["id"]
    request("POST", f"/case-versions/{parent_id}/desensitization-rules", {
        "mode": "DELETE", "title": "Remove 125 synthetic grid points",
        "geometry": {"type": "BOX", "min": [-0.5, -0.5, -0.5], "max": [4.5, 4.5, 4.5]}})
    derived = request("POST", f"/case-versions/{parent_id}/desensitization/apply")
    ready = wait(derived["versionId"])
    assert ready["pointCount"] == 875
    with SessionLocal() as db:
        version = db.get(CaseVersion, ready["id"])
        parent = db.get(CaseVersion, parent_id)
        output = root / version.source_file.storage_key
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        assert version.source_file_id != parent.source_file_id
        assert digest == version.source_file.checksum_sha256
        assert hashlib.sha256((root / parent.source_file.storage_key).read_bytes()).hexdigest() == parent.source_file.checksum_sha256
        audit = db.scalar(select(AuditLog).where(AuditLog.case_version_id == version.id,
                          AuditLog.action == "DESENSITIZATION_DELETE_SUCCEEDED"))
        assert audit and audit.detail["sha256"] == digest and audit.detail["pointCount"] == 875
        validate_potree((root / version.viewer_manifest_key).parent, 875)
        report["delete"] = {"id": version.id, "points": 875, "sha256": digest, "audit_id": audit.id,
                            "source": version.source_file.storage_key, "manifest": version.viewer_manifest_key}


if __name__ == "__main__":
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--report", type=Path, default=Path("storage/verification/m7-result.json"))
    args = parser.parse_args()
    result = {"started_at": datetime.now(UTC).isoformat(), "passed": False}
    try:
        verify(args.base_url, result, os.environ.get("M7_ADMIN_PASSWORD", "M0DemoPass!2026"))
        result["passed"] = True
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
