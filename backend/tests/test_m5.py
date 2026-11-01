import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from sqlalchemy import delete, select
import test_m4
from app.core.config import get_settings
from app.models.case import CaseVersion
from app.models.publication import TeachingCopy


class PublicationWorkflow(unittest.TestCase):
    call = test_m4.TeachingWorkflow.call
    setup_task = test_m4.TeachingWorkflow.setup_task

    def setUp(self):
        test_m4.TeachingWorkflow.setUp(self)
        self.old_storage=get_settings().storage_root
        get_settings().storage_root=str(Path(self.tmp.name)/'storage')
        with self.sessions.begin() as db:
            v=db.get(CaseVersion,self.version);self.case_id=v.case_id
            db.execute(delete(TeachingCopy));v.status='READY'
        self.source=Path(get_settings().storage_root)/'cases'/self.case_id/'versions'/self.version/'potree'
        self.source.mkdir(parents=True)
        (self.source/'metadata.json').write_text(json.dumps({'name':'synthetic-test'}))
        (self.source/'octree.bin').write_bytes(b'synthetic-points')
        expiry=(datetime.now(UTC)+timedelta(days=5)).isoformat()
        a=self.call('POST',f'/cases/{self.case_id}/authorizations',{'reference':'TEST-ONLY','scope':'synthetic teaching','validUntil':expiry},user='admin',code=201)
        self.authorization_id=a['id']
        self.publication={'authorizationId':a['id'],'validUntil':expiry,'reviewConfirmed':True,'reviewNote':'synthetic reviewed data'}

    def tearDown(self):
        get_settings().storage_root=self.old_storage
        test_m4.TeachingWorkflow.tearDown(self)

    def test_copy_is_independent_and_revocation_blocks_access(self):
        path=f'/case-versions/{self.version}/publish'
        self.call('POST',path,self.publication,user='teacher',code=403)
        self.call('POST',path,{**self.publication,'reviewConfirmed':False},user='admin',code=422)
        self.call('POST',path,self.publication,user='admin')
        self.call('POST',path,self.publication,user='admin',code=409)
        with self.sessions() as db:
            copy=db.scalar(select(TeachingCopy));manifest=Path(get_settings().storage_root)/copy.manifest_key
        self.assertNotEqual(manifest.parent,self.source)
        (self.source/'metadata.json').write_text('changed source')
        self.assertEqual(json.loads(manifest.read_text())['name'],'synthetic-test')
        task=self.setup_task();tid=task['id']
        self.call('POST',f'/teacher/tasks/{tid}/publish')
        self.call('GET',f'/student/tasks/{tid}/workspace',user='student')
        asset=f'/viewer-assets/{self.version}/metadata.json'
        response=self.client.get('/api/v1'+asset)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['name'],'synthetic-test')
        self.call('POST',f'/authorizations/{self.authorization_id}/revoke',user='admin')
        self.assertEqual(self.call('GET','/teacher/case-versions'),[])
        self.call('GET',f'/student/tasks/{tid}/workspace',user='student',code=409)
        self.call('GET',asset,user='student',code=409)
        self.call('PUT',f'/student/tasks/{tid}/draft',{},user='student',code=409)
        self.call('POST','/teacher/tasks',self.payload,code=409)
        logs=self.call('GET',f'/audit-logs?caseId={self.case_id}&action=VERSION_PUBLISHED',user='admin')
        self.assertEqual(logs['total'],1)
        self.call('GET','/audit-logs',user='student',code=403)

    def test_expiry_blocks_new_tasks_and_submission(self):
        self.call('POST',f'/case-versions/{self.version}/publish',self.publication,user='admin')
        task=self.setup_task();self.call('POST',f'/teacher/tasks/{task["id"]}/publish')
        with self.sessions.begin() as db:db.scalar(select(TeachingCopy)).valid_until=datetime.now(UTC)-timedelta(seconds=1)
        self.call('POST','/teacher/tasks',self.payload,code=409)
        self.call('POST',f'/student/tasks/{task["id"]}/submissions',{},user='student',code=409)
        self.assertEqual(self.call('GET','/teacher/case-versions'),[])

    def test_invalid_publication_and_lineage(self):
        self.call('POST',f'/case-versions/{self.version}/publish',{**self.publication,'validUntil':(datetime.now(UTC)+timedelta(days=10)).isoformat()},user='admin',code=422)
        (self.source/'raw.las').write_bytes(b'not allowed')
        self.call('POST',f'/case-versions/{self.version}/publish',self.publication,user='admin',code=409)
        self.assertEqual(list((Path(get_settings().storage_root)/'teaching').glob('*')),[])
        versions=self.call('GET',f'/cases/{self.case_id}/versions',user='admin')
        self.assertEqual(versions[0]['parentVersionId'],None)
        self.call('GET',f'/cases/{self.case_id}/authorizations',user='teacher',code=403)

    def test_published_version_cannot_be_reconverted(self):
        from unittest.mock import patch
        from app.models.case import Job
        from app.services.conversion import run_conversion
        self.call('POST',f'/case-versions/{self.version}/publish',self.publication,user='admin')
        with self.sessions.begin() as db:
            job=Job(case_version_id=self.version,status='PENDING',progress=0)
            db.add(job);db.flush();jid=job.id
        with patch('app.services.conversion.SessionLocal',self.sessions):run_conversion(jid)
        with self.sessions() as db:
            self.assertEqual(db.get(CaseVersion,self.version).status,'PUBLISHED')
            self.assertEqual(db.get(Job,jid).status,'PENDING')
