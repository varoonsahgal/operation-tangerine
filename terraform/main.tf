###############################################################################
# Operation Tangerine - shared locals + networking
#
# Architecture (all in one region):
#
#   Lambda "zest-agent" --(RDS Data API)--> Aurora PostgreSQL Serverless v2 (pgvector)
#          |   |                                   ^
#          |   +--(DynamoDB API)--> agent-memory   |  (Data API, bedrock_user secret)
#          |                                       |
#          +--(bedrock:Retrieve)--> Bedrock Knowledge Base <-- S3 docs bucket
#          +--(bedrock-mantle)----> Claude in Amazon Bedrock
#
# The Lambda is NOT in the VPC: it reaches Aurora through the Data API (HTTPS),
# so no NAT gateway or VPC endpoints are needed. That keeps the lab cheap.
###############################################################################

data "aws_caller_identity" "me" {}
data "aws_partition" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

resource "random_id" "suffix" {
  byte_length = 3
}

locals {
  name       = "${var.prefix}-${var.student_id}"
  suffix     = random_id.suffix.hex
  account_id = data.aws_caller_identity.me.account_id
  partition  = data.aws_partition.current.partition

  embedding_model_arn = "arn:${local.partition}:bedrock:${var.region}::foundation-model/${var.embedding_model_id}"
  kb_arn_pattern      = "arn:${local.partition}:bedrock:${var.region}:${local.account_id}:knowledge-base/*"

  lambda_name = "${local.name}-zest-agent"
  azs         = slice(data.aws_availability_zones.available.names, 0, 2)
}

# ---------------- VPC (private only - Aurora lives here) ----------------

resource "aws_vpc" "lab" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${local.name}-vpc" }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.lab.id
  cidr_block        = cidrsubnet(aws_vpc.lab.cidr_block, 8, count.index + 10)
  availability_zone = local.azs[count.index]

  tags = { Name = "${local.name}-private-${local.azs[count.index]}" }
}

resource "aws_security_group" "aurora" {
  name        = "${local.name}-aurora-sg"
  description = "Aurora PostgreSQL - only reachable from inside the lab VPC"
  vpc_id      = aws_vpc.lab.id

  ingress {
    description = "PostgreSQL from inside the VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.lab.cidr_block]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-aurora-sg" }
}

resource "aws_db_subnet_group" "aurora" {
  name       = "${local.name}-aurora-subnets"
  subnet_ids = aws_subnet.private[*].id
}
