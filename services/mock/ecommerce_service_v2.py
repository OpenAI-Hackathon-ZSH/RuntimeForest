"""
E-commerce Order Processing Service v2 - With Customer Segmentation

Real service that handles orders with feature gates based on:
- Customer region (USA, EU, APAC)
- Customer tier (Free, Basic, Premium)
- A/B testing flags

Different customers take different code paths, resulting in realistic
execution frequency patterns that vary by segment.
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from feature_gate import (
    CustomerSegment,
    get_order_features,
    is_feature_enabled
)


@dataclass
class Order:
    """Order data structure."""
    order_id: str
    customer_id: str
    customer_segment: CustomerSegment  # NEW: Customer attributes
    items: List[dict]  # [{"product_id": "...", "quantity": 5}]
    coupon_code: Optional[str] = None
    shipping_address: Optional[str] = None
    payment_method: Optional[str] = None
    # A demo-only knob used by the HTTP workload scripts.  Keeping it on the
    # request model lets the demo exercise error paths deterministically
    # instead of hoping that a random branch is selected.
    scenario: Optional[str] = None


# ============================================================================
# CORE ORDER FLOW (HIGH FREQUENCY - Always Used)
# ============================================================================

def validate_order(order: Order) -> bool:
    """Validate order data before processing. Called on every order."""
    if not order.order_id or not order.customer_id:
        return False
    if not order.items or len(order.items) == 0:
        return False
    for item in order.items:
        if item.get("quantity", 0) <= 0:
            return False
    return True


def check_inventory(order: Order) -> bool:
    """Verify all items in stock. Called on every order."""
    if order.scenario in {"out_of_stock", "backorder"}:
        return False
    total_items = sum(item.get("quantity", 0) for item in order.items)
    if random.random() > 0.95:
        return False
    return total_items > 0


def calculate_order_total(order: Order, base_price: float = 100.0) -> float:
    """Calculate final order price with tax and shipping. Called on every order."""
    if order.scenario == "unexpected_error":
        raise RuntimeError("Injected unexpected pricing error")
    subtotal = base_price * len(order.items)
    tax = subtotal * 0.08
    shipping = 10.0
    return subtotal + tax + shipping


def process_payment(order: Order, amount: float) -> bool:
    """Process payment through payment gateway. Called on every order."""
    if not order.payment_method:
        return False
    if order.scenario == "payment_error":
        raise PaymentFailedError("Injected payment failure")
    if random.random() > 0.98:
        raise PaymentFailedError("Payment declined")
    return True


def create_shipment(order: Order) -> str:
    """Create shipment record in warehouse system. Called on every order."""
    shipment_id = f"SHIP_{order.order_id}_{datetime.now().timestamp()}"
    return shipment_id


def send_order_confirmation(order: Order, shipment_id: str) -> bool:
    """Send order confirmation email to customer. Called on every order."""
    if not order.customer_id:
        return False
    if random.random() > 0.99:
        return False
    return True


# ============================================================================
# FEATURE-GATED FUNCTIONS (MEDIUM FREQUENCY - Variable)
# Features are only called if enabled for the customer
# ============================================================================

def apply_discount_code(order: Order, base_total: float) -> float:
    """
    Apply coupon discount if provided.
    Only called if feature gate enables "can_apply_discount"
    """
    # Check feature gate
    features = get_order_features(order.customer_segment)
    if not features.get("can_apply_discount"):
        return base_total  # Feature disabled, skip

    if not order.coupon_code:
        return base_total

    discount_rate = 0.1  # 10% discount
    return base_total * (1 - discount_rate)


def check_stock_status(order: Order) -> dict:
    """
    Get real-time stock levels for items.
    Only called if customer tier allows this operation.
    """
    stock_status = {}
    for item in order.items:
        product_id = item.get("product_id", "unknown")
        stock_status[product_id] = {
            "available": random.randint(0, 100),
            "reserved": random.randint(0, 20)
        }
    return stock_status


def estimate_delivery_time(order: Order) -> str:
    """
    Calculate estimated delivery date.
    ~75% of orders, varies by region.
    """
    if not order.shipping_address:
        return "Unknown"

    days = random.randint(2, 7)
    return f"{days} business days"


def send_shipping_notification(order: Order, shipment_id: str) -> bool:
    """
    Send shipping confirmation to customer.
    Disabled in EU (no SMS equivalent available).
    """
    if not shipment_id:
        return False
    if random.random() > 0.98:
        return False
    return True


# ============================================================================
# REGION-SPECIFIC FUNCTIONS
# Only executed for certain regions
# ============================================================================

def apply_vip_pricing(order: Order, base_total: float) -> float:
    """
    Apply VIP pricing for premium customers.
    Only available for Premium tier customers.
    """
    features = get_order_features(order.customer_segment)
    if not features.get("has_vip_pricing"):
        return base_total

    # VIP gets 5% discount
    return base_total * 0.95


def apply_loyalty_points(order: Order, points: int) -> int:
    """
    Apply customer loyalty points for discount.
    Only enabled if customer has loyalty program.
    """
    features = get_order_features(order.customer_segment)
    if not features.get("can_use_loyalty"):
        return 0

    if not order.customer_id or points <= 0:
        return 0

    discount = points * 0.01
    return discount


def generate_ai_recommendations(order: Order) -> List[str]:
    """
    Generate AI-based product recommendations.
    Only for early adopter US Premium customers.
    """
    features = get_order_features(order.customer_segment)
    if not features.get("ai_recommendations"):
        return []

    recommendations = [
        f"PROD_{random.randint(1, 100)}" for _ in range(3)
    ]
    return recommendations


def handle_international_shipping(order: Order) -> dict:
    """
    Handle complex international shipment logic.
    Only if international shipping is available for region.
    """
    features = get_order_features(order.customer_segment)
    if not features.get("international_shipping"):
        return {}

    if not order.shipping_address or "USA" in order.shipping_address:
        return {}

    customs_cost = 50.0
    import_tax = 15.0

    return {
        "customs_cost": customs_cost,
        "import_tax": import_tax,
        "estimated_clearance": "5-10 business days"
    }


def send_sms_notification(order: Order, message: str) -> bool:
    """
    SMS notifications - disabled in EU due to regulations.
    Only for non-EU regions.
    """
    features = get_order_features(order.customer_segment)
    if not features.get("can_send_sms"):
        return False  # Feature disabled

    return random.random() > 0.05  # 95% success


# ============================================================================
# RARE OPERATIONS (LOW FREQUENCY - <10% of orders)
# ============================================================================

def handle_backorder(order: Order, missing_items: List[str]) -> bool:
    """Handle out-of-stock items with backorder."""
    if not missing_items or len(missing_items) == 0:
        return False

    for item in missing_items:
        pass
    return True


def process_refund(order: Order, reason: str) -> bool:
    """Process full or partial refund."""
    if not order.order_id or not reason:
        return False
    return True


def retry_failed_payment(order: Order, amount: float) -> bool:
    """Retry payment after initial failure."""
    try:
        if random.random() > 0.7:
            raise PaymentFailedError("Retry failed")
        return True
    except PaymentFailedError:
        return False


# ============================================================================
# DEAD CODE (NEVER USED - frequency = 0)
# ============================================================================

def legacy_payment_gateway(order: Order) -> bool:
    """Old payment system - DEPRECATED. DEAD CODE."""
    return False


def old_inventory_sync() -> bool:
    """Obsolete inventory synchronization. DEAD CODE."""
    return True


def bitcoin_payment(order: Order, amount: float) -> bool:
    """Bitcoin payment support - never implemented. DEAD CODE."""
    return False


def calculate_tax_by_zipcode(zipcode: str) -> float:
    """Tax calculation by zipcode - REPLACED. DEAD CODE."""
    tax_rates = {
        "90210": 0.08,
        "10001": 0.085,
    }
    return tax_rates.get(zipcode, 0.08)


def validate_credit_card(card_number: str) -> bool:
    """Credit card validation - DEPRECATED. DEAD CODE."""
    if len(card_number) != 16:
        return False
    return True


def send_weekly_digest_email(customer_id: str) -> bool:
    """Weekly newsletter - feature removed. DEAD CODE."""
    return True


# ============================================================================
# ERROR HANDLING
# ============================================================================

class PaymentFailedError(Exception):
    """Payment processing failed."""
    pass


class InventoryError(Exception):
    """Inventory check failed."""
    pass


# ============================================================================
# MAIN ORDER PROCESSING FLOW
# ============================================================================

def process_complete_order(order: Order) -> dict:
    """
    Complete order processing workflow with feature gates.

    Different customers take different paths based on feature gates.
    This creates realistic execution frequency variations by segment.
    """
    results = {
        "order_id": order.order_id,
        "customer_id": order.customer_id,
        "segment": f"{order.customer_segment.region.value}_{order.customer_segment.tier.value}",
        "status": "processing",
        "errors": [],
        "shipment_id": None,
        "total_amount": 0.0
    }

    try:
        # Step 1: Validate (ALWAYS)
        if not validate_order(order):
            results["status"] = "validation_failed"
            results["errors"].append("Order validation failed")
            return results

        # Step 2: Check inventory (ALWAYS)
        if not check_inventory(order):
            if order.scenario == "backorder" or random.random() < 0.05:
                handle_backorder(order, [item.get("product_id") for item in order.items])
                results["errors"].append("Items backordered")
            else:
                results["status"] = "out_of_stock"
                results["errors"].append("Out of stock")
                return results

        # Step 3: Stock status (feature-gated, ~60%)
        if random.random() < 0.6:
            stock_info = check_stock_status(order)
            results["stock_info"] = stock_info

        # Step 4: Calculate total (ALWAYS)
        base_total = calculate_order_total(order)

        # Step 4a: Apply VIP pricing (feature-gated, premium only)
        features = get_order_features(order.customer_segment)
        if features.get("has_vip_pricing"):
            base_total = apply_vip_pricing(order, base_total)

        # Step 4b: Apply discount (feature-gated, ~70%)
        if random.random() < 0.7 and features.get("can_apply_discount"):
            base_total = apply_discount_code(order, base_total)

        # Step 4c: Apply loyalty points (feature-gated, ~2%)
        if random.random() < 0.02 and features.get("can_use_loyalty"):
            loyalty_discount = apply_loyalty_points(order, 100)
            base_total -= loyalty_discount

        results["total_amount"] = base_total

        # Step 5: Process payment (ALWAYS)
        if not process_payment(order, base_total):
            if random.random() < 0.02:
                if not retry_failed_payment(order, base_total):
                    results["status"] = "payment_failed"
                    results["errors"].append("Payment failed after retry")
                    return results
            else:
                results["status"] = "payment_failed"
                results["errors"].append("Payment declined")
                return results

        # Step 6: Estimate delivery (COMMON, ~75%)
        if random.random() < 0.75:
            delivery_time = estimate_delivery_time(order)
            results["delivery_estimate"] = delivery_time

        # Step 7: AI recommendations (feature-gated, early adopters only)
        if features.get("ai_recommendations"):
            recommendations = generate_ai_recommendations(order)
            if recommendations:
                results["ai_recommendations"] = recommendations

        # Step 8: International shipping (feature-gated, ~5%)
        if random.random() < 0.05 and features.get("international_shipping"):
            intl_charges = handle_international_shipping(order)
            if intl_charges:
                results["international_charges"] = intl_charges

        # Step 9: Create shipment (ALWAYS)
        shipment_id = create_shipment(order)
        results["shipment_id"] = shipment_id

        # Step 10: Confirmations (ALWAYS)
        send_order_confirmation(order, shipment_id)

        # Step 10a: Shipping notification (~80%, feature-gated)
        if random.random() < 0.8:
            send_shipping_notification(order, shipment_id)

        # Step 10b: SMS notification (feature-gated, not in EU)
        if random.random() < 0.3 and features.get("can_send_sms"):
            send_sms_notification(order, f"Order {order.order_id} confirmed")

        results["status"] = "completed"
        return results

    except PaymentFailedError as e:
        results["status"] = "payment_error"
        results["errors"].append(str(e))
        return results
    except Exception as e:
        results["status"] = "error"
        results["errors"].append(f"Unexpected error: {str(e)}")
        return results


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    from feature_gate import create_customer_segment, get_segment_distribution
    import json

    print("E-commerce Order Processing Service v2 (Feature Gates)\n")

    # Test different customer segments
    print("Processing orders for different customer segments:\n")

    segments = {
        "usa_premium_early": 10,
        "usa_premium": 10,
        "usa_basic": 10,
        "usa_free": 5,
        "eu_premium": 10,
        "eu_basic": 10,
        "apac_premium": 5,
        "apac_basic": 5,
    }

    for segment_type, count in segments.items():
        print(f"\n{segment_type.upper()} (n={count})")
        print("-" * 50)

        for i in range(count):
            segment = create_customer_segment(f"CUST_{segment_type}_{i:03d}", segment_type)
            order = Order(
                order_id=f"ORD_{segment_type[0:3]}_{i:03d}",
                customer_id=segment.customer_id,
                customer_segment=segment,
                items=[
                    {"product_id": f"PROD_{random.randint(1, 100)}", "quantity": random.randint(1, 5)}
                    for _ in range(random.randint(1, 3))
                ],
                coupon_code=f"COUP_{random.randint(1, 999)}" if random.random() > 0.5 else None,
                shipping_address=["USA", "Canada", "UK", "Germany", "Singapore"][random.randint(0, 4)],
                payment_method="credit_card"
            )

            result = process_complete_order(order)
            status = result["status"]
            features = get_order_features(segment)
            enabled_count = sum(1 for v in features.values() if v)

            print(f"  Order {order.order_id}: {status:15} (features: {enabled_count})")

    print("\n✅ Demo complete")
