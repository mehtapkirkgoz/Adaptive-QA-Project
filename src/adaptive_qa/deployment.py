"""Validated deployment plans; never activate hosting or relax execution guards."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import re
from urllib.parse import urlsplit


class Environment(StrEnum):
    LOCAL = 'local'
    STAGING = 'staging'
    PRODUCTION = 'production'


@dataclass(frozen=True)
class DeploymentPlan:
    environment: Environment
    data_root: Path
    public_origin: str

    def __post_init__(self):
        if not isinstance(self.environment, Environment):
            raise ValueError('A typed deployment environment is required.')
        if (not isinstance(self.data_root, Path) or not self.data_root.is_absolute()
                or '..' in self.data_root.parts or self.data_root.parent == self.data_root
                or str(self.data_root).startswith(('\\\\', '//'))):
            raise ValueError('Use an absolute local data root below the filesystem root, without traversal.')
        try:
            root = self.data_root.resolve()
            directory = root / self.environment.value
            redirected = directory.resolve() != directory
        except (OSError, RuntimeError):
            raise ValueError('Deployment paths could not be resolved safely.') from None
        if redirected:
            raise ValueError('Environment data must not redirect through a symlink.')
        origin = self.public_origin
        if (not isinstance(origin, str) or len(origin) > 512 or not origin
                or any(character.isspace() or ord(character) < 32 for character in origin)
                or any(character in origin for character in ('?', '#', '\\'))):
            raise ValueError('An explicit HTTP(S) origin without query, fragment or whitespace is required.')
        try:
            parsed = urlsplit(origin)
            host = (parsed.hostname or '').encode('idna').decode('ascii').lower()
            port = parsed.port
        except (ValueError, UnicodeError):
            raise ValueError('Invalid deployment origin.') from None
        if parsed.username is not None or parsed.password is not None or parsed.path not in ('', '/'):
            raise ValueError('Deployment origins must not contain credentials or application paths.')
        if self.environment == Environment.LOCAL:
            if parsed.scheme != 'http' or host != '127.0.0.1' or port is None or not 1024 <= port <= 65535:
                raise ValueError('Local plans require http://127.0.0.1 with an explicit unprivileged port.')
            canonical = f'http://127.0.0.1:{port}'
        else:
            labels = host.split('.')
            if (parsed.scheme != 'https' or port not in (None, 443) or len(host) > 253
                    or len(labels) < 2 or all(label.isdigit() for label in labels)
                    or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in labels)
                    or host.endswith(('.localhost', '.local'))):
                raise ValueError('Staging/production plans require a DNS hostname with HTTPS on port 443.')
            canonical = f'https://{host}'
        object.__setattr__(self, 'data_root', root)
        object.__setattr__(self, 'public_origin', canonical)

    @property
    def directory(self):
        return self.data_root / self.environment.value

    def describe(self):
        return {'schema_version': 1, 'environment': self.environment.value,
            'public_origin': self.public_origin,
            'auth_database': str(self.directory / 'auth.sqlite'),
            'projects_database': str(self.directory / 'projects.sqlite'),
            'backup_directory': str(self.directory / 'backups'),
            'secure_cookies_required': self.environment != Environment.LOCAL,
            'backend_bind': '127.0.0.1:8765', 'activation_enabled': False,
            'limitations': ['Planning only; no files, services, DNS records or network requests are created.',
                'The current dashboard server remains loopback-only; HTTPS activation is not implemented here.',
                'Worker target guards and explicit test admission remain unchanged.']}
