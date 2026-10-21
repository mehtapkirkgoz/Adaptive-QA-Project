"""Real persisted cross-owner access checks before exposing dashboard endpoints."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from adaptive_qa.project_store import ProjectActor, ProjectNotFound, ProjectStore


class ProjectStoreTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'dashboard.db'
        self.store = ProjectStore(self.path)
        self.alice, self.bob = ProjectActor(uuid4().hex), ProjectActor(uuid4().hex)
        self.project = self.store.create(self.alice, 'First project')

    def test_project_persists_across_instances(self):
        self.assertEqual(ProjectStore(self.path).get(self.alice, self.project.project_id), self.project)

    def test_other_owner_cannot_get_or_rename_project(self):
        for operation in (lambda: self.store.get(self.bob, self.project.project_id),
                          lambda: self.store.rename(self.bob, self.project.project_id, 'Taken')):
            with self.assertRaises(ProjectNotFound):
                operation()
        self.assertEqual(self.store.get(self.alice, self.project.project_id), self.project)

    def test_missing_and_other_owner_projects_have_same_error(self):
        messages = []
        for identity in (uuid4().hex, self.project.project_id):
            with self.assertRaises(ProjectNotFound) as failure:
                self.store.get(self.bob, identity)
            messages.append(str(failure.exception))
        self.assertEqual(messages, ['Project not found.'] * 2)

    def test_list_only_contains_current_owner_and_stable_pages(self):
        second = self.store.create(self.alice, 'Second')
        other = self.store.create(self.bob, 'Other')
        self.assertEqual(self.store.list(self.alice, limit=1), (second,))
        self.assertEqual(self.store.list(self.alice, limit=1, offset=1), (self.project,))
        self.assertEqual(self.store.list(self.bob), (other,))

    def test_rename_keeps_owner_and_identity(self):
        renamed = self.store.rename(self.alice, self.project.project_id, 'Renamed')
        self.assertEqual(renamed.owner_id, self.alice.user_id)
        self.assertEqual(renamed.project_id, self.project.project_id)
        self.assertEqual(self.store.get(self.alice, renamed.project_id), renamed)

    def test_sql_looking_project_name_is_bound_as_text(self):
        name = "Project'); DROP TABLE dashboard_projects; --"
        created = self.store.create(self.alice, name)
        self.assertEqual(self.store.get(self.alice, created.project_id).name, name)
        self.assertEqual(len(self.store.list(self.alice)), 2)

    def test_raw_actor_strings_and_malformed_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.list(self.alice.user_id)
        for identity in ('other', '../file', "' OR 1=1", True):
            with self.assertRaises(ValueError):
                self.store.get(self.alice, identity)

    def test_unbounded_pagination_and_invalid_names_are_rejected(self):
        for values in ({'limit': True}, {'limit': 101}, {'offset': -1}, {'offset': 100001}):
            with self.assertRaises(ValueError):
                self.store.list(self.alice, **values)
        for name in ('', ' ', 'x' * 101, 'New\nProject'):
            with self.assertRaises(ValueError):
                self.store.create(self.alice, name)
