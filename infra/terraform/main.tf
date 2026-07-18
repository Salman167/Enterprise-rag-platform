terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# EU data residency — deploy in eu-west-1 (Ireland) or eu-central-1 (Frankfurt)
# MENA — use me-south-1 (Bahrain) or Azure UAE North

variable "region" {
  default = "eu-west-1"
}

variable "environment" {
  default = "dev"
}

provider "aws" {
  region = var.region
}

resource "aws_s3_bucket" "documents" {
  bucket = "enterprise-rag-documents-${var.environment}"

  tags = {
    Project     = "enterprise-rag"
    DataRegion  = "EU"
    GDPR        = "true"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

output "documents_bucket" {
  value = aws_s3_bucket.documents.bucket
}
