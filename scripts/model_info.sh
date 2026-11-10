#!/usr/bin/env bash
# Shows the imported model's ARN and the Custom Model Unit details that drive cost.
set -euo pipefail
REGION="${AWS_REGION:-eu-central-1}"
MODEL_NAME="${MODEL_NAME:-ticket-triage-qwen}"

aws bedrock get-imported-model --region "$REGION" --model-identifier "$MODEL_NAME"

ARN="$(aws bedrock get-imported-model --region "$REGION" \
  --model-identifier "$MODEL_NAME" --query modelArn --output text)"
echo
echo ">> Look for the custom model units per copy and the CMU version above."
echo ">> Then run:"
echo "export BEDROCK_MODEL_ARN=$ARN"
