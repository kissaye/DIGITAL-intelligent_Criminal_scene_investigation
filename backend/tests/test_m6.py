"""Focused M6 contract tests; reuses the isolated M5 publication fixture."""
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
import pytest
from sqlalchemy import select
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.case import AuditLog, CaseVersion, DesensitizationRule, File, Job, TeachingCopy
from app.models.practice import Task, TaskAssignment
from app.models.user import User
from app.services import desensitization as desensitization_service
from test_m5 import published

BOX={"type":"BOX","min":[0,0,0],"max":[1,1,1]}

def test_admin_and_box_validation(published):
    client,admin,teacher,_,_,version_id,_,_=published
    with SessionLocal.begin() as db:
        parent=db.get(CaseVersion,version_id); draft=CaseVersion(case_id=parent.case_id,source_file_id=parent.source_file_id,parent_version_id=parent.id,version_number=97,status="DRAFT");db.add(draft);db.flush(); draft_id=draft.id
    url=f"/api/v1/case-versions/{draft_id}/desensitization-rules"
    assert client.post(url,headers=teacher,json={"mode":"HIDE","geometry":BOX,"title":"x"}).status_code==403
    assert client.post(url,headers=admin,json={"mode":"HIDE","geometry":{"type":"BOX","min":[1,0,0],"max":[1,2,3]},"title":"x"}).status_code==422
    assert client.post(url,headers=admin,json={"mode":"HIDE","geometry":BOX,"title":"x"}).status_code==201

def test_apply_lineage_publish_guard_and_forced_viewer_rules(published):
    client,admin,teacher,student,case_id,version_id,auth,publish=published
    url=f"/api/v1/case-versions/{version_id}/desensitization-rules"
    # Parent is already published: direct edits are blocked.
    assert client.post(url,headers=admin,json={"mode":"HIDE","geometry":BOX,"title":"blocked"}).status_code==409
    # A READY parent permits a new HIDE-only lineage; create directly for isolation.
    with SessionLocal.begin() as db:
        parent=db.get(CaseVersion,version_id); child=CaseVersion(case_id=parent.case_id,source_file_id=parent.source_file_id,parent_version_id=parent.id,version_number=99,status="READY",viewer_manifest_key=f"cases/{case_id}/versions/{version_id}/potree/metadata.json");db.add(child);db.flush(); child_id=child.id
    r=client.post(f"/api/v1/case-versions/{child_id}/desensitization-rules",headers=admin,json={"mode":"HIDE","geometry":BOX,"title":"mask"});assert r.status_code==201
    applied=client.post(f"/api/v1/case-versions/{child_id}/desensitization/apply",headers=admin);assert applied.status_code==202
    derived_id=applied.json()["data"]["versionId"]
    assert applied.json()["data"]["parentVersionId"]==child_id
    with SessionLocal() as db:
        assert db.scalar(select(DesensitizationRule).where(DesensitizationRule.case_version_id==child_id)).status=="DRAFT"
        assert db.scalar(select(DesensitizationRule).where(DesensitizationRule.case_version_id==derived_id)).status=="APPLIED"
    config=client.get(f"/api/v1/case-versions/{derived_id}/viewer-config",headers=admin)
    assert config.status_code==200
    preview=config.json()["data"]["forcedDesensitizationRules"]
    assert preview[0]["mode"]=="HIDE" and preview[0]["preview"] is True and preview[0]["enforced"] is False

def test_delete_apply_creates_derived_failed_when_pdal_missing(published):
    client,admin,_,_,_,version_id,_,_=published
    with SessionLocal.begin() as db:
        parent=db.get(CaseVersion,version_id); draft=CaseVersion(case_id=parent.case_id,source_file_id=parent.source_file_id,parent_version_id=parent.id,version_number=100,status="DRAFT");db.add(draft);db.flush();draft_id=draft.id
    assert client.post(f"/api/v1/case-versions/{draft_id}/desensitization-rules",headers=admin,json={"mode":"DELETE","geometry":BOX,"title":"delete"}).status_code==201
    response=client.post(f"/api/v1/case-versions/{draft_id}/desensitization/apply",headers=admin);assert response.status_code==202
    derived=response.json()["data"];assert derived["parentVersionId"]==draft_id
    # Queue or PDAL failure is durable and never reported as READY.
    with SessionLocal() as db: assert db.get(CaseVersion,derived["versionId"]).status in {"PROCESSING","FAILED"}

