#!/usr/bin/env python3
"""
Pushes a single CloudWatch PutMetricData point. Invoked by
roles/disk_monitoring/tasks/push_metrics.yml, delegated to localhost
(the Ansible control node), using the named AWS CLI profile for the
target VM's own account -- so the metric is written into that
account's CloudWatch, not the monitoring account's.
"""
import argparse
import json
import sys

import boto3


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--profile", required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--namespace", required=True)
    p.add_argument("--metric-name", required=True)
    p.add_argument("--value", type=float, required=True)
    p.add_argument("--unit", default="None")
    p.add_argument("--dimensions", required=True,
                    help="JSON object of dimension name/value pairs")
    args = p.parse_args()

    dims = json.loads(args.dimensions)
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    cw = session.client("cloudwatch")
    cw.put_metric_data(
        Namespace=args.namespace,
        MetricData=[{
            "MetricName": args.metric_name,
            "Value": args.value,
            "Unit": args.unit,
            "Dimensions": [{"Name": k, "Value": str(v)} for k, v in dims.items()],
        }],
    )
    print(f"OK: {args.namespace}/{args.metric_name}={args.value} ({args.unit}) "
          f"profile={args.profile} dims={dims}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
