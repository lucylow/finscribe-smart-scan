"""
Partner Attribution & Revenue Share (QuickBooks / Xero)
"""
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_partner_by_code(db: Session, code: str) -> Optional[Dict]:
    """
    Get partner by referral code.
    In production, this would query the partners table.
    """
    # Mock data - in production, query database
    partners = {
        "quickbooks": {
            "id": "partner_qb_123",
            "name": "QuickBooks",
            "type": "quickbooks",
            "code": "quickbooks",
            "revenue_share": 0.25,
        },
        "xero": {
            "id": "partner_xero_123",
            "name": "Xero",
            "type": "xero",
            "code": "xero",
            "revenue_share": 0.30,
        },
    }
    return partners.get(code.lower())


def record_partner_referral(
    db: Session,
    user_id: str,
    partner_code: str
) -> Optional[str]:
    """
    Record that a user was referred by a partner.
    Returns partner_id if found, None otherwise.
    """
    partner = get_partner_by_code(db, partner_code)
    if not partner:
        return None
    
    # In production:
    # db.execute(
    #     "UPDATE profiles SET referred_by_partner_id = :partner_id WHERE id = :user_id",
    #     {"partner_id": partner["id"], "user_id": user_id}
    # )
    # db.commit()
    
    return partner["id"]


def record_revenue_share(
    db: Session,
    user_id: str,
    invoice_id: str,
    revenue_usd: float
) -> Optional[Dict[str, Any]]:
    """
    Record revenue share when an invoice is paid.
    Returns referral record if user was referred by a partner.
    """
    # In production, query user's referred_by_partner_id
    # For now, return None (no partner)
    
    # Example production code:
    # user = db.query(User).filter_by(id=user_id).first()
    # if not user or not user.referred_by_partner_id:
    #     return None
    # 
    # partner = db.query(Partner).filter_by(id=user.referred_by_partner_id).first()
    # if not partner:
    #     return None
    # 
    # partner_cut = revenue_usd * partner.revenue_share
    # 
    # referral = PartnerReferral(
    #     partner_id=partner.id,
    #     user_id=user_id,
    #     stripe_invoice_id=invoice_id,
    #     revenue_usd=partner_cut,
    # )
    # db.add(referral)
    # db.commit()
    # 
    # return {
    #     "partner_id": partner.id,
    #     "partner_name": partner.name,
    #     "revenue_share": partner_cut,
    #     "total_revenue": revenue_usd,
    # }
    
    return None


