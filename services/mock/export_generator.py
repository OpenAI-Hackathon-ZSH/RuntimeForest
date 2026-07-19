"""Generate synthetic RuntimeSpy exports with error handling tracking"""

import random
import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional

from .code_generator import PythonCodeGenerator


@dataclass
class ExceptionEvent:
    """Track exception occurrence"""
    exception_type: str
    is_caught: bool
    caught_by_type: Optional[str] = None
    is_correct_type: bool = False
    handled_gracefully: bool = False
    frequency: int = 1


@dataclass
class ExceptionHandler:
    """Represents a try/except block"""
    handler_id: str
    exception_types: list[str]
    path: str
    start_line: int
    catches_count: int = 0
    dead_handler: bool = False


class MockExportGenerator:
    """Generate synthetic RuntimeSpy exports"""

    def __init__(self, seed: int = 42):
        self.random = random.Random(seed)
        self.seed = seed
        self.code_gen = PythonCodeGenerator(self.random)
        self.node_id_counter = 0
        self.edge_id_counter = 0

    def generate_export(
        self,
        num_files: int = 3,
        functions_per_file: int = 8,
        dead_code_percentage: float = 0.15,
        total_executions: int = 1000
    ) -> dict:
        """Generate complete RuntimeSpy-compatible export"""

        nodes = []
        edges = []
        hierarchy_files = []
        exception_events = []
        exception_handlers = []

        # Generate files
        for file_idx in range(num_files):
            file_path = f"src/module_{file_idx}.py"
            module_name = f"myapp.module_{file_idx}"

            # Module entry
            module_entry_id = self._next_node_id()
            nodes.append({
                "id": module_entry_id,
                "type": "module_entry",
                "label": module_name,
                "path": file_path,
                "module": module_name,
                "qualname": "<module>",
                "parent_id": None,
                "start_line": 1,
                "start_column": 0,
                "end_line": 999,
                "end_column": 0,
                "entry_line": 1,
                "frequency": 1,
                "source_code": "# Module initialization"
            })

            # Generate functions
            num_funcs = self.random.randint(
                max(1, functions_per_file - 2),
                functions_per_file + 2
            )

            file_functions = []
            file_node_ids = [module_entry_id]

            for func_idx in range(num_funcs):
                func_name = f"func_{file_idx}_{func_idx}"

                # Generate code
                func_code = self.code_gen.generate_function(
                    func_name,
                    self.random.randint(1, 3),
                    has_error_handling=self.random.random() > 0.3
                )

                # Function entry node
                func_entry_id = self._next_node_id()
                func_node = {
                    "id": func_entry_id,
                    "type": "function_entry",
                    "label": func_code.name,
                    "path": file_path,
                    "module": module_name,
                    "qualname": f"{module_name}.{func_code.name}",
                    "parent_id": module_entry_id,
                    "start_line": 10 + func_idx * 20,
                    "start_column": 0,
                    "end_line": 10 + func_idx * 20 + 15,
                    "end_column": 0,
                    "entry_line": 10 + func_idx * 20,
                    "frequency": 0,  # Will be set by execution patterns
                    "source_code": func_code.source,
                    "has_error_handling": func_code.has_error_handling,
                    "exception_types": func_code.exception_types,
                    "retry_logic": func_code.retry_logic
                }
                nodes.append(func_node)
                file_functions.append(func_node)
                file_node_ids.append(func_entry_id)

                # Entry edge
                edges.append({
                    "id": self._next_edge_id(),
                    "from": module_entry_id,
                    "to": func_entry_id,
                    "type": "entry",
                    "frequency": 0
                })

                # Basic block
                basic_block_id = self._next_node_id()
                nodes.append({
                    "id": basic_block_id,
                    "type": "basic_block",
                    "label": "statements",
                    "path": file_path,
                    "module": module_name,
                    "qualname": func_node["qualname"],
                    "parent_id": func_entry_id,
                    "start_line": func_node["start_line"] + 1,
                    "start_column": 4,
                    "end_line": func_node["end_line"] - 1,
                    "end_column": 0,
                    "entry_line": func_node["start_line"] + 1,
                    "frequency": 0
                })
                file_node_ids.append(basic_block_id)

                edges.append({
                    "id": self._next_edge_id(),
                    "from": func_entry_id,
                    "to": basic_block_id,
                    "type": "entry",
                    "frequency": 0
                })

                # Add conditional if appropriate
                if self.random.random() < 0.4:
                    condition_id = self._next_node_id()
                    nodes.append({
                        "id": condition_id,
                        "type": "condition",
                        "label": "if condition",
                        "path": file_path,
                        "module": module_name,
                        "qualname": func_node["qualname"],
                        "parent_id": func_entry_id,
                        "start_line": func_node["start_line"] + 5,
                        "start_column": 4,
                        "end_line": func_node["start_line"] + 5,
                        "end_column": 20,
                        "entry_line": func_node["start_line"] + 5,
                        "frequency": 0
                    })
                    file_node_ids.append(condition_id)

                    # True branch
                    true_branch_id = self._next_node_id()
                    nodes.append({
                        "id": true_branch_id,
                        "type": "branch_true",
                        "label": "if true",
                        "path": file_path,
                        "module": module_name,
                        "qualname": func_node["qualname"],
                        "parent_id": condition_id,
                        "start_line": func_node["start_line"] + 6,
                        "start_column": 8,
                        "end_line": func_node["start_line"] + 8,
                        "end_column": 0,
                        "entry_line": func_node["start_line"] + 6,
                        "frequency": 0
                    })
                    file_node_ids.append(true_branch_id)

                    edges.append({
                        "id": self._next_edge_id(),
                        "from": condition_id,
                        "to": true_branch_id,
                        "type": "true",
                        "frequency": 0
                    })

                    # False branch
                    false_branch_id = self._next_node_id()
                    nodes.append({
                        "id": false_branch_id,
                        "type": "branch_false",
                        "label": "if false",
                        "path": file_path,
                        "module": module_name,
                        "qualname": func_node["qualname"],
                        "parent_id": condition_id,
                        "start_line": func_node["start_line"] + 9,
                        "start_column": 8,
                        "end_line": func_node["start_line"] + 10,
                        "end_column": 0,
                        "entry_line": func_node["start_line"] + 9,
                        "frequency": 0
                    })
                    file_node_ids.append(false_branch_id)

                    edges.append({
                        "id": self._next_edge_id(),
                        "from": condition_id,
                        "to": false_branch_id,
                        "type": "false",
                        "frequency": 0
                    })

            # Hierarchy entry
            hierarchy_files.append({
                "path": file_path,
                "module": module_name,
                "root_node_id": module_entry_id,
                "node_ids": file_node_ids,
                "scopes": [
                    {
                        "id": f["id"],
                        "type": "function_entry",
                        "qualname": f["qualname"]
                    }
                    for f in file_functions
                ]
            })

        # Apply execution patterns (power law distribution)
        self._apply_execution_patterns(nodes, total_executions)

        # Apply dead code injection
        self._inject_dead_code(nodes, dead_code_percentage)

        # Generate exception events
        for node in nodes:
            if node.get("has_error_handling") and node.get("frequency", 0) > 0:
                events = self._generate_exception_events(node)
                exception_events.extend(events)
                handlers = self._generate_exception_handlers(node, events)
                exception_handlers.extend(handlers)

        # Build export
        export = {
            "schema_version": 2,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "final",
            "project": {"roots": ["/workspace/mock-project"]},
            "session": {
                "run_id": self.random.randint(1, 100),
                "pid": self.random.randint(10000, 99999),
                "context": "demo",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "command": "python -m myapp",
                "exit_code": 0
            },
            "summary": self._compute_summary(nodes, edges),
            "graph": {
                "schema_version": 1,
                "type": "control_flow",
                "summary": self._compute_summary(nodes, edges),
                "hierarchy": {"files": hierarchy_files},
                "nodes": nodes,
                "edges": edges
            },
            "exception_handling": {
                "exception_events": exception_events,
                "exception_handlers": exception_handlers,
                "statistics": self._compute_error_stats(exception_events, exception_handlers)
            }
        }

        return export

    def _apply_execution_patterns(self, nodes: list, total_executions: int):
        """Apply Zipf (power law) distribution to execution frequencies"""
        function_nodes = [n for n in nodes if n["type"] == "function_entry"]

        if not function_nodes:
            return

        # Zipf distribution: rank i has probability 1 / (i^1.5)
        sorted_indices = sorted(
            range(len(function_nodes)),
            key=lambda i: function_nodes[i]["label"]
        )

        zipf_values = [
            1.0 / ((i + 1) ** 1.5) for i in range(len(function_nodes))
        ]

        total_zipf = sum(zipf_values)
        probabilities = [z / total_zipf for z in zipf_values]

        for idx, prob in zip(sorted_indices, probabilities):
            function_nodes[idx]["frequency"] = max(1, int(total_executions * prob))

        # Propagate frequency to child nodes
        for node in nodes:
            if node["type"] in ["basic_block", "condition", "branch_true", "branch_false"]:
                parent = next(
                    (n for n in nodes if n["id"] == node.get("parent_id")),
                    None
                )
                if parent:
                    node["frequency"] = int(parent.get("frequency", 0) * 0.9)

    def _inject_dead_code(self, nodes: list, dead_percentage: float):
        """Mark some functions as never executed"""
        function_nodes = [
            (i, n) for i, n in enumerate(nodes)
            if n["type"] == "function_entry"
        ]

        if not function_nodes:
            return

        num_to_kill = max(1, int(len(function_nodes) * dead_percentage))
        indices_to_kill = self.random.sample(range(len(function_nodes)), num_to_kill)

        for idx in indices_to_kill:
            node_idx, node = function_nodes[idx]
            nodes[node_idx]["frequency"] = 0

            # Zero out child nodes
            for child in nodes:
                if child.get("parent_id") == node["id"]:
                    child["frequency"] = 0

    def _generate_exception_events(self, node: dict) -> list:
        """Generate exception events for a function"""
        events = []

        if not node.get("exception_types"):
            return events

        execution_count = node.get("frequency", 0)
        if execution_count == 0:
            return events

        # Simulate exceptions (5-30% of executions throw)
        exception_probability = self.random.uniform(0.05, 0.3)
        num_exceptions = max(0, int(execution_count * exception_probability))

        for _ in range(num_exceptions):
            thrown_type = self.random.choice(node.get("exception_types", ["Exception"]))
            caught_types = node.get("exception_types", ["Exception"])

            if caught_types:
                caught_type = self.random.choice(caught_types)
                is_caught = True
                is_correct_type = caught_type == thrown_type or caught_type == "Exception"
            else:
                is_caught = False
                caught_type = None
                is_correct_type = False

            events.append({
                "exception_type": thrown_type,
                "is_caught": is_caught,
                "caught_by_type": caught_type,
                "is_correct_type": is_correct_type,
                "handled_gracefully": is_caught,
                "frequency": 1
            })

        return events

    def _generate_exception_handlers(self, node: dict, events: list) -> list:
        """Generate exception handler definitions"""
        handlers = []

        if not node.get("exception_types"):
            return handlers

        for exc_type in node.get("exception_types", []):
            catches = len([e for e in events if e.get("caught_by_type") == exc_type])

            handler = {
                "handler_id": f"{node['id']}_handler_{self.random.randint(1000, 9999)}",
                "exception_types": [exc_type],
                "path": node["path"],
                "start_line": node["start_line"],
                "catches_count": catches,
                "dead_handler": catches == 0
            }
            handlers.append(handler)

        return handlers

    def _compute_error_stats(self, events: list, handlers: list) -> dict:
        """Compute error handling statistics"""
        if not events:
            return {
                "total_exceptions_thrown": 0,
                "total_exceptions_caught": 0,
                "catch_rate": 0.0,
                "wrong_exception_types": 0,
                "dead_handlers": len([h for h in handlers if h["dead_handler"]]),
                "unhandled_exception_types": []
            }

        total_thrown = len(events)
        total_caught = len([e for e in events if e.get("is_caught")])
        wrong_types = len([e for e in events if not e.get("is_correct_type") and e.get("is_caught")])
        unhandled_types = list(set(
            e["exception_type"] for e in events if not e.get("is_caught")
        ))

        return {
            "total_exceptions_thrown": total_thrown,
            "total_exceptions_caught": total_caught,
            "catch_rate": total_caught / total_thrown if total_thrown > 0 else 0.0,
            "wrong_exception_types": wrong_types,
            "dead_handlers": len([h for h in handlers if h["dead_handler"]]),
            "unhandled_exception_types": unhandled_types
        }

    def _compute_summary(self, nodes: list, edges: list) -> dict:
        """Compute graph summary statistics"""
        total_nodes = len(nodes)
        executed_nodes = len([n for n in nodes if n.get("frequency", 0) > 0])
        unseen_nodes = total_nodes - executed_nodes

        return {
            "nodes": total_nodes,
            "edges": len(edges),
            "executed_nodes": executed_nodes,
            "unseen_nodes": unseen_nodes
        }

    def _next_node_id(self) -> str:
        """Generate unique node ID"""
        self.node_id_counter += 1
        return f"node_{self.node_id_counter:020d}"

    def _next_edge_id(self) -> str:
        """Generate unique edge ID"""
        self.edge_id_counter += 1
        return f"edge_{self.edge_id_counter:020d}"
