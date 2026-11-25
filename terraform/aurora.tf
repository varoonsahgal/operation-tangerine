###############################################################################
# Aurora PostgreSQL Serverless v2 + Data API + Secrets Manager
###############################################################################

data "aws_rds_engine_version" "pg" {
  engine  = "aurora-postgresql"
  version = var.aurora_pg_major
  latest  = true
}

# ---------------- credentials ----------------

resource "random_password" "admin" {
  length  = 32
  special = false
}

# Password for the least-privilege role that Bedrock Knowledge Bases uses.
# The DB role itself is created with SQL in Lab 2.5 (labctl db-setup kb).
resource "random_password" "kb_user" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "admin" {
  name                    = "${local.name}/aurora/admin-${local.suffix}"
  description             = "Aurora admin credentials used by the Zest agent Lambda and labctl"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "admin" {
  secret_id = aws_secretsmanager_secret.admin.id
  secret_string = jsonencode({
    engine              = "postgres"
    username            = "agentadmin"
    password            = random_password.admin.result
    host                = aws_rds_cluster.aurora.endpoint
    port                = 5432
    dbname              = var.db_name
    dbClusterIdentifier = aws_rds_cluster.aurora.cluster_identifier
  })
}

resource "aws_secretsmanager_secret" "kb_user" {
  name                    = "${local.name}/aurora/bedrock-user-${local.suffix}"
  description             = "Least-privilege credentials Bedrock Knowledge Bases uses to write vectors into Aurora"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "kb_user" {
  secret_id = aws_secretsmanager_secret.kb_user.id
  secret_string = jsonencode({
    username = "bedrock_user"
    password = random_password.kb_user.result
  })
}

# ---------------- cluster ----------------

resource "aws_rds_cluster_parameter_group" "aurora" {
  name        = "${local.name}-aurora-pg"
  family      = data.aws_rds_engine_version.pg.parameter_group_family
  description = "Operation Tangerine - log slow statements to CloudWatch"

  # Any statement slower than 250 ms lands in the postgresql log -> CloudWatch.
  parameter {
    name  = "log_min_duration_statement"
    value = "250"
  }
}

resource "aws_rds_cluster" "aurora" {
  cluster_identifier = "${local.name}-aurora"
  engine             = "aurora-postgresql"
  engine_mode        = "provisioned"
  engine_version     = data.aws_rds_engine_version.pg.version_actual
  database_name      = var.db_name
  master_username    = "agentadmin"
  master_password    = random_password.admin.result

  db_subnet_group_name            = aws_db_subnet_group.aurora.name
  vpc_security_group_ids          = [aws_security_group.aurora.id]
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.aurora.name

  # The RDS Data API (HTTP endpoint). Bedrock Knowledge Bases, the Query
  # Editor, the Aurora MCP server and our Lambda all depend on it.
  enable_http_endpoint = true

  serverlessv2_scaling_configuration {
    min_capacity = var.aurora_min_acu
    max_capacity = var.aurora_max_acu
  }

  storage_encrypted               = true
  backup_retention_period         = 1
  skip_final_snapshot             = true
  deletion_protection             = false
  apply_immediately               = true
  enabled_cloudwatch_logs_exports = ["postgresql"]

  # NOTE: labctl switches the Data API off during break-fix drills. A plain
  # `terraform apply` switches it back on - that is the intended "reset button".

  lifecycle {
    # "latest minor" moves over time; don't let that trigger surprise upgrades.
    ignore_changes = [engine_version]
  }
}

resource "aws_rds_cluster_instance" "writer" {
  identifier         = "${local.name}-aurora-writer"
  cluster_identifier = aws_rds_cluster.aurora.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.aurora.engine
  engine_version     = aws_rds_cluster.aurora.engine_version

  performance_insights_enabled = true
  publicly_accessible          = false
  apply_immediately            = true
}
