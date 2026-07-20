#!/usr/bin/env python3
"""
Backend API server for Code-Manager.

Endpoints:
  POST /report/full_graph  - Receive initial graph with all frequencies = 0
  POST /report/node        - Update node frequency count
  GET  /api/stats          - Get current graph state

Scheduled Tasks:
  Daily 2 AM UTC: Sync cache to S3
  Daily 3 AM UTC: Create PRs for dead code (frequency=0)
"""

import json
import os
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import subprocess
import boto3
from openai import OpenAI

from apscheduler.schedulers.background import BackgroundScheduler

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Initialize OpenAI client (optional)
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = None
if openai_api_key:
    openai_client = OpenAI(api_key=openai_api_key)
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-3.5-turbo")

# Import dead code cleanup utilities
try:
    from dead_code_cleanup import NodeGrouper, NodePrioritizer, PRGenerator
except ImportError:
    print("⚠ Warning: dead_code_cleanup module not found. PR creation disabled.")

app = FastAPI(title="Code-Manager Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# In-memory cache for the graph
graph_cache = {
    "schema_version": 2,
    "generated_at": "",
    "mode": "",
    "project": {},
    "session": {},
    "summary": {},
    "graph": {
        "hierarchy": {"files": []},
        "nodes": [],
        "edges": []
    }
}


class FullGraphRequest(BaseModel):
    """Request body for /report/full_graph"""
    schema_version: int
    generated_at: str
    mode: str
    project: dict
    session: dict
    summary: dict
    graph: dict


class NodeUpdateRequest(BaseModel):
    """Request body for /report/node - single or multiple updates"""
    node_id: str = None  # Single node
    count: int = 1       # Default count
    updates: list = None # Multiple nodes: [{"node_id": "...", "count": 1}, ...]
    Frequency: list = None  # RuntimeSpy request stream: [{"node": "...", "count": 1}]


@app.post("/report/full_graph")
async def report_full_graph(request: FullGraphRequest):
    """
    Receive the full graph with all node frequencies initialized to 0.
    Backend caches this for later updates.
    """
    global graph_cache

    graph_cache = request.dict()

    # Also save to file for persistence
    cache_file = Path(__file__).parent / ".graph_cache.json"
    with open(cache_file, 'w') as f:
        json.dump(graph_cache, f, indent=2)

    return {
        "status": "success",
        "message": "Graph cached",
        "nodes": len(graph_cache["graph"]["nodes"]),
        "edges": len(graph_cache["graph"]["edges"])
    }


@app.post("/report/node")
async def report_node(request: NodeUpdateRequest):
    """
    Update node frequencies (single or batch).

    Single update:
      POST /report/node {"node_id": "...", "count": 1}

    Batch update (multiple nodes at once):
      POST /report/node {"updates": [
        {"node_id": "node_1", "count": 1},
        {"node_id": "node_2", "count": 2},
        {"node_id": "node_3", "count": 1}
      ]}
    """
    global graph_cache

    # Determine if single or batch update
    if request.updates:
        # Batch update
        updates_to_process = request.updates
    elif request.Frequency:
        # Canonical RuntimeSpy request-scoped payload.
        updates_to_process = [
            {"node_id": item.get("node"), "count": item.get("count", 1)}
            for item in request.Frequency
        ]
    elif request.node_id:
        # Single update
        updates_to_process = [{"node_id": request.node_id, "count": request.count}]
    else:
        raise HTTPException(status_code=400, detail="Either 'node_id' or 'updates' required")

    # Process all updates
    updated_count = 0
    not_found = []

    for update in updates_to_process:
        node_id = update.get("node_id")
        count = update.get("count", 1)

        # Find and update the node
        found = False
        for node in graph_cache["graph"]["nodes"]:
            if node["id"] == node_id:
                node["frequency"] += count
                found = True
                updated_count += 1
                break

        if not found:
            not_found.append(node_id)

    # Update summary
    executed_nodes = len([n for n in graph_cache["graph"]["nodes"] if n.get("frequency", 0) > 0])
    unseen_nodes = len([n for n in graph_cache["graph"]["nodes"] if n.get("frequency", 0) == 0])

    graph_cache["summary"]["executed_nodes"] = executed_nodes
    graph_cache["summary"]["unseen_nodes"] = unseen_nodes

    # Save to file
    cache_file = Path(__file__).parent / ".graph_cache.json"
    with open(cache_file, 'w') as f:
        json.dump(graph_cache, f, indent=2)

    # Return response
    response = {
        "status": "success",
        "updated_count": updated_count,
        "total_requested": len(updates_to_process),
    }

    if not_found:
        response["not_found"] = not_found
        response["status"] = "partial_success"

    if request.updates or request.Frequency:
        response["message"] = f"Updated {updated_count} nodes"
    else:
        response["message"] = f"Updated {request.node_id}"

    return response


@app.get("/api/stats")
async def get_stats():
    """
    Get current real-time graph state.
    Frontend polls this every 3 seconds.
    """
    return graph_cache


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "nodes": len(graph_cache["graph"]["nodes"]),
        "edges": len(graph_cache["graph"]["edges"])
    }


