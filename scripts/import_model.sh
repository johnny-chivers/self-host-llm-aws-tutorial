#!/usr/bin/env bash
# Starts a Bedrock Custom Model Import job and waits for it to finish.
set -euo pipefail

: "${BUCKET:?Run scripts/setup_aws.sh and export BUCKET}"
: "${ROLE_ARN:?Run scripts/setup_aws.sh and export ROLE_ARN}"
REGION="${AWS_REGION:-eu-central-1}"
MODEL_NAME="${MODEL_NAME:-ticket-triage-qwen}"
PREFIX="qwen2.5-1.5b-instruct"
JOB_NAME="ticket-triage-import-$(date +%Y%m%d%H%M%S)"

echo ">> Starting import job $JOB_NAME"
JOB_ARN="$(aws bedrock create-model-import-job \
  --region "$REGION" \
  --job-name "$JOB_NAME" \
  --imported-model-name "$MODEL_NAME" \
  --role-arn "$ROLE_ARN" \
  --model-data-source "{\"s3DataSource\":{\"s3Uri\":\"s3://$BUCKET/$PREFIX/\"}}" \
  --query jobArn --output text)"
echo ">> Job ARN: $JOB_ARN"

while true; do
  STATUS="$(aws bedrock get-model-import-job --region "$REGION" \
    --job-identifier "$JOB_ARN" --query status --output text)"
  echo "$(date +%H:%M:%S)  $STATUS"
  case "$STATUS" in
    Completed) break ;;
    Failed)
      aws bedrock get-model-import-job --region "$REGION" \
        --job-identifier "$JOB_ARN" --query failureMessage --output text
      exit 1 ;;
  esac
  sleep 30
done

echo ">> Imported. Next: ./scripts/model_info.sh"
