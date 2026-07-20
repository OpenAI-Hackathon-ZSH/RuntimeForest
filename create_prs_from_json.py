#!/usr/bin/env python3
"""
Claude Code Skill: Create PRs from instrumentation JSON

Reads JSON output from instrumentation and creates pull requests
to remove dead code (frequency=0).

Usage:
  python3 create_prs_from_json.py [--limit N] [--dry-run] [--verbose] [INPUT_FILE]

  Without INPUT_FILE, reads from stdin.
"""

import argparse
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create PRs for dead code from instrumentation JSON"
    )
    parser.add_argument("input_file", nargs="?", help="JSON file to read (stdin if omitted)")
    parser.add_argument("--limit", type=int, default=10, help="Max PRs to create")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating PRs")
    parser.add_argument("--verbose", action="store_true", help="Show debug output")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000",
                       help="Backend URL for PR creation")
    return parser.parse_args()


def read_json_input(input_file):
    """Read JSON from file or stdin."""
    if input_file:
        with open(input_file) as f:
            return json.load(f)
    else:
        return json.load(sys.stdin)


def extract_dead_nodes(data):
    """Extract all nodes with frequency=0."""
    nodes = data.get("graph", {}).get("nodes", [])
    dead_nodes = [n for n in nodes if n.get("frequency", 0) == 0]
    return dead_nodes


def trigger_backend_pr_creation(backend_url, limit, dry_run=False):
    """Trigger PR creation via backend API."""
    try:
        endpoint = "trigger/cleanup"
        if dry_run:
            endpoint += "?dry-run=true"

        url = f"{backend_url.rstrip('/')}/{endpoint}?limit={limit}"
        request = Request(url, method="POST")
        request.add_header("Content-Type", "application/json")

        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as e:
        print(f"✗ Backend error: {e}")
        return None


def preview_dead_code(dead_nodes, limit):
    """Show preview of what would be deleted."""
    print(f"\n📊 DEAD CODE ANALYSIS")
    print(f"   Total dead nodes: {len(dead_nodes)}")
    print(f"   Will create PRs for: {min(len(dead_nodes), limit)} groups")

    # Group by file
    by_file = {}
    for node in dead_nodes[:limit]:
        path = node.get("path", "unknown")
        if path not in by_file:
            by_file[path] = []
        by_file[path].append(node)

    print(f"\n📁 FILES AFFECTED:")
    for path, nodes in sorted(by_file.items()):
        line_ranges = ", ".join([
            f"{n.get('start_line', 0)}-{n.get('end_line', 0)}"
            for n in nodes
        ])
        print(f"   {path}")
        print(f"      Lines: {line_ranges}")
        print(f"      Nodes: {len(nodes)}")


def main() -> int:
    args = parse_args()

    print("🚀 Claude PR Creation Skill")
    print("=" * 60)

    # Read JSON
    try:
        if args.verbose:
            print("Reading JSON input...")
        data = read_json_input(args.input_file)
    except FileNotFoundError as e:
        print(f"✗ File not found: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {e}")
        return 1

    # Extract dead nodes
    dead_nodes = extract_dead_nodes(data)
    print(f"\n✓ Found {len(dead_nodes)} dead nodes (frequency=0)")

    if not dead_nodes:
        print("  Nothing to clean up!")
        return 0

    # Preview
    preview_dead_code(dead_nodes, args.limit)

    # Trigger backend
    if args.dry_run:
        print(f"\n📋 DRY RUN MODE - No PRs will be created")
        return 0

    print(f"\n🔄 Connecting to backend at {args.backend_url}...")
    result = trigger_backend_pr_creation(args.backend_url, args.limit)

    if result:
        print(f"\n✅ SUCCESS")
        print(f"   Status: {result.get('status')}")
        print(f"   Message: {result.get('message')}")
        if args.verbose:
            print(f"   Response: {json.dumps(result, indent=2)}")
        return 0
    else:
        print(f"\n✗ FAILED - Could not create PRs")
        return 1


if __name__ == "__main__":
    sys.exit(main())