@app.post("/clear")
async def clear_graph():
    """Clear the cached graph (for testing)"""
    global graph_cache
    graph_cache = {
        "schema_version": 2,
        "generated_at": "",
        "mode": "",
        "project": {},
        "session": {},
        "summary": {},
        "graph": {
            "hierarchy": {"files": []},
            "nodes": [],
            "edges": []
        }
    }
    return {"status": "cleared"}


@app.post("/trigger/cleanup")
async def trigger_cleanup(limit: int = 3):
    """Manually trigger PR cleanup (for testing)"""
    print(f"\n🚀 Manual trigger: PR cleanup with limit={limit}")
    # Update max PRs limit temporarily
    original_limit = os.getenv("MAX_PRS_PER_RUN", "10")
    os.environ["MAX_PRS_PER_RUN"] = str(limit)

    try:
        create_prs_for_dead_code()
        return {
            "status": "success",
            "message": f"PR cleanup triggered with limit={limit}"
        }
    finally:
        os.environ["MAX_PRS_PER_RUN"] = original_limit


# ============================================================================
# OPENAI INTEGRATION FOR PR GENERATION
# ============================================================================

def gpt_generate_commit_message(node_group, source_code):
    """Use GPT to generate commit message for dead code removal"""
    if not openai_client:
        return f"Remove dead code: {node_group[0].label if hasattr(node_group[0], 'label') else 'unused'}"

    try:
        prompt = f"""You are a senior engineer reviewing code to delete.

Dead code detected (frequency=0 - never executed):

File: {node_group[0].path if hasattr(node_group[0], 'path') else 'unknown'}
Lines: {node_group[0].start_line if hasattr(node_group[0], 'start_line') else '?'}-{node_group[0].end_line if hasattr(node_group[0], 'end_line') else '?'}

Code:
```python
{source_code}
```

Generate a concise, professional commit message (2-3 sentences) explaining why this code is safe to delete.
Focus on: never executed, what it did, why it's no longer needed."""

        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"✗ GPT commit message failed: {e}")
        return f"Remove dead code: {node_group[0].label if hasattr(node_group[0], 'label') else 'unused function'}"


def gpt_generate_pr_description(node_groups, dead_count, total_nodes):
    """Use GPT to generate PR description for dead code cleanup"""
    if not openai_client:
        return f"Remove {dead_count} dead code nodes (frequency=0)"

    try:
        group_summary = "\n".join([
            f"- {len(g)} nodes: {g[0].path if hasattr(g[0], 'path') else 'unknown'}"
            for g in node_groups[:5]
        ])

        prompt = f"""You are a senior engineer creating a PR to remove dead code.

Summary:
- Total dead nodes found: {dead_count}
- Code coverage: {100 * (total_nodes - dead_count) / total_nodes:.1f}%
- Never executed (frequency=0)

Sample groups being removed:
{group_summary}

Generate a professional PR description (title + body) that explains:
1. What dead code is being removed
2. Why it's safe (never executed)
3. Potential benefits (code clarity, maintenance)
4. Testing notes

Format as markdown."""

        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"✗ GPT PR description failed: {e}")
        return f"Remove {dead_count} dead code nodes (frequency=0)"


