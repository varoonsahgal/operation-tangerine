###############################################################################
# DynamoDB - agent memory
#
#   session_id (PK)        sk (SK)                         what
#   ---------------------  ------------------------------  ----------------------
#   sess-123               MSG#2026-11-24T09:15:02.123Z#ab  one conversation turn
#   sess-123               STATE                           working state / slots
#
# GSI customer-index (customer_id, sk) -> "every session for customer C00042"
# TTL attribute expires_at (epoch seconds) -> old memory deletes itself.
###############################################################################

resource "aws_dynamodb_table" "memory" {
  name         = "${local.name}-agent-memory"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"
  range_key    = "sk"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "customer_id"
    type = "S"
  }

  global_secondary_index {
    name            = "customer-index"
    hash_key        = "customer_id"
    range_key       = "sk"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  deletion_protection_enabled = false
}
