import json
import logging
from typing import Dict, Any, List
from .camel_invoice import create_extractor_agent, create_validator_agent, create_auditor_agent

logger = logging.getLogger(__name__)

class EnhancedInvoiceReasoning:
    """
    Advanced multi-agent reasoning for financial documents.
    Implements a 'Chain of Verification' (CoVe) pattern.
    """
    
    def __init__(self):
        self.extractor = create_extractor_agent()
        self.validator = create_validator_agent()
        self.auditor = create_auditor_agent()

    async def process(self, ocr_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Starting enhanced multi-agent reasoning...")
        
        # 1. Initial Extraction
        extraction = self.extractor.step(f"Extract fields from: {json.dumps(ocr_data)}")
        
        # 2. Verification (Self-Correction)
        verification = self.validator.step(f"Verify this extraction for math errors: {extraction}")
        
        # 3. Final Audit & Confidence Scoring
        audit = self.auditor.step(f"Audit the final result and provide a confidence score: {verification}")
        
        return {
            "final_json": verification,
            "audit_report": audit,
            "reasoning_steps": ["extraction", "verification", "audit"]
        }