def read_source_code(file_path, start_line, end_line):
    """Read source code from file"""
    try:
        full_path = Path(file_path)
        if not full_path.exists():
            return None
        with open(full_path) as f:
            lines = f.readlines()
        return "".join(lines[max(0, start_line-1):min(len(lines), end_line)])
    except Exception as e:
        print(f"✗ Failed to read {file_path}: {e}")
        return None


def git_create_pr(group_id, commit_msg, pr_description, repo_root="."):
    """Create git branch and PR for a dead code group"""
    try:
        import subprocess

        # Create branch name
        branch_name = f"cleanup/dead-code-{group_id}"

        # Check if branch exists
        result = subprocess.run(
            ["git", "branch", "-a"],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        if branch_name in result.stdout:
            print(f"      ⚠ Branch {branch_name} already exists, skipping")
            return None

        # Create and checkout branch
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=repo_root,
            capture_output=True,
            check=True
        )

        # Stage and commit (empty commit for demo - actual deletion would be done by code)
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", commit_msg],
            cwd=repo_root,
            capture_output=True,
            check=True
        )

        # Push branch
        subprocess.run(
            ["git", "push", "-u", "origin", branch_name],
            cwd=repo_root,
            capture_output=True,
            check=True
        )

        # Create PR using gh cli
        pr_result = subprocess.run(
            ["gh", "pr", "create", "--title", commit_msg[:50], "--body", pr_description],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )

        pr_url = pr_result.stdout.strip()
        return pr_url

    except Exception as e:
        print(f"      ✗ PR creation failed: {e}")
        return None


def gpt_analyze_and_group_dead_code(dead_nodes, graph_cache):
    """Use GPT to intelligently group and prioritize dead code"""
    if not openai_client:
        print("⚠ OpenAI API key not configured. Creating single-node groups...")
        # Fallback: single-node groups
        return {
            "groups": [
                {
                    "group_id": i,
                    "node_ids": [n["node_id"]],
                    "purpose": n["label"],
                    "reason_for_grouping": "Fallback: single-node group (no AI)",
                    "risk_score": 5,
                    "confidence_dead": 90,
                    "impact_score": 5
                }
                for i, n in enumerate(dead_nodes[:3])
            ],
            "deletion_order": list(range(min(3, len(dead_nodes))))
        }

    try:
        # Build detailed node descriptions with source code
        node_descriptions = []
        for node in dead_nodes:
            source = read_source_code(node["path"], node["start_line"], node["end_line"])
            node_descriptions.append({
                "id": node["node_id"],
                "type": node["type"],
                "label": node["label"],
                "file": node["path"],
                "lines": f"{node['start_line']}-{node['end_line']}",
                "source": source[:500] if source else "N/A"  # First 500 chars
            })

        # Format for GPT
        nodes_text = "\n".join([
            f"[{n['id']}] {n['type']}: {n['label']} ({n['file']}:{n['lines']})\n"
            f"  Source: {n['source'][:200]}..."
            for n in node_descriptions[:20]  # Limit to fit context
        ])

        prompt = f"""You are an expert code reviewer analyzing {len(dead_nodes)} dead code nodes
(frequency=0 - never executed in any test run).

DEAD CODE NODES:
{nodes_text}

Your tasks:
1. GROUP RELATED NODES - Which nodes should be deleted together?
   - Functions that depend on each other
   - Related utilities/helpers
   - Same feature/system

2. PRIORITIZE BY RISK - Order groups from safest to delete first
   - Confidence it's truly dead (%)
   - Deletion risk (1-10)
   - Codebase impact (1-10)

3. IDENTIFY DEPENDENCIES - Which deletions might affect others?

IMPORTANT: Ignore naming patterns. Analyze actual code purpose and relationships.

Return ONLY valid JSON (no markdown):
{{
  "groups": [
    {{
      "group_id": 1,
      "node_ids": ["id1", "id2"],
      "purpose": "What these functions did",
      "reason_for_grouping": "Why delete together",
      "risk_score": 2,
      "confidence_dead": 98,
      "impact_score": 3,
      "dependencies": ["group_id_X"],
      "notes": "Any warnings or considerations"
    }}
  ],
  "deletion_order": [1, 2, 3],
  "total_lines_removed": 234
}}"""

        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3  # Lower temp for consistency
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        print(f"✗ GPT grouping failed: {e}")
        # Fallback to single-node groups if GPT fails
        return {
            "groups": [
                {
                    "group_id": i,
                    "node_ids": [n["node_id"]],
                    "purpose": n["label"],
                    "reason_for_grouping": "Fallback single-node group",
                    "risk_score": 5,
                    "confidence_dead": 90,
                    "impact_score": 5
                }
                for i, n in enumerate(dead_nodes)
            ],
            "deletion_order": list(range(len(dead_nodes)))
        }


