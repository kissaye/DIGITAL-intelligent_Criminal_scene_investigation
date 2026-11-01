"""Explicit integration check on an EMPTY disposable local PostgreSQL database.

Set PG_VALIDATION_URL to a database named diep_migration_check*. Never uses DATABASE_URL.
Run from backend: python tests/validate_postgresql_migrations.py
"""
import hashlib
import json
import os
import sys
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from alembic import command
from alembic.config import Config

url = os.environ['PG_VALIDATION_URL']
parsed = make_url(url)
if parsed.host not in {'127.0.0.1', 'localhost'} or not (parsed.database or '').startswith('diep_migration_check'):
    raise SystemExit('Only disposable local diep_migration_check* databases are permitted')
os.environ['DATABASE_URL'] = url
from app.core.config import get_settings
get_settings().database_url = url

engine = create_engine(url)
if inspect(engine).get_table_names():
    raise SystemExit('Database must be empty; refusing to modify existing data')
config = Config('alembic.ini')
checks = []


def revision():
    with engine.connect() as db:
        return db.execute(text('select version_num from alembic_version')).scalar_one()


command.upgrade(config, '202610300005')
meta = MetaData(); meta.reflect(engine)
now = datetime.now(UTC)
fixtures = {
    'roles': [dict(id=1, code='ADMIN', name='Admin'), dict(id=2, code='TEACHER', name='Teacher'), dict(id=3, code='STUDENT', name='Student')],
    'users': [dict(id=i, username=name, display_name=name, password_hash='synthetic-not-a-login-password') for i,name in [(1,'admin'),(2,'teacher'),(3,'student')]],
    'user_roles': [dict(user_id=i,role_id=i) for i in (1,2,3)],
    'cases': [dict(id='case-legacy',title='Synthetic case',internal_code='SYNTHETIC',teaching_title='Synthetic teaching',created_by_id=1)],
    'files': [dict(id='file-legacy',case_id='case-legacy',storage_key='synthetic/raw',original_name='synthetic.las',mime_type='application/octet-stream',size_bytes=1,checksum_sha256='0'*64)],
    'case_versions': [dict(id='version-legacy',case_id='case-legacy',source_file_id='file-legacy',version_number=1,status='READY',viewer_manifest_key='cases/case-legacy/versions/version-legacy/potree/metadata.json')],
    'courses': [dict(id='course-legacy',name='Legacy course',created_by=2)],
    'classes': [dict(id='class-legacy',course_id='course-legacy',name='Legacy class')],
    'class_members': [dict(id='member-legacy',class_id='class-legacy',user_id=3)],
    'tasks': [dict(id='task-legacy',title='Legacy task',case_version_id='version-legacy',created_by=2,status='PUBLISHED',allow_late=False)],
    'task_assignments': [dict(id='assignment-legacy',task_id='task-legacy',student_id=3)],
    'submissions': [dict(id='submission-legacy',task_id='task-legacy',student_id=3,status='SUBMITTED',report_content={'overview':'preserve me'},version_no=1,submitted_at=now)],
    'submission_marks': [dict(id='mark-legacy',submission_id='submission-legacy',title='Legacy mark',geometry={'position':{'x':1,'y':2,'z':3}})],
    'submission_measurements': [dict(id='measurement-legacy',submission_id='submission-legacy',start_point={'x':0,'y':0,'z':0},end_point={'x':3,'y':4,'z':0},distance=5)],
    'audit_logs': [dict(id='audit-legacy',action='SYNTHETIC_FIXTURE',actor_id=1,case_id='case-legacy')],
}
with engine.begin() as db:
    for table, rows in fixtures.items(): db.execute(meta.tables[table].insert(), rows)


def snapshot():
    data = {}
    with engine.connect() as db:
        for name in fixtures:
            # Use the original M3 reflected columns so new nullable columns are excluded.
            data[name] = sorted([dict(r) for r in db.execute(select(meta.tables[name])).mappings()],key=lambda r:json.dumps(r,sort_keys=True,default=str))
    return data


baseline = snapshot()
pg_bin = Path(os.environ['PG_VALIDATION_BIN']) if os.environ.get('PG_VALIDATION_BIN') else None
backup = Path('../tmp/pg-validation/m3-backup.dump').resolve()
if pg_bin:
    subprocess.run([str(pg_bin/'pg_dump.exe'),'-h',parsed.host,'-p',str(parsed.port or 5432),'-U',parsed.username,'-Fc','-f',str(backup),parsed.database],check=True)
    checks.append('M3 pg_dump custom-format backup: passed')
