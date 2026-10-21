"""Development entry point for platform status."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive QA platform")
    parser.add_argument(
        "--status", action="store_true", help="Show the implementation status"
    )
    args = parser.parse_args()
    if args.status:
        from adaptive_qa.catalog import TEST_CASES
        from adaptive_qa.api_catalog import API_CASES
        print(f"Local prototype: {len(TEST_CASES)} UI + {len(API_CASES)} API scenarios, bounded discovery, and scoped planning available; "
              "general website execution is not enabled.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
