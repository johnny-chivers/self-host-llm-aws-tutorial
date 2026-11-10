#!/usr/bin/env bash
# Deletes everything this demo created in AWS.
set -euo pipefail
REGION="${AWS_REGION:-eu-central-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${BUCKET:-llm-demo-$ACCOUNT_ID}"
ROLE_NAME="${ROLE_NAME:-BedrockModelImportRole}"
MODEL_NAME="${MODEL_NAME:-ticket-triage-qwen}"

echo "This will delete:"
echo "  - imported model $MODEL_NAME ($REGION)"
echo "  - bucket s3://$BUCKET and everything in it"
echo "  - IAM role $ROLE_NAME"
read -r -p "Type 'delete' to continue: " CONFIRM
[ "$CONFIRM" = "delete" ] || { echo "Cancelled."; exit 1; }

aws bedrock delete-imported-model --region "$REGION" --model-identifier "$MODEL_NAME" \
  && echo ">> Model deleted" || echo ">> Model not found, skipping"
aws s3 rb "s3://$BUCKET" --force \
  && echo ">> Bucket deleted" || echo ">> Bucket not found, skipping"
aws iam delete-role-policy --role-name "$ROLE_NAME" --policy-name S3ModelRead 2>/dev/null || true
aws iam delete-role --role-name "$ROLE_NAME" 2>/dev/null \
  && echo ">> Role deleted" || echo ">> Role not found, skipping"

echo ">> AWS teardown complete. Optional: ollama rm qwen2.5:1.5b"
