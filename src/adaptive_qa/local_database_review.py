"""Explicit count-only SQLite review on caller-owned controlled fixture roots."""
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from adaptive_qa.local_database_settings import DatabaseCountBinding

from adaptive_qa.database_models import DatabaseCase, DatabaseCheck, DatabaseConfiguration, DatabaseOperator, QueryTemplate
from adaptive_qa.models import TestCase, TestType


def _digest(configuration, table, count, root, identity):
    raw=json.dumps(dict(configuration=asdict(configuration),table=table,expected_count=count,
        fixture_root=str(root),root_identity=identity),sort_keys=True,separators=(',',':'),allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class LocalDatabaseReview:
    configuration: DatabaseConfiguration
    table: str
    expected_count: int
    fixture_root: Path = field(repr=False)
    root_identity: tuple[int, int] = field(repr=False)
    fingerprint: str

    def __post_init__(self):
        if not isinstance(self.configuration,DatabaseConfiguration):
            raise ValueError('A typed database configuration is required.')
        project=self.configuration.project
        if project.base_url.rstrip('/')!='http://127.0.0.1:8000' or project.allowed_hosts!=('127.0.0.1',):
            raise ValueError('Only the controlled local fixture project is supported.')
        DatabaseCountBinding(self.table,self.expected_count)
        if (not isinstance(self.fixture_root,Path) or not self.fixture_root.is_absolute()
                or '..' in self.fixture_root.parts or len(str(self.fixture_root))>512
                or not isinstance(self.root_identity,tuple) or len(self.root_identity)!=2
                or any(type(value) is not int for value in self.root_identity)):
            raise ValueError('A bounded owned fixture root identity is required.')
        if self.fingerprint!=_digest(self.configuration,self.table,self.expected_count,self.fixture_root,self.root_identity):
            raise ValueError('Database review fingerprint does not match the declared scope.')

    @property
    def case(self):
        return DatabaseCase(TestCase('LOCAL-DB-COUNT','Explicit local record count',TestType.DATABASE,
            ('database',),('Count records in the declared owned fixture table',),'Match the explicit expected count'),
            QueryTemplate(self.configuration.project.project_id,'local_record_count',f'SELECT COUNT(*) FROM "{self.table}"'),
            checks=(DatabaseCheck(DatabaseOperator.ROW_COUNT,1),DatabaseCheck(DatabaseOperator.CELL_EQUALS,self.expected_count)))


def review_local_database(configuration, *, table, expected_count, fixture_root):
    """Inspect directory identity only; never resolve the DB reference or open SQLite."""
    if not isinstance(configuration,DatabaseConfiguration):
        raise ValueError('A typed database configuration is required.')
    root=Path(fixture_root).resolve(strict=True)
    if not root.is_dir():raise ValueError('An existing owned fixture directory is required.')
    stat=root.stat();identity=(stat.st_dev,stat.st_ino)
    return LocalDatabaseReview(configuration,table,expected_count,root,identity,
        _digest(configuration,table,expected_count,root,identity))


def run_reviewed_local_database(review,current_configuration, *, confirmed_fingerprint,should_cancel=None):
    """Internal operator dispatch; not a saved-project admission or customer route."""
    if not isinstance(review,LocalDatabaseReview):raise ValueError('A typed local database review is required.')
    review.__post_init__()
    if current_configuration!=review.configuration or confirmed_fingerprint!=review.fingerprint:
        raise ValueError('Current database configuration and explicit confirmation must match review.')
    root=review.fixture_root
    stat=root.stat()
    if root.resolve(strict=True)!=root or not root.is_dir() or (stat.st_dev,stat.st_ino)!=review.root_identity:
        raise ValueError('The reviewed fixture directory identity changed.')
    from adaptive_qa.database_process import run_isolated_database_case
    return run_isolated_database_case(review.case,current_configuration,timeout_seconds=15,
        fixture_root=root,should_cancel=should_cancel)
