"""Saved HTTPS metadata remains owner-scoped and non-executing."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy
from adaptive_qa.project_settings import reference_name
from adaptive_qa.project_store import ProjectActor, ProjectStore, ProjectNotFound
from adaptive_qa.public_form_review import review_saved_public_form, revalidate_saved_public_form
from adaptive_qa.secrets import SecretReference


class SavedPublicFormReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=ProjectStore(Path(self.temp.name)/'projects.sqlite')
        self.owner=ProjectActor('a'*32);self.other=ProjectActor('b'*32)
        self.project=self.store.create(self.owner,'HTTPS review');self.pid=self.project.project_id
        self.data=dict(base_url='https://qa.example.test/search',allowed_hosts=['qa.example.test'],
            allow_data_changes=True,secret_references={'search_query':reference_name(self.owner.user_id,self.pid,'search_query')},
            local_form_binding=dict(profile='public_https',operation='search',
                document_url='https://qa.example.test/search',endpoint_url='https://qa.example.test/search/execute',
                field_names=['query'],accepted=dict(status_code=200,field_name='found',expected_value=True),
                rejected=dict(status_code=404,field_name='found',expected_value=False)))
        self.completion=ElementMapping('search.results',(LocatorSpec(LocatorStrategy.TEST_ID,'results-ready'),))
        self.save()

    def save(self,data=None):self.store.save_configuration(self.owner,self.pid,data or self.data)
    def review(self):return review_saved_public_form(self.store,self.owner,self.pid,completion=self.completion)

    def test_review_never_resolves_or_contacts_and_revalidates_unchanged(self):
        with patch.object(SecretReference,'resolve',side_effect=AssertionError('No values')),patch('socket.getaddrinfo',side_effect=AssertionError('No DNS')):
            review=self.review()
            self.assertFalse(review.execution_authorized)
            self.assertFalse(review.public()['execution_authorized'])
            self.assertEqual(revalidate_saved_public_form(self.store,self.owner,review),review)

    def test_owner_boundary_and_missing_project(self):
        for actor,pid in ((self.other,self.pid),(self.owner,'0'*32)):
            with self.assertRaises(ProjectNotFound):
                review_saved_public_form(self.store,actor,pid,completion=self.completion)
        with self.assertRaises(ProjectNotFound):revalidate_saved_public_form(self.store,self.other,self.review())

    def test_non_executing_save_does_not_bypass_policy_or_missing_references(self):
        for change in ({'allow_data_changes':False},{'secret_references':{}}):
            self.save(dict(self.data,**change))
            with self.assertRaises(ValueError):self.review()
        self.save()
        with self.assertRaises(ValueError):
            review_saved_public_form(self.store,self.owner,self.pid,completion=None)

    def test_changed_endpoint_or_settings_invalidates_previous_review(self):
        review=self.review()
        data=deepcopy(self.data);data['local_form_binding']['endpoint_url']='https://qa.example.test/v2/search'
        self.save(data)
        with self.assertRaises(ValueError):revalidate_saved_public_form(self.store,self.owner,review)
        self.save();self.assertEqual(revalidate_saved_public_form(self.store,self.owner,review),review)

    def test_explicit_profile_and_exact_origin_are_required(self):
        for change in ({'profile':'unknown'},{'endpoint_url':'https://127.0.0.1/execute'},
                       {'document_url':'https://qa.example.test/other'}):
            data=deepcopy(self.data);data['local_form_binding'].update(change)
            with self.assertRaises(ValueError):self.save(data)
        data=deepcopy(self.data);del data['local_form_binding']['profile']
        with self.assertRaises(ValueError):self.save(data)

    def test_review_cannot_enter_existing_local_execution_queue(self):
        from adaptive_qa.interactive_queue import OwnedInteractiveQueue
        queue=OwnedInteractiveQueue(self.store)
        with patch.object(SecretReference,'resolve',side_effect=AssertionError('No values')),self.assertRaises(ValueError):
            queue.submit(self.owner,self.review())

