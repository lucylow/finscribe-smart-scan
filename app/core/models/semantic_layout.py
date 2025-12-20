"""
Semantic Layout Understanding Module

This module implements PaddleOCR-VL's two-stage semantic layout understanding:
1. Stage 1: Layout Analysis (PP-DocLayoutV2) - Detects and classifies semantic regions with reading order
2. Stage 2: Element Recognition (PaddleOCR-VL-0.9B) - Recognizes content and internal structure

This enables deep structural and semantic understanding of document layout, crucial for
financial documents where relationships between headers, values, tables, and their order
are essential for accurate structured data extraction.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RegionType(Enum):
    """Semantic region types detected by layout analysis"""
    TEXT_BLOCK = "text_block"
    TABLE = "table"
    FORMULA = "formula"
    IMAGE = "image"
    TITLE = "title"
    HEADER = "header"
    FOOTER = "footer"
    VENDOR_BLOCK = "vendor_block"
    CLIENT_BLOCK = "client_block"
    LINE_ITEMS_TABLE = "line_items_table"
    FINANCIAL_SUMMARY = "financial_summary"


@dataclass
class BoundingBox:
    """Bounding box coordinates"""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float = 1.0
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get center point of bounding box"""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)
    
    @property
    def width(self) -> float:
        """Get width of bounding box"""
        return self.x2 - self.x1
    
    @property
    def height(self) -> float:
        """Get height of bounding box"""
        return self.y2 - self.y1
    
    @property
    def area(self) -> float:
        """Get area of bounding box"""
        return self.width * self.height


@dataclass
class SemanticRegion:
    """
    Represents a semantic region detected by layout analysis (Stage 1).
    Each region has a type, position, and reading order.
    """
    region_type: RegionType
    bbox: BoundingBox
    reading_order: int  # Order in which this region should be read
    confidence: float = 1.0
    page_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "type": self.region_type.value,
            "bbox": {
                "x1": self.bbox.x1,
                "y1": self.bbox.y1,
                "x2": self.bbox.x2,
                "y2": self.bbox.y2,
                "confidence": self.bbox.confidence
            },
            "reading_order": self.reading_order,
            "confidence": self.confidence,
            "page_index": self.page_index,
            "metadata": self.metadata
        }


@dataclass
class RecognizedElement:
    """
    Represents content recognized from a semantic region (Stage 2).
    Contains the actual text, structure, and internal organization.
    """
    region: SemanticRegion
    content: Dict[str, Any]  # Structured content (text, table cells, etc.)
    internal_structure: Optional[Dict[str, Any]] = None  # For tables: rows, columns, merged cells
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "region": self.region.to_dict(),
            "content": self.content,
            "internal_structure": self.internal_structure,
            "confidence": self.confidence
        }


