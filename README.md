# Multi-Account EC2 Disk Monitoring

Automated disk-space monitoring for Amazon EC2 instances across multiple AWS accounts and Regions.

The solution uses **Ansible**, **AWS Systems Manager (SSM)**, and **Amazon CloudWatch** to discover enrolled EC2 instances, collect filesystem usage, and publish disk metrics centrally—without SSH access, bastion hosts, or long-lived AWS credentials.

---

## Overview

This project enables a central operations team to monitor disk capacity across AWS accounts while keeping access secure and scalable.

During each scheduled run, the automation:

1. Reads the AWS accounts and Regions configured in `accounts.yml`
2. Assumes a short-lived IAM role in each target account
3. Finds running EC2 instances tagged with `Monitoring=enabled`
4. Connects through AWS Systems Manager Session Manager
5. Collects filesystem usage, such as `/`, `/var`, and `/data`
6. Calculates available disk space in GB and percentage
7. Publishes metrics to Amazon CloudWatch
8. Displays cross-account health in a central CloudWatch dashboard

---

## Architecture

```text
┌─────────────────────────────┐
│ ECS/Fargate Scheduled Task  │
│     Runs Ansible Job        │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       accounts.yml          │
│ Accounts, Roles, Regions    │
└──────────────┬──────────────┘
               │ AssumeRole
               ▼
┌─────────────────────────────────────────┐
│           Target AWS Account             │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ EC2 instances                      │ │
│  │ Tag: Monitoring=enabled            │ │
│  └────────────────────────────────────┘ │
│                    │                     │
│                    ▼                     │
│          AWS Systems Manager             │
│                    │                     │
│                    ▼                     │
│          Ansible disk-monitoring role   │
│                    │                     │
│                    ▼                     │
│           Amazon CloudWatch Metrics      │
└─────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────┐
│ Central CloudWatch Dashboard │
│ Cross-Account Observability  │
└─────────────────────────────┘
```

---

## Key Features

- Monitors disk usage across multiple AWS accounts and Regions
- Uses EC2 tags for automatic monitoring enrollment
- Uses AWS Systems Manager instead of SSH
- Avoids SSH keys, bastion hosts, and permanent AWS access keys
- Uses short-lived IAM credentials through role assumption
- Publishes free disk space in GB and percentage to CloudWatch
- Supports centralized CloudWatch dashboards and alarms
- Scales by configuration rather than playbook changes

---

## Repository Structure

```text
.
├── accounts.yml                  # AWS account, role, external ID, and Region configuration
├── inventory/
│   └── aws_ec2.yml               # Dynamic EC2 inventory configuration
├── playbooks/
│   └── disk-monitoring.yml       # Main Ansible playbook
├── roles/
│   └── disk-monitoring/
│       ├── tasks/
│       │   └── main.yml           # Disk collection and CloudWatch publishing tasks
│       ├── defaults/
│       │   └── main.yml           # Default role variables
│       └── templates/             # Optional metric payload templates
├── requirements.yml              # Required Ansible collections
├── Dockerfile                    # Container image for ECS/Fargate execution
├── task-definition.json          # ECS task definition, if managed in source
└── README.md
```

> Adjust the file names and folders above to match the repository implementation.

---

## Prerequisites

Before running this project, ensure the following are available:

- AWS CLI configured for the central monitoring account
- Ansible Core installed
- Required Ansible collections installed
- AWS Systems Manager Agent installed and running on monitored EC2 instances
- EC2 instances configured with an IAM instance profile that permits SSM connectivity
- A cross-account IAM role deployed in every target AWS account
- CloudWatch permissions for writing custom metrics
- EC2 instances tagged with `Monitoring=enabled`

---

## Required AWS Access

### Central Monitoring Account

The account running Ansible must be allowed to assume the monitoring role in each target AWS account.

Example actions commonly required:

```json
{
  "Effect": "Allow",
  "Action": [
    "sts:AssumeRole"
  ],
  "Resource": "arn:aws:iam::*:role/EC2DiskMonitoringRole"
}
```

### Target AWS Account

Each target account requires a role that the central monitoring account can assume.

Typical permissions include:

```json
{
  "Effect": "Allow",
  "Action": [
    "ec2:DescribeInstances",
    "ec2:DescribeRegions",
    "ssm:DescribeInstanceInformation",
    "ssm:SendCommand",
    "ssm:GetCommandInvocation",
    "cloudwatch:PutMetricData"
  ],
  "Resource": "*"
}
```

