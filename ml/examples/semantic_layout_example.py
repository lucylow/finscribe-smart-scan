"""
Example: Semantic Layout Understanding with PaddleOCR-VL

This example demonstrates how to use PaddleOCR-VL's semantic layout understanding
to extract structured data from financial documents with deep layout awareness.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.models.paddleocr_vl_service import PaddleOCRVLService
from app.config.settings import load_config


async def example_basic_semantic_layout():
    """Example 1: Basic semantic layout parsing"""
    print("=" * 60)
    print("Example 1: Basic Semantic Layout Parsing")
    print("=" * 60)
    
    config = load_config()
    service = PaddleOCRVLService(config)
    
    # Read a sample document (replace with your document path)
    # For this example, we'll use the mock mode
    image_bytes = b""  # In real usage, load from file
    
    try:
        # Parse with semantic layout understanding
        result = await service.parse_document_with_semantic_layout(image_bytes)
        
        # Access semantic layout
        semantic_layout = result.get("semantic_layout", {})
        regions = semantic_layout.get("regions", [])
        
        print(f"\nDetected {len(regions)} semantic regions:")
        for region in regions:
            print(f"  - {region['type']} (order: {region['reading_order']})")
            bbox = region['bbox']
            print(f"    BBox: ({bbox['x1']:.0f}, {bbox['y1']:.0f}) to ({bbox['x2']:.0f}, {bbox['y2']:.0f})")
        
        print(f"\nReading order: {semantic_layout.get('reading_order', [])}")
        
    except Exception as e:
        print(f"Error: {e}")


async def example_region_analysis():
    """Example 2: Analyze specific regions"""
    print("\n" + "=" * 60)
    print("Example 2: Region-Specific Analysis")
    print("=" * 60)
    
    config = load_config()
    service = PaddleOCRVLService(config)
    
    image_bytes = b""  # In real usage, load from file
    
    try:
        # First, get semantic layout to identify regions
        result = await service.parse_document_with_semantic_layout(image_bytes)
        semantic_layout = result.get("semantic_layout", {})
        regions = semantic_layout.get("regions", [])
        
        # Find table regions
        table_regions = [r for r in regions if r['type'] in ['table', 'line_items_table']]
        
        print(f"\nFound {len(table_regions)} table region(s):")
        for table_region in table_regions:
            print(f"\nTable Region:")
            print(f"  Type: {table_region['type']}")
            print(f"  Reading Order: {table_region['reading_order']}")
            print(f"  Confidence: {table_region['confidence']:.2%}")
            
            # Process this specific region with table recognition prompt
            bbox = table_region['bbox']
            region_bbox = {
                "x": int(bbox['x1']),
                "y": int(bbox['y1']),
                "w": int(bbox['x2'] - bbox['x1']),
                "h": int(bbox['y2'] - bbox['y1'])
            }
            
            region_result = await service.parse_region(
                image_bytes,
                region_type="line_items_table",
                bbox=region_bbox
            )
            
            print(f"  Extracted content: {region_result.get('status', 'unknown')}")
        
    except Exception as e:
        print(f"Error: {e}")


async def example_structured_output():
    """Example 3: Access structured output format"""
    print("\n" + "=" * 60)
    print("Example 3: Structured Output Format")
    print("=" * 60)
    
    config = load_config()
    service = PaddleOCRVLService(config)
    
    image_bytes = b""  # In real usage, load from file
    
    try:
        result = await service.parse_document_with_semantic_layout(image_bytes)
        semantic_layout = result.get("semantic_layout", {})
        pages = semantic_layout.get("pages", [])
        
        print(f"\nDocument has {len(pages)} page(s)")
        
        for page_idx, page in enumerate(pages):
            print(f"\n--- Page {page_idx + 1} ---")
            
            # Text blocks
            text_blocks = page.get("text_blocks", [])
            print(f"Text blocks: {len(text_blocks)}")
            for block in text_blocks[:3]:  # Show first 3
                print(f"  - [{block['type']}] {block['text'][:50]}...")
            
            # Tables
            tables = page.get("tables", [])
            print(f"Tables: {len(tables)}")
            for table in tables:
                structure = table.get("structure", {})
                print(f"  - {structure.get('num_rows', 0)} rows × {structure.get('num_cols', 0)} cols")
            
            # Images
            images = page.get("images", [])
            print(f"Images: {len(images)}")
            for img in images:
                print(f"  - Type: {img.get('type', 'unknown')}")
        
        # Export to JSON
        output_file = "semantic_layout_output.json"
        with open(output_file, "w") as f:
            json.dump(semantic_layout, f, indent=2)
        print(f"\n✓ Exported semantic layout to {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")


async def example_reading_order():
    """Example 4: Understanding reading order"""
    print("\n" + "=" * 60)
    print("Example 4: Reading Order Analysis")
    print("=" * 60)
    
    config = load_config()
    service = PaddleOCRVLService(config)
    
    image_bytes = b""  # In real usage, load from file
    
    try:
        result = await service.parse_document_with_semantic_layout(image_bytes)
        semantic_layout = result.get("semantic_layout", {})
        regions = semantic_layout.get("regions", [])
        reading_order = semantic_layout.get("reading_order", [])
        
        print(f"\nDocument reading order (top-to-bottom, left-to-right):")
        print("-" * 60)
        
        # Sort regions by reading order
        sorted_regions = sorted(regions, key=lambda r: r['reading_order'])
        
        for i, region in enumerate(sorted_regions):
            print(f"{i+1}. {region['type'].upper()}")
            bbox = region['bbox']
            print(f"   Position: ({bbox['x1']:.0f}, {bbox['y1']:.0f})")
            print(f"   Confidence: {region['confidence']:.2%}")
        
        print("\nThis reading order is crucial for:")
        print("  - Multi-column financial statements")
        print("  - Understanding relationships between headers and values")
        print("  - Correctly parsing tables with merged cells")
        print("  - Maintaining context across document sections")
        
    except Exception as e:
        print(f"Error: {e}")


async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("PaddleOCR-VL Semantic Layout Understanding Examples")
    print("=" * 60)
    print("\nNote: These examples use mock mode. For real usage:")
    print("  1. Configure PaddleOCR-VL server URL in config")
    print("  2. Load actual document images")
    print("  3. Process with real OCR service")
    print()
    
    await example_basic_semantic_layout()
    await example_region_analysis()
    await example_structured_output()
    await example_reading_order()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

