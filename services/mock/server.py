#!/usr/bin/env python3
"""HTTP mock service used by the repeatable runtime-evidence demo."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

from services.mock.ecommerce_service_v2 import Order, process_complete_order
from services.mock.feature_gate import create_customer_segment


app = FastAPI(title="Code-Manager Mock Commerce Service", version="1.0.0")
request_count = 0


instrumentation_enabled = False


@app.on_event("startup")
def start_runtime_instrumentation() -> None:
    """Enable RuntimeSpy only when the demo explicitly requests it."""
    global instrumentation_enabled
    if os.getenv("CODE_MANAGER_INSTRUMENT") != "1":
        return
    try:
        import runtimespy

        runtimespy.init(
            source=["services/mock"],
            skip_modules=["runtimespy.*", "services.mock.server", "services.mock.workloads"],
            project_root=Path.cwd(),
            context="mock_http_service",
            report=False,
            endpoint=os.getenv("CODE_MANAGER_BACKEND_URL", "http://127.0.0.1:8000"),
            serve_export=False,
        )
        instrumentation_enabled = True
        print("RuntimeSpy enabled: publishing request-scoped RuntimeSpy counts")
    except Exception as error:
        print(f"RuntimeSpy disabled: {error}")


@app.middleware("http")
async def publish_request_evidence(request, call_next):
    """FastAPI adapter for the remote RuntimeSpy request-boundary API."""
    trace = None
    if instrumentation_enabled and request.url.path == "/orders":
        import runtimespy
        trace = runtimespy.begin_request()
    try:
        return await call_next(request)
    finally:
        if trace is not None:
            runtimespy.end_request(trace)


class OrderRequest(BaseModel):
    """A single request sent by a workload script."""

    segment: str = Field(description="e.g. usa_premium_early or eu_basic")
    items: list[dict] = Field(default_factory=lambda: [{"product_id": "PROD_1", "quantity": 1}])
    coupon_code: str | None = "DEMO10"
    shipping_address: str | None = "USA"
    payment_method: str | None = "credit_card"
    scenario: str | None = Field(
        default=None,
        description="Optional deterministic path: out_of_stock, backorder, payment_error, unexpected_error",
    )


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "requests_processed": request_count}


@app.post("/orders")
def create_order(payload: OrderRequest) -> dict:
    """Process one real HTTP request through the feature-gated service."""
    global request_count
    request_count += 1
    request_id = uuid4().hex[:12]
    segment = create_customer_segment(f"CUST_{request_id}", payload.segment)
    order = Order(
        order_id=f"ORD_{request_id}",
        customer_id=segment.customer_id,
        customer_segment=segment,
        items=payload.items,
        coupon_code=payload.coupon_code,
        shipping_address=payload.shipping_address,
        payment_method=payload.payment_method,
        scenario=payload.scenario,
    )
    result = process_complete_order(order)
    return {"request_number": request_count, "scenario": payload.scenario, "result": result}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8100)
