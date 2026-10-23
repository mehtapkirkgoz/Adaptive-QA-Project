"""Local signed-license persistence; never caches an entitlement decision."""

from contextlib import closing, contextmanager
from pathlib import Path
import re
import sqlite3
import time

from adaptive_qa.licensing import LicenseError, verify_license


class LicenseStore:
    """Caller-owned trust anchors are separate from imported customer documents."""

    def __init__(self, database, trusted_keys, *, clock=time.time):
        if (not isinstance(trusted_keys, dict) or not 1 <= len(trusted_keys) <= 10
                or any(not isinstance(key, str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}', key)
                       or not isinstance(value, bytes) or len(value) != 32
                       for key, value in trusted_keys.items())):
            raise LicenseError('Invalid trusted license keys.')
        self._keys = dict(trusted_keys)
        self.clock = clock
        self.database = Path(database).resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS local_license ('
                'slot INTEGER PRIMARY KEY CHECK (slot=1), '
                "document BLOB NOT NULL CHECK (typeof(document)='blob' AND length(document) BETWEEN 1 AND 8192))")

    @contextmanager
    def _connection(self):
        with closing(sqlite3.connect(self.database, timeout=5)) as connection:
            with connection:
                yield connection

    def install(self, document):
        """Invalid imports cannot replace a previously valid stored document."""
        with self._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            claims = verify_license(document, self._keys, now=self.clock())
            connection.execute('INSERT INTO local_license(slot, document) VALUES(1, ?) '
                'ON CONFLICT(slot) DO UPDATE SET document=excluded.document', (document,))
        return claims

    def current(self):
        """None means absent; invalid/expired stored licenses fail closed without deletion."""
        with self._connection() as connection:
            row = connection.execute("SELECT CASE WHEN typeof(document)='blob' "
                'AND length(document) BETWEEN 1 AND 8192 THEN document ELSE NULL END '
                'FROM local_license WHERE slot=1').fetchone()
        if row is None:
            return None
        return verify_license(row[0], self._keys, now=self.clock())
