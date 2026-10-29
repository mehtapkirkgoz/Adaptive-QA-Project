"""Development entry point for platform status."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive QA platform")
    parser.add_argument(
        "--status", action="store_true", help="Show the implementation status"
    )
    from adaptive_qa.dashboard_cli import configure_parser
    commands = parser.add_subparsers(dest='command')
    configure_parser(commands)
    from adaptive_qa.local_cli import configure_parser as configure_local
    configure_local(commands)
    from adaptive_qa.deployment_cli import configure_parser as configure_deployment
    configure_deployment(commands)
    from adaptive_qa.hosted_cli import configure_parser as configure_hosted
    configure_hosted(commands)
    args = parser.parse_args()
    if args.command == 'hosted':
        from adaptive_qa.hosted_cli import run
        try:run(args)
        except ValueError as error:parser.exit(2,f'{error}\n')
    elif args.command == 'dashboard':
        from adaptive_qa.dashboard_cli import run
        try:
            run(args)
        except ValueError as error:
            parser.exit(2, f'{error}\n')
    elif args.command == 'local':
        from adaptive_qa.local_cli import run
        try:
            run(args)
        except ValueError as error:
            parser.exit(2, f'{error}\n')
    elif args.command == 'deployment':
        from adaptive_qa.deployment_cli import run
        try:
            run(args)
        except ValueError as error:
            parser.exit(2, f'{error}\n')
    elif args.status:
        from adaptive_qa.catalog import TEST_CASES
        from adaptive_qa.api_catalog import API_CASES
        from adaptive_qa.database_catalog import DATABASE_CASES
        print(f"Local prototype: {len(TEST_CASES)} UI + {len(API_CASES)} API + {len(DATABASE_CASES)} database scenarios, bounded discovery, and scoped planning available; "
              "general website execution is not enabled.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
