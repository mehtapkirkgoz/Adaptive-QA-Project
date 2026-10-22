"""Versioned additive migrations applied only to inactive recovery copies."""


SCHEMA_REVISION = 1

AUTH_COLUMNS = {
    'dashboard_users': {'user_id', 'email', 'salt', 'password_hash'},
    'dashboard_sessions': {'sequence', 'token_hash', 'csrf_hash', 'user_id', 'expires_at'},
    'dashboard_login_admission': {'identity_hash', 'attempts', 'window_start'},
}
PROJECT_COLUMNS = {
    'dashboard_projects': {'sequence', 'project_id', 'owner_id', 'name'},
    'dashboard_project_settings': {'project_id', 'settings_json'},
    'dashboard_discovery_jobs': {'sequence', 'job_id', 'project_id', 'owner_id', 'status',
                                 'configuration_json', 'claim_token'},
    'dashboard_test_runs': {'sequence', 'run_id', 'project_id', 'owner_id', 'discovery_job_id',
                            'case_ids_json', 'configuration_json', 'status'},
    'dashboard_run_evidence': {'evidence_id', 'run_id', 'case_id', 'png'},
}
ADDITIONS = {
    'dashboard_discovery_jobs': (('report_json', 'TEXT'),),
    'dashboard_test_runs': (('claim_token', 'TEXT'), ('results_json', "TEXT NOT NULL DEFAULT '[]'"),
                            ('rerun_of', 'TEXT'), ('contracts_json', 'TEXT'), ('execution_context', 'TEXT')),
    'dashboard_run_evidence': (('expires_at', 'REAL'),),
}


def validate_runtime_schema(connection, database_name):
    """Read-only gate before store initialization or operations; never migrates."""
    if database_name not in ('auth.sqlite', 'projects.sqlite'):
        raise ValueError('A known dashboard database kind is required.')
    revision = connection.execute('PRAGMA user_version').fetchone()[0]
    if revision not in (0, SCHEMA_REVISION):
        raise ValueError('Database schema revision is unsupported; runtime access refused.')
    if revision == 0:
        return  # Retain the existing unversioned local initialization contract.
    required = AUTH_COLUMNS if database_name == 'auth.sqlite' else PROJECT_COLUMNS
    for table, columns in required.items():
        definition = connection.execute('SELECT type FROM sqlite_master WHERE name=?', (table,)).fetchone()
        actual = {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}
        expected = columns | {name for name, _ in ADDITIONS.get(table, ())}
        if definition is None or definition[0] != 'table' or not expected <= actual:
            raise ValueError('Versioned database schema is incomplete; runtime access refused.')


def migrate_recovery_connection(connection, database_name):
    """Caller owns a disposable offline copy and a bounded SQLite progress handler."""
    if database_name not in ('auth.sqlite', 'projects.sqlite'):
        raise ValueError('Only the fixed dashboard database pair can be migrated.')
    revision = connection.execute('PRAGMA user_version').fetchone()[0]
    if revision not in (0, SCHEMA_REVISION):
        raise ValueError('Database schema revision is unsupported; no downgrade is allowed.')
    required = AUTH_COLUMNS if database_name == 'auth.sqlite' else PROJECT_COLUMNS
    existing = {}
    for table, columns in required.items():
        # Identifiers below come exclusively from fixed application constants.
        existing[table] = {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}
        if not columns <= existing[table]:
            raise ValueError('Database core columns do not match the supported schema.')
    additions = []
    if database_name == 'projects.sqlite':
        for table, definitions in ADDITIONS.items():
            for column, declaration in definitions:
                if column not in existing[table]:
                    if revision == SCHEMA_REVISION:
                        raise ValueError('Versioned database is missing required schema columns.')
                    additions.append((table, column, declaration))
    # No destructive migration or guessed downgrade. Publication happens only
    # after the enclosing recovery operation verifies both copied databases.
    for table, column, declaration in additions:
        connection.execute(f'ALTER TABLE {table} ADD COLUMN {column} {declaration}')
    if database_name == 'projects.sqlite':
        connection.execute('CREATE INDEX IF NOT EXISTS dashboard_evidence_expiry '
                           'ON dashboard_run_evidence(coalesce(expires_at, 0), evidence_id)')
    connection.execute(f'PRAGMA user_version={SCHEMA_REVISION}')
    return {'from_revision': revision, 'to_revision': SCHEMA_REVISION,
            'added_columns': [f'{table}.{column}' for table, column, _ in additions]}
