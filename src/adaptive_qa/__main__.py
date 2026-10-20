"""Development entry point for platform status."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive QA platform")
    parser.add_argument(
        "--status", action="store_true", help="Show the implementation status"
    )
    args = parser.parse_args()
    if args.status:
        print("Sprint 1: 10 local smoke scenarios available; general website execution is not enabled.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
