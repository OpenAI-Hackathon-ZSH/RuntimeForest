#!/usr/bin/env python3
"""
Backend API server for Code-Manager.

Endpoints:
  POST /report/full_graph  - Receive initial graph with all frequencies = 0
  POST /report/node        - Update node frequency count
  GET  /api/stats          - Get current graph state
"""

import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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


@app.post("/reset")
async def reset_graph_frequencies():
    """Keep the current graph structure and reset every node frequency to zero."""
    global graph_cache

    nodes = graph_cache["graph"]["nodes"]
    for node in nodes:
        node["frequency"] = 0

    graph_cache["summary"]["executed_nodes"] = 0
    graph_cache["summary"]["unseen_nodes"] = len(nodes)

    cache_file = Path(__file__).parent / ".graph_cache.json"
    with open(cache_file, 'w') as f:
        json.dump(graph_cache, f, indent=2)

    return {
        "status": "reset",
        "nodes_reset": len(nodes),
    }


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
    print("  POST /reset              - Reset node frequencies to zero")
    print("\nStarting server on http://localhost:8000")
    print("="*70 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
