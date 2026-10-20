"""Development entry point for platform status."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive QA platform")
    parser.add_argument(
        "--status", action="store_true", help="Show the implementation status"
    )
    args = parser.parse_args()
    if args.status:
        print("Local prototype: 10 smoke scenarios, bounded discovery, and scoped test planning available; "
              "general website execution is not enabled.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
