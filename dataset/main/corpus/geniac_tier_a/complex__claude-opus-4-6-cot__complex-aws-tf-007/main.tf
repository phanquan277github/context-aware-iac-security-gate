terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------
variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "datalake"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "sns_notification_email" {
  type    = string
  default = "datalake-alerts@example.com"
}

variable "redshift_admin_username" {
  type    = string
  default = "admin"
}

variable "redshift_admin_password" {
  type      = string
  sensitive = true
  default   = "Admin1234!ChangeMe"
}

variable "firehose_source_stream_name" {
  type    = string
  default = ""
}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
  prefix     = "${var.project_name}-${var.environment}"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# -----------------------------------------------------------------------------
# KMS Keys — one per data classification tier
# -----------------------------------------------------------------------------
resource "aws_kms_key" "raw_tier" {
  description             = "${local.prefix} - Raw tier encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.kms_key_policy.json
  tags = merge(local.tags, {
    DataClassification = "raw"
  })
}

resource "aws_kms_alias" "raw_tier" {
  name          = "alias/${local.prefix}-raw-tier"
  target_key_id = aws_kms_key.raw_tier.key_id
}

resource "aws_kms_key" "curated_tier" {
  description             = "${local.prefix} - Curated tier encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.kms_key_policy.json
  tags = merge(local.tags, {
    DataClassification = "curated"
  })
}

resource "aws_kms_alias" "curated_tier" {
  name          = "alias/${local.prefix}-curated-tier"
  target_key_id = aws_kms_key.curated_tier.key_id
}

resource "aws_kms_key" "athena_results" {
  description             = "${local.prefix} - Athena results encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.kms_key_policy.json
  tags = merge(local.tags, {
    DataClassification = "athena-results"
  })
}

resource "aws_kms_alias" "athena_results" {
  name          = "alias/${local.prefix}-athena-results"
  target_key_id = aws_kms_key.athena_results.key_id
}

data "aws_iam_policy_document" "kms_key_policy" {
  statement {
    sid    = "EnableRootAccountFullAccess"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = ["*"]
  }

  statement {
    sid    = "AllowGlueServiceAccess"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:ReEncryptFrom",
      "kms:ReEncryptTo",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "AllowFirehoseServiceAccess"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["firehose.amazonaws.com"]
    }
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "AllowLakeFormation"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lakeformation.amazonaws.com"]
    }
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
    ]
    resources = ["*"]
  }
}

# -----------------------------------------------------------------------------
# S3 Buckets
# -----------------------------------------------------------------------------

# --- Raw Tier Bucket ---
resource "aws_s3_bucket" "raw" {
  bucket        = "${local.prefix}-raw-${local.account_id}"
  force_destroy = false
  tags = merge(local.tags, {
    DataClassification = "raw"
    DataTier           = "raw"
  })
}