Apply least-privilege IAM policies appropriate for your environment.

---

## Instance Enrollment

An EC2 instance is monitored only when it has the following tag:

```text
Monitoring=enabled
```

Example AWS CLI command:

```bash
aws ec2 create-tags \
  --resources i-0123456789abcdef0 \
  --tags Key=Monitoring,Value=enabled
```

This tag-driven approach lets teams onboard and offboard instances without modifying the Ansible playbook.

---

## Configuration

### `accounts.yml`

Use `accounts.yml` to define each AWS account, the role to assume, external ID, and Regions to scan.

```yaml
accounts:
  - name: payments-production
    account_id: "123456789012"
    role_arn: "arn:aws:iam::123456789012:role/EC2DiskMonitoringRole"
    external_id: "replace-with-secure-external-id"
    regions:
      - ap-south-1
      - us-east-1

  - name: analytics-production
    account_id: "210987654321"
    role_arn: "arn:aws:iam::210987654321:role/EC2DiskMonitoringRole"
    external_id: "replace-with-secure-external-id"
    regions:
      - ap-south-1
```

> Do not commit real external IDs, account-specific secrets, or credentials to source control. Use AWS Secrets Manager, Parameter Store, CI/CD secrets, or ECS task secrets where appropriate.

---

## Dynamic Inventory

The project uses Ansible dynamic inventory to discover EC2 instances automatically.

Example inventory configuration:

```yaml
plugin: amazon.aws.aws_ec2
regions:
  - ap-south-1

filters:
  instance-state-name: running
  "tag:Monitoring": enabled

hostnames:
  - instance-id

compose:
  ansible_connection: aws_ssm
```

The inventory should return only running instances with the monitoring tag.

---

## Installation

### 1. Clone the repository

```bash
git clone [https://github.com/](https://github.com/)<your-org>/ec2-disk-monitoring.git
cd ec2-disk-monitoring
```

### 2. Create a Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Ansible dependencies

```bash
pip install ansible boto3 botocore
ansible-galaxy collection install -r requirements.yml
```

### 4. Configure AWS authentication

For local testing, authenticate through AWS IAM Identity Center, environment credentials, or another approved AWS authentication method.

```bash
aws sts get-caller-identity
```

---

## Running the Playbook

Run the disk-monitoring playbook manually:

```bash
ansible-playbook \
  -i inventory/aws_ec2.yml \
  playbooks/disk-monitoring.yml \
  -e @accounts.yml
```

For a specific environment or account:

```bash
ansible-playbook \
  -i inventory/aws_ec2.yml \
  playbooks/disk-monitoring.yml \
  -e target_account=payments-production
```

Use the exact variables implemented by your playbook.

---

## Metrics Published

The automation publishes custom CloudWatch metrics for each monitored filesystem.

| Metric | Description | Example |
|---|---|---:|
| `DiskFreePercent` | Percentage of free disk space | `8` |
| `DiskFreeGB` | Available disk capacity in GB | `16` |
| `DiskUsedPercent` | Percentage of disk capacity used | `92` |
| `DiskUsedGB` | Used disk capacity in GB | `184` |

Recommended CloudWatch dimensions:

| Dimension | Example |
|---|---|
| `InstanceId` | `i-0123456789abcdef0` |
| `InstanceName` | `payment-api-01` |
| `Filesystem` | `/data` |
| `AccountName` | `payments-production` |
| `Region` | `ap-south-1` |

Example CloudWatch namespace:

```text
Organization/EC2/DiskMonitoring
```

---

## Example Scenario

Assume the following EC2 instance is enrolled:

| Item | Example |
|---|---|
| AWS account | Payments-Production |
| EC2 instance | `payment-api-01` |
| Monitoring tag | `Monitoring=enabled` |
| Filesystem | `/data` |
| Disk capacity | 200 GB |
| Available space | 16 GB |
| Free space | 8% |

During the next scheduled run, Ansible discovers the instance, connects through SSM, reads `/data`, and publishes metrics similar to:

```text
DiskFreePercent = 8
DiskFreeGB = 16
```

A CloudWatch alarm can notify the operations team when free disk space drops below a defined threshold, such as 15%.

