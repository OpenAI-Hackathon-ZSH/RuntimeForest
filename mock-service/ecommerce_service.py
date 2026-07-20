"""
E-commerce Order Processing Service

Real service that handles complete order workflow:
1. Order validation
2. Inventory check
3. Payment processing
4. Shipment creation
5. Notifications

This service naturally demonstrates:
- High frequency: core order flow
- Medium frequency: common features
- Low frequency: rare operations
- Dead code: deprecated methods
- Error handling: payment failures, stock issues
- Complex logic: interconnected methods
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
import random


@dataclass
class Order:
    """Order data structure."""
    order_id: str
    customer_id: str
    items: List[dict]  # [{"product_id": "...", "quantity": 5}]
    coupon_code: Optional[str] = None
    shipping_address: Optional[str] = None
    payment_method: Optional[str] = None


# ============================================================================
# CORE ORDER FLOW (HIGH FREQUENCY - Always Used)
# ============================================================================

def validate_order(order: Order) -> bool:
    """
    Validate order data before processing.
    Called on every order.
    """
    if not order.order_id or not order.customer_id:
        return False
    if not order.items or len(order.items) == 0:
        return False
    for item in order.items:
        if item.get("quantity", 0) <= 0:
            return False
    return True


def check_inventory(order: Order) -> bool:
    """
    Verify all items in stock.
    Called on every order.
    """
    total_items = sum(item.get("quantity", 0) for item in order.items)
    # Simulate: 95% of orders have items in stock
    if random.random() > 0.95:
        return False
    return total_items > 0


def calculate_order_total(order: Order, base_price: float = 100.0) -> float:
    """
    Calculate final order price with tax and shipping.
    Called on every order.
    """
    subtotal = base_price * len(order.items)
    tax = subtotal * 0.08  # 8% tax
    shipping = 10.0
    return subtotal + tax + shipping


def process_payment(order: Order, amount: float) -> bool:
    """
    Process payment through payment gateway.
    Called on every order.
    """
    if not order.payment_method:
        return False
    # Simulate: 98% success rate
    if random.random() > 0.98:
        raise PaymentFailedError("Payment declined")
    return True


def create_shipment(order: Order) -> str:
    """
    Create shipment record in warehouse system.
    Called on every order.
    """
    shipment_id = f"SHIP_{order.order_id}_{datetime.now().timestamp()}"
    # Simulate warehouse pickup
    return shipment_id


def send_order_confirmation(order: Order, shipment_id: str) -> bool:
    """
    Send order confirmation email to customer.
    Called on every order.
    """
    if not order.customer_id:
        return False
    # Simulate email send: 99% success
    if random.random() > 0.99:
        return False
    return True


# ============================================================================
# COMMON FEATURES (MEDIUM FREQUENCY - ~50% of orders)
# ============================================================================

def apply_discount_code(order: Order, base_total: float) -> float:
    """
    Apply coupon discount if provided.
    ~70% of orders use coupon codes.
    """
    if not order.coupon_code:
        return base_total

    # Simulate different coupon values
    discount_rate = 0.1  # 10% discount
    return base_total * (1 - discount_rate)


def check_stock_status(order: Order) -> dict:
    """
    Get real-time stock levels for items.
    Called when inventory check needed.
    ~60% of orders.
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
    ~75% of orders need delivery estimate.
    """
    if not order.shipping_address:
        return "Unknown"

    # Simulate delivery time
    days = random.randint(2, 7)
    return f"{days} business days"


def send_shipping_notification(order: Order, shipment_id: str) -> bool:
    """
    Send shipping confirmation to customer.
    ~80% of orders get shipping notification.
    """
    if not shipment_id:
        return False
    # Simulate notification: 98% success
    if random.random() > 0.98:
        return False
    return True


# ============================================================================
# RARE OPERATIONS (LOW FREQUENCY - <10% of orders)
# ============================================================================

def handle_backorder(order: Order, missing_items: List[str]) -> bool:
    """
    Handle out-of-stock items with backorder.
    ~5% of orders need backorder handling.
    """
    if not missing_items or len(missing_items) == 0:
        return False

    # Backorder logic
    for item in missing_items:
        # Create backorder record
        pass
    return True


def process_refund(order: Order, reason: str) -> bool:
    """
    Process full or partial refund.
    ~3% of orders get refunds.
    """
    if not order.order_id or not reason:
        return False

    # Refund to original payment method
    return True


def retry_failed_payment(order: Order, amount: float) -> bool:
    """
    Retry payment after initial failure.
    ~2% of orders need retry.
    """
    try:
        # Retry payment
        if random.random() > 0.7:  # 70% retry success
            raise PaymentFailedError("Retry failed")
        return True
    except PaymentFailedError:
        return False


def handle_international_shipping(order: Order) -> dict:
    """
    Handle complex international shipment logic.
    ~5% of orders are international.
    """
    if not order.shipping_address or "USA" in order.shipping_address:
        return {}  # Not international

    # Complex customs and international logic
    customs_cost = 50.0
    import_tax = 15.0

    return {
        "customs_cost": customs_cost,
        "import_tax": import_tax,
        "estimated_clearance": "5-10 business days"
    }


def apply_loyalty_points(order: Order, points: int) -> int:
    """
    Apply customer loyalty points for discount.
    ~2% of orders use loyalty points.
    """
    if not order.customer_id or points <= 0:
        return 0

    # Convert points to discount
    discount = points * 0.01
    return discount


# ============================================================================
# DEAD CODE (NEVER USED - frequency = 0)
# ============================================================================

def legacy_payment_gateway(order: Order) -> bool:
    """
    Old payment system - DEPRECATED.
    Never called anymore, use process_payment() instead.
    DEAD CODE.
    """
    # Old implementation
    return False


def old_inventory_sync() -> bool:
    """
    Obsolete inventory synchronization.
    Replaced by real-time check_inventory().
    DEAD CODE.
    """
    # Old sync logic
    return True


def bitcoin_payment(order: Order, amount: float) -> bool:
    """
    Bitcoin payment support - never implemented.
    Removed from UI but code not deleted.
    DEAD CODE.
    """
    # Never actually used
    return False


def send_sms_notification(order: Order, message: str) -> bool:
    """
    SMS notifications - feature abandoned.
    Use send_order_confirmation() and send_shipping_notification() instead.
    DEAD CODE.
    """
    # SMS service no longer used
    return False


def calculate_tax_by_zipcode(zipcode: str) -> float:
    """
    Tax calculation by zipcode - REPLACED.
    Now uses tax API instead.
    DEAD CODE.
    """
    # Old zipcode lookup table
    tax_rates = {
        "90210": 0.08,
        "10001": 0.085,
    }
    return tax_rates.get(zipcode, 0.08)


def validate_credit_card(card_number: str) -> bool:
    """
    Credit card validation - DEPRECATED.
    Now handled by payment provider.
    DEAD CODE.
    """
    if len(card_number) != 16:
        return False
    return True


def send_weekly_digest_email(customer_id: str) -> bool:
    """
    Weekly newsletter - feature removed.
    DEAD CODE - never called.
    """
    # Newsletter logic
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


class ValidationError(Exception):
    """Order validation failed."""
    pass


# ============================================================================
# MAIN ORDER PROCESSING FLOW
# ============================================================================

def process_complete_order(order: Order) -> dict:
    """
    Complete order processing workflow.
    This is the main entry point.
    """
    results = {
        "order_id": order.order_id,
        "status": "processing",
        "errors": [],
        "shipment_id": None,
        "total_amount": 0.0
    }

    try:
        # Step 1: Validate order (ALWAYS)
        if not validate_order(order):
            results["status"] = "validation_failed"
            results["errors"].append("Order validation failed")
            return results

        # Step 2: Check inventory (ALWAYS)
        if not check_inventory(order):
            # Step 2a: Rare - handle backorder (~5%)
            if random.random() < 0.05:
                handle_backorder(order, [item.get("product_id") for item in order.items])
                results["errors"].append("Items backordered")
            else:
                results["status"] = "out_of_stock"
                results["errors"].append("Out of stock")
                return results

        # Step 3: Check stock status (COMMON - ~60%)
        if random.random() < 0.6:
            stock_info = check_stock_status(order)
            results["stock_info"] = stock_info

        # Step 4: Calculate total (ALWAYS)
        base_total = calculate_order_total(order)

        # Step 4a: Apply discount (COMMON - ~70%)
        if random.random() < 0.7:
            base_total = apply_discount_code(order, base_total)

        # Step 4b: Rare - apply loyalty points (~2%)
        if random.random() < 0.02:
            loyalty_discount = apply_loyalty_points(order, 100)
            base_total -= loyalty_discount

        results["total_amount"] = base_total

        # Step 5: Process payment (ALWAYS)
        if not process_payment(order, base_total):
            # Rare - retry payment (~2%)
            if random.random() < 0.02:
                if not retry_failed_payment(order, base_total):
                    results["status"] = "payment_failed"
                    results["errors"].append("Payment failed after retry")
                    return results
            else:
                results["status"] = "payment_failed"
                results["errors"].append("Payment declined")
                return results

        # Step 6: Estimate delivery (COMMON - ~75%)
        if random.random() < 0.75:
            delivery_time = estimate_delivery_time(order)
            results["delivery_estimate"] = delivery_time

        # Step 7: Handle international shipping (RARE - ~5%)
        if random.random() < 0.05:
            intl_charges = handle_international_shipping(order)
            if intl_charges:
                results["international_charges"] = intl_charges

        # Step 8: Create shipment (ALWAYS)
        shipment_id = create_shipment(order)
        results["shipment_id"] = shipment_id

        # Step 9: Send confirmations (ALWAYS)
        send_order_confirmation(order, shipment_id)

        # Step 9a: Send shipping notification (COMMON - ~80%)
        if random.random() < 0.8:
            send_shipping_notification(order, shipment_id)

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
    print("E-commerce Order Processing Service\n")

    # Process 50 orders with different paths
    for i in range(50):
        order = Order(
            order_id=f"ORD_{i:04d}",
            customer_id=f"CUST_{random.randint(1000, 9999)}",
            items=[
                {"product_id": f"PROD_{random.randint(1, 100)}", "quantity": random.randint(1, 5)}
                for _ in range(random.randint(1, 3))
            ],
            coupon_code=f"COUP_{random.randint(1, 999)}" if random.random() > 0.5 else None,
            shipping_address=["USA", "Canada", "UK"][random.randint(0, 2)],
            payment_method="credit_card"
        )

        result = process_complete_order(order)
        status = result["status"]
        print(f"Order {order.order_id}: {status}")

    print("\n✅ Order processing demo complete")
