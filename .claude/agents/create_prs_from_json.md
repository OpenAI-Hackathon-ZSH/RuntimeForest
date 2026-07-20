---
name: create-prs-from-json
description: Creates pull requests for dead code (frequency=0) from instrumentation JSON
category: automation
---

# PR Creation from Instrumentation JSON

Creates focused pull requests to remove dead code identified by instrumentation data.

## Usage

```bash
/create-prs-from-json
```

Then provide JSON with instrumentation data containing nodes with frequency values.

## Input Format

The skill expects JSON with this structure:

```json
{
  "graph": {
    "nodes": [
      {
        "id": "node_123",
        "label": "function_name",
        "type": "function_entry",
        "path": "services/mock/file.py",
        "start_line": 10,
        "end_line": 25,
        "frequency": 0
      }
    ]
  },
  "summary": {
    "nodes": 1202,
    "executed_nodes": 456,
    "unseen_nodes": 746
  }
}
```

## Features

- ✅ Identifies all nodes with `frequency=0` (never executed)
- ✅ Groups related dead code for focused PRs
- ✅ Uses GPT to prioritize by risk/confidence/impact
- ✅ Generates commit messages and PR descriptions
- ✅ Creates git branches and real GitHub PRs
- ✅ Selective staging (only mock-service files)
- ✅ Deletes actual lines from source files

## Options

- `--limit N` - Create maximum N PRs (default: 10)
- `--dry-run` - Show what would be deleted without creating PRs
- `--verbose` - Show detailed debug output

## Examples

### Analyze and create PRs for dead code

```bash
/create-prs-from-json --limit 5
# Paste your instrumentation JSON
```

### Dry-run to preview changes

```bash
/create-prs-from-json --dry-run
# See what would be deleted without creating PRs
```

### Process with full verbosity

```bash
/create-prs-from-json --verbose --limit 3
```

## Output

Reports:
- Number of dead nodes found
- Groups created and prioritization scores
- PRs successfully created with URLs
- Files modified and lines deleted
- Any errors or warnings

## Integration

This skill integrates with:
- **Backend API**: `POST /trigger/cleanup?limit=N`
- **Git**: Creates branches and commits
- **GitHub**: Creates real PRs via `gh` CLI
- **GPT**: Generates commit messages and descriptions

## Safety

- Only removes code with `frequency=0` (confirmed never executed)
- Creates focused PRs per dead code group
- Selective git staging (only mock-service files)
- Full audit trail in commit messages
- Reversible via git (can revert PRs)
