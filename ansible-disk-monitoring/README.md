# AWS Multi-Account Disk Monitoring — Ansible Solution

Detects low disk space early, across every AWS account in the organization,
using Ansible as the automation core and exactly two AWS-native services
where they provide a substantial benefit Ansible can't reasonably replicate:

- **AWS Systems Manager (SSM)** for VM access — no SSH keys, no bastion
  hosts, no inbound ports to manage across dozens of accounts.
- **Amazon CloudWatch + Cross-Account Observability (OAM)** for
  centralized visualization/alerting — a single pane of glass without
  building and operating a bespoke time-series store.

Everything else (discovery, collection, orchestration, scaling) is plain
Ansible.

## How a run works (see `playbooks/site.yml`)

1. `automation/generate_aws_profiles.py` reads `accounts.yml` and writes
   one AWS CLI profile per spoke account into `~/.aws/config`, each using
   `credential_process` to assume that account's
   `DiskMonitoring-CrossAccountRole` on demand (temporary creds only,
   auto-refreshed, never written to disk).
2. `inventory/generate_inventory.py` reads the same `accounts.yml` and
   writes one `amazon.aws.aws_ec2` dynamic-inventory file per
   account/region, filtered to `tag:Monitoring=enabled`.
3. Ansible connects to every discovered instance over
   `community.aws.aws_ssm` (the SSM connection plugin) — no SSH.
4. `roles/disk_monitoring` gathers mount facts and pushes
   `DiskPercentFree` / `DiskFreeGB` metrics to CloudWatch **in the same
   account the VM lives in**, using that account's temporary
   credentials.
5. CloudWatch Observability Access Manager links every spoke account's
   metrics into the central monitoring account's dashboard/alarms — no
   metric copying, no extra pipeline.
6. Amazon EventBridge Scheduler triggers the whole playbook on a fixed
   cadence (e.g. every 15 min) from an ECS Fargate task
   (`automation/ecs_task_and_schedule.tf`).

## Onboarding a new account or acquisition (the scaling story)

1. Deploy `iam/spoke-account-cross-account-role-*` in the new account
   (one IAM role, one trust policy, one external ID).
2. Add one entry to `accounts.yml`.
3. Nothing else changes — no new playbook, no new inventory file to
   hand-write, no control-node redeploy. The next scheduled run
   discovers it automatically.

Adding VMs inside an already-enrolled account is even simpler: tag the
instance `Monitoring=enabled` (and attach the standard
`AmazonSSMManagedInstanceCore` instance profile, if your golden AMI
doesn't already). It appears in the next dynamic-inventory refresh.

## Prerequisites

- Every monitored EC2 instance has the SSM Agent running (default on
  Amazon Linux 2/2023, Ubuntu, Windows Server AMIs since ~2017) and an
  instance profile that includes `AmazonSSMManagedInstanceCore`.
- `session-manager-plugin` installed on the Ansible control node
  (baked into the ECS Fargate container image).
- Collections in `requirements.yml` installed:
  `ansible-galaxy collection install -r requirements.yml`.

## Repository layout

```
accounts.yml                 Single source of truth: enrolled accounts
ansible.cfg                  Dynamic-inventory + connection defaults
requirements.yml             Required Ansible collections
group_vars/all.yml           SSM connection vars, alert thresholds
inventory/generate_inventory.py   Renders one aws_ec2 file per account/region
automation/
  assume_role_creds.py       credential_process helper (STS AssumeRole)
  generate_aws_profiles.py   Renders ~/.aws/config from accounts.yml
  ecs_task_and_schedule.tf   Illustrative Fargate task + EventBridge Scheduler
  cloudwatch_oam_link.tf     Illustrative cross-account observability link
playbooks/site.yml           Entry point run on every schedule tick
roles/disk_monitoring/       Collect facts -> push CloudWatch metrics
files/push_cloudwatch_metrics.py   boto3 PutMetricData helper (control node)
iam/                         Trust + permission policies, both sides
dashboards/cloudwatch_dashboard.json   Example central dashboard
```

## Security notes

- No long-lived AWS keys anywhere: the ECS task's own IAM role is the
  root of trust; everything downstream is a short-lived
  `sts:AssumeRole`, refreshed automatically by `credential_process`.
- No inbound network exposure on any VM: SSM Session Manager is
  outbound-only from the instance's perspective.
- Cross-account trust is scoped with a per-account external ID and the
  spoke role's permissions are tag-scoped (`ssm:resourceTag/Monitoring
  = enabled`) and namespace-scoped
  (`cloudwatch:namespace = DiskMonitoring`), so a compromised
  monitoring pipeline can't pivot to unrelated resources.
- All session activity is logged by AWS Systems Manager / CloudTrail
  in the account where it happens — no separate audit trail to build.

## Illustrative, not turnkey

This is a minimal-working reference implementation to demonstrate the
approach end-to-end, sized for a design review — not a hardened,
tested production module set. Treat account IDs, ARNs, and bucket
names as placeholders, and treat the Terraform files as illustrative
of the trigger wiring rather than a reviewed IaC module.