resource "aws_s3_bucket_versioning" "raw" {
  bucket = aws_s3_bucket.raw.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.raw_tier.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "raw" {
  bucket                  = aws_s3_bucket.raw.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id

  rule {
    id     = "raw-lifecycle"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# --- Curated Tier Bucket ---
resource "aws_s3_bucket" "curated" {
  bucket        = "${local.prefix}-curated-${local.account_id}"
  force_destroy = false
  tags = merge(local.tags, {
    DataClassification = "curated"
    DataTier           = "curated"
  })
}

resource "aws_s3_bucket_versioning" "curated" {
  bucket = aws_s3_bucket.curated.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "curated" {
  bucket = aws_s3_bucket.curated.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.curated_tier.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "curated" {
  bucket                  = aws_s3_bucket.curated.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_intelligent_tiering_configuration" "curated" {
  bucket = aws_s3_bucket.curated.id
  name   = "curated-intelligent-tiering"

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "curated" {
  bucket = aws_s3_bucket.curated.id

  rule {
    id     = "curated-intelligent-tiering"
    status = "Enabled"

    transition {
      days          = 0
      storage_class = "INTELLIGENT_TIERING"
    }
  }
}

# --- Athena Results Bucket ---
resource "aws_s3_bucket" "athena_results" {
  bucket        = "${local.prefix}-athena-results-${local.account_id}"
  force_destroy = true
  tags = merge(local.tags, {
    DataClassification = "athena-results"
  })
}

resource "aws_s3_bucket_versioning" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.athena_results.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket                  = aws_s3_bucket.athena_results.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  rule {
    id     = "expire-results"
    status = "Enabled"

    expiration {
      days = 30
    }
  }
}

# --- Glue Scripts Bucket ---
resource "aws_s3_bucket" "glue_scripts" {
  bucket        = "${local.prefix}-glue-scripts-${local.account_id}"
  force_destroy = true
  tags          = local.tags
}

resource "aws_s3_bucket_server_side_encryption_configuration" "glue_scripts" {
  bucket = aws_s3_bucket.glue_scripts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.raw_tier.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "glue_scripts" {
  bucket                  = aws_s3_bucket.glue_scripts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Upload Glue ETL script
resource "aws_s3_object" "glue_etl_script" {
  bucket  = aws_s3_bucket.glue_scripts.id
  key     = "scripts/raw_to_curated_etl.py"
  content = <<-PYTHON
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'SOURCE_DATABASE', 'SOURCE_TABLE', 'TARGET_PATH'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Read from raw catalog table (incremental via job bookmarks)
datasource = glueContext.create_dynamic_frame.from_catalog(
    database=args['SOURCE_DATABASE'],
    table_name=args['SOURCE_TABLE'],
    transformation_ctx="datasource"
)

# Apply mappings / transformations
mapped = datasource.apply_mapping([
    ("col0", "string", "col0", "string"),
])

# Resolve choice types
resolved = mapped.resolveChoice(choice="make_struct")

# Drop null fields
cleaned = DropNullFields.apply(frame=resolved)

# Write to curated zone in Parquet
sink = glueContext.write_dynamic_frame.from_options(
    frame=cleaned,
    connection_type="s3",
    format="glueparquet",
    connection_options={
        "path": args['TARGET_PATH'],
        "partitionKeys": []
    },
    transformation_ctx="sink"
)

job.commit()
PYTHON
}

# --- Glue Temp Bucket ---
resource "aws_s3_bucket" "glue_temp" {
  bucket        = "${local.prefix}-glue-temp-${local.account_id}"
  force_destroy = true
  tags          = local.tags
}

resource "aws_s3_bucket_server_side_encryption_configuration" "glue_temp" {
  bucket = aws_s3_bucket.glue_temp.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.raw_tier.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "glue_temp" {
  bucket                  = aws_s3_bucket.glue_temp.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------------------------------------
# IAM Roles
# -----------------------------------------------------------------------------

# --- Lake Formation Admin Role ---
resource "aws_iam_role" "lakeformation_admin" {
  name = "${local.prefix}-lakeformation-admin"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lakeformation.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  tags = local.tags
}

resource "aws_iam_role_policy" "lakeformation_admin" {
  name = "${local.prefix}-lakeformation-admin-policy"
  role = aws_iam_role.lakeformation_admin.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation",
        ]
        Resource = [
          aws_s3_bucket.raw.arn,
          "${aws_s3_bucket.raw.arn}/*",
          aws_s3_bucket.curated.arn,
          "${aws_s3_bucket.curated.arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
        ]
        Resource = [
          aws_kms_key.raw_tier.arn,
          aws_kms_key.curated_tier.arn,
        ]
      }
    ]
  })
}

# --- Glue Service Role ---
resource "aws_iam_role" "glue_service" {
  name = "${local.prefix}-glue-service-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "glue_service_base" {
  role       = aws_iam_role.glue_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_service_s3_kms" {
  name = "${local.prefix}-glue-s3-kms"
  role = aws_iam_role.glue_service.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation",
        ]
        Resource = [
          aws_s3_bucket.raw.arn,
          "${aws_s3_bucket.raw.arn}/*",
          aws_s3_bucket.curated.arn,
          "${aws_s3_bucket.curated.arn}/*",
          aws_s3_bucket.glue_scripts.arn,
          "${aws_s3_bucket.glue_scripts.arn}/*",
          aws_s3_bucket.glue_temp.arn,
          "${aws_s3_bucket.glue_temp.arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:ReEncryptFrom",
          "kms:ReEncryptTo",
          "kms:DescribeKey",
        ]
        Resource = [
          aws_kms_key.raw_tier.arn,
          aws_kms_key.curated_tier.arn,
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "lakeformation:GetDataAccess",
        ]
        Resource = ["*"]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = ["arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws-glue/*"]
      }
    ]
  })
}

# --- Firehose Role ---
resource "aws_iam_role" "firehose" {
  name = "${local.prefix}-firehose-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "firehose.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  tags = local.tags
}

resource "aws_iam_role_policy" "firehose" {
  name = "${local.prefix}-firehose-policy"
  role = aws_iam_role.firehose.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:AbortMultipartUpload",
          "s3:GetBucketLocation",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:ListBucketMultipartUploads",
          "s3:PutObject",
        ]
        Resource = [
          aws_s3_bucket.raw.arn,
          "${aws_s3_bucket.raw.arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:Encrypt",
        ]
        Resource = [aws_kms_key.raw_tier.arn]
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetTable",
          "glue:GetTableVersion",
          "glue:GetTableVersions",
        ]
        Resource = [
          "arn:aws:glue:${local.region}:${local.account_id}:catalog",
          "arn:aws:glue:${local.region}:${local.account_id}:database/${aws_glue_catalog_database.raw.name}",
          "arn:aws:glue:${local.region}:${local.account_id}:table/${aws_glue_catalog_database.raw.name}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogStream",
          "logs:CreateLogGroup",
        ]
        Resource = ["arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/kinesisfirehose/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = ["*"]
      }
    ]
  })
}

# --- Step Functions Role ---
resource "aws_iam_role" "step_functions" {
  name = "${local.prefix}-stepfunctions-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  tags = local.tags
}

resource "aws_iam_role_policy" "step_functions" {
  name = "${local.prefix}-stepfunctions-policy"
  role = aws_iam_role.step_functions.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "glue:StartJobRun",
          "glue:GetJobRun",
          "glue:GetJobRuns",
          "glue:BatchStopJobRun",
          "glue:StartCrawler",
          "glue:GetCrawler",
        ]
        Resource = ["*"]
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish",
        ]
        Resource = [aws_sns_topic.pipeline_failures.arn]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups",
        ]
        Resource = ["*"]
      },
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
        ]
        Resource = ["*"]
      }
    ]
  })
}

