"""Development entry point; test execution is introduced in Sprint 1."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive QA platform")
    parser.add_argument(
        "--status", action="store_true", help="Show the implementation status"
    )
    args = parser.parse_args()
    if args.status:
        print("Sprint 0: project scaffold ready; test execution is not implemented.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
