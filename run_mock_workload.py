#!/usr/bin/env python3
"""Run a named mock-service workload once, for a duration, or until Ctrl-C."""

from __future__ import annotations

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from services.mock.workloads import iter_requests, list_scripts, load_script


def post_order(base_url: str, payload: dict) -> dict:
    request = Request(
        f"{base_url.rstrip('/')}/orders",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", default="representative", choices=list_scripts())
    parser.add_argument("--file", help="Custom JSON workload file; overrides --script")
    parser.add_argument("--base-url", default="http://100.58.3.145:8100/")
    parser.add_argument("--duration", type=float, help="Repeat passes until this many seconds elapse")
    parser.add_argument("--repeat", action="store_true", help="Repeat passes until interrupted (or --duration elapses)")
    parser.add_argument("--max-requests", type=int, help="Safety cap, useful with --repeat")
    parser.add_argument(
        "--interval", type=float,
        help="Override the pause between every request in seconds (for example, 2)",
    )
    args = parser.parse_args()

    name, steps = load_script(args.script, args.file)
    if args.interval is not None and args.interval < 0:
        parser.error("--interval must be zero or greater")
    deadline = time.monotonic() + args.duration if args.duration is not None else None
    repeat = args.repeat or deadline is not None
    sent = 0
    passes = 0
    print(f"Running workload '{name}' against {args.base_url}")

    try:
        while True:
            passes += 1
            for step, payload in iter_requests(steps):
                if deadline is not None and time.monotonic() >= deadline:
                    print(f"Completed {sent} requests in {passes - 1} full pass(es).")
                    return 0
                if args.max_requests is not None and sent >= args.max_requests:
                    print(f"Stopped at safety cap of {sent} requests.")
                    return 0
                response = post_order(args.base_url, payload)
                sent += 1
                status = response["result"].get("status", "unknown")
                print(f"[{sent:04d}] {step.name}: {status}")
                time.sleep(step.interval_seconds if args.interval is None else args.interval)
            if not repeat:
                print(f"Completed one pass: {sent} requests.")
                return 0
    except KeyboardInterrupt:
        print(f"\nStopped by user after {sent} requests and {passes} pass(es).")
        return 0
    except (HTTPError, URLError, TimeoutError) as error:
        print(f"Could not call mock service: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