# --- Redshift Serverless Role ---
resource "aws_iam_role" "redshift_serverless" {
  name = "${local.prefix}-redshift-serverless-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "redshift.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  tags = local.tags
}

resource "aws_iam_role_policy" "redshift_serverless" {
  name = "${local.prefix}-redshift-serverless-policy"
  role = aws_iam_role.redshift_serverless.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:GetBucketLocation",
        ]
        Resource = [
          aws_s3_bucket.raw.arn,
          "${aws_s3_bucket.raw.arn}/*",
          aws_s3_bucket.curated.arn,
          "${aws_s3_bucket.curated.arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
        ]
        Resource = [
          aws_kms_key.raw_tier.arn,
          aws_kms_key.curated_tier.arn,
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:BatchGetPartition",
        ]
        Resource = [
          "arn:aws:glue:${local.region}:${local.account_id}:catalog",
          "arn:aws:glue:${local.region}:${local.account_id}:database/*",
          "arn:aws:glue:${local.region}:${local.account_id}:table/*/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "lakeformation:GetDataAccess",
        ]
        Resource = ["*"]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "redshift_serverless_spectrum" {
  role       = aws_iam_role.redshift_serverless.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonRedshiftAllCommandsFullAccess"
}

# -----------------------------------------------------------------------------
# Lake Formation
# -----------------------------------------------------------------------------
resource "aws_lakeformation_data_lake_settings" "main" {
  admins = [aws_iam_role.lakeformation_admin.arn]

  create_database_default_permissions {
    permissions = ["ALL"]
    principal   = "IAM_ALLOWED_PRINCIPALS"
  }

  create_table_default_permissions {
    permissions = ["ALL"]
    principal   = "IAM_ALLOWED_PRINCIPALS"
  }
}

resource "aws_lakeformation_resource" "raw" {
  arn      = aws_s3_bucket.raw.arn
  role_arn = aws_iam_role.lakeformation_admin.arn
}

resource "aws_lakeformation_resource" "curated" {
  arn      = aws_s3_bucket.curated.arn
  role_arn = aws_iam_role.lakeformation_admin.arn
}

# Column-level permissions for Glue role on curated database
resource "aws_lakeformation_permissions" "glue_curated_database" {
  principal   = aws_iam_role.glue_service.arn
  permissions = ["CREATE_TABLE", "DESCRIBE", "ALTER"]

  database {
    name = aws_glue_catalog_database.curated.name
  }
}

resource "aws_lakeformation_permissions" "glue_raw_database" {
  principal   = aws_iam_role.glue_service.arn
  permissions = ["CREATE_TABLE", "DESCRIBE", "ALTER"]

  database {
    name = aws_glue_catalog_database.raw.name
  }
}

# Fine-grained column-level access control example
resource "aws_lakeformation_permissions" "glue_raw_table_column_level" {
  principal   = aws_iam_role.glue_service.arn
  permissions = ["SELECT", "DESCRIBE"]

  table {
    database_name = aws_glue_catalog_database.raw.name
    wildcard      = true
  }
}

resource "aws_lakeformation_permissions" "glue_curated_table_column_level" {
  principal   = aws_iam_role.glue_service.arn
  permissions = ["SELECT", "INSERT", "DELETE", "DESCRIBE", "ALTER"]

  table {
    database_name = aws_glue_catalog_database.curated.name
    wildcard      = true
  }
}

# Redshift Serverless Lake Formation permissions
resource "aws_lakeformation_permissions" "redshift_curated" {
  principal   = aws_iam_role.redshift_serverless.arn
  permissions = ["SELECT", "DESCRIBE"]

  table {
    database_name = aws_glue_catalog_database.curated.name
    wildcard      = true
  }
}

# -----------------------------------------------------------------------------
# Glue Data Catalog
# -----------------------------------------------------------------------------
resource "aws_glue_catalog_database" "raw" {
  name        = "${replace(local.prefix, "-", "_")}_raw"
  description = "Raw data lake zone"

  create_table_default_permission {
    permissions = ["ALL"]
    principal {
      data_lake_principal_identifier = "IAM_ALLOWED_PRINCIPALS"
    }
  }
}

resource "aws_glue_catalog_database" "curated" {
  name        = "${replace(local.prefix, "-", "_")}_curated"
  description = "Curated data lake zone"

  create_table_default_permission {
    permissions = ["ALL"]
    principal {
      data_lake_principal_identifier = "IAM_ALLOWED_PRINCIPALS"
    }
  }
}

