"""Publisher-only offline issuance; never bundled as a customer runtime command."""
import argparse
import base64
from dataclasses import asdict
import json
import os
from pathlib import Path
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from adaptive_qa.licensing import LicenseClaims, license_message

REPOSITORY = Path(__file__).resolve().parents[1]


def external_path(value):
    path = Path(value).absolute()
    if (path.resolve() != path or path.is_relative_to(REPOSITORY)
            or str(path).startswith(('\\\\','//'))):
        raise ValueError('Issuer files must use unredirected local paths outside the repository.')
    return path


def write_new(path, content, mode):
    # Exclusive creation never overwrites an issuer key or an issued license.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(content)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Publisher-only offline local license issuance')
    commands = parser.add_subparsers(dest='command',required=True)
    generate = commands.add_parser('generate-key')
    issue = commands.add_parser('issue')
    for command in (generate,issue):
        command.add_argument('--private-key',required=True,type=external_path)
        command.add_argument('--key-id',required=True)
    generate.add_argument('--public-keys',required=True,type=external_path)
    issue.add_argument('--output',required=True,type=external_path)
    issue.add_argument('--customer-id',required=True)
    issue.add_argument('--license-id',required=True)
    issue.add_argument('--expires-at',required=True,type=int,help='Exclusive Unix expiry timestamp')
    issue.add_argument('--max-projects',type=int,help='Omit for unlimited local projects')
    issue.add_argument('--max-concurrent-runs',type=int,default=1)
    args = parser.parse_args(argv)
    license_message(args.key_id,{})  # Validate issuer key ID before creating files.
    if args.command == 'generate-key':
        if args.private_key == args.public_keys or args.private_key.exists() or args.public_keys.exists():
            raise ValueError('Choose distinct new issuer key files.')
        private = Ed25519PrivateKey.generate()
        public = json.dumps({args.key_id:private.public_key().public_bytes_raw().hex()},indent=2).encode()+b'\n'
        write_new(args.private_key,private.private_bytes_raw(),0o600)
        write_new(args.public_keys,public,0o644)
        print('Issuer key files created outside the repository. Distribute only the public-key file.')
        return
    if args.private_key.stat().st_nlink != 1:
        raise ValueError('Issuer private key must be a regular non-shared file.')
    with args.private_key.open('rb') as stream: raw = stream.read(33)
    if len(raw)!=32: raise ValueError('Issuer private key must contain exactly 32 raw bytes.')
    now = int(time.time())
    claims = LicenseClaims(args.license_id,args.customer_id,now,now,args.expires_at,
        args.max_projects,args.max_concurrent_runs)
    payload = asdict(claims)
    signature = Ed25519PrivateKey.from_private_bytes(raw).sign(license_message(args.key_id,payload))
    document = json.dumps(dict(key_id=args.key_id,payload=payload,
        signature=base64.urlsafe_b64encode(signature).rstrip(b'=').decode()),sort_keys=True).encode()+b'\n'
    write_new(args.output,document,0o600)
    print('Signed customer license created. No target data or network service was used.')


if __name__ == '__main__':
    try: main()
    except (ValueError,OSError) as error:
        raise SystemExit('Offline issuance failed; check paths, claims and private-key storage.') from None
