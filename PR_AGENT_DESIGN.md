# PR Agent Design - Dead Code Cleanup Automation

## Overview

A long-running service that automatically creates PRs to delete dead code (frequency=0 nodes) based on instrumentation data.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PR AGENT SERVICE                          │
│                    (Port 8200)                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ HTTP Endpoints                                       │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ POST /analyze          → Process instrumentation    │   │
│  │ POST /cleanup          → Trigger cleanup run        │   │
│  │ GET  /status           → Service status             │   │
│  │ GET  /history          → Past PR runs               │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ↓                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Processing Pipeline                                 │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ 1. Parse JSON (graph with nodes/edges)             │   │
│  │ 2. Extract dead nodes (frequency = 0)              │   │
│  │ 3. Group related nodes                             │   │
│  │ 4. Prioritize by impact (size, type, naming)       │   │
│  │ 5. Create PRs (git + gh cli)                        │   │
│  │ 6. Log results                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ↓                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ State Management                                    │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ • Processed PR runs (avoid duplicates)             │   │
│  │ • PR creation history                              │   │
│  │ • Error tracking                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         ↑                                        ↓
      Backend                                  GitHub
    (Port 8000)                              (repo PRs)
   POSTs JSON                              Creates branches
```

## Key Design Decisions

### 1. Processing Flow
- Receive JSON with full graph + execution data
- Identify frequency=0 nodes (dead code)
- Group by file/function to create focused PRs
- Score by importance: size + type + naming patterns
- Create one PR per group

### 2. State Tracking
- Store run history (hash of processed data)
- Track created PR URLs
- Prevent duplicate PRs for same dead code

### 3. PR Strategy
- One focused PR per dead code group
- Auto-generated commit messages with stats
- Branch naming: `cleanup/dead-code-{timestamp}`
- Include safety note: "frequency=0, never executed"

### 4. Batch Processing
- Can create multiple PRs in one run
- Limit PRs per run (configurable)
- Return summary of created/failed PRs

### 5. Error Handling
- Retry logic for flaky git operations
- Graceful handling of repo lock
- Return detailed error messages

## API Endpoints

### POST /analyze
Receive instrumentation data and create PRs for dead code.

**Request**:
```json
{
  "graph": {
    "nodes": [...],
    "edges": [...]
  },
  "summary": {
    "nodes": 1202,
    "executed_nodes": 456,
    "unseen_nodes": 746
  },
  "limit": 5
}
```

**Response**:
```json
{
  "status": "success",
  "dead_nodes_found": 15,
  "prs_created": 5,
  "prs_failed": 0,
  "prs": [
    {
      "title": "Remove dead code: legacy_payment_gateway",
      "url": "https://github.com/.../pull/123"
    }
  ]
}
```

### POST /cleanup
Trigger a cleanup run (optional - for scheduled tasks).

### GET /status
Service health and current activity status.

### GET /history
View past PR runs and creation history.

## Components

1. **InstrumentationReader** - Parse JSON input
2. **DeadNodeExtractor** - Find frequency=0 nodes
3. **NodeGrouper** - Group related nodes
4. **NodePrioritizer** - Score and sort by importance
5. **PRGenerator** - Create branches and PRs
6. **StateManager** - Track processed runs
7. **ErrorHandler** - Graceful failure handling

## Implementation Phases

### Phase 1: Basic Agent
- HTTP endpoint to receive JSON
- Dead code extraction and grouping
- PR creation for single nodes
- Basic error handling

### Phase 2: State & History
- Duplicate detection
- Run history tracking
- PR link storage
- Deduplication logic

### Phase 3: Optimization
- Batch processing improvements
- Better prioritization
- Performance tuning
- Monitoring/alerts

## Configuration

```yaml
pr_agent:
  port: 8200
  repo_root: "."
  github_repo: "OpenAI-Hackathon-ZSH/RuntimeForest"
  max_prs_per_run: 10
  branch_prefix: "cleanup/dead-code"
  commit_author: "Claude PR Agent"
```

## State Models

### Run Record
```python
{
  "id": "uuid",
  "timestamp": "2026-07-19T00:00:00Z",
  "data_hash": "sha256_of_graph",
  "dead_nodes_count": 15,
  "prs_created": [
    {
      "title": "...",
      "url": "...",
      "nodes": 3
    }
  ],
  "status": "success|failed",
  "errors": []
}
```

## Safety Guarantees

- ✅ Only removes code with frequency = 0
- ✅ Confirmed never executed during instrumentation
- ✅ Each PR focused on related dead code
- ✅ Detailed commit messages with stats
- ✅ Safe to review and merge independently
