"""Shared prompt, parsing and scoring for the laptop-to-AWS demo."""
import json
import re

SERVICES = ["Lambda", "S3", "EC2", "RDS", "DynamoDB", "API Gateway",
            "CloudFront", "ECS", "EKS", "IAM", "SQS"]
SEVERITIES = ["low", "medium", "high", "critical"]
CATEGORIES = ["timeout", "permissions", "cost", "outage", "configuration",
              "throttling", "performance", "quota"]
KEYS = {"service", "severity", "category", "summary"}

SYSTEM_PROMPT = f"""You triage AWS support tickets.
Return ONLY a JSON object with exactly these keys:
- "service": one of {json.dumps(SERVICES)}
- "severity": one of {json.dumps(SEVERITIES)}
- "category": one of {json.dumps(CATEGORIES)}
- "summary": one short sentence, max 15 words

Severity rules:
- critical: production is down, customers fully blocked, or data lost
- high: production degraded, slow, or a major function blocked
- medium: non-production issue, or production issue with a workaround
- low: questions, billing queries, planned limit increases

No markdown. No explanation. JSON only."""


def build_messages(ticket: str):
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": ticket},
    ]


def parse_output(raw: str):
    """Return (parsed_dict_or_None, strict_ok).
    strict_ok = the raw text was pure JSON with no cleanup needed."""
    try:
        obj = json.loads(raw.strip())
        if isinstance(obj, dict):
            return obj, True
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)  # strip fences / chatter
    if match:
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return obj, False
        except json.JSONDecodeError:
            pass
    return None, False


def _norm(value) -> str:
    v = str(value or "").strip().lower()
    for prefix in ("amazon ", "aws "):
        if v.startswith(prefix):
            v = v[len(prefix):]
    return v


def score(parsed, strict_ok, expected):
    result = {"strict_json": strict_ok, "valid_json": parsed is not None,
              "keys_ok": False, "service": False, "severity": False,
              "category": False}
    if parsed is None:
        return result
    result["keys_ok"] = set(parsed.keys()) == KEYS
    for field in ("service", "severity", "category"):
        result[field] = _norm(parsed.get(field)) == _norm(expected[field])
    return result