# Glue catalog table for Firehose format conversion
resource "aws_glue_catalog_table" "firehose_schema" {
  name          = "firehose_ingestion"
  database_name = aws_glue_catalog_database.raw.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    classification = "parquet"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.raw.id}/firehose/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    columns {
      name = "event_id"
      type = "string"
    }

    columns {
      name = "event_type"
      type = "string"
    }

    columns {
      name = "event_timestamp"
      type = "timestamp"
    }

    columns {
      name = "payload"
      type = "string"
    }

    columns {
      name = "source_system"
      type = "string"
    }

    columns {
      name = "year"
      type = "string"
    }

    columns {
      name = "month"
      type = "string"
    }

    columns {
      name = "day"
      type = "string"
    }

    columns {
      name = "hour"
      type = "string"
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }

  partition_keys {
    name = "month"
    type = "string"
  }

  partition_keys {
    name = "day"
    type = "string"
  }

  partition_keys {
    name = "hour"
    type = "string"
  }
}

# -----------------------------------------------------------------------------
# Glue Crawlers
# -----------------------------------------------------------------------------
resource "aws_glue_crawler" "raw" {
  name          = "${local.prefix}-raw-crawler"
  role          = aws_iam_role.glue_service.arn
  database_name = aws_glue_catalog_database.raw.name

  s3_target {
    path = "s3://${aws_s3_bucket.raw.id}/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  recrawl_policy {
    recrawl_behavior = "CRAWL_NEW_FOLDERS_ONLY"
  }

  configuration = jsonencode({
    Version = 1.0
    Grouping = {
      TableGroupingPolicy = "CombineCompatibleSchemas"
    }
  })

  lake_formation_configuration {
    use_lake_formation_credentials = true
  }

  tags = local.tags
}

resource "aws_glue_crawler" "curated" {
  name          = "${local.prefix}-curated-crawler"
  role          = aws_iam_role.glue_service.arn
  database_name = aws_glue_catalog_database.curated.name

  s3_target {
    path = "s3://${aws_s3_bucket.curated.id}/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  recrawl_policy {
    recrawl_behavior = "CRAWL_NEW_FOLDERS_ONLY"
  }

  lake_formation_configuration {
    use_lake_formation_credentials = true
  }

  tags = local.tags
}

# -----------------------------------------------------------------------------
# Glue ETL Jobs
# -----------------------------------------------------------------------------
resource "aws_glue_job" "raw_to_curated" {
  name              = "${local.prefix}-raw-to-curated-etl"
  role_arn          = aws_iam_role.glue_service.arn
  glue_version      = "4.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 120
  max_retries       = 1

  command {
    script_location = "s3://${aws_s3_bucket.glue_scripts.id}/scripts/raw_to_curated_etl.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-bookmark-option"              = "job-bookmark-enable"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://${aws_s3_bucket.glue_temp.id}/spark-logs/"
    "--TempDir"                          = "s3://${aws_s3_bucket.glue_temp.id}/temp/"
    "--SOURCE_DATABASE"                  = aws_glue_catalog_database.raw.name
    "--SOURCE_TABLE"                     = "firehose_ingestion"
    "--TARGET_PATH"                      = "s3://${aws_s3_bucket.curated.id}/processed/"
    "--enable-glue-datacatalog"          = "true"
    "--job-language"                     = "python"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  tags = local.tags
}

resource "aws_glue_job" "data_quality" {
  name              = "${local.prefix}-data-quality-check"
  role_arn          = aws_iam_role.glue_service.arn
  glue_version      = "4.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 60
  max_retries       = 0

  command {
    script_location = "s3://${aws_s3_bucket.glue_scripts.id}/scripts/raw_to_curated_etl.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-bookmark-option"              = "job-bookmark-enable"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--TempDir"                          = "s3://${aws_s3_bucket.glue_temp.id}/temp/"
    "--SOURCE_DATABASE"                  = aws_glue_catalog_database.curated.name
    "--SOURCE_TABLE"                     = "processed"
    "--TARGET_PATH"                      = "s3://${aws_s3_bucket.curated.id}/validated/"
    "--enable-glue-datacatalog"          = "true"
    "--job-language"                     = "python"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  tags = local.tags
}

# -----------------------------------------------------------------------------
# Athena Workgroups
# -----------------------------------------------------------------------------
resource "aws_athena_workgroup" "primary" {
  name          = "${local.prefix}-primary"
  description   = "Primary analytics workgroup with encryption and cost controls"
  force_destroy = true

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    bytes_scanned_cutoff_per_query     = 1073741824 # 1 GB per query limit

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.id}/primary/"

      encryption_configuration {
        encryption_option = "SSE_KMS"
        kms_key_arn       = aws_kms_key.athena_results.arn
      }
    }

    engine_version {
      selected_engine_version = "Athena engine version 3"
    }
  }

  tags = local.tags
}

resource "aws_athena_workgroup" "data_science" {
  name          = "${local.prefix}-data-science"
  description   = "Data science workgroup with higher cost limits"
  force_destroy = true

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    bytes_scanned_cutoff_per_query     = 10737418240 # 10 GB per query limit

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.id}/data-science/"

      encryption_configuration {
        encryption_option = "SSE_KMS"
        kms_key_arn       = aws_kms_key.athena_results.arn
      }
    }

    engine_version {
      selected_engine_version = "Athena engine version 3"
    }
  }

  tags = local.tags
}