---

## CloudWatch Alarms

A recommended alarm policy is to alert when available disk space falls below a safe threshold.

Example thresholds:

| Severity | Free Disk Space |
|---|---:|
| Warning | Less than 20% |
| Critical | Less than 15% |
| Urgent | Less than 10% |

Example alarm logic:

```text
ALARM when DiskFreePercent < 15
for 2 consecutive evaluation periods
```

Tune thresholds based on workload type, growth rate, and filesystem purpose.

---

## Deployment with ECS/Fargate

For scheduled execution, package the Ansible project in a container and run it as an Amazon ECS Fargate task.

Typical workflow:

1. Build and push the Docker image to Amazon ECR.
2. Create an ECS task definition with required IAM roles.
3. Store sensitive configuration in AWS Secrets Manager or Parameter Store.
4. Trigger the task using Amazon EventBridge Scheduler.
5. Review task logs in Amazon CloudWatch Logs.

Example build and push commands:

```bash
docker build -t ec2-disk-monitoring .

aws ecr get-login-password --region ap-south-1 \
  | docker login \
    --username AWS \
    --password-stdin <account-id>.dkr.ecr.ap-south-1.amazonaws.com

docker tag ec2-disk-monitoring:latest \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com/ec2-disk-monitoring:latest

docker push \
  <account-id>.dkr.ecr.ap-south-1.amazonaws.com/ec2-disk-monitoring:latest
```

---

## Onboarding a New AWS Account

To onboard an acquired or new AWS account:

1. Deploy the approved cross-account IAM role in the target account.
2. Configure the role trust policy to allow the central monitoring account to assume it.
3. Ensure monitored EC2 instances have SSM Agent and a suitable instance profile.
4. Add the account ID, role ARN, external ID, and Regions to `accounts.yml`.
5. Tag eligible EC2 instances with `Monitoring=enabled`.
6. Confirm that metrics appear in CloudWatch after the next scheduled run.

No change to the main Ansible playbook should be required.

---

## Security Model

This project is designed to avoid common infrastructure-access risks.

- **No SSH keys:** Remote access uses AWS Systems Manager instead of SSH.
- **No bastion hosts:** SSM removes the need for inbound SSH connectivity.
- **No permanent AWS keys:** Cross-account access uses temporary STS credentials.
- **Tag-based scope:** Only explicitly enrolled instances are targeted.
- **Least privilege:** IAM roles should grant only the permissions required for discovery, SSM access, and CloudWatch metric publishing.
- **External IDs:** Use an external ID when assuming roles across accounts to help prevent confused-deputy risks.

---

## Troubleshooting

### Instance is not discovered

Check the following:

- The instance is in the configured AWS account and Region
- The instance state is `running`
- The instance has the tag `Monitoring=enabled`
- The dynamic inventory filter matches the tag format
- The assumed role has `ec2:DescribeInstances` permission

### SSM connection fails

Check the following:

- SSM Agent is installed and running
- The EC2 instance has an IAM instance profile with SSM permissions
- The instance can reach SSM endpoints through internet access, NAT, or VPC endpoints
- The assumed role has the required SSM permissions

### Metrics are missing

Check the following:

- The Ansible task completed successfully
- The CloudWatch namespace and Region are correct
- The role has `cloudwatch:PutMetricData`
- Metric dimensions match the CloudWatch dashboard or alarm configuration
- The filesystem is mounted and accessible on the target instance

---

## Operational Notes

- Schedule the job based on your operational requirements, such as every 15 minutes or hourly.
- Use CloudWatch dashboards for centralized visibility across accounts.
- Use CloudWatch cross-account observability to view metrics from linked AWS accounts in one monitoring account.
- Review IAM policies regularly and remove unused account entries from `accounts.yml`.
- Test role assumption, inventory discovery, and CloudWatch publishing whenever onboarding a new account.

---

## Contributing

1. Create a feature branch.
2. Add or update tests and documentation where applicable.
3. Validate Ansible syntax before opening a pull request.
4. Submit a pull request with a clear description of the change.

Validate playbook syntax:

```bash
ansible-playbook playbooks/disk-monitoring.yml --syntax-check
```

Run Ansible linting if configured:

```bash
ansible-lint
```

---

## License

Add the license applicable to your organization and repository.

```text
Copyright © <year> <organization>.
```
