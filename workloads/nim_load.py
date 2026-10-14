#!/usr/bin/env python3
"""Optional black-box streaming NIM load test; fixed public prompt and bounded requests."""
import argparse
import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen


def send(url, model, tokens):
    data = {"model": model, "messages": [{"role": "user", "content": "Explain how a GPU processes a matrix multiplication in simple terms."}], "max_tokens": tokens, "temperature": 0, "stream": True}
    headers = {"Content-Type": "application/json"}
    if os.environ.get("NIM_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["NIM_API_KEY"]
    start = time.perf_counter()
    first = None
    try:
        with urlopen(Request(url.rstrip("/") + "/v1/chat/completions", data=json.dumps(data).encode(), headers=headers), timeout=60) as response:
            for line in response:
                if not line.startswith(b"data: "):
                    continue
                body = line[6:].strip()
                if body == b"[DONE]":
                    break
                packet = json.loads(body)
                if any(c.get("delta", {}).get("content") for c in packet.get("choices", [])) and first is None:
                    first = time.perf_counter() - start
        return {"success": first is not None, "ttft_seconds": first, "completion_seconds": time.perf_counter() - start}
    except Exception as error:
        return {"success": False, "error_type": type(error).__name__, "completion_seconds": time.perf_counter() - start}


def percentile(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int((len(values) - 1) * p))] if values else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--model", required=True)
    parser.add_argument("--requests", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--tokens", type=int, default=64)
    parser.add_argument("--output")
    args = parser.parse_args()
    if not 1 <= args.requests <= 1000 or not 1 <= args.concurrency <= 64:
        raise SystemExit("Use 1–1000 requests and 1–64 concurrent workers.")
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(lambda _: send(args.url, args.model, args.tokens), range(args.requests)))
    first = [r["ttft_seconds"] for r in results if r.get("ttft_seconds") is not None]
    report = {"requests": len(results), "concurrency": args.concurrency, "success_ratio": sum(r["success"] for r in results) / len(results), "ttft_p50_seconds": percentile(first, .5), "ttft_p95_seconds": percentile(first, .95), "results": results}
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))


if __name__ == "__main__":
    main()