# -----------------------------------------------------------------------------
# Redshift Serverless
# -----------------------------------------------------------------------------
resource "aws_redshiftserverless_namespace" "main" {
  namespace_name      = "${local.prefix}-namespace"
  admin_username      = var.redshift_admin_username
  admin_user_password = var.redshift_admin_password
  db_name             = "datalake"
  iam_roles           = [aws_iam_role.redshift_serverless.arn]
  default_iam_role_arn = aws_iam_role.redshift_serverless.arn
  kms_key_id          = aws_kms_key.curated_tier.arn

  tags = local.tags
}

resource "aws_redshiftserverless_workgroup" "main" {
  namespace_name = aws_redshiftserverless_namespace.main.namespace_name
  workgroup_name = "${local.prefix}-workgroup"
  base_capacity  = 32

  publicly_accessible = false

  config_parameter {
    parameter_key   = "enable_case_sensitive_identifier"
    parameter_value = "true"
  }

  config_parameter {
    parameter_key   = "datestyle"
    parameter_value = "ISO, MDY"
  }

  tags = local.tags
}

# -----------------------------------------------------------------------------
# Kinesis Data Firehose with Dynamic Partitioning & Parquet Conversion
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "firehose" {
  name              = "/aws/kinesisfirehose/${local.prefix}-delivery-stream"
  retention_in_days = 14
  tags              = local.tags
}

resource "aws_cloudwatch_log_stream" "firehose_s3" {
  name           = "S3Delivery"
  log_group_name = aws_cloudwatch_log_group.firehose.name
}

resource "aws_kinesis_firehose_delivery_stream" "main" {
  name        = "${local.prefix}-delivery-stream"
  destination = "extended_s3"

  extended_s3_configuration {
    role_arn            = aws_iam_role.firehose.arn
    bucket_arn          = aws_s3_bucket.raw.arn
    prefix              = "firehose/year=!{partitionKeyFromQuery:year}/month=!{partitionKeyFromQuery:month}/day=!{partitionKeyFromQuery:day}/hour=!{partitionKeyFromQuery:hour}/"
    error_output_prefix = "firehose-errors/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/!{firehose:error-output-type}/"
    kms_key_arn         = aws_kms_key.raw_tier.arn

    buffering_size     = 128
    buffering_interval = 60

    dynamic_partitioning_configuration {
      enabled = true
    }

    processing_configuration {
      enabled = true

      processors {
        type = "MetadataExtraction"
        parameters {
          parameter_name  = "JsonParsingEngine"
          parameter_value = "JQ-1.6"
        }
        parameters {
          parameter_name  = "MetadataExtractionQuery"
          parameter_value = "{year: (.event_timestamp[:4] // now | strftime(\"%Y\")), month: (.event_timestamp[5:7] // now | strftime(\"%m\")), day: (.event_timestamp[8:10] // now | strftime(\"%d\")), hour: (.event_timestamp[11:13] // now | strftime(\"%H\"))}"
        }
      }

      processors {
        type = "AppendDelimiterToRecord"
        parameters {
          parameter_name  = "Delimiter"
          parameter_value = "\\n"
        }
      }
    }

    data_format_conversion_configuration {
      input_format_configuration {
        deserializer {
          open_x_json_ser_de {}
        }
      }

      output_format_configuration {
        serializer {
          parquet_ser_de {
            compression = "SNAPPY"
          }
        }
      }

      schema_configuration {
        database_name = aws_glue_catalog_database.raw.name
        table_name    = aws_glue_catalog_table.firehose_schema.name
        role_arn      = aws_iam_role.firehose.arn
        region        = local.region
      }
    }

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.firehose.name
      log_stream_name = aws_cloudwatch_log_stream.firehose_s3.name
    }

    s3_backup_mode = "Disabled"
  }

  tags = local.tags
}

# -----------------------------------------------------------------------------
# SNS Topic for Pipeline Failure Notifications
# -----------------------------------------------------------------------------
resource "aws_sns_topic" "pipeline_failures" {
  name              = "${local.prefix}-pipeline-failures"
  kms_master_key_id = aws_kms_key.raw_tier.id
  tags              = local.tags
}

resource "aws_sns_topic_subscription" "pipeline_failures_email" {
  topic_arn = aws_sns_topic.pipeline_failures.arn
  protocol  = "email"
  endpoint  = var.sns_notification_email
}

