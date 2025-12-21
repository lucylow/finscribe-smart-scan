"""
Document Transformer for ETL Pipeline.

Transforms raw OCR output into structured, canonical schema.
Implements:
- Lexical cleaning (OCR error correction)
- Semantic structuring (field extraction)
- Schema mapping (canonical format)
- Data enrichment (entity resolution, normalization)
"""
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class DocumentTransformer:
    """
    Transforms OCR output into structured, canonical schema.
    
    This is where intelligence lives - converting noisy OCR text
    into clean, structured data that downstream systems can use.
    """
    
    # Canonical schema definition
    CANONICAL_SCHEMA = {
        "invoice_id": str,
        "vendor": str,
        "date": str,  # ISO format
        "due_date": Optional[str],
        "line_items": List[Dict[str, Any]],
        "subtotal": Optional[float],
        "tax": Optional[float],
        "total": float,
        "currency": str,
        "payment_terms": Optional[str],
        "vendor_address": Optional[Dict[str, str]],
        "customer_address": Optional[Dict[str, str]],
        "notes": Optional[str],
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize transformer.
        
        Args:
            config: Transformation configuration
        """
        self.config = config or {}
        self.enable_lexical_cleaning = self.config.get("enable_lexical_cleaning", True)
        self.enable_enrichment = self.config.get("enable_enrichment", False)
        
        # Common OCR error patterns
        self.ocr_corrections = {
            r'\b0\b': 'O',  # Context-dependent, simplified
            r'\b1\b': 'I',  # Context-dependent, simplified
        }
    
    async def transform(
        self,
        ocr_results: Dict[str, Any],
        classification: Dict[str, Any],
        metadata: Any  # PipelineMetadata
    ) -> Dict[str, Any]:
        """
        Transform OCR output into structured data.
        
        Args:
            ocr_results: Raw OCR output from PaddleOCR-VL
            classification: Document classification results
            metadata: Pipeline metadata
            
        Returns:
            Transformation result with:
            - structured_data: Extracted fields
            - canonical_schema: Mapped to canonical format
            - confidence_scores: Per-field confidence
        """
        result = {
            "structured_data": {},
            "canonical_schema": {},
            "confidence_scores": {},
            "transformation_metadata": {}
        }
        
        try:
            # Step 1: Extract raw text and structure
            raw_text = self._extract_text(ocr_results)
            
            # Step 2: Lexical cleaning
            if self.enable_lexical_cleaning:
                cleaned_text = self._clean_text(raw_text)
            else:
                cleaned_text = raw_text
            
            # Step 3: Semantic structuring (field extraction)
            structured_data = await self._extract_fields(cleaned_text, ocr_results, classification)
            
            # Step 4: Schema mapping (canonical format)
            canonical_schema = self._map_to_canonical_schema(structured_data, classification)
            
            # Step 5: Data enrichment (optional)
            if self.enable_enrichment:
                enriched_data = await self._enrich_data(canonical_schema, metadata)
                canonical_schema.update(enriched_data)
            
            result["structured_data"] = structured_data
            result["canonical_schema"] = canonical_schema
            result["confidence_scores"] = self._calculate_confidence_scores(
                structured_data, ocr_results
            )
            
            logger.info(f"Transformation completed: {len(canonical_schema)} fields extracted")
            
        except Exception as e:
            logger.error(f"Transformation error: {str(e)}", exc_info=True)
            result["error"] = str(e)
        
        return result
    
    def _extract_text(self, ocr_results: Dict[str, Any]) -> str:
        """Extract raw text from OCR results."""
        text_blocks = ocr_results.get("text_blocks", [])
        if not text_blocks:
            # Try alternative structure
            text_blocks = ocr_results.get("results", [])
        
        text_parts = []
        for block in text_blocks:
            if isinstance(block, dict):
                text = block.get("text", "") or block.get("content", "")
            elif isinstance(block, str):
                text = block
            else:
                text = str(block)
            
            if text:
                text_parts.append(text)
        
        return "\n".join(text_parts)
    
    def _clean_text(self, text: str) -> str:
        """
        Clean OCR text: remove noise, fix common errors.
        
        This is a simplified version - production would use
        more sophisticated NLP techniques.
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common OCR errors (context-dependent, simplified)
        # In production, use ML-based correction
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        return text.strip()
    
    async def _extract_fields(
        self,
        cleaned_text: str,
        ocr_results: Dict[str, Any],
        classification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract structured fields from cleaned text.
        
        This uses pattern matching and heuristics.
        In production, this would use ML models or LLM-based extraction.
        """
        fields = {}
        
        # Extract invoice ID
        invoice_id_patterns = [
            r'(?:invoice|inv)[\s#:]*([A-Z0-9\-]+)',
            r'invoice[\s#:]*#?[\s]*([0-9A-Z\-]+)',
            r'#[\s]*([0-9A-Z\-]{6,})',
        ]
        for pattern in invoice_id_patterns:
            match = re.search(pattern, cleaned_text, re.IGNORECASE)
            if match:
                fields["invoice_id"] = match.group(1).strip()
                break
        
        # Extract vendor name (simplified - would use NER in production)
        # Look for common vendor patterns
        vendor_patterns = [
            r'(?:from|vendor|supplier)[\s:]+([A-Z][A-Za-z\s&]+)',
            r'^([A-Z][A-Za-z\s&]{3,30})\s+(?:invoice|bill)',
        ]
        for pattern in vendor_patterns:
            match = re.search(pattern, cleaned_text, re.IGNORECASE)
            if match:
                fields["vendor"] = match.group(1).strip()
                break
        
        # Extract dates
        date_patterns = [
            r'(?:date|invoice date)[\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        ]
        dates_found = []
        for pattern in date_patterns:
            matches = re.findall(pattern, cleaned_text, re.IGNORECASE)
            dates_found.extend(matches)
        
        if dates_found:
            fields["date"] = dates_found[0]  # Take first date as invoice date
        
        # Extract currency amounts
        amount_patterns = [
            r'(?:total|amount due|balance)[\s:]*\$?[\s]*([\d,]+\.?\d*)',
            r'\$[\s]*([\d,]+\.?\d*)',
        ]
        amounts_found = []
        for pattern in amount_patterns:
            matches = re.findall(pattern, cleaned_text, re.IGNORECASE)
            for match in matches:
                try:
                    amount = float(match.replace(',', ''))
                    amounts_found.append(amount)
                except ValueError:
                    pass
        
        if amounts_found:
            # Largest amount is likely the total
            fields["total"] = max(amounts_found)
            # Second largest might be subtotal
            if len(amounts_found) > 1:
                amounts_sorted = sorted(amounts_found, reverse=True)
                if amounts_sorted[1] < amounts_sorted[0] * 0.9:  # Reasonable subtotal
                    fields["subtotal"] = amounts_sorted[1]
        
        # Extract currency (default to USD)
        currency_match = re.search(r'([A-Z]{3})', cleaned_text)
        if currency_match:
            currency = currency_match.group(1)
            if currency in ["USD", "EUR", "GBP", "CAD", "AUD"]:
                fields["currency"] = currency
        else:
            fields["currency"] = "USD"  # Default
        
        # Extract line items (simplified - would use table detection in production)
        line_items = self._extract_line_items(cleaned_text, ocr_results)
        if line_items:
            fields["line_items"] = line_items
        
        return fields
    
    def _extract_line_items(
        self,
        text: str,
        ocr_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract line items from document.
        
        This is simplified - production would use table detection
        and structured extraction.
        """
        line_items = []
        
        # Look for table structures in OCR results
        tables = ocr_results.get("tables", [])
        if tables:
            for table in tables:
                # Process table structure
                rows = table.get("rows", [])
                for row in rows[1:]:  # Skip header
                    if len(row) >= 3:  # At least description, quantity, amount
                        item = {
                            "description": row[0] if len(row) > 0 else "",
                            "quantity": self._parse_number(row[1]) if len(row) > 1 else 1,
                            "unit_price": self._parse_number(row[2]) if len(row) > 2 else 0,
                            "amount": self._parse_number(row[-1]) if len(row) > 2 else 0,
                        }
                        line_items.append(item)
        
        return line_items
    
    def _parse_number(self, text: str) -> float:
        """Parse number from text, handling currency symbols and commas."""
        if not text:
            return 0.0
        
        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d.]', '', str(text))
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def _map_to_canonical_schema(
        self,
        structured_data: Dict[str, Any],
        classification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Map extracted fields to canonical schema.
        
        This ensures consistent output format regardless of
        source document format.
        """
        canonical = {}
        
        # Direct mappings
        field_mappings = {
            "invoice_id": "invoice_id",
            "vendor": "vendor",
            "date": "date",
            "due_date": "due_date",
            "subtotal": "subtotal",
            "tax": "tax",
            "total": "total",
            "currency": "currency",
            "line_items": "line_items",
        }
        
        for source_key, target_key in field_mappings.items():
            if source_key in structured_data:
                value = structured_data[source_key]
                
                # Type conversion and validation
                if target_key == "date" and value:
                    # Normalize date format
                    canonical[target_key] = self._normalize_date(value)
                elif target_key in ["subtotal", "tax", "total"] and value:
                    canonical[target_key] = float(value)
                elif target_key == "line_items" and isinstance(value, list):
                    canonical[target_key] = value
                else:
                    canonical[target_key] = value
        
        # Ensure required fields have defaults
        if "total" not in canonical:
            canonical["total"] = 0.0
        if "currency" not in canonical:
            canonical["currency"] = "USD"
        if "line_items" not in canonical:
            canonical["line_items"] = []
        
        return canonical
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to ISO format."""
        # This is simplified - production would handle more formats
        try:
            # Try common formats
            formats = [
                "%m/%d/%Y",
                "%m-%d-%Y",
                "%d/%m/%Y",
                "%Y-%m-%d",
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            # If no format matches, return as-is
            return date_str
        except Exception:
            return date_str
    
    def _calculate_confidence_scores(
        self,
        structured_data: Dict[str, Any],
        ocr_results: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate confidence scores for extracted fields."""
        scores = {}
        
        # Base confidence from OCR
        base_confidence = ocr_results.get("confidence", 0.5)
        
        for field, value in structured_data.items():
            if value is None or value == "":
                scores[field] = 0.0
            elif isinstance(value, (int, float)) and value == 0:
                scores[field] = 0.3
            else:
                # Field extracted with some value
                scores[field] = min(base_confidence + 0.2, 1.0)
        
        return scores
    
    async def _enrich_data(
        self,
        canonical_schema: Dict[str, Any],
        metadata: Any
    ) -> Dict[str, Any]:
        """
        Enrich data with external sources.
        
        Examples:
        - Vendor name normalization (business registry lookup)
        - Address validation
        - Currency conversion
        - Entity resolution
        """
        enriched = {}
        
        # Placeholder for enrichment logic
        # In production, this would:
        # 1. Look up vendor in business registry
        # 2. Normalize addresses
        # 3. Convert currencies using historical rates
        # 4. Resolve entities
        
        return enriched


