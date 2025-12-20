"""
Financial Projections and Revenue Calculator for SaaS Business
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("Pandas not available, revenue calculator will use basic calculations")


@dataclass
class RevenueModel:
    """Revenue model configuration"""
    name: str
    pricing_model: str  # subscription, usage, transaction, revenue_share
    base_price: Decimal
    variable_rate: Decimal
    churn_rate: float  # Monthly churn rate
    growth_rate: float  # Monthly growth rate
    acquisition_cost: Decimal
    support_cost_per_user: Decimal


class FinancialProjections:
    """Generate financial projections for SaaS business"""
    
    def __init__(self):
        self.models = {
            "subscription": RevenueModel(
                name="Subscription SaaS",
                pricing_model="subscription",
                base_price=Decimal("99"),
                variable_rate=Decimal("0.10"),  # Overage per document
                churn_rate=0.03,  # 3% monthly churn
                growth_rate=0.10,  # 10% monthly growth
                acquisition_cost=Decimal("500"),  # CAC
                support_cost_per_user=Decimal("10")
            ),
            "transaction": RevenueModel(
                name="Transaction-based",
                pricing_model="transaction",
                base_price=Decimal("0"),
                variable_rate=Decimal("0.005"),  # 0.5% of transaction
                churn_rate=0.02,
                growth_rate=0.15,
                acquisition_cost=Decimal("300"),
                support_cost_per_user=Decimal("5")
            ),
            "hybrid": RevenueModel(
                name="Hybrid Model",
                pricing_model="hybrid",
                base_price=Decimal("49"),
                variable_rate=Decimal("0.08"),  # Base + overage
                churn_rate=0.025,
                growth_rate=0.12,
                acquisition_cost=Decimal("400"),
                support_cost_per_user=Decimal("8")
            )
        }
    
    def calculate_monthly_recurring_revenue(self,
                                          starting_mrr: Decimal,
                                          model: RevenueModel,
                                          months: int = 36) -> List[Dict]:
        """Calculate MRR growth over time"""
        data = []
        current_mrr = starting_mrr
        current_customers = 100  # Starting customers
        
        for month in range(months):
            # Calculate new customers
            new_customers = int(current_customers * model.growth_rate)
            churned_customers = int(current_customers * model.churn_rate)
            
            # Update customer count
            current_customers = current_customers + new_customers - churned_customers
            
            # Calculate MRR
            base_mrr = Decimal(str(current_customers)) * model.base_price
            
            # Add variable revenue (usage-based)
            avg_documents_per_customer = 1000  # Example
            variable_revenue = Decimal(str(current_customers * avg_documents_per_customer)) * model.variable_rate
            
            total_mrr = base_mrr + variable_revenue
            
            # Calculate costs
            acquisition_cost = Decimal(str(new_customers)) * model.acquisition_cost
            support_cost = Decimal(str(current_customers)) * model.support_cost_per_user
            infrastructure_cost = total_mrr * Decimal("0.10")  # 10% of revenue
            total_cost = acquisition_cost + support_cost + infrastructure_cost
            
            # Profit
            profit = total_mrr - total_cost
            profit_margin = (profit / total_mrr * 100) if total_mrr > 0 else 0
            
            data.append({
                "month": month + 1,
                "customers": current_customers,
                "new_customers": new_customers,
                "churned_customers": churned_customers,
                "mrr": float(total_mrr),
                "base_mrr": float(base_mrr),
                "variable_revenue": float(variable_revenue),
                "acquisition_cost": float(acquisition_cost),
                "support_cost": float(support_cost),
                "infrastructure_cost": float(infrastructure_cost),
                "total_cost": float(total_cost),
                "profit": float(profit),
                "profit_margin": float(profit_margin),
                "cac": float(model.acquisition_cost),
                "ltv": self._calculate_ltv(model, total_mrr / current_customers if current_customers > 0 else Decimal("0"))
            })
            
            current_mrr = total_mrr
        
        return data
    
    def calculate_break_even(self, model: RevenueModel, initial_investment: Decimal, months: int = 60) -> Dict:
        """Calculate break-even point"""
        projections = self.calculate_monthly_recurring_revenue(Decimal("0"), model, months)
        
        cumulative_profit = 0
        break_even_month = None
        
        for row in projections:
            cumulative_profit += row['profit']
            if cumulative_profit >= float(initial_investment) and break_even_month is None:
                break_even_month = row['month']
                break
        
        break_even_mrr = None
        break_even_customers = None
        if break_even_month:
            break_even_data = projections[break_even_month - 1]
            break_even_mrr = break_even_data['mrr']
            break_even_customers = break_even_data['customers']
        
        return {
            "break_even_month": break_even_month,
            "initial_investment": float(initial_investment),
            "required_mrr_at_break_even": break_even_mrr,
            "required_customers_at_break_even": break_even_customers
        }
    
    def calculate_customer_lifetime_value(self, model: RevenueModel) -> Dict:
        """Calculate Customer Lifetime Value (LTV)"""
        # Calculate average revenue per user (ARPU)
        arpu = model.base_price + (Decimal("1000") * model.variable_rate)  # Assuming 1000 docs/month
        
        # Calculate customer lifetime in months
        monthly_churn_rate = model.churn_rate
        lifetime_months = 1 / monthly_churn_rate if monthly_churn_rate > 0 else 120
        
        # Calculate LTV
        ltv = arpu * Decimal(str(lifetime_months))
        
        # Calculate LTV:CAC ratio
        cac = model.acquisition_cost
        ltv_cac_ratio = ltv / cac if cac > 0 else 0
        
        return {
            "arpu": float(arpu),
            "monthly_churn_rate": monthly_churn_rate,
            "lifetime_months": lifetime_months,
            "ltv": float(ltv),
            "cac": float(cac),
            "ltv_cac_ratio": float(ltv_cac_ratio),
            "recommended_cac": float(ltv / 3) if ltv > 0 else 0  # Ideally, CAC should be < 1/3 of LTV
        }
    
    def generate_investor_deck_numbers(self,
                                     model_name: str = "subscription",
                                     years: int = 5) -> Dict:
        """Generate numbers for investor pitch deck"""
        model = self.models[model_name]
        
        # Multi-year projections
        projections = self.calculate_monthly_recurring_revenue(Decimal("9900"), model, years * 12)
        
        # Annual summary
        annual_summary = []
        for year in range(1, years + 1):
            year_data = [p for p in projections if p['month'] <= year * 12]
            if year_data:
                last_month = year_data[-1]
                total_revenue = sum(p['mrr'] for p in year_data)  # Sum of monthly MRR
                total_profit = sum(p['profit'] for p in year_data)
                
                annual_summary.append({
                    "year": year,
                    "ending_mrr": last_month['mrr'],
                    "ending_customers": last_month['customers'],
                    "total_revenue": total_revenue,
                    "total_profit": total_profit,
                    "avg_profit_margin": total_profit / total_revenue * 100 if total_revenue > 0 else 0
                })
        
        # Key metrics
        ltv_analysis = self.calculate_customer_lifetime_value(model)
        break_even = self.calculate_break_even(model, Decimal("500000"))  # $500k initial investment
        
        return {
            "annual_summary": annual_summary,
            "year_5_projections": annual_summary[-1] if annual_summary else {},
            "ltv_analysis": ltv_analysis,
            "break_even_analysis": break_even,
            "key_metrics": {
                "monthly_growth_rate": model.growth_rate * 100,
                "monthly_churn_rate": model.churn_rate * 100,
                "gross_margin": 85,  # Estimated
                "net_revenue_retention": 110,  # 110% including expansion
                "magic_number": (model.growth_rate / model.churn_rate) > 0.75 if model.churn_rate > 0 else False
            }
        }
    
    def _calculate_ltv(self, model: RevenueModel, arpu: Decimal) -> float:
        """Calculate Lifetime Value"""
        if model.churn_rate == 0:
            return float('inf')
        lifetime_months = 1 / model.churn_rate
        return float(arpu * Decimal(str(lifetime_months)))
    
    def calculate_roi_for_investor(self, investment_amount: float, exit_multiple: float = 10, model_name: str = "subscription") -> Dict:
        """Calculate potential ROI for investors"""
        model = self.models[model_name]
        projections = self.generate_investor_deck_numbers(model_name, 3)
        
        year_3_arr = projections['year_5_projections'].get('ending_mrr', 0) * 12
        year_3_valuation = year_3_arr * exit_multiple
        
        return {
            "investment": investment_amount,
            "year_3_arr": year_3_arr,
            "year_3_valuation": year_3_valuation,
            "multiple_on_investment": year_3_valuation / investment_amount if investment_amount > 0 else 0,
            "annualized_roi": ((year_3_valuation / investment_amount) ** (1/3) - 1) * 100 if investment_amount > 0 else 0
        }