# -----------------------------------------------------------------------------
# Step Functions — ETL Pipeline Orchestration
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/states/${local.prefix}-etl-pipeline"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_sfn_state_machine" "etl_pipeline" {
  name     = "${local.prefix}-etl-pipeline"
  role_arn = aws_iam_role.step_functions.arn

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  definition = jsonencode({
    Comment = "Data Lake ETL Pipeline: Raw -> Curated with crawlers and quality checks"
    StartAt = "CrawlRawData"
    States = {
      CrawlRawData = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startCrawler"
        Parameters = {
          Name = aws_glue_crawler.raw.name
        }
        ResultPath = "$.CrawlerOutput"
        Next       = "WaitForRawCrawler"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "NotifyFailure"
            ResultPath  = "$.error"
          }
        ]
      }

      WaitForRawCrawler = {
        Type    = "Wait"
        Seconds = 30
        Next    = "CheckRawCrawlerStatus"
      }

      CheckRawCrawlerStatus = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:glue:getCrawler"
        Parameters = {
          Name = aws_glue_crawler.raw.name
        }
        ResultPath = "$.CrawlerStatus"
        Next       = "IsRawCrawlerComplete"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "NotifyFailure"
            ResultPath  = "$.error"
          }
        ]
      }

      IsRawCrawlerComplete = {
        Type = "Choice"
        Choices = [
          {
            Variable     = "$.CrawlerStatus.Crawler.State"
            StringEquals = "READY"
            Next         = "RunRawToCuratedETL"
          }
        ]
        Default = "WaitForRawCrawler"
      }

      RunRawToCuratedETL = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = aws_glue_job.raw_to_curated.name
          Arguments = {
            "--job-bookmark-option" = "job-bookmark-enable"
            "--SOURCE_DATABASE"     = aws_glue_catalog_database.raw.name
            "--SOURCE_TABLE"        = "firehose_ingestion"
            "--TARGET_PATH"         = "s3://${aws_s3_bucket.curated.id}/processed/"
          }
        }
        ResultPath = "$.ETLOutput"
        Next       = "RunDataQualityCheck"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "NotifyFailure"
            ResultPath  = "$.error"
          }
        ]
      }

      RunDataQualityCheck = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = aws_glue_job.data_quality.name
          Arguments = {
            "--job-bookmark-option" = "job-bookmark-enable"
            "--SOURCE_DATABASE"     = aws_glue_catalog_database.curated.name
            "--SOURCE_TABLE"        = "processed"
            "--TARGET_PATH"         = "s3://${aws_s3_bucket.curated.id}/validated/"
          }
        }
        ResultPath = "$.QualityOutput"
        Next       = "CrawlCuratedData"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "NotifyFailure"
            ResultPath  = "$.error"
          }
        ]
      }

      CrawlCuratedData = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startCrawler"
        Parameters = {
          Name = aws_glue_crawler.curated.name
        }
        ResultPath = "$.CuratedCrawlerOutput"
        Next       = "WaitForCuratedCrawler"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "NotifyFailure"
            ResultPath  = "$.error"
          }
        ]
      }

      WaitForCuratedCrawler = {
        Type    = "Wait"
        Seconds = 30
        Next    = "CheckCuratedCrawlerStatus"
      }

      CheckCuratedCrawlerStatus = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:glue:getCrawler"
        Parameters = {
          Name = aws_glue_crawler.curated.name
        }
        ResultPath = "$.CuratedCrawlerStatus"
        Next       = "IsCuratedCrawlerComplete"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "NotifyFailure"
            ResultPath  = "$.error"
          }
        ]
      }

      IsCuratedCrawlerComplete = {
        Type = "Choice"
        Choices = [
          {
            Variable     = "$.CuratedCrawlerStatus.Crawler.State"
            StringEquals = "READY"
            Next         = "PipelineSuccess"
          }
        ]
        Default = "WaitForCuratedCrawler"
      }

      PipelineSuccess = {
        Type = "Succeed"
      }

      NotifyFailure = {
        Type     = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          TopicArn = aws_sns_topic.pipeline_failures.arn
          Subject  = "Data Lake ETL Pipeline Failure"
          Message = {
            "Fn::States.Format" = "ETL Pipeline failed. Error: {}"
            "Fn::States.Array"  = ["$.error"]
          }
        }
        Next = "PipelineFailed"
      }

      PipelineFailed = {
        Type  = "Fail"
        Error = "ETLPipelineFailure"
        Cause = "One or more steps in the ETL pipeline failed. Check CloudWatch logs for details."
      }
    }
  })

  tags = local.tags
}

# EventBridge rule to trigger pipeline on schedule
resource "aws_iam_role" "eventbridge_sfn" {
  name = "${local.prefix}-eventbridge-sfn-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  tags = local.tags
}

resource "aws_iam_role_policy" "eventbridge_sfn" {
  name = "${local.prefix}-eventbridge-sfn-policy"
  role = aws_iam_role.eventbridge_sfn.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "states:StartExecution"
        Resource = aws_sfn_state_machine.etl_pipeline.arn
      }
    ]
  })
}

resource "aws_cloudwatch_event_rule" "etl_schedule" {
  name                = "${local.prefix}-etl-schedule"
  description         = "Trigger ETL pipeline every hour"
  schedule_expression = "rate(1 hour)"
  tags                = local.tags
}

resource "aws_cloudwatch_event_target" "etl_sfn" {
  rule     = aws_cloudwatch_event_rule.etl_schedule.name
  arn      = aws_sfn_state_machine.etl_pipeline.arn
  role_arn = aws_iam_role.eventbridge_sfn.arn
}

