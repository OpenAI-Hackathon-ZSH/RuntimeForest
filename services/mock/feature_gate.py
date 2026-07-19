"""
Feature Gate Service - Determines which features are enabled per customer/region.

This service identifies which code paths execute based on:
- Customer region (USA, EU, APAC)
- Customer tier (free, basic, premium)
- A/B testing flags
- Feature rollout status
"""

from dataclasses import dataclass
from typing import Set
from enum import Enum


class Region(Enum):
    USA = "usa"
    EU = "eu"
    APAC = "apac"


class CustomerTier(Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"


@dataclass
class CustomerSegment:
    """Customer attributes that determine feature availability."""
    customer_id: str
    region: Region
    tier: CustomerTier
    is_early_adopter: bool = False
    loyalty_program_enabled: bool = False


class FeatureGateService:
    """
    Determines which features are enabled for a customer.

    This creates realistic execution patterns where:
    - Different regions have different features
    - Premium customers get early features
    - Some features are disabled for certain regions (GDPR, regulations)
    """

    def __init__(self):
        # Feature availability by region
        self.region_features = {
            Region.USA: {
                "discount_codes",
                "loyalty_points",
                "international_shipping",
                "sms_notifications",
                "one_click_checkout",
                "save_payment_method",
                "expedited_shipping"
            },
            Region.EU: {
                # GDPR restrictions: no sms
                "discount_codes",
                "loyalty_points",
                "international_shipping",
                "one_click_checkout",
                "save_payment_method",
                "expedited_shipping"
            },
            Region.APAC: {
                "discount_codes",
                "loyalty_points",
                "international_shipping",
                "expedited_shipping",
                # Limited feature set
            }
        }

        # Premium-only features
        self.premium_features = {
            "loyalty_points",
            "expedited_shipping",
            "priority_support",
            "vip_pricing"
        }

        # Early adopter features
        self.early_adopter_features = {
            "ai_recommendations",
            "dynamic_pricing",
            "personalized_checkout"
        }

    def is_feature_enabled(self, segment: CustomerSegment, feature: str) -> bool:
        """Check if a feature is enabled for this customer."""

        # Check region availability
        if feature not in self.region_features.get(segment.region, set()):
            return False

        # Check tier requirements
        if feature in self.premium_features and segment.tier == CustomerTier.FREE:
            return False

        # Check early adopter requirement
        if feature in self.early_adopter_features and not segment.is_early_adopter:
            return False

        # Loyalty program must be explicitly enabled
        if feature == "loyalty_points" and not segment.loyalty_program_enabled:
            return False

        return True

    def get_enabled_features(self, segment: CustomerSegment) -> Set[str]:
        """Get all enabled features for a customer."""
        features = set()

        # Get region features
        region_features = self.region_features.get(segment.region, set())

        for feature in region_features:
            if self.is_feature_enabled(segment, feature):
                features.add(feature)

        # Add early adopter features if applicable
        if segment.is_early_adopter:
            for feature in self.early_adopter_features:
                features.add(feature)

        return features

    def get_order_features(self, segment: CustomerSegment) -> dict:
        """
        Get feature availability for order processing.

        Returns a dict indicating which code paths should execute.
        """
        enabled = self.get_enabled_features(segment)

        return {
            "can_apply_discount": "discount_codes" in enabled,
            "can_use_loyalty": "loyalty_points" in enabled and segment.loyalty_program_enabled,
            "can_expedite": "expedited_shipping" in enabled,
            "can_save_payment": "save_payment_method" in enabled,
            "can_one_click": "one_click_checkout" in enabled,
            "can_send_sms": "sms_notifications" in enabled,
            "has_vip_pricing": "vip_pricing" in enabled,
            "ai_recommendations": "ai_recommendations" in enabled,
            "international_shipping": "international_shipping" in enabled,
        }


# Global feature gate service
_gate_service = FeatureGateService()


def is_feature_enabled(segment: CustomerSegment, feature: str) -> bool:
    """Helper function to check if feature is enabled."""
    return _gate_service.is_feature_enabled(segment, feature)


def get_order_features(segment: CustomerSegment) -> dict:
    """Helper function to get order features."""
    return _gate_service.get_order_features(segment)


def get_enabled_features(segment: CustomerSegment) -> Set[str]:
    """Helper function to get all enabled features."""
    return _gate_service.get_enabled_features(segment)


# ============================================================================
# CUSTOMER SEGMENT FACTORY
# ============================================================================

def create_customer_segment(customer_id: str, segment_type: str) -> CustomerSegment:
    """
    Create a customer segment based on segment type.

    Segment types:
    - "usa_premium_early": USA, Premium tier, early adopter
    - "usa_basic": USA, Basic tier
    - "usa_free": USA, Free tier
    - "eu_premium": EU, Premium tier (no SMS)
    - "eu_basic": EU, Basic tier
    - "apac_premium": APAC, Premium tier (limited features)
    - "apac_basic": APAC, Basic tier
    """

    mapping = {
        "usa_premium_early": CustomerSegment(
            customer_id=customer_id,
            region=Region.USA,
            tier=CustomerTier.PREMIUM,
            is_early_adopter=True,
            loyalty_program_enabled=True
        ),
        "usa_premium": CustomerSegment(
            customer_id=customer_id,
            region=Region.USA,
            tier=CustomerTier.PREMIUM,
            is_early_adopter=False,
            loyalty_program_enabled=True
        ),
        "usa_basic": CustomerSegment(
            customer_id=customer_id,
            region=Region.USA,
            tier=CustomerTier.BASIC,
            is_early_adopter=False,
            loyalty_program_enabled=False
        ),
        "usa_free": CustomerSegment(
            customer_id=customer_id,
            region=Region.USA,
            tier=CustomerTier.FREE,
            is_early_adopter=False,
            loyalty_program_enabled=False
        ),
        "eu_premium": CustomerSegment(
            customer_id=customer_id,
            region=Region.EU,
            tier=CustomerTier.PREMIUM,
            is_early_adopter=False,
            loyalty_program_enabled=True
        ),
        "eu_basic": CustomerSegment(
            customer_id=customer_id,
            region=Region.EU,
            tier=CustomerTier.BASIC,
            is_early_adopter=False,
            loyalty_program_enabled=False
        ),
        "apac_premium": CustomerSegment(
            customer_id=customer_id,
            region=Region.APAC,
            tier=CustomerTier.PREMIUM,
            is_early_adopter=False,
            loyalty_program_enabled=True
        ),
        "apac_basic": CustomerSegment(
            customer_id=customer_id,
            region=Region.APAC,
            tier=CustomerTier.BASIC,
            is_early_adopter=False,
            loyalty_program_enabled=False
        ),
    }

    return mapping.get(segment_type, mapping["usa_basic"])


def get_segment_distribution() -> dict:
    """
    Distribution of customer segments for realistic testing.

    Returns: {segment_type: percentage}
    """
    return {
        "usa_premium_early": 0.05,   # 5% early adopters
        "usa_premium": 0.15,         # 15% premium US customers
        "usa_basic": 0.25,           # 25% basic US customers
        "usa_free": 0.15,            # 15% free US customers
        "eu_premium": 0.10,          # 10% premium EU customers
        "eu_basic": 0.15,            # 15% basic EU customers
        "apac_premium": 0.05,        # 5% premium APAC customers
        "apac_basic": 0.10,          # 10% basic APAC customers
    }
