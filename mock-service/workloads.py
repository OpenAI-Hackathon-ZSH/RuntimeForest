"""Named, deterministic HTTP workload scripts for the mock service."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class WorkloadStep:
    name: str
    segment: str
    requests: int = 1
    interval_seconds: float = 0.05
    scenario: str | None = None
    coupon_code: str | None = "DEMO10"
    shipping_address: str | None = "USA"
    payment_method: str | None = "credit_card"
    items: tuple[dict, ...] = ({"product_id": "PROD_1", "quantity": 1},)

    def payload(self) -> dict:
        value = asdict(self)
        return {key: value[key] for key in ("segment", "scenario", "coupon_code", "shipping_address", "payment_method", "items")}


BUILTIN_SCRIPTS: dict[str, tuple[WorkloadStep, ...]] = {
    "representative": (
        WorkloadStep("US premium early adopter", "usa_premium_early", requests=5),
        WorkloadStep("EU premium, no SMS", "eu_premium", requests=5, shipping_address="Germany"),
        WorkloadStep("APAC basic restricted features", "apac_basic", requests=5, shipping_address="Singapore"),
        WorkloadStep("US free tier", "usa_free", requests=3),
    ),
    "edge_cases": (
        WorkloadStep("validation failure", "usa_basic", scenario=None, items=()),
        WorkloadStep("out of stock", "usa_basic", scenario="out_of_stock"),
        WorkloadStep("backorder", "usa_basic", scenario="backorder"),
        WorkloadStep("specific payment exception", "usa_premium", scenario="payment_error"),
        WorkloadStep("broad exception handler", "usa_premium", scenario="unexpected_error"),
    ),
}


def list_scripts() -> list[str]:
    return sorted(BUILTIN_SCRIPTS)


def load_script(name: str | None = None, path: str | None = None) -> tuple[str, tuple[WorkloadStep, ...]]:
    """Load a built-in script or JSON file with ``{name, steps}`` schema."""
    if path:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        steps = tuple(WorkloadStep(**step) for step in document["steps"])
        return str(document.get("name", Path(path).stem)), steps
    if not name or name not in BUILTIN_SCRIPTS:
        available = ", ".join(list_scripts())
        raise ValueError(f"Unknown script {name!r}. Available scripts: {available}")
    return name, BUILTIN_SCRIPTS[name]


def iter_requests(steps: tuple[WorkloadStep, ...]) -> Iterator[tuple[WorkloadStep, dict]]:
    """Yield every request in one pass of a script, in declaration order."""
    for step in steps:
        for _ in range(step.requests):
            yield step, step.payload()