def test_delete_worker_success_builds_pipeline_and_new_file(published, monkeypatch):
    client,admin,_,_,_,version_id,_,_=published
    settings=get_settings(); root=Path(settings.storage_root).resolve()
    with SessionLocal.begin() as db:
        published_parent=db.get(CaseVersion,version_id)
        parent=CaseVersion(case_id=published_parent.case_id,source_file_id=published_parent.source_file_id,parent_version_id=published_parent.id,version_number=101,status="READY",point_count=10,bounds={"min":[0,0,0],"max":[9,9,9]})
        db.add(parent);db.flush();parent_id=parent.id;source_key=parent.source_file.storage_key
    source=root/source_key;source.parent.mkdir(parents=True,exist_ok=True);source.write_bytes(b"parent-las")
    assert client.post(f"/api/v1/case-versions/{parent_id}/desensitization-rules",headers=admin,json={"mode":"DELETE","geometry":BOX,"title":"delete"}).status_code==201
    class OfflineQueue:
        def enqueue(self,*args,**kwargs): raise RuntimeError("offline test queue")
    monkeypatch.setattr("app.api.routes.desensitization.get_queue",lambda:OfflineQueue())
    response=client.post(f"/api/v1/case-versions/{parent_id}/desensitization/apply",headers=admin)
    assert response.status_code==202
    derived=response.json()["data"];derived_id=derived["versionId"];job_id=derived["jobId"]
    with SessionLocal.begin() as db:
        version=db.get(CaseVersion,derived_id);job=db.get(Job,job_id)
        version.status="PROCESSING";version.error_message=None;job.status="PENDING";job.error_message=None
        output_key=version.source_file.storage_key
        assert version.source_file_id!=db.get(CaseVersion,parent_id).source_file_id
    captured={}
    def fake_run(command,**kwargs):
        captured["command"]=command;captured["pipeline"]=json.loads(kwargs["input"])["pipeline"]
        output=Path(captured["pipeline"][-1]["filename"]);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(b"derived-las")
        class Result: returncode=0;stdout="";stderr=""
        return Result()
    converted=[]
    monkeypatch.setattr(desensitization_service,"_tool_error",lambda *args:None)
    monkeypatch.setattr(desensitization_service.subprocess,"run",fake_run)
    monkeypatch.setattr(desensitization_service,"_read_pdal_metadata",lambda path:(7,{"min":[0,0,0],"max":[9,9,9]}))
    monkeypatch.setattr(desensitization_service,"run_conversion",lambda value:converted.append(value))
    desensitization_service.run_delete_desensitization(job_id)
    assert captured["pipeline"][1]=={"type":"filters.crop","bounds":"([0.0,1.0],[0.0,1.0],[0.0,1.0])","outside":True}
    assert converted==[job_id]
    with SessionLocal() as db:
        version=db.get(CaseVersion,derived_id);output_file=db.get(File,version.source_file_id)
        assert output_file.storage_key==output_key and output_file.size_bytes==len(b"derived-las")
        assert output_file.checksum_sha256==hashlib.sha256(b"derived-las").hexdigest()
        assert version.point_count==7 and source.read_bytes()==b"parent-las"
        audit=db.scalar(select(AuditLog).where(AuditLog.case_version_id==derived_id,AuditLog.action=="DESENSITIZATION_DELETE_SUCCEEDED"))
        assert audit.detail["parentPointCount"]==10 and audit.detail["pointCount"]==7
