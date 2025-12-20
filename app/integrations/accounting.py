"""
Accounting Connectors - QuickBooks & Xero Integration
Abstracted interface for pushing invoice data to accounting systems.
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)


class AccountingConnector(ABC):
    """Abstract base class for accounting system connectors."""
    
    @abstractmethod
    def push_invoice(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Push invoice data to the accounting system."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if the connection to the accounting system is valid."""
        pass


class QuickBooksConnector(AccountingConnector):
    """QuickBooks API connector."""
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("QUICKBOOKS_ACCESS_TOKEN", "")
        self.base_url = "https://quickbooks.api.intuit.com/v3/company"
        self.company_id = os.getenv("QUICKBOOKS_COMPANY_ID", "")
    
    def push_invoice(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Push invoice data to QuickBooks.
        Expects data in QuickBooks invoice format.
        """
        if not self.access_token:
            raise ValueError("QuickBooks access token not configured")
        
        try:
            url = f"{self.base_url}/{self.company_id}/invoice"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            return {
                "success": True,
                "data": response.json(),
                "connector": "quickbooks",
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"QuickBooks API error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "connector": "quickbooks",
            }
    
    def test_connection(self) -> bool:
        """Test QuickBooks connection."""
        try:
            url = f"{self.base_url}/{self.company_id}/companyinfo/{self.company_id}"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False


class XeroConnector(AccountingConnector):
    """Xero API connector."""
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or os.getenv("XERO_ACCESS_TOKEN", "")
        self.base_url = "https://api.xero.com/api.xro/2.0"
        self.tenant_id = os.getenv("XERO_TENANT_ID", "")
    
    def push_invoice(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Push invoice data to Xero.
        Expects data in Xero invoice format.
        """
        if not self.access_token:
            raise ValueError("Xero access token not configured")
        
        try:
            url = f"{self.base_url}/Invoices"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Xero-tenant-id": self.tenant_id,
                "Content-Type": "application/json",
            }
            
            # Xero expects invoices in a specific format
            xero_data = {
                "Invoices": [data]
            }
            
            response = requests.post(url, json=xero_data, headers=headers, timeout=30)
            response.raise_for_status()
            
            return {
                "success": True,
                "data": response.json(),
                "connector": "xero",
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Xero API error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "connector": "xero",
            }
    
    def test_connection(self) -> bool:
        """Test Xero connection."""
        try:
            url = f"{self.base_url}/Organisation"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Xero-tenant-id": self.tenant_id,
            }
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False


def get_connector(connector_type: str, access_token: Optional[str] = None) -> Optional[AccountingConnector]:
    """Factory function to get the appropriate connector."""
    if connector_type.lower() == "quickbooks":
        return QuickBooksConnector(access_token)
    elif connector_type.lower() == "xero":
        return XeroConnector(access_token)
    else:
        logger.warning(f"Unknown connector type: {connector_type}")
        return None


# Usage example:
# if user.has_integration("quickbooks"):
#     connector = get_connector("quickbooks", user.quickbooks_token)
#     result = connector.push_invoice(parsed_invoice_data)

