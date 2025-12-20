"""
Marketplace for Fine-Tuned Models
"""
from typing import Dict, List, Optional


class MarketplaceModel:
    """Represents a marketplace model available for purchase."""
    
    def __init__(
        self,
        id: str,
        name: str,
        price_usd: int,
        description: str,
        model_path: Optional[str] = None
    ):
        self.id = id
        self.name = name
        self.price_usd = price_usd
        self.description = description
        self.model_path = model_path


# Example marketplace models
MARKETPLACE_MODELS: List[MarketplaceModel] = [
    MarketplaceModel(
        id="retail_receipt_v1",
        name="Retail Receipt Model",
        price_usd=499,
        description="Fine-tuned for retail receipts and point-of-sale documents",
        model_path="models/retail_receipt_v1"
    ),
    MarketplaceModel(
        id="handwritten_check_v1",
        name="Handwritten Check Model",
        price_usd=299,
        description="Specialized for handwritten bank checks and financial documents",
        model_path="models/handwritten_check_v1"
    ),
    MarketplaceModel(
        id="multilang_invoice_v1",
        name="Multi-Language Invoice Model",
        price_usd=799,
        description="Supports invoices in 20+ languages with currency conversion",
        model_path="models/multilang_invoice_v1"
    ),
]


def get_marketplace_model(model_id: str) -> Optional[MarketplaceModel]:
    """Get a marketplace model by ID."""
    for model in MARKETPLACE_MODELS:
        if model.id == model_id:
            return model
    return None


def list_marketplace_models() -> List[Dict]:
    """List all available marketplace models."""
    return [
        {
            "id": model.id,
            "name": model.name,
            "price_usd": model.price_usd,
            "description": model.description,
        }
        for model in MARKETPLACE_MODELS
    ]

