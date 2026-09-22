#!/usr/bin/env python3
"""
Generates one named AWS CLI profile per enrolled spoke account in
~/.aws/config, each using `credential_process` to assume that
account's DiskMonitoring-CrossAccountRole on demand.

Run before every Ansible execution (playbooks/site.yml does this as
its first play) so a newly added account in accounts.yml is picked up
automatically -- this is what makes onboarding a new account a
config-only change, with no control-node redeploy.
"""
import configparser
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_FILE = os.path.join(HERE, "..", "accounts.yml")
AWS_CONFIG_PATH = os.path.expanduser("~/.aws/config")
CRED_HELPER = os.path.join(HERE, "assume_role_creds.py")


def main() -> int:
    with open(ACCOUNTS_FILE) as f:
        data = yaml.safe_load(f)

    config = configparser.ConfigParser()
    if os.path.exists(AWS_CONFIG_PATH):
        config.read(AWS_CONFIG_PATH)

    for acct in data["accounts"]:
        section = f"profile {acct['alias']}"
        cmd = (
            f"python3 {CRED_HELPER} "
            f"--role-arn {acct['role_arn']} "
            f"--external-id {acct['external_id']} "
            f"--session-name diskmon-{acct['alias']}"
        )
        config[section] = {"credential_process": cmd}

    os.makedirs(os.path.dirname(AWS_CONFIG_PATH), exist_ok=True)
    with open(AWS_CONFIG_PATH, "w") as f:
        config.write(f)

    print(f"Wrote {len(data['accounts'])} profile(s) to {AWS_CONFIG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
