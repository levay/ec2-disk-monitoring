#!/usr/bin/env python3
"""
credential_process helper for ~/.aws/config.

AWS CLI/SDKs invoke this automatically and cache the result until
shortly before `Expiration`, so temporary cross-account credentials are
refreshed with no custom scheduling logic. Spec:
https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sourcing-external.html
"""
import argparse
import json
import sys

import boto3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--external-id", required=True)
    parser.add_argument("--session-name", default="disk-monitoring")
    parser.add_argument("--duration-seconds", type=int, default=3600)
    args = parser.parse_args()

    # Uses whatever credentials this process already has: the ECS
    # Fargate task role of the monitoring-account control node. No
    # long-lived keys anywhere in this chain.
    sts = boto3.client("sts")
    resp = sts.assume_role(
        RoleArn=args.role_arn,
        RoleSessionName=args.session_name,
        ExternalId=args.external_id,
        DurationSeconds=args.duration_seconds,
    )
    creds = resp["Credentials"]
    out = {
        "Version": 1,
        "AccessKeyId": creds["AccessKeyId"],
        "SecretAccessKey": creds["SecretAccessKey"],
        "SessionToken": creds["SessionToken"],
        "Expiration": creds["Expiration"].strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
