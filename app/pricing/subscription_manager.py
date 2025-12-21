"""
Enhanced SaaS Subscription Manager with comprehensive pricing tiers
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Feature(str, Enum):
    """Available features"""
    BASIC_OCR = "basic_ocr"
    ADVANCED_OCR = "advanced_ocr"
    MULTI_CURRENCY = "multi_currency"
    API_ACCESS = "api_access"
    BULK_PROCESSING = "bulk_processing"
    CUSTOM_MODELS = "custom_models"
    WORKFLOW_AUTOMATION = "workflow_automation"
    INTEGRATIONS = "integrations"
    WHITE_LABEL = "white_label"
    DEDICATED_SUPPORT = "dedicated_support"
    BATCH_PROCESSING = "batch_processing"
    WEBHOOKS = "webhooks"
    CUSTOM_FIELDS = "custom_fields"
    ON_PREM = "on_prem"
    SLA = "sla"


@dataclass
class PricingTier:
    """Pricing tier configuration"""
    name: str
    code: str
    monthly_price: Decimal
    annual_price: Decimal  # Annual discount applied
    features: List[Feature]
    limits: Dict[str, int]
    overage_rates: Dict[str, Decimal]
    addons: List[str]


class SaaSSubscriptionManager:
    """Manage SaaS subscriptions and pricing"""
    
    def __init__(self):
        # Define pricing tiers
        self.tiers = {
            "starter": PricingTier(
                name="Starter",
                code="starter",
                monthly_price=Decimal("49"),
                annual_price=Decimal("470.40"),  # 20% discount
                features=[
                    Feature.BASIC_OCR,
                    Feature.API_ACCESS,
                ],
                limits={
                    "documents_per_month": 500,
                    "users": 3,
                    "storage_gb": 10,
                    "api_requests_per_month": 1000,
                },
                overage_rates={
                    "document": Decimal("0.10"),
                    "api_request": Decimal("0.001"),
                    "storage_gb": Decimal("0.50"),
                },
                addons=["basic_support"]
            ),
            "growth": PricingTier(
                name="Growth",
                code="growth",
                monthly_price=Decimal("199"),
                annual_price=Decimal("1910.40"),  # 20% discount
                features=[
                    Feature.BASIC_OCR,
                    Feature.ADVANCED_OCR,
                    Feature.MULTI_CURRENCY,
                    Feature.API_ACCESS,
                    Feature.BULK_PROCESSING,
                    Feature.INTEGRATIONS,
                ],
                limits={
                    "documents_per_month": 5000,
                    "users": 10,
                    "storage_gb": 50,
                    "api_requests_per_month": 10000,
                },
                overage_rates={
                    "document": Decimal("0.08"),
                    "api_request": Decimal("0.0008"),
                    "storage_gb": Decimal("0.40"),
                },
                addons=["priority_support", "basic_integrations"]
            ),
            "professional": PricingTier(
                name="Professional",
                code="professional",
                monthly_price=Decimal("499"),
                annual_price=Decimal("4790.40"),  # 20% discount
                features=[
                    Feature.BASIC_OCR,
                    Feature.ADVANCED_OCR,
                    Feature.MULTI_CURRENCY,
                    Feature.API_ACCESS,
                    Feature.BULK_PROCESSING,
                    Feature.WORKFLOW_AUTOMATION,
                    Feature.INTEGRATIONS,
                    Feature.BATCH_PROCESSING,
                    Feature.WEBHOOKS,
                    Feature.CUSTOM_FIELDS,
                ],
                limits={
                    "documents_per_month": 25000,
                    "users": 25,
                    "storage_gb": 100,
                    "api_requests_per_month": 50000,
                },
                overage_rates={
                    "document": Decimal("0.06"),
                    "api_request": Decimal("0.0006"),
                    "storage_gb": Decimal("0.30"),
                },
                addons=["priority_support", "advanced_integrations", "custom_fields"]
            ),
            "enterprise": PricingTier(
                name="Enterprise",
                code="enterprise",
                monthly_price=Decimal("999"),
                annual_price=Decimal("9580.80"),  # 20% discount
                features=[
                    Feature.BASIC_OCR,
                    Feature.ADVANCED_OCR,
                    Feature.MULTI_CURRENCY,
                    Feature.API_ACCESS,
                    Feature.BULK_PROCESSING,
                    Feature.WORKFLOW_AUTOMATION,
                    Feature.INTEGRATIONS,
                    Feature.CUSTOM_MODELS,
                    Feature.WHITE_LABEL,
                    Feature.DEDICATED_SUPPORT,
                    Feature.BATCH_PROCESSING,
                    Feature.WEBHOOKS,
                    Feature.CUSTOM_FIELDS,
                    Feature.ON_PREM,
                    Feature.SLA,
                ],
                limits={
                    "documents_per_month": 100000,
                    "users": 100,
                    "storage_gb": 500,
                    "api_requests_per_month": 200000,
                },
                overage_rates={
                    "document": Decimal("0.04"),
                    "api_request": Decimal("0.0004"),
                    "storage_gb": Decimal("0.20"),
                },
                addons=["all"]
            )
        }
        
        # Define addons
        self.addons = {
            "custom_model_training": {
                "name": "Custom Model Training",
                "monthly_price": Decimal("299"),
                "features": ["Industry-specific OCR models"]
            },
            "advanced_integrations": {
                "name": "Advanced Integrations",
                "monthly_price": Decimal("99"),
                "features": ["QuickBooks", "Xero", "NetSuite", "SAP"]
            },
            "dedicated_support": {
                "name": "Dedicated Support",
                "monthly_price": Decimal("199"),
                "features": ["24/7 support", "4-hour response", "Dedicated engineer"]
            },
            "white_label": {
                "name": "White Label",
                "monthly_price": Decimal("499"),
                "features": ["Custom branding", "Domain", "No FinScribe branding"]
            }
        }
        
        # Promotions
        self.promotions = {
            "LAUNCH20": {"type": "percentage", "value": 20, "valid_until": "2025-12-31"},
            "STARTUP50": {"type": "percentage", "value": 50, "valid_until": "2025-12-31", "min_tier": "growth"},
            "FREEMONTH": {"type": "fixed", "value": 49, "valid_until": "2025-12-31"},
        }
    
    def get_tier(self, tier_code: str) -> Optional[PricingTier]:
        """Get pricing tier by code"""
        return self.tiers.get(tier_code.lower())
    
    def calculate_subscription_price(self,
                                   tier_code: str,
                                   billing_cycle: str = "monthly",
                                   addons: List[str] = None,
                                   promo_code: Optional[str] = None) -> Dict:
        """Calculate subscription price with addons and promotions"""
        tier = self.get_tier(tier_code)
        if not tier:
            raise ValueError(f"Invalid tier code: {tier_code}")
        
        addons = addons or []
        
        # Base price
        if billing_cycle == "annual":
            base_price = tier.annual_price
        else:
            base_price = tier.monthly_price
        
        # Addon prices
        addon_price = Decimal("0")
        addon_features = []
        
        for addon_code in addons:
            if addon_code in self.addons:
                addon_price += self.addons[addon_code]["monthly_price"] * (
                    12 if billing_cycle == "annual" else 1
                )
                addon_features.extend(self.addons[addon_code]["features"])
        
        # Apply promotion
        discount_amount = Decimal("0")
        discount_percent = Decimal("0")
        
        if promo_code:
            discount = self._get_promo_discount(promo_code, tier_code)
            if discount:
                if discount["type"] == "percentage":
                    discount_percent = Decimal(str(discount["value"]))
                    discount_amount = (base_price + addon_price) * discount_percent / 100
                else:  # fixed amount
                    discount_amount = Decimal(str(discount["value"]))
        
        subtotal = base_price + addon_price
        tax_rate = Decimal("0.10")  # Example 10% tax (adjust based on location)
        tax_amount = (subtotal - discount_amount) * tax_rate
        total = subtotal - discount_amount + tax_amount
        
        return {
            "tier": tier.name,
            "tier_code": tier.code,
            "billing_cycle": billing_cycle,
            "base_price": float(base_price),
            "addon_price": float(addon_price),
            "subtotal": float(subtotal),
            "discount_percent": float(discount_percent),
            "discount_amount": float(discount_amount),
            "tax_rate": float(tax_rate),
            "tax_amount": float(tax_amount),
            "total": float(total),
            "features": [f.value for f in tier.features] + addon_features,
            "limits": tier.limits,
            "overage_rates": {k: float(v) for k, v in tier.overage_rates.items()}
        }
    
    def check_feature_access(self, tier_code: str, feature: Feature) -> bool:
        """Check if tier has access to a feature"""
        tier = self.get_tier(tier_code)
        if not tier:
            return False
        return feature in tier.features
    
    def calculate_usage_charges(self,
                               tier_code: str,
                               usage_data: Dict[str, int]) -> Dict:
        """Calculate overage charges for the month"""
        tier = self.get_tier(tier_code)
        if not tier:
            tier = self.tiers["starter"]
        
        overage_charges = {}
        total_overage = Decimal("0")
        
        for resource, usage in usage_data.items():
            # Map resource names
            resource_key = resource.replace("documents", "document").replace("api_requests", "api_request")
            resource_key = resource_key.replace("_per_month", "")
            
            if resource_key in tier.overage_rates:
                limit_key = resource.replace("_per_month", "_per_month")
                limit = tier.limits.get(limit_key, 0)
                
                if limit and usage > limit:
                    overage = usage - limit
                    rate = tier.overage_rates[resource_key]
                    charge = Decimal(str(overage)) * rate
                    overage_charges[resource] = {
                        "limit": limit,
                        "usage": usage,
                        "overage": overage,
                        "rate": float(rate),
                        "charge": float(charge)
                    }
                    total_overage += charge
        
        return {
            "overage_charges": overage_charges,
            "total_overage": float(total_overage),
            "currency": "USD"
        }
    
    def _get_promo_discount(self, promo_code: str, tier_code: str = None) -> Optional[Dict]:
        """Get promotion discount details"""
        promo = self.promotions.get(promo_code.upper())
        if not promo:
            return None
        
        # Check if promo has minimum tier requirement
        if "min_tier" in promo:
            tier_hierarchy = ["starter", "growth", "professional", "enterprise"]
            if tier_code and tier_code.lower() in tier_hierarchy:
                promo_min_index = tier_hierarchy.index(promo["min_tier"])
                tier_index = tier_hierarchy.index(tier_code.lower())
                if tier_index < promo_min_index:
                    return None
        
        # Check expiry
        valid_until = datetime.strptime(promo["valid_until"], "%Y-%m-%d")
        if datetime.now() > valid_until:
            return None
        
        return promo
    
    def get_all_tiers(self) -> Dict[str, PricingTier]:
        """Get all available tiers"""
        return self.tiers
    
    def get_upgrade_path(self, current_tier: str) -> List[str]:
        """Get recommended upgrade path from current tier"""
        tier_hierarchy = ["starter", "growth", "professional", "enterprise"]
        try:
            current_index = tier_hierarchy.index(current_tier.lower())
            return tier_hierarchy[current_index + 1:]
        except (ValueError, IndexError):
            return []