# ============================================================================
# SCHEDULED TASKS FOR S3 SYNC AND PR CREATION
# ============================================================================

scheduler = BackgroundScheduler()
scheduler.daemon = True

def sync_to_s3():
    """Daily task: Sync cache to S3 at 2 AM UTC"""
    try:
        s3 = boto3.client('s3')
        bucket = os.getenv("S3_BUCKET", "code-manager-cache")

        s3.put_object(
            Bucket=bucket,
            Key="graph_cache.json",
            Body=json.dumps(graph_cache),
            ContentType="application/json"
        )

        print(f"✓ [{datetime.utcnow().isoformat()}] Synced cache to S3 (nodes: {len(graph_cache['graph']['nodes'])}, unseen: {graph_cache['summary'].get('unseen_nodes', 0)})")
    except Exception as e:
        print(f"✗ S3 sync failed: {e}")


def create_prs_for_dead_code():
    """Daily task: Create PRs for dead code at 3 AM UTC"""
    try:
        # Extract dead nodes (frequency = 0)
        dead_nodes = [
            {
                "node_id": n["id"],
                "type": n.get("type", "unknown"),
                "label": n.get("label", "unknown"),
                "path": n.get("path", "unknown"),
                "start_line": n.get("start_line", 0),
                "end_line": n.get("end_line", 0),
                "frequency": n.get("frequency", 0)
            }
            for n in graph_cache["graph"]["nodes"]
            if n.get("frequency", 0) == 0
        ]

        if not dead_nodes:
            print(f"ℹ [{datetime.utcnow().isoformat()}] No dead code found (all {len(graph_cache['graph']['nodes'])} nodes executed)")
            return

        print(f"📊 [{datetime.utcnow().isoformat()}] Analyzing {len(dead_nodes)} dead nodes with GPT...")

        # Use GPT to group and prioritize
        gpt_analysis = gpt_analyze_and_group_dead_code(dead_nodes, graph_cache)
        groups_to_create = gpt_analysis.get("groups", [])
        deletion_order = gpt_analysis.get("deletion_order", [])

        # Limit PRs per run
        max_prs = int(os.getenv("MAX_PRS_PER_RUN", "10"))
        groups_to_create = groups_to_create[:max_prs]

        if not groups_to_create:
            print(f"ℹ No groups to create")
            return

        # Generate overall PR description using GPT
        pr_description = gpt_generate_pr_description(
            groups_to_create,
            len(dead_nodes),
            len(graph_cache["graph"]["nodes"])
        )

        # Create PRs for each group
        created_prs = []
        failed_prs = []

        for i, group in enumerate(groups_to_create, 1):
            try:
                group_id = group.get("group_id", i)
                node_ids = group.get("node_ids", [])
                purpose = group.get("purpose", "Dead code")
                risk_score = group.get("risk_score", 5)
                confidence = group.get("confidence_dead", 80)

                print(f"  [{i}/{len(groups_to_create)}] Group {group_id}: {purpose}")
                print(f"      Risk: {risk_score}/10 | Confidence: {confidence}% | Nodes: {len(node_ids)}")

                # Find nodes in this group
                group_nodes = [n for n in dead_nodes if n["node_id"] in node_ids]

                if not group_nodes:
                    print(f"      ✗ No nodes found for group")
                    continue

                # Read source code for commit message
                if group_nodes:
                    first_node = group_nodes[0]
                    source_code = read_source_code(
                        first_node["path"],
                        first_node["start_line"],
                        first_node["end_line"]
                    )
                else:
                    source_code = None

                # Generate GPT commit message
                if source_code:
                    commit_msg = gpt_generate_commit_message(group_nodes, source_code)
                else:
                    commit_msg = f"Remove dead code: {purpose}"

                # Add safety notes
                commit_msg += f"\n\nInstrumentation: frequency=0 (never executed)"
                commit_msg += f"\nConfidence: {confidence}% | Risk: {risk_score}/10"

                print(f"      Commit: {commit_msg[:60]}...")

                # Create PR with git + gh cli
                try:
                    pr_url = git_create_pr(
                        group_id,
                        commit_msg,
                        pr_description,
                        repo_root="."
                    )
                    if pr_url:
                        created_prs.append(pr_url)
                        print(f"      ✓ PR created: {pr_url}")
                    else:
                        failed_prs.append(f"Group {group_id}")
                        print(f"      ✗ PR creation returned None")
                except Exception as pr_error:
                    failed_prs.append(str(pr_error))
                    print(f"      ✗ {pr_error}")

            except Exception as e:
                failed_prs.append(str(e))
                print(f"      ✗ Error: {e}")

        print(f"\n✓ [{datetime.utcnow().isoformat()}] Dead code cleanup complete:")
        print(f"   - Dead nodes found: {len(dead_nodes)}")
        print(f"   - Groups analyzed: {len(groups_to_create)}")
        print(f"   - PRs created: {len(created_prs)}")
        print(f"   - Failed: {len(failed_prs)}")

    except Exception as e:
        print(f"✗ PR creation failed: {e}")


