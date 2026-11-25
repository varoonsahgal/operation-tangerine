###############################################################################
# S3 - source documents for the Bedrock Knowledge Base
###############################################################################

resource "aws_s3_bucket" "docs" {
  bucket        = "${local.name}-kb-docs-${local.account_id}-${local.suffix}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "docs" {
  bucket                  = aws_s3_bucket.docs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "docs" {
  bucket = aws_s3_bucket.docs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Every *.md file plus its *.md.metadata.json sidecar (used for KB metadata filtering).
resource "aws_s3_object" "docs" {
  for_each = fileset("${path.module}/sample-docs", "*")

  bucket       = aws_s3_bucket.docs.id
  key          = "docs/${each.value}"
  source       = "${path.module}/sample-docs/${each.value}"
  etag         = filemd5("${path.module}/sample-docs/${each.value}")
  content_type = endswith(each.value, ".json") ? "application/json" : "text/markdown"
}
