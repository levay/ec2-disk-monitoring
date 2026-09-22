# Illustrative only — shows how the pieces connect; treat as a sketch
# for your platform team to review, not reviewed/tested IaC.
#
# An EventBridge Scheduler rule invokes RunTask on a small ECS Fargate
# task on a fixed cadence. The task's container image bundles Ansible,
# the collections in requirements.yml, session-manager-plugin, and this
# repository.

resource "aws_ecs_task_definition" "disk_monitoring" {
  family                   = "diskmon-runner"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.diskmon_execution.arn
  task_role_arn             = aws_iam_role.diskmon_execution.arn

  container_definitions = jsonencode([
    {
      name  = "diskmon-runner"
      image = "999999999999.dkr.ecr.ap-south-1.amazonaws.com/diskmon-runner:latest"
      command = [
        "ansible-playbook", "playbooks/site.yml"
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/diskmon/runner"
          "awslogs-region"        = "ap-south-1"
          "awslogs-stream-prefix" = "diskmon"
        }
      }
    }
  ])
}

resource "aws_iam_role" "diskmon_execution" {
  name               = "DiskMonitoring-ExecutionRole"
  assume_role_policy = file("../iam/monitoring-account-execution-role-trust-policy.json")
}

resource "aws_iam_role_policy" "diskmon_execution_perms" {
  name   = "diskmon-execution-permissions"
  role   = aws_iam_role.diskmon_execution.id
  policy = file("../iam/monitoring-account-execution-role-permissions-policy.json")
}

resource "aws_scheduler_schedule" "diskmon_every_15_min" {
  name                         = "diskmon-runner-every-15-min"
  schedule_expression          = "rate(15 minutes)"
  schedule_expression_timezone = "Asia/Kolkata"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ecs:runTask"
    role_arn = aws_iam_role.diskmon_execution.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.disk_monitoring.arn
      launch_type          = "FARGATE"
      network_configuration {
        subnets          = ["subnet-example1", "subnet-example2"]
        security_groups  = ["sg-example"]
        assign_public_ip = false
      }
    }
  }
}