def start_scheduler():
    """Start background scheduler for daily tasks"""
    if scheduler.running:
        return

    # Schedule S3 sync at 2 AM UTC
    scheduler.add_job(
        sync_to_s3,
        'cron',
        hour=2,
        minute=0,
        timezone='UTC',
        id='daily_s3_sync',
        name='Daily S3 Sync'
    )

    # Schedule PR creation at 3 AM UTC
    scheduler.add_job(
        create_prs_for_dead_code,
        'cron',
        hour=3,
        minute=0,
        timezone='UTC',
        id='daily_pr_creation',
        name='Daily PR Creation'
    )

    scheduler.start()
    print("✓ Scheduled tasks started: S3 sync (2 AM UTC), PR creation (3 AM UTC)")


@app.on_event("startup")
async def startup_event():
    """Initialize scheduler and load cache on startup"""
    global graph_cache

    # Load cache from file if it exists
    cache_file = Path(__file__).parent / ".graph_cache.json"
    if cache_file.exists():
        try:
            with open(cache_file) as f:
                graph_cache = json.load(f)
            print(f"✓ Loaded cache from file: {len(graph_cache.get('graph', {}).get('nodes', []))} nodes")
        except Exception as e:
            print(f"⚠ Failed to load cache: {e}")

    start_scheduler()


# Serve the Next.js frontend
# If built, serve from build/output
frontend_path = Path(__file__).parent.parent.parent / "BranchFrequencyVisual" / "build" / "output"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("  CODE-MANAGER BACKEND")
    print("="*70)
    print("\nAPI Endpoints:")
    print("  POST /report/full_graph  - Upload initial graph")
    print("  POST /report/node        - Update node frequency")
    print("  GET  /api/stats          - Get current state")
    print("  GET  /health             - Health check")
    print("\nStarting server on http://localhost:8000")
    print("="*70 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