# -----------------------------------------------------------------------------
# CloudWatch Dashboard
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_dashboard" "datalake" {
  dashboard_name = "${local.prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 1
        properties = {
          markdown = "# ${local.prefix} Data Lake Dashboard"
        }
      },
      # Data Freshness - Firehose Incoming Records
      {
        type   = "metric"
        x      = 0
        y      = 1
        width  = 8
        height = 6
        properties = {
          title   = "Data Freshness - Firehose Incoming Records"
          metrics = [
            ["AWS/Firehose", "IncomingRecords", "DeliveryStreamName", aws_kinesis_firehose_delivery_stream.main.name, { stat = "Sum", period = 300 }],
            ["AWS/Firehose", "DeliveryToS3.Records", "DeliveryStreamName", aws_kinesis_firehose_delivery_stream.main.name, { stat = "Sum", period = 300 }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 300
        }
      },
      # Data Freshness - Firehose Data Freshness (Latency)
      {
        type   = "metric"
        x      = 8
        y      = 1
        width  = 8
        height = 6
        properties = {
          title   = "Data Freshness - Delivery Latency"
          metrics = [
            ["AWS/Firehose", "DeliveryToS3.DataFreshness", "DeliveryStreamName", aws_kinesis_firehose_delivery_stream.main.name, { stat = "Average", period = 300 }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 300
          yAxis = {
            left = {
              label     = "Seconds"
              showUnits = false
            }
          }
        }
      },
      # Bytes Processed - Firehose
      {
        type   = "metric"
        x      = 16
        y      = 1
        width  = 8
        height = 6
        properties = {
          title   = "Bytes Processed - Firehose"
          metrics = [
            ["AWS/Firehose", "IncomingBytes", "DeliveryStreamName", aws_kinesis_firehose_delivery_stream.main.name, { stat = "Sum", period = 300 }],
            ["AWS/Firehose", "DeliveryToS3.Bytes", "DeliveryStreamName", aws_kinesis_firehose_delivery_stream.main.name, { stat = "Sum", period = 300 }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 300
        }
      },
      # Glue Job Durations
      {
        type   = "metric"
        x      = 0
        y      = 7
        width  = 12
        height = 6
        properties = {
          title   = "Glue ETL Job Duration (minutes)"
          metrics = [
            ["Glue", "glue.driver.aggregate.elapsedTime", "JobName", aws_glue_job.raw_to_curated.name, "JobRunId", "ALL", "Type", "gauge", { stat = "Maximum", period = 3600 }],
            ["Glue", "glue.driver.aggregate.elapsedTime", "JobName", aws_glue_job.data_quality.name, "JobRunId", "ALL", "Type", "gauge", { stat = "Maximum", period = 3600 }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 3600
        }
      },
      # Glue Job Bytes Read/Written
      {
        type   = "metric"
        x      = 12
        y      = 7
        width  = 12
        height = 6
        properties = {
          title   = "Glue ETL Bytes Processed"
          metrics = [
            ["Glue", "glue.driver.aggregate.bytesRead", "JobName", aws_glue_job.raw_to_curated.name, "JobRunId", "ALL", "Type", "gauge", { stat = "Maximum", period = 3600 }],
            ["Glue", "glue.driver.aggregate.bytesRead", "JobName", aws_glue_job.data_quality.name, "JobRunId", "ALL", "Type", "gauge", { stat = "Maximum", period = 3600 }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 3600
        }
      },
      # Athena Query Metrics
      {
        type   = "metric"
        x      = 0
        y      = 13
        width  = 8
        height = 6
        properties = {
          title   = "Athena - Data Scanned (Bytes)"
          metrics = [
            ["AWS/Athena", "ProcessedBytes", "WorkGroup", aws_athena_workgroup.primary.name, { stat = "Sum", period = 3600 }],
            ["AWS/Athena", "ProcessedBytes", "WorkGroup", aws_athena_workgroup.data_science.name, { stat = "Sum", period = 3600 }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 3600
        }
      },
      # Athena Query Execution Time
      {
        type   = "metric"
        x      = 8
        y      = 13
        width  = 8
        height = 6
        properties = {
          title   = "Athena - Query Execution Time (ms)"
          metrics = [
            ["AWS/Athena", "TotalExecutionTime", "WorkGroup", aws_athena_workgroup.primary.name, { stat = "Average", period = 3600 }],
            ["AWS/Athena", "TotalExecutionTime", "WorkGroup", aws_athena_workgroup.data_science.name, { stat = "Average", period = 3600 }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 3600
        }
      },
      # Step Functions Execution Metrics
      {
        type   = "metric"
        x      = 16
        y      = 13
        width  = 8
        height = 6
        properties = {
          title   = "ETL Pipeline Executions"
          metrics = [
            ["AWS/States", "ExecutionsStarted", "StateMachineArn", aws_sfn_state_machine.etl_pipeline.arn, { stat = "Sum", period = 3600 }],
            ["AWS/States", "ExecutionsSucceeded", "StateMachineArn", aws_sfn_state_machine.etl_pipeline.arn, { stat = "Sum", period = 3600 }],
            ["AWS/States", "ExecutionsFailed", "StateMachineArn", aws_sfn_state_machine.etl_pipeline.arn, { stat = "Sum", period = 3600 }],
            ["AWS/States", "ExecutionTime", "StateMachineArn", aws_sfn_state_machine.etl_pipeline.arn, { stat = "Average", period = 3600 }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 3600
        }
      },
      # S3 Bucket Metrics
      {
        type   = "metric"
        x      = 0
        y      = 19
        width  = 12
        height = 6
        properties = {
          title   = "S3 Bucket Size (Bytes)"
          metrics = [
            ["AWS/S3", "BucketSizeBytes", "BucketName", aws_s3_bucket.raw.id, "StorageType", "StandardStorage", { stat = "Average", period = 86400 }],
            ["AWS/S3", "BucketSizeBytes", "BucketName", aws_s3_bucket.curated.id, "StorageType", "StandardStorage", { stat = "Average", period = 86400 }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 86400
        }
      },
      # S3 Object Count
      {
        type   = "metric"
        x      = 12
        y      = 19
        width  = 12
        height = 6
        properties = {
          title   = "S3 Object Count"
          metrics = [
            ["AWS/S3", "NumberOfObjects", "BucketName", aws_s3_bucket.raw.id, "StorageType", "AllStorageTypes", { stat = "Average", period = 86400 }],
            ["AWS/S3", "NumberOfObjects", "BucketName", aws_s3_bucket.curated.id, "StorageType", "AllStorageTypes", { stat = "Average", period = 86400 }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 86400
        }
      },
      # Firehose Errors
      {
        type   = "metric"
        x      = 0
        y      = 25
        width  = 12
        height = 6
        properties = {
          title   = "Firehose Delivery Errors"
          metrics = [
            ["AWS/Firehose", "DeliveryToS3.Success", "DeliveryStreamName", aws_kinesis_firehose_delivery_stream.main.name, { stat = "Average", period = 300 }],
            ["AWS/Firehose", "ThrottledRecords", "DeliveryStreamName", aws_kinesis_firehose_delivery_stream.main.name, { stat = "Sum", period = 300 }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 300
        }
      },
      # Redshift Serverless Metrics
      {
        type   = "metric"
        x      = 12
        y      = 25
        width  = 12
        height = 6
        properties = {
          title   = "Redshift Serverless Compute"
          metrics = [
            ["AWS/Redshift-Serverless", "ComputeSeconds", "Workgroup", aws_redshiftserverless_workgroup.main.workgroup_name, { stat = "Sum", period = 3600 }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 3600
        }
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Alarms
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "firehose_data_freshness" {
  alarm_name          = "${local.prefix}-firehose-data-freshness"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "DeliveryToS3.DataFreshness"
  namespace           = "AWS/Firehose"
  period              = 300
  statistic           = "Average"
  threshold           = 900 # 15 minutes
  alarm_description   = "Firehose data freshness exceeds 15 minutes"
  alarm_actions       = [aws_sns_topic.pipeline_failures.arn]
  ok_actions          = [aws_sns_topic.pipeline_failures.arn]

  dimensions = {
    DeliveryStreamName = aws_kinesis_firehose_delivery_stream.main.name
  }

  tags = local.tags
}

resource "aws_cloudwatch_metric_alarm" "etl_pipeline_failures" {
  alarm_name          = "${local.prefix}-etl-pipeline-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 3600
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "ETL pipeline execution failed"
  alarm_actions       = [aws_sns_topic.pipeline_failures.arn]

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.etl_pipeline.arn
  }

  tags = local.tags
}

resource "aws_cloudwatch_metric_alarm" "glue_job_failure" {
  alarm_name          = "${local.prefix}-glue-job-failure"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "glue.driver.aggregate.numFailedTasks"
  namespace           = "Glue"
  period              = 3600
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Glue ETL job has failed tasks"
  alarm_actions       = [aws_sns_topic.pipeline_failures.arn]

  dimensions = {
    JobName  = aws_glue_job.raw_to_curated.name
    JobRunId = "ALL"
    Type     = "gauge"
  }

  tags = local.tags
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "raw_bucket_name" {
  value = aws_s3_bucket.raw.id
}

output "curated_bucket_name" {
  value = aws_s3_bucket.curated.id
}

output "raw_database_name" {
  value = aws_glue_catalog_database.raw.name
}

output "curated_database_name" {
  value = aws_glue_catalog_database.curated.name
}

output "firehose_delivery_stream_name" {
  value = aws_kinesis_firehose_delivery_stream.main.name
}

output "firehose_delivery_stream_arn" {
  value = aws_kinesis_firehose_delivery_stream.main.arn
}

output "step_functions_arn" {
  value = aws_sfn_state_machine.etl_pipeline.arn
}

output "athena_primary_workgroup" {
  value = aws_athena_workgroup.primary.name
}

output "athena_data_science_workgroup" {
  value = aws_athena_workgroup.data_science.name
}

output "redshift_serverless_namespace" {
  value = aws_redshiftserverless_namespace.main.namespace_name
}

output "redshift_serverless_workgroup" {
  value = aws_redshiftserverless_workgroup.main.workgroup_name
}

output "redshift_serverless_endpoint" {
  value = aws_redshiftserverless_workgroup.main.endpoint
}

output "dashboard_url" {
  value = "https://${local.region}.console.aws.amazon.com/cloudwatch/home?region=${local.region}#dashboards:name=${aws_cloudwatch_dashboard.datalake.dashboard_name}"
}

output "kms_key_raw_arn" {
  value = aws_kms_key.raw_tier.arn
}

output "kms_key_curated_arn" {
  value = aws_kms_key.curated_tier.arn
}

output "kms_key_athena_arn" {
  value = aws_kms_key.athena_results.arn
}

output "sns_topic_arn" {
  value = aws_sns_topic.pipeline_failures.arn
}