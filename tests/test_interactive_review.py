"""Saved interactive review never grants execution or accesses unscoped secrets."""
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy
from adaptive_qa.interactive_review import review_saved_interactive, revalidate_saved_interactive
from adaptive_qa.local_free import LocalFreeProjects, LOCAL_ACTOR
from adaptive_qa.project_settings import reference_name
from adaptive_qa.project_store import ProjectActor, ProjectStore, ProjectNotFound
from adaptive_qa.secrets import SecretReference


class SavedInteractiveReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=ProjectStore(Path(self.temp.name)/'projects.sqlite')
        self.owner=ProjectActor('a'*32);self.other=ProjectActor('b'*32)
        self.project=self.store.create(self.owner,'Interactive review')
        self.pid=self.project.project_id
        self.data=dict(base_url='http://127.0.0.1:8000/interactive/login-transition',allowed_hosts=['127.0.0.1'],
            allow_data_changes=True,secret_references={slot:reference_name(self.owner.user_id,self.pid,slot)
                for slot in ('login_username','login_password')})
        self.store.save_configuration(self.owner,self.pid,self.data)
        self.completion=ElementMapping('login.accepted',(LocatorSpec(LocatorStrategy.TEST_ID,'result'),))

    def review(self):
        return review_saved_interactive(self.store,self.owner,self.pid,fixture_id='login-transition',completion=self.completion)

    def test_review_never_resolves_connects_enqueues_or_authorizes_execution(self):
        with patch.object(SecretReference,'resolve',side_effect=AssertionError('No values')),patch('socket.socket',side_effect=AssertionError('No sockets')):
            review=self.review()
            self.assertFalse(review.execution_authorized)
            self.assertFalse(review.public()['execution_authorized'])
            self.assertEqual(revalidate_saved_interactive(self.store,self.owner,review),review)
        self.assertEqual(tuple(ref.environment_variable for ref in review.submission.form.inputs),tuple(self.data['secret_references'].values()))
        with self.store._connection() as connection:
            tables={row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn('dashboard_test_runs',tables)
        self.assertNotIn('secret_references',json.dumps(review.public()))

    def test_cross_owner_and_missing_project_have_identical_not_found(self):
        errors=[]
        for actor,pid in ((self.other,self.pid),(self.owner,'0'*32)):
            with self.assertRaises(ProjectNotFound) as raised:
                review_saved_interactive(self.store,actor,pid,fixture_id='login-transition',completion=self.completion)
            errors.append(str(raised.exception))
        self.assertEqual(errors[0],errors[1])
        with self.assertRaises(ProjectNotFound):revalidate_saved_interactive(self.store,self.other,self.review())

    def test_policy_reference_target_and_mapping_changes_invalidate_review(self):
        review=self.review()
        changes=({'allow_data_changes':False},{'secret_references':{}},
            {'base_url':'http://127.0.0.1:8000/interactive/login-rejected'},
            {'form_mappings':[dict(logical_name='login.username',scope_test_id=None,
                locators=[dict(strategy='label',value='Different input',role=None)])]})
        for change in changes:
            self.store.save_configuration(self.owner,self.pid,dict(self.data,**change))
            with self.assertRaises(ValueError):revalidate_saved_interactive(self.store,self.owner,review)
            self.store.save_configuration(self.owner,self.pid,self.data)
        self.assertEqual(revalidate_saved_interactive(self.store,self.owner,review),review)

    def test_invalid_or_cross_scope_saved_reference_never_resolves(self):
        for value in ('PATH',reference_name(self.other.user_id,self.pid,'login_password')):
            with self.store._connection() as connection:
                corrupted=dict(self.data,secret_references=dict(self.data['secret_references'],login_password=value))
                connection.execute('UPDATE dashboard_project_settings SET settings_json=? WHERE project_id=?',(json.dumps(corrupted),self.pid))
            with patch.object(SecretReference,'resolve',side_effect=AssertionError('No values')),self.assertRaises(ValueError):self.review()
        self.store.save_configuration(self.owner,self.pid,self.data)

    def test_missing_references_and_mismatched_postconditions_are_blocked(self):
        for completion in (None,replace(self.completion,logical_name='login.rejected')):
            with self.assertRaises(ValueError):
                review_saved_interactive(self.store,self.owner,self.pid,fixture_id='login-transition',completion=completion)
        self.store.save_configuration(self.owner,self.pid,dict(self.data,secret_references={}))
        with self.assertRaises(ValueError):self.review()

    def test_search_uses_its_own_scoped_saved_reference(self):
        data=dict(self.data,base_url='http://127.0.0.1:8000/interactive/search-empty',
            secret_references={'search_query':reference_name(self.owner.user_id,self.pid,'search_query')})
        self.store.save_configuration(self.owner,self.pid,data)
        completion=replace(self.completion,logical_name='search.empty')
        review=review_saved_interactive(self.store,self.owner,self.pid,fixture_id='search-empty',completion=completion)
        self.assertEqual(review.submission.form.inputs,(SecretReference(data['secret_references']['search_query']),))
        self.assertFalse(review.public()['execution_authorized'])

    def test_free_single_project_workspace_preserves_local_identity(self):
        store=LocalFreeProjects(Path(self.temp.name)/'free.sqlite')
        project=store.create(LOCAL_ACTOR,'Free local project')
        data=dict(self.data,secret_references={slot:reference_name(LOCAL_ACTOR.user_id,project.project_id,slot)
            for slot in ('login_username','login_password')})
        store.save_configuration(LOCAL_ACTOR,project.project_id,data)
        review=review_saved_interactive(store,LOCAL_ACTOR,project.project_id,fixture_id='login-transition',completion=self.completion)
        self.assertEqual(review.owner_id,LOCAL_ACTOR.user_id)
        with self.assertRaises(ValueError):store.create(LOCAL_ACTOR,'Second')

    def test_external_target_and_unbound_fixture_do_not_expand_execution_scope(self):
        self.store.save_configuration(self.owner,self.pid,dict(self.data,base_url='https://example.com/',allowed_hosts=['example.com']))
        with self.assertRaises(ValueError):self.review()
        with self.assertRaises(ValueError):
            review_saved_interactive(self.store,self.owner,self.pid,fixture_id='busy',completion=self.completion)
