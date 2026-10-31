"""Run from backend: python -m unittest discover -s tests -v."""
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.session import Base
from app.main import app
from app.models.case import Case, CaseVersion, File
from app.models.practice import Submission, Task
from app.models.role import Role
from app.models.user import User


class TeachingWorkflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = create_engine('sqlite:///' + str(Path(self.tmp.name) / 'test.db'), connect_args={'check_same_thread': False})
        @event.listens_for(self.engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False, autoflush=False)
        def database():
            with self.sessions() as session:
                yield session
        app.dependency_overrides[get_db] = database
        self.client = TestClient(app)
        with self.sessions.begin() as db:
            roles = {code: Role(code=code, name=code) for code in ('TEACHER','STUDENT','ADMIN')}
            db.add_all(roles.values())
            for name, code in [('teacher','TEACHER'),('other','TEACHER'),('student','STUDENT'),('outsider','STUDENT'),('admin','ADMIN')]:
                db.add(User(username=name, display_name=name, password_hash='unused', roles=[roles[code]]))
            db.flush()
            admin = db.scalar(select(User).where(User.username=='admin'))
            case = Case(title='fixture', teaching_title='教学场景', internal_code='TEST', created_by_id=admin.id)
            db.add(case); db.flush()
            file = File(case_id=case.id, storage_key='test/raw', original_name='fixture.las', mime_type='application/octet-stream', size_bytes=1, checksum_sha256='0'*64)
            db.add(file); db.flush()
            version = CaseVersion(case_id=case.id, source_file_id=file.id, version_number=1, status='READY', viewer_manifest_key='test/metadata.json')
            db.add(version); db.flush(); self.version = version.id

    def tearDown(self):
        self.client.close(); app.dependency_overrides.clear(); self.engine.dispose(); self.tmp.cleanup()

    def call(self, method, path, data=None, user='teacher', code=200):
        token = create_access_token(user)[0]
        response = self.client.request(method, '/api/v1'+path, json=data, headers={'Authorization':'Bearer '+token})
        self.assertEqual(response.status_code, code, response.text)
        return response.json().get('data')

    def setup_task(self):
        c = self.call('POST','/teacher/courses',{'name':'现场勘验'},code=201)
        g = self.call('POST',f'/teacher/courses/{c["id"]}/classes',{'name':'一班'},code=201)
        student = self.call('GET','/teacher/students?username=student')[0]
        for _ in range(2):
            group = self.call('POST',f'/teacher/classes/{g["id"]}/members',{'studentId':student['id']})
            self.assertEqual(len(group['members']),1)
        now = datetime.now(UTC)
        payload = {'courseId':c['id'],'title':'任务','classIds':[g['id']],'caseVersionId':self.version,'startAt':(now-timedelta(hours=1)).isoformat(),'dueAt':(now+timedelta(days=1)).isoformat(),'rubric':[{'title':'观察','maxScore':'60.10'},{'title':'笔录','maxScore':'39.90'}]}
        task = self.call('POST','/teacher/tasks',payload,code=201)
        self.course_id, self.class_id, self.student_id, self.payload = c['id'],g['id'],student['id'],payload
        return task

    def test_full_workflow_and_ownership(self):
        task = self.setup_task(); tid = task['id']
        self.call('GET',f'/teacher/courses/{self.course_id}',user='other',code=404)
        self.call('PATCH',f'/teacher/classes/{self.class_id}',{'name':'越权'},user='other',code=404)
        self.call('GET','/teacher/courses',user='student',code=403)
        self.call('GET','/teacher/courses',user='admin',code=403)
        self.assertEqual(self.call('GET','/student/tasks',user='student'),[])
        self.call('POST',f'/teacher/tasks/{tid}/publish',user='other',code=404)
        self.call('POST',f'/teacher/tasks/{tid}/publish')
        self.call('PATCH',f'/teacher/tasks/{tid}',self.payload,code=409)
        self.assertEqual(self.call('GET','/student/tasks',user='student')[0]['status'],'IN_PROGRESS')
        self.assertEqual(self.call('GET','/student/tasks',user='outsider'),[])
        self.call('GET',f'/student/tasks/{tid}/workspace',user='outsider',code=404)
        self.call('GET',f'/student/tasks/{tid}/workspace',user='student')
        draft={'reportContent':{'overview':'观察记录'},'marks':[{'geometry':{'position':{'x':1,'y':2,'z':3}},'title':'点位'}],'measurements':[{'startPoint':{'x':0,'y':0,'z':0},'endPoint':{'x':3,'y':4,'z':0},'distance':999}]}
        saved=self.call('PUT',f'/student/tasks/{tid}/draft',draft,user='student')
        self.assertEqual(saved['measurements'][0]['distance'],5)
        self.call('GET',f'/teacher/submissions/{saved["id"]}',code=409)
        submitted=self.call('POST',f'/student/tasks/{tid}/submissions',draft,user='student'); sid=submitted['id']
        self.call('PUT',f'/student/tasks/{tid}/draft',draft,user='student',code=409)
        self.call('POST',f'/student/tasks/{tid}/submissions',draft,user='student',code=409)
        self.call('GET',f'/teacher/submissions/{sid}',user='other',code=404)
        rubric=task['rubric']
        path=f'/teacher/submissions/{sid}/grade'
        self.call('PUT',path,{'items':[{'rubricItemId':rubric[0]['id'],'score':61}]},code=422)
        self.call('PUT',path,{'items':[{'rubricItemId':'foreign','score':1}]},code=422)
        self.call('PUT',path,{'items':[{'rubricItemId':rubric[0]['id'],'score':60.10}]})
        self.call('GET',f'/student/submissions/{sid}/grade',user='student',code=404)
        self.call('POST',path+'/publish',code=409)
        grade={'feedback':'完成良好','items':[{'rubricItemId':r['id'],'score':r['maxScore'],'comment':'达标'} for r in rubric]}
        self.call('PUT',path,grade)
        published=self.call('POST',path+'/publish'); self.assertEqual(float(published['totalScore']),100)
        self.call('PUT',path,grade,code=409)
        self.call('GET',f'/student/submissions/{sid}/grade',user='outsider',code=404)
        self.assertEqual(self.call('GET',f'/student/submissions/{sid}/grade',user='student')['feedback'],'完成良好')
        self.call('POST',f'/teacher/tasks/{tid}/close')
        self.call('GET',f'/student/tasks/{tid}/workspace',user='student',code=409)
        self.call('GET',f'/student/submissions/{sid}',user='student')

    def test_time_boundaries_close_and_asset_revocation(self):
        import jwt
        task=self.setup_task(); tid=task['id']
        self.call('POST',f'/teacher/tasks/{tid}/publish')
        with self.sessions.begin() as db:
            t=db.get(Task,tid); t.start_at=datetime.now(UTC)+timedelta(days=1)
        self.call('GET',f'/student/tasks/{tid}/workspace',user='student',code=409)
        self.call('PUT',f'/student/tasks/{tid}/draft',{'marks':[]},user='student',code=409)
        with self.sessions.begin() as db:
            t=db.get(Task,tid);t.start_at=None;t.due_at=datetime.now(UTC)-timedelta(seconds=1)
        self.assertEqual(self.call('GET','/student/tasks',user='student')[0]['status'],'EXPIRED')
        self.call('POST',f'/student/tasks/{tid}/submissions',{},user='student',code=409)
        with self.sessions.begin() as db: db.get(Task,tid).allow_late=True
        self.call('PUT',f'/student/tasks/{tid}/draft',{},user='student')
        token=jwt.encode({'sub':str(self.student_id),'version':self.version,'task':tid,'type':'student_viewer','exp':datetime.now(UTC)+timedelta(minutes=5)},get_settings().jwt_secret_key,algorithm='HS256')
        self.client.cookies.set(f'viewer_{self.version}',token)
        self.call('POST',f'/teacher/tasks/{tid}/close')
        self.assertEqual(self.call('GET','/student/tasks',user='student')[0]['status'],'CLOSED')
        self.call('PUT',f'/student/tasks/{tid}/draft',{},user='student',code=409)
        self.call('POST',f'/student/tasks/{tid}/submissions',{},user='student',code=409)
        self.call('GET',f'/viewer-assets/{self.version}/metadata.json',user='student',code=409)

    def test_publish_validation_and_assignment_snapshot(self):
        task=self.setup_task(); tid=task['id']
        invalid={**self.payload,'dueAt':self.payload['startAt']}
        self.call('POST','/teacher/tasks',invalid,code=422)
        self.call('POST',f'/teacher/classes/{self.class_id}/members',{'studentId':999999},code=422)
        self.call('POST',f'/teacher/tasks/{tid}/publish')
        self.call('POST',f'/teacher/tasks/{tid}/publish',code=409)
        self.call('DELETE',f'/teacher/classes/{self.class_id}/members/{self.student_id}')
        self.assertEqual(len(self.call('GET','/student/tasks',user='student')),1)
        other=self.call('POST','/teacher/courses',{'name':'其他教师'},user='other',code=201)
        group=self.call('POST',f'/teacher/courses/{other["id"]}/classes',{'name':'其他班'},user='other',code=201)
        self.call('POST','/teacher/tasks',{**self.payload,'classIds':[group['id']]},code=404)

    def test_migration_preserves_m3_rows_and_downgrades(self):
        from sqlalchemy import inspect, text
        settings=get_settings(); previous=settings.database_url
        url='sqlite:///'+str(Path(self.tmp.name)/'migration.db')
        settings.database_url=url
        config=Config('alembic.ini')
        migrated=create_engine(url)
        try:
            command.upgrade(config,'202610300005')
            with migrated.begin() as db:
                db.execute(text("INSERT INTO courses(id,name,created_by) VALUES ('legacy-course','M3 course',NULL)"))
                db.execute(text("INSERT INTO tasks(id,title,status) VALUES ('legacy-task','M3 task','PUBLISHED')"))
            command.upgrade(config,'head')
            with migrated.connect() as db:
                self.assertEqual(db.execute(text("SELECT course_id FROM tasks WHERE id='legacy-task'")).scalar(),None)
                self.assertEqual(db.execute(text("SELECT title FROM tasks WHERE id='legacy-task'")).scalar(),'M3 task')
            self.assertIn('submission_grades',inspect(migrated).get_table_names())
            command.downgrade(config,'202610300005')
            self.assertNotIn('course_id',[c['name'] for c in inspect(migrated).get_columns('tasks')])
            with migrated.connect() as db:
                self.assertEqual(db.execute(text('SELECT count(*) FROM tasks')).scalar(),1)
        finally:
            settings.database_url=previous; migrated.dispose()


if __name__ == '__main__':
    unittest.main()