for target in ('202610310006','202611010007'):
    command.upgrade(config,target)
    assert revision() == target
    assert snapshot() == baseline, 'Legacy data changed during upgrade'
    checks.append('upgrade '+target+': legacy rows unchanged')
with engine.connect() as db:
    assert db.execute(text('select course_id from tasks')).scalar_one() is None
    assert db.execute(text('select parent_version_id from case_versions')).scalar_one() is None
checks.append('new nullable columns preserve unassigned M3 tasks/versions')
for target in ('202610310006','202610300005'):
    command.downgrade(config,target)
    assert revision() == target and snapshot() == baseline
    checks.append('downgrade '+target+': legacy rows unchanged')
command.upgrade(config,'head')
assert snapshot() == baseline
checks.append('repeat upgrade to head: passed')

# Real API requests against the migrated PostgreSQL schema, with synthetic point-cloud output.
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.api.deps import get_db
from app.core.security import create_access_token
sessions = sessionmaker(engine,autoflush=False,expire_on_commit=False)
def database():
    with sessions() as db: yield db
app.dependency_overrides[get_db] = database
storage = Path('../tmp/pg-validation/synthetic-storage').resolve()
get_settings().storage_root = str(storage)
source = storage/'cases/case-legacy/versions/version-legacy/potree'
source.mkdir(parents=True,exist_ok=True)
(source/'metadata.json').write_text('{"name":"synthetic"}',encoding='utf-8')
(source/'octree.bin').write_bytes(b'synthetic')
client = TestClient(app)
def api(method,path,data=None,user='teacher',status=200):
    response = client.request(method,'/api/v1'+path,json=data,headers={'Authorization':'Bearer '+create_access_token(user)[0]})
    assert response.status_code == status, (path,response.status_code,response.text)
    return response.json()['data']
expiry = (now+timedelta(days=10)).isoformat()
a = api('POST','/cases/case-legacy/authorizations',dict(reference='SYNTHETIC',scope='test',validUntil=expiry),user='admin',status=201)
api('POST','/case-versions/version-legacy/publish',dict(authorizationId=a['id'],validUntil=expiry,reviewConfirmed=True,reviewNote='synthetic review'),user='admin')
task_payload=dict(courseId='course-legacy',title='PostgreSQL task',classIds=['class-legacy'],caseVersionId='version-legacy',rubric=[dict(title='Observation',maxScore='60.10'),dict(title='Report',maxScore='39.90')])
t = api('POST','/teacher/tasks',task_payload,status=201)
api('POST',f'/teacher/tasks/{t["id"]}/publish')
s = api('POST',f'/student/tasks/{t["id"]}/submissions',dict(reportContent={'overview':'PostgreSQL test'}),user='student')
grade = dict(feedback='passed',items=[dict(rubricItemId=r['id'],score=r['maxScore']) for r in t['rubric']])
api('PUT',f'/teacher/submissions/{s["id"]}/grade',grade)
g = api('POST',f'/teacher/submissions/{s["id"]}/grade/publish')
assert float(g['totalScore']) == 100
api('GET',f'/student/submissions/{s["id"]}/grade',user='student')
api('POST',f'/authorizations/{a["id"]}/revoke',user='admin')
api('POST','/teacher/tasks',task_payload,status=409)
checks.append('PostgreSQL-backed M4/M5 API publication/task/submission/Decimal grading/revocation: passed')
client.close();app.dependency_overrides.clear()
if pg_bin:
    restore_name=parsed.database+'_restore'
    restored=create_engine(parsed.set(database=restore_name))
    if inspect(restored).get_table_names():raise RuntimeError('Restore database must be empty')
    subprocess.run([str(pg_bin/'pg_restore.exe'),'-h',parsed.host,'-p',str(parsed.port or 5432),'-U',parsed.username,'--exit-on-error','-d',restore_name,str(backup)],check=True)
    with restored.connect() as db:
        for name, expected in baseline.items():
            rows=sorted([dict(r) for r in db.execute(select(meta.tables[name])).mappings()],key=lambda r:json.dumps(r,sort_keys=True,default=str))
            assert rows==expected, 'Backup restore mismatch: '+name
    restored.dispose()
    checks.append('pg_restore into separate database: all M3 fixture rows identical')
with engine.connect() as db: server=db.execute(text('select version()')).scalar_one()
report=dict(server=server,revision=revision(),checks=checks,legacyRowCounts={k:len(v) for k,v in baseline.items()},baselineSha256=hashlib.sha256(json.dumps(baseline,sort_keys=True,default=str).encode()).hexdigest(),note='Synthetic isolated PostgreSQL validation; no production data migrated')
output=Path('../tmp/pg-validation/result.json');output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(report,indent=2,ensure_ascii=False))
engine.dispose()
