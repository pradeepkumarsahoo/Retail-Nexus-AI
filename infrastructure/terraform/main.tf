# Author: Pradeep Sahoo — Retail Nexus AI
# REFERENCE ONLY — not applied to any environment.
# A minimal shape for the AWS topology described in infrastructure/aws/README.md.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = ">= 5.0" }
  }
  required_version = ">= 1.6.0"
}

provider "aws" {
  region = var.region
}

variable "region"       { default = "us-east-1" }
variable "project"      { default = "control-tower" }
variable "db_password"  { sensitive = true }

resource "aws_s3_bucket" "artifacts" {
  bucket = "${var.project}-artifacts"
}

resource "aws_sns_topic" "stockout_detected"     { name = "ct-stockout-detected" }
resource "aws_sns_topic" "supplier_detected"     { name = "ct-supplier-detected" }
resource "aws_sns_topic" "recommendation_events" { name = "ct-recommendation-events" }

resource "aws_sqs_queue" "agents_work"  { name = "ct-agents-work" }
resource "aws_sqs_queue" "notifications" { name = "ct-notifications" }
resource "aws_sqs_queue" "audit"        { name = "ct-audit" }

resource "aws_sns_topic_subscription" "stockout_to_agents" {
  topic_arn = aws_sns_topic.stockout_detected.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.agents_work.arn
}

resource "aws_db_instance" "ct" {
  identifier               = "${var.project}-db"
  engine                   = "postgres"
  engine_version           = "16"
  instance_class           = "db.t4g.small"
  allocated_storage        = 20
  username                 = "ctadmin"
  password                 = var.db_password
  skip_final_snapshot      = true
  publicly_accessible      = false
  backup_retention_period  = 7
}

output "artifacts_bucket" { value = aws_s3_bucket.artifacts.bucket }
output "db_endpoint"      { value = aws_db_instance.ct.endpoint }
