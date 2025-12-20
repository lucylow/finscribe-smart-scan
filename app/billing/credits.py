"""
API Credit System - Developer Monetization
"""
import logging
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def has_api_credits(user, required: int = 1) -> bool:
    """Check if user has sufficient API credits."""
    api_credits = getattr(user, "api_credits", 0)
    return api_credits >= required


def deduct_api_credits(db: Session, user, amount: int = 1):
    """
    Deduct API credits from user account.
    Raises exception if insufficient credits.
    """
    if not has_api_credits(user, amount):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient API credits. Required: {amount}, Available: {getattr(user, 'api_credits', 0)}"
        )
    
    # In production, update database:
    # user.api_credits -= amount
    # db.commit()
    
    # For now, just update the attribute
    user.api_credits = getattr(user, "api_credits", 0) - amount


def add_api_credits(db: Session, user, amount: int):
    """Add API credits to user account."""
    current = getattr(user, "api_credits", 0)
    user.api_credits = current + amount
    # In production: db.commit()


# Example usage in API endpoint:
# if not has_api_credits(user):
#     raise HTTPException(402, "Out of API credits")
# deduct_api_credits(db, user)

