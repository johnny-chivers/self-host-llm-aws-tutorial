#!/usr/bin/env bash
# Download Qwen 2.5 1.5B Instruct (safetensors) and sync it to S3.
set -euo pipefail

: "${BUCKET:?Set BUCKET, e.g. export BUCKET=llm-demo-<account-id>}"
REGION="${AWS_REGION:-eu-central-1}"
MODEL_ID="Qwen/Qwen2.5-1.5B-Instruct"
PREFIX="qwen2.5-1.5b-instruct"

echo ">> Downloading $MODEL_ID (~3 GB)"
hf download "$MODEL_ID" --local-dir "./model/$PREFIX"

echo ">> Files:"
ls -lh "./model/$PREFIX"

if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo ">> Creating bucket s3://$BUCKET in $REGION"
  aws s3 mb "s3://$BUCKET" --region "$REGION"
fi

echo ">> Uploading to s3://$BUCKET/$PREFIX/"
aws s3 sync "./model/$PREFIX" "s3://$BUCKET/$PREFIX/" \
  --region "$REGION" --exclude ".cache/*" --exclude "*.md" --exclude ".gitattributes"

echo ">> Done. S3 URI for the import job: s3://$BUCKET/$PREFIX/"
