#!/usr/bin/env bash
# Creates the S3 bucket and the IAM role Bedrock uses to read your model files.
# Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."

REGION="${AWS_REGION:-eu-central-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${BUCKET:-llm-demo-$ACCOUNT_ID}"
ROLE_NAME="${ROLE_NAME:-BedrockModelImportRole}"

echo ">> Account: $ACCOUNT_ID  Region: $REGION"

if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo ">> Bucket s3://$BUCKET already exists"
else
  echo ">> Creating bucket s3://$BUCKET"
  aws s3 mb "s3://$BUCKET" --region "$REGION"
fi

TMP="$(mktemp -d)"
sed "s/ACCOUNT_ID/$ACCOUNT_ID/g; s/eu-central-1/$REGION/g" iam/import-role-trust.json > "$TMP/trust.json"
sed "s/ACCOUNT_ID/$ACCOUNT_ID/g; s/BUCKET_NAME/$BUCKET/g" iam/import-role-s3.json > "$TMP/s3.json"

if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo ">> Role $ROLE_NAME already exists"
else
  echo ">> Creating role $ROLE_NAME"
  aws iam create-role --role-name "$ROLE_NAME" \
    --assume-role-policy-document "file://$TMP/trust.json" >/dev/null
fi
aws iam put-role-policy --role-name "$ROLE_NAME" \
  --policy-name S3ModelRead --policy-document "file://$TMP/s3.json"
rm -rf "$TMP"

echo
echo ">> Done. Run these in your terminal:"
echo "export AWS_REGION=$REGION"
echo "export BUCKET=$BUCKET"
echo "export ROLE_ARN=arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"
