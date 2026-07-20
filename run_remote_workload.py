#!/usr/bin/env python3
"""Run mock-service workload against remote demo service."""

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def post_order(base_url: str, payload: dict) -> dict:
    """Send POST request to /orders endpoint."""
    request = Request(
        f"{base_url.rstrip('/')}/orders",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def generate_workload(workload_type: str = "representative"):
    """Generate test workload payloads."""
    workloads = {
        "simple": [
            {"segment": "USA_Premium_Early", "items": [{"product_id": "PROD_1", "quantity": 1}]},
        ],
        "representative": [
            {"segment": "USA_Premium_Early", "items": [{"product_id": "PROD_1", "quantity": 1}]},
            {"segment": "USA_Premium", "items": [{"product_id": "PROD_2", "quantity": 2}]},
            {"segment": "EU_Premium", "items": [{"product_id": "PROD_3", "quantity": 1}]},
            {"segment": "APAC_Basic", "items": [{"product_id": "PROD_1", "quantity": 3}]},
        ],
        "stress": [
            {"segment": f"segment_{i}", "items": [{"product_id": f"PROD_{i}", "quantity": (i % 5) + 1}]}
            for i in range(20)
        ],
        "error_injection": [
            {"segment": "USA_Premium_Early", "scenario": "payment_error"},
            {"segment": "USA_Premium", "scenario": "out_of_stock"},
            {"segment": "EU_Premium", "scenario": "unexpected_error"},
        ],
    }
    return workloads.get(workload_type, workloads["representative"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workload", default="representative",
                       choices=["simple", "representative", "stress", "error_injection"],
                       help="Workload type to run")
    parser.add_argument("--base-url", default="http://100.58.3.145:8100",
                       help="Base URL of mock service")
    parser.add_argument("--duration", type=float, help="Run for N seconds")
    parser.add_argument("--repeat", action="store_true", help="Repeat until Ctrl-C or duration")
    parser.add_argument("--max-requests", type=int, help="Stop after N requests")
    parser.add_argument("--interval", type=float, default=0.5, help="Pause between requests (seconds)")
    args = parser.parse_args()

    workload = generate_workload(args.workload)
    deadline = time.monotonic() + args.duration if args.duration else None
    repeat = args.repeat or deadline is not None
    sent = 0
    passes = 0

    print(f"🚀 Running '{args.workload}' workload against {args.base_url}")
    print(f"   Requests per pass: {len(workload)}")
    if args.max_requests:
        print(f"   Max requests: {args.max_requests}")
    if deadline:
        print(f"   Duration: {args.duration}s")
    print()

    try:
        while True:
            passes += 1
            for i, payload in enumerate(workload):
                if deadline and time.monotonic() >= deadline:
                    print(f"\n✓ Duration limit reached: {sent} requests in {passes - 1} pass(es)")
                    return 0
                if args.max_requests and sent >= args.max_requests:
                    print(f"\n✓ Max requests reached: {sent} requests")
                    return 0

                try:
                    response = post_order(args.base_url, payload)
                    status = response.get("result", {}).get("status", "unknown")
                    sent += 1
                    print(f"[{sent:04d}] Pass {passes}, Request {i+1}: {status} | {payload['segment']}")
                except (HTTPError, URLError, TimeoutError) as e:
                    print(f"[{sent + 1:04d}] ✗ Error: {e}")
                    return 1

                time.sleep(args.interval)

            if not repeat:
                print(f"\n✓ Completed one pass: {sent} requests")
                return 0

    except KeyboardInterrupt:
        print(f"\n✓ Stopped by user: {sent} requests in {passes} pass(es)")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
