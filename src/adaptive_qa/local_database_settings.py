"""Count-only saved metadata: no SQL, resolved paths or database input values."""
from dataclasses import asdict, dataclass
import re
from adaptive_qa.config import ProjectConfig


@dataclass(frozen=True)
class DatabaseCountBinding:
    table: str
    expected_count: int

    def __post_init__(self):
        if (not isinstance(self.table,str) or not re.fullmatch('[a-z][a-z0-9_]{0,63}',self.table)
                or self.table.startswith('sqlite_') or type(self.expected_count) is not int
                or not 0<=self.expected_count<=2147483647):
            raise ValueError('An explicit application table and bounded record count are required.')


def validate_saved_database_binding(data,project):
    if not isinstance(data,dict) or set(data)!={'table','expected_count'}:
        raise ValueError('Exact count-only database binding fields are required.')
    if (not isinstance(project,ProjectConfig) or project.base_url.rstrip('/')!='http://127.0.0.1:8000'
            or project.allowed_hosts!=('127.0.0.1',)):
        raise ValueError('Only the controlled local fixture project is supported.')
    return asdict(DatabaseCountBinding(**data))
