"""PDAL-backed physical DELETE desensitization for derived versions."""
import hashlib,json,subprocess
from datetime import UTC,datetime
from pathlib import Path
from sqlalchemy import select
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.case import AuditLog,CaseVersion,DesensitizationRule,Job
from app.services.conversion import _read_pdal_metadata,_tool_error,run_conversion
def _safe(root,key):
 raw=root/Path(key)
 if Path(key).is_absolute() or ".." in Path(key).parts or raw.is_symlink(): raise RuntimeError("Unsafe controlled storage path")
 path=raw.resolve()
 if root not in path.parents: raise RuntimeError("Unsafe controlled storage path")
 return path
def _bounds(g):
 a,b=g["min"],g["max"];return f"([{a[0]},{b[0]}],[{a[1]},{b[1]}],[{a[2]},{b[2]}])"
def run_delete_desensitization(job_id):
 s=get_settings();root=Path(s.storage_root).resolve()
 try:
  with SessionLocal.begin() as db:
   job=db.scalar(select(Job).where(Job.id==job_id));v=job.case_version if job else None
   if not job or not v:return
   parent=db.get(CaseVersion,v.parent_version_id);rules=db.scalars(select(DesensitizationRule).where(DesensitizationRule.case_version_id==v.id,DesensitizationRule.mode=="DELETE",DesensitizationRule.status=="APPLIED")).all()
   if not parent or not rules: raise RuntimeError("Derived DELETE version has no parent/rules")
   unavailable=_tool_error("PDAL",s.pdal_path)
   if unavailable: raise RuntimeError(unavailable)
   source=_safe(root,parent.source_file.storage_key);output=_safe(root,v.source_file.storage_key)
   if not source.is_file() or output.exists(): raise RuntimeError("Derived output is unsafe or already exists")
   output.parent.mkdir(parents=True,exist_ok=True)
   pipeline=[str(source)]+[{"type":"filters.crop","bounds":_bounds(r.geometry),"outside":True} for r in rules]+[{"type":"writers.las","filename":str(output)}]
   result=subprocess.run([s.pdal_path,"pipeline","--stdin"],input=json.dumps({"pipeline":pipeline}),capture_output=True,text=True,timeout=s.conversion_timeout_seconds,check=False)
   if result.returncode!=0 or not output.is_file(): raise RuntimeError(f"PDAL delete pipeline failed: {result.stderr.strip() or result.stdout.strip()}")
   count,bounds=_read_pdal_metadata(output);pc=parent.point_count
   if pc is None: pc,_=_read_pdal_metadata(source)
   if count>pc: raise RuntimeError("DELETE output point count exceeds parent")
   with output.open("rb") as stream: digest=hashlib.file_digest(stream,"sha256").hexdigest()
   v.source_file.size_bytes=output.stat().st_size;v.source_file.checksum_sha256=digest;v.point_count=count;v.bounds=bounds;job.progress=45
   db.add(AuditLog(action="DESENSITIZATION_DELETE_SUCCEEDED",case_id=v.case_id,case_version_id=v.id,job_id=job.id,detail={"deleteRuleCount":len(rules),"parentPointCount":pc,"pointCount":count,"sha256":digest}))
  run_conversion(job_id)
 except Exception as exc:
  with SessionLocal.begin() as db:
   job=db.scalar(select(Job).where(Job.id==job_id))
   if job:
    v=job.case_version;v.status,v.error_message="FAILED",str(exc)[:4000];job.status,job.error_message,job.finished_at="FAILED",v.error_message,datetime.now(UTC);db.add(AuditLog(action="DESENSITIZATION_DELETE_FAILED",case_id=v.case_id,case_version_id=v.id,job_id=job.id,detail={"error":v.error_message}))