@dataclass
class SemanticLayoutResult:
    """
    Complete semantic layout understanding result from both stages.
    Provides structured representation of the entire document with semantic relationships.
    """
    pages: List[Dict[str, Any]] = field(default_factory=list)
    regions: List[SemanticRegion] = field(default_factory=list)
    recognized_elements: List[RecognizedElement] = field(default_factory=list)
    reading_order: List[int] = field(default_factory=list)  # Ordered list of region indices
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to structured JSON format matching PaddleOCR-VL output"""
        # Group elements by page
        pages_dict = {}
        for region in self.regions:
            page_idx = region.page_index
            if page_idx not in pages_dict:
                pages_dict[page_idx] = {
                    "text_blocks": [],
                    "tables": [],
                    "images": [],
                    "formulas": []
                }
        
        # Add recognized elements to appropriate page sections
        for element in self.recognized_elements:
            page_idx = element.region.page_index
            region_type = element.region.region_type
            
            if region_type == RegionType.TABLE or region_type == RegionType.LINE_ITEMS_TABLE:
                pages_dict[page_idx]["tables"].append({
                    "html": element.content.get("html", ""),
                    "bbox": [
                        element.region.bbox.x1,
                        element.region.bbox.y1,
                        element.region.bbox.x2,
                        element.region.bbox.y2
                    ],
                    "structure": element.internal_structure,
                    "reading_order": element.region.reading_order
                })
            elif region_type == RegionType.IMAGE:
                pages_dict[page_idx]["images"].append({
                    "type": element.content.get("type", "unknown"),
                    "bbox": [
                        element.region.bbox.x1,
                        element.region.bbox.y1,
                        element.region.bbox.x2,
                        element.region.bbox.y2
                    ],
                    "reading_order": element.region.reading_order
                })
            elif region_type == RegionType.FORMULA:
                pages_dict[page_idx]["formulas"].append({
                    "formula": element.content.get("formula", ""),
                    "bbox": [
                        element.region.bbox.x1,
                        element.region.bbox.y1,
                        element.region.bbox.x2,
                        element.region.bbox.y2
                    ],
                    "reading_order": element.region.reading_order
                })
            else:
                # Text blocks
                pages_dict[page_idx]["text_blocks"].append({
                    "text": element.content.get("text", ""),
                    "type": region_type.value,
                    "bbox": [
                        element.region.bbox.x1,
                        element.region.bbox.y1,
                        element.region.bbox.x2,
                        element.region.bbox.y2
                    ],
                    "reading_order": element.region.reading_order
                })
        
        # Convert to list format
        pages_list = [
            pages_dict[i] for i in sorted(pages_dict.keys())
        ]
        
        return {
            "pages": pages_list,
            "regions": [r.to_dict() for r in sorted(self.regions, key=lambda x: x.reading_order)],
            "reading_order": self.reading_order,
            "metadata": self.metadata
        }


class SemanticLayoutAnalyzer:
    """
    Analyzes semantic layout from PaddleOCR-VL output.
    
    This class processes the raw output from PaddleOCR-VL to extract:
    1. Semantic regions with their types and reading order (Stage 1 results)
    2. Recognized content and structure for each region (Stage 2 results)
    """
    
    def __init__(self):
        """Initialize the semantic layout analyzer"""
        pass
    
    def analyze_layout(self, ocr_results: Dict[str, Any]) -> SemanticLayoutResult:
        """
        Analyze OCR results to extract semantic layout understanding.
        
        This processes the output from PaddleOCR-VL which includes both:
        - Layout analysis results (regions, types, reading order)
        - Element recognition results (content, structure)
        
        Args:
            ocr_results: Raw output from PaddleOCR-VL service
            
        Returns:
            SemanticLayoutResult with structured semantic understanding
        """
        result = SemanticLayoutResult()
        
        # Extract regions from OCR results
        regions = self._extract_regions(ocr_results)
        result.regions = regions
        
        # Extract reading order
        result.reading_order = self._extract_reading_order(regions)
        
        # Extract recognized elements
        recognized_elements = self._extract_recognized_elements(ocr_results, regions)
        result.recognized_elements = recognized_elements
        
        # Extract metadata
        result.metadata = {
            "model_version": ocr_results.get("model_version", "PaddleOCR-VL-0.9B"),
            "status": ocr_results.get("status", "success"),
            "latency_ms": ocr_results.get("latency_ms", 0),
            "models_used": ocr_results.get("models_used", ["PaddleOCR-VL-0.9B"])
        }
        
        return result
    
    def _extract_regions(self, ocr_results: Dict[str, Any]) -> List[SemanticRegion]:
        """
        Extract semantic regions from OCR results.
        
        PaddleOCR-VL's layout analysis (PP-DocLayoutV2) provides:
        - Region types (text, table, formula, image)
        - Bounding boxes
        - Reading order (implicit from coordinates or explicit)
        """
        regions = []
        
        # Check for explicit regions in OCR results
        if "regions" in ocr_results:
            for i, region_data in enumerate(ocr_results["regions"]):
                region_type_str = region_data.get("type", "text_block")
                try:
                    region_type = RegionType(region_type_str)
                except ValueError:
                    # Map common aliases
                    region_type = self._map_region_type(region_type_str)
                
                # Extract bounding box
                bbox = self._extract_bbox_from_region(region_data, ocr_results, i)
                
                # Determine reading order (from explicit field or infer from position)
                reading_order = region_data.get("reading_order", i)
                
                region = SemanticRegion(
                    region_type=region_type,
                    bbox=bbox,
                    reading_order=reading_order,
                    confidence=region_data.get("confidence", 1.0),
                    page_index=region_data.get("page_index", 0),
                    metadata=region_data.get("metadata", {})
                )
                regions.append(region)
        
        # If no explicit regions, infer from bboxes and tokens
        elif "bboxes" in ocr_results and "tokens" in ocr_results:
            regions = self._infer_regions_from_bboxes(ocr_results)
        
        # Sort by reading order (top-to-bottom, left-to-right)
        regions.sort(key=lambda r: (r.bbox.y1, r.bbox.x1))
        
        # Assign reading order if not present
        for i, region in enumerate(regions):
            if not hasattr(region, 'reading_order') or region.reading_order is None:
                region.reading_order = i
        
        return regions
    
    def _extract_bbox_from_region(
        self, 
        region_data: Dict[str, Any], 
        ocr_results: Dict[str, Any],
        region_index: int
    ) -> BoundingBox:
        """Extract bounding box from region data or associated bbox"""
        # Check if bbox is in region_data
        if "bbox" in region_data:
            bbox_data = region_data["bbox"]
            if isinstance(bbox_data, list) and len(bbox_data) >= 4:
                return BoundingBox(
                    x1=float(bbox_data[0]),
                    y1=float(bbox_data[1]),
                    x2=float(bbox_data[2]),
                    y2=float(bbox_data[3]),
                    confidence=bbox_data[4] if len(bbox_data) > 4 else 1.0
                )
            elif isinstance(bbox_data, dict):
                return BoundingBox(
                    x1=float(bbox_data.get("x1", bbox_data.get("x", 0))),
                    y1=float(bbox_data.get("y1", bbox_data.get("y", 0))),
                    x2=float(bbox_data.get("x2", bbox_data.get("x", 0) + bbox_data.get("w", 0))),
                    y2=float(bbox_data.get("y2", bbox_data.get("y", 0) + bbox_data.get("h", 0))),
                    confidence=bbox_data.get("confidence", 1.0)
                )
        
        # Try to get from bboxes array
        if "bboxes" in ocr_results and region_index < len(ocr_results["bboxes"]):
            bbox_data = ocr_results["bboxes"][region_index]
            if isinstance(bbox_data, dict):
                x = bbox_data.get("x", 0)
                y = bbox_data.get("y", 0)
                w = bbox_data.get("w", 0)
                h = bbox_data.get("h", 0)
                return BoundingBox(
                    x1=float(x),
                    y1=float(y),
                    x2=float(x + w),
                    y2=float(y + h),
                    confidence=bbox_data.get("confidence", 1.0)
                )
        
        # Default empty bbox
        return BoundingBox(x1=0, y1=0, x2=0, y2=0, confidence=0.0)
    
    def _infer_regions_from_bboxes(self, ocr_results: Dict[str, Any]) -> List[SemanticRegion]:
        """Infer semantic regions from bboxes and tokens when explicit regions aren't available"""
        regions = []
        bboxes = ocr_results.get("bboxes", [])
        tokens = ocr_results.get("tokens", [])
        
        # Group bboxes by region_type if available
        region_groups = {}
        for i, bbox_data in enumerate(bboxes):
            region_type_str = bbox_data.get("region_type", "text_block")
            if region_type_str not in region_groups:
                region_groups[region_type_str] = []
            region_groups[region_type_str].append((i, bbox_data))
        
        # Create regions from groups
        reading_order = 0
        for region_type_str, bbox_group in region_groups.items():
            try:
                region_type = RegionType(region_type_str)
            except ValueError:
                region_type = self._map_region_type(region_type_str)
            
            # Merge bboxes in the same group to create a region
            if bbox_group:
                # Use the first bbox as representative, or merge all
                first_idx, first_bbox = bbox_group[0]
                bbox = self._dict_to_bbox(first_bbox)
                
                region = SemanticRegion(
                    region_type=region_type,
                    bbox=bbox,
                    reading_order=reading_order,
                    confidence=first_bbox.get("confidence", 1.0),
                    page_index=first_bbox.get("page_index", 0)
                )
                regions.append(region)
                reading_order += 1
        
        return regions
    
    def _dict_to_bbox(self, bbox_dict: Dict[str, Any]) -> BoundingBox:
        """Convert bbox dictionary to BoundingBox object"""
        if isinstance(bbox_dict, dict):
            x = bbox_dict.get("x", 0)
            y = bbox_dict.get("y", 0)
            w = bbox_dict.get("w", 0)
            h = bbox_dict.get("h", 0)
            return BoundingBox(
                x1=float(x),
                y1=float(y),
                x2=float(x + w),
                y2=float(y + h),
                confidence=bbox_dict.get("confidence", 1.0)
            )
        return BoundingBox(x1=0, y1=0, x2=0, y2=0, confidence=0.0)
    
    def _map_region_type(self, region_type_str: str) -> RegionType:
        """Map common region type strings to RegionType enum"""
        mapping = {
            "text": RegionType.TEXT_BLOCK,
            "text_block": RegionType.TEXT_BLOCK,
            "table": RegionType.TABLE,
            "line_items": RegionType.LINE_ITEMS_TABLE,
            "line_items_table": RegionType.LINE_ITEMS_TABLE,
            "formula": RegionType.FORMULA,
            "image": RegionType.IMAGE,
            "title": RegionType.TITLE,
            "header": RegionType.HEADER,
            "footer": RegionType.FOOTER,
            "vendor": RegionType.VENDOR_BLOCK,
            "vendor_block": RegionType.VENDOR_BLOCK,
            "client": RegionType.CLIENT_BLOCK,
            "client_block": RegionType.CLIENT_BLOCK,
            "summary": RegionType.FINANCIAL_SUMMARY,
            "financial_summary": RegionType.FINANCIAL_SUMMARY,
        }
        return mapping.get(region_type_str.lower(), RegionType.TEXT_BLOCK)
    
    def _extract_reading_order(self, regions: List[SemanticRegion]) -> List[int]:
        """Extract reading order from regions"""
        # Sort by reading_order attribute
        sorted_regions = sorted(regions, key=lambda r: r.reading_order)
        return [r.reading_order for r in sorted_regions]
    
    def _extract_recognized_elements(
        self, 
        ocr_results: Dict[str, Any],
        regions: List[SemanticRegion]
    ) -> List[RecognizedElement]:
        """
        Extract recognized content from each region (Stage 2 results).
        
        For each semantic region, extract:
        - Text content (for text blocks)
        - Table structure (for tables)
        - Formula representation (for formulas)
        - Image metadata (for images)
        """
        elements = []
        
        # Map regions by index for quick lookup
        region_map = {i: region for i, region in enumerate(regions)}
        
        # Extract content from tokens/bboxes
        tokens = ocr_results.get("tokens", [])
        bboxes = ocr_results.get("bboxes", [])
        
        # Group tokens by region
        region_content = {}
        for i, token in enumerate(tokens):
            # Find which region this token belongs to
            region_idx = self._find_region_for_token(i, bboxes, regions)
            if region_idx is not None:
                if region_idx not in region_content:
                    region_content[region_idx] = []
                region_content[region_idx].append(token)
        
        # Create recognized elements for each region
        for region_idx, region in region_map.items():
            tokens_in_region = region_content.get(region_idx, [])
            
            # Extract content based on region type
            if region.region_type in [RegionType.TABLE, RegionType.LINE_ITEMS_TABLE]:
                content, structure = self._extract_table_content(tokens_in_region)
            elif region.region_type == RegionType.FORMULA:
                content = self._extract_formula_content(tokens_in_region)
                structure = None
            elif region.region_type == RegionType.IMAGE:
                content = self._extract_image_content(region)
                structure = None
            else:
                # Text block
                content = self._extract_text_content(tokens_in_region)
                structure = None
            
            element = RecognizedElement(
                region=region,
                content=content,
                internal_structure=structure,
                confidence=region.confidence
            )
            elements.append(element)
        
        return elements
    
    def _find_region_for_token(
        self, 
        token_idx: int, 
        bboxes: List[Dict[str, Any]], 
        regions: List[SemanticRegion]
    ) -> Optional[int]:
        """Find which region a token belongs to based on bbox overlap"""
        if token_idx >= len(bboxes):
            return None
        
        token_bbox = self._dict_to_bbox(bboxes[token_idx])
        
        # Find region with maximum overlap
        best_region_idx = None
        best_overlap = 0.0
        
        for i, region in enumerate(regions):
            overlap = self._calculate_overlap(token_bbox, region.bbox)
            if overlap > best_overlap:
                best_overlap = overlap
                best_region_idx = i
        
        return best_region_idx if best_overlap > 0.1 else None  # 10% overlap threshold
    
    def _calculate_overlap(self, bbox1: BoundingBox, bbox2: BoundingBox) -> float:
        """Calculate overlap ratio between two bounding boxes"""
        # Calculate intersection
        x1 = max(bbox1.x1, bbox2.x1)
        y1 = max(bbox1.y1, bbox2.y1)
        x2 = min(bbox1.x2, bbox2.x2)
        y2 = min(bbox1.y2, bbox2.y2)
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        union = bbox1.area + bbox2.area - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_text_content(self, tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract text content from tokens"""
        text_parts = [token.get("text", "") for token in tokens]
        return {
            "text": " ".join(text_parts),
            "tokens": text_parts
        }
    
    def _extract_table_content(
        self, 
        tokens: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Extract table structure from tokens"""
        # For now, return basic structure
        # In a full implementation, this would parse table cells, rows, columns
        rows = []
        for token in tokens:
            text = token.get("text", "")
            if "|" in text or "\t" in text:
                # Likely a table row
                cells = [cell.strip() for cell in text.split("|") if cell.strip()]
                rows.append(cells)
        
        content = {
            "html": self._table_to_html(rows),
            "rows": rows
        }
        
        structure = {
            "num_rows": len(rows),
            "num_cols": max(len(row) for row in rows) if rows else 0,
            "has_header": len(rows) > 0
        }
        
        return content, structure
    
    def _table_to_html(self, rows: List[List[str]]) -> str:
        """Convert table rows to HTML"""
        if not rows:
            return "<table></table>"
        
        html = "<table>"
        for i, row in enumerate(rows):
            tag = "th" if i == 0 else "td"
            html += "<tr>"
            for cell in row:
                html += f"<{tag}>{cell}</{tag}>"
            html += "</tr>"
        html += "</table>"
        return html
    
    def _extract_formula_content(self, tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract formula content"""
        formula_text = " ".join(token.get("text", "") for token in tokens)
        return {
            "formula": formula_text,
            "type": "mathematical"
        }
    
    def _extract_image_content(self, region: SemanticRegion) -> Dict[str, Any]:
        """Extract image metadata"""
        return {
            "type": region.metadata.get("image_type", "unknown"),
            "description": region.metadata.get("description", "")
        }

