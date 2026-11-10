#!/usr/bin/env python3
"""Score the ticket-triage model on your laptop (Ollama) and/or on AWS (Bedrock).

Examples:
  python test_model.py --target local
  python test_model.py --target bedrock
  python test_model.py --target both --ticket "lambda timing out in prod"
  python test_model.py --target bedrock --max-attempts 1 --ticket "..."   # show a cold start
"""
import argparse
import json
import os
import sys
import time

from common import build_messages, parse_output, score

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/v1/chat/completions")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
BEDROCK_MODEL_ARN = os.environ.get("BEDROCK_MODEL_ARN", "")
AWS_REGION = os.environ.get("AWS_REGION", "eu-central-1")


def payload(messages, json_mode):
    body = {"messages": messages, "temperature": 0, "max_tokens": 200}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    return body


class Local:
    name = "laptop"

    def __init__(self, json_mode):
        import requests
        self.requests, self.json_mode = requests, json_mode

    def __call__(self, messages):
        body = payload(messages, self.json_mode) | {"model": OLLAMA_MODEL}
        r = self.requests.post(OLLAMA_URL, json=body, timeout=120)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


class Bedrock:
    name = "aws"

    def __init__(self, json_mode, max_attempts=10):
        if not BEDROCK_MODEL_ARN:
            sys.exit("Set BEDROCK_MODEL_ARN first (see README step 6).")
        import boto3
        from botocore.config import Config
        # Standard retries handle ModelNotReadyException while a scaled-to-zero model restores
        cfg = Config(retries={"total_max_attempts": max_attempts, "mode": "standard"}, read_timeout=120)
        self.client = boto3.client("bedrock-runtime", region_name=AWS_REGION, config=cfg)
        self.json_mode = json_mode

    def __call__(self, messages):
        resp = self.client.invoke_model(
            modelId=BEDROCK_MODEL_ARN,
            body=json.dumps(payload(messages, self.json_mode)),
            accept="application/json",
            contentType="application/json",
        )
        data = json.loads(resp["body"].read())
        return data["choices"][0]["message"]["content"]


def timed(backend, messages):
    start = time.perf_counter()
    raw = backend(messages)
    return raw, time.perf_counter() - start


def single(backends, ticket):
    for b in backends:
        raw, secs = timed(b, build_messages(ticket))
        print(f"\n[{b.name}] {secs:.2f}s\n{raw}")


def run_suite(backend, tickets, show):
    totals = {k: 0 for k in ("strict_json", "valid_json", "keys_ok", "service", "severity", "category")}
    latencies = []
    print(f"\n=== {backend.name.upper()} ===")
    for i, t in enumerate(tickets, 1):
        raw, secs = timed(backend, build_messages(t["ticket"]))
        if i == 1:
            print(f"first call: {secs:.2f}s (on AWS this can include a cold start)")
        else:
            latencies.append(secs)
        parsed, strict = parse_output(raw)
        s = score(parsed, strict, t)
        for k, v in s.items():
            totals[k] += int(v)
        ok = all(v for k, v in s.items() if k != "strict_json")
        print(f"{i:>2}. {'PASS' if ok else 'MISS'} {secs:5.2f}s  "
              f"svc={'Y' if s['service'] else 'n'} sev={'Y' if s['severity'] else 'n'} "
              f"cat={'Y' if s['category'] else 'n'} strict={'Y' if s['strict_json'] else 'n'}")
        if show or not ok:
            print(f"    got: {raw.strip()[:200]}")
    n = len(tickets)
    print(f"\n--- {backend.name} scoreboard ({n} tickets) ---")
    labels = {"strict_json": "Pure JSON (no cleanup)", "valid_json": "Valid JSON",
              "keys_ok": "Exact keys", "service": "Correct service",
              "severity": "Correct severity", "category": "Correct category"}
    for k, label in labels.items():
        print(f"{label:<24} {100 * totals[k] / n:5.0f}%")
    if latencies:
        latencies.sort()
        print(f"{'Avg latency (warm)':<24} {sum(latencies) / len(latencies):5.2f}s")
        print(f"{'p90 latency (warm)':<24} {latencies[int(0.9 * (len(latencies) - 1))]:5.2f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["local", "bedrock", "both"], default="local")
    ap.add_argument("--ticket", help="Run one ticket instead of the test set")
    ap.add_argument("--json-mode", action="store_true", help="Also send response_format=json_object")
    ap.add_argument("--show", action="store_true", help="Print raw output for every ticket")
    ap.add_argument("--file", default="tickets.jsonl")
    ap.add_argument("--max-attempts", type=int, default=10,
                    help="Bedrock retry attempts. Use 1 to see ModelNotReadyException on a cold model")
    args = ap.parse_args()

    backends = []
    if args.target in ("local", "both"):
        backends.append(Local(args.json_mode))
    if args.target in ("bedrock", "both"):
        backends.append(Bedrock(args.json_mode, args.max_attempts))

    if args.ticket:
        single(backends, args.ticket)
        return
    with open(args.file) as f:
        tickets = [json.loads(line) for line in f if line.strip()]
    for b in backends:
        run_suite(b, tickets, args.show)


if __name__ == "__main__":
    main()
