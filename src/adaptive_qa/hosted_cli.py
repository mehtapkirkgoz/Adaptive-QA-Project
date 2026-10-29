"""Operator-provisioned server accounts and one bounded authenticated web process."""
import getpass
import json
import os
from pathlib import Path
import sys


def configure_parser(commands):
    parser=commands.add_parser('hosted',help='Manage the separate authenticated server edition')
    sub=parser.add_subparsers(dest='hosted_command',required=True)
    for name in ('create-user','serve'):
        command=sub.add_parser(name)
        command.add_argument('--workspace',type=Path,default=Path('/data'))
        if name=='create-user':command.add_argument('--email',required=True)
        else:
            command.add_argument('--public-origin',required=True)
            command.add_argument('--ui-directory',type=Path,default=Path('/app/dashboard'))


def run(args):
    from adaptive_qa.hosted import HostedSessions,create_hosted_app,HostedOrigin,hosted_workspace
    root=hosted_workspace(args.workspace)
    if args.hosted_command=='create-user':
        if not sys.stdin.isatty():raise ValueError('Use an interactive private terminal for account provisioning.')
        password=getpass.getpass('New account password: ')
        if password!=getpass.getpass('Confirm password: '):raise ValueError('Passwords do not match.')
        HostedSessions(root/'auth.sqlite').create_user(args.email,password)
        print(json.dumps({'account_created':True}));return
    HostedOrigin(args.public_origin)
    if sys.platform!='linux' or os.geteuid()==0:
        raise ValueError('Server execution requires non-root Linux and a working Chromium sandbox.')
    os.environ['ADAPTIVE_QA_HOSTED_SANDBOX']='1'
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(chromium_sandbox=True,timeout=10000)
        browser.close()
    # Fail before binding if the operator has not provisioned an account.
    if not (root/'auth.sqlite').is_file():raise ValueError('Create the first server account before serving.')
    store=HostedSessions(root/'auth.sqlite')
    with store._connection() as c:
        if not c.execute('SELECT 1 FROM dashboard_users LIMIT 1').fetchone():raise ValueError('No server account exists.')
    import uvicorn
    uvicorn.run(create_hosted_app(root,args.public_origin,ui_directory=args.ui_directory),
        host='0.0.0.0',port=8080,workers=1,proxy_headers=False,access_log=False,
        log_level='warning',limit_concurrency=20,backlog=64,timeout_keep_alive=5)
