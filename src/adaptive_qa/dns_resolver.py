"""Resolve destinations in a deadline-bound subprocess."""

import argparse
import json
import subprocess
import sys

from adaptive_qa.targets import resolve_addresses


def resolve_with_deadline(hostname: str, port: int) -> tuple[str, ...]:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "adaptive_qa.dns_resolver", hostname, str(port)],
            capture_output=True, text=True, timeout=5, check=False,
            **({"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}),
        )
        if completed.returncode != 0:
            raise ValueError("Destination DNS resolution failed.")
        addresses = json.loads(completed.stdout)
        if not isinstance(addresses, list) or not addresses or any(
            not isinstance(address, str) for address in addresses
        ):
            raise ValueError("Invalid DNS result.")
        return tuple(addresses)
    except (OSError, subprocess.TimeoutExpired, ValueError) as error:
        raise ValueError("Destination DNS resolution failed or exceeded its deadline.") from error


def main() -> None:
    parser = argparse.ArgumentParser(description="Internal DNS resolver process.")
    parser.add_argument("hostname")
    parser.add_argument("port", type=int)
    args = parser.parse_args()
    print(json.dumps(resolve_addresses(args.hostname, args.port)))


if __name__ == "__main__":
    main()
