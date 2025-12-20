#!/usr/bin/env python3
"""
Utility script to inspect instruction-response pairs

This script helps visualize and validate the structure of instruction pairs
created by create_instruction_pairs.py.
"""

import json
import sys
from pathlib import Path
from collections import Counter


def inspect_jsonl(jsonl_path: str, num_samples: int = 5):
    """
    Inspect instruction pairs in a JSONL file.
    
    Args:
        jsonl_path: Path to JSONL file
        num_samples: Number of samples to display
    """
    jsonl_file = Path(jsonl_path)
    
    if not jsonl_file.exists():
        print(f"Error: File not found: {jsonl_path}")
        return
    
    print("=" * 60)
    print(f"Inspecting: {jsonl_path}")
    print("=" * 60)
    
    samples = []
    regions = Counter()
    image_paths = set()
    
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    sample = json.loads(line)
                    samples.append((line_num, sample))
                    
                    # Extract region from response
                    conversations = sample.get('conversations', [])
                    if len(conversations) >= 2:
                        response = conversations[1]['content']
                        try:
                            response_dict = json.loads(response)
                            region = response_dict.get('region', 'unknown')
                            regions[region] += 1
                        except:
                            pass
                    
                    # Track image paths
                    image_path = sample.get('image', '')
                    if image_path:
                        image_paths.add(image_path)
                        
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON on line {line_num}: {e}")
    
    print(f"\nTotal samples: {len(samples)}")
    print(f"Unique images: {len(image_paths)}")
    print(f"\nRegion distribution:")
    for region, count in regions.most_common():
        print(f"  {region}: {count}")
    
    print(f"\n{'=' * 60}")
    print(f"Sample pairs (showing first {num_samples}):")
    print("=" * 60)
    
    for idx, (line_num, sample) in enumerate(samples[:num_samples], 1):
        print(f"\n--- Sample {idx} (line {line_num}) ---")
        
        # Image path
        image_path = sample.get('image', 'N/A')
        print(f"Image: {image_path}")
        
        # Conversations
        conversations = sample.get('conversations', [])
        if len(conversations) >= 2:
            human_msg = conversations[0]
            assistant_msg = conversations[1]
            
            print(f"\nHuman ({human_msg.get('role', 'unknown')}):")
            prompt = human_msg.get('content', '')
            if len(prompt) > 150:
                print(f"  {prompt[:150]}...")
            else:
                print(f"  {prompt}")
            
            print(f"\nAssistant ({assistant_msg.get('role', 'unknown')}):")
            response = assistant_msg.get('content', '')
            
            # Try to parse and pretty-print JSON
            try:
                response_dict = json.loads(response)
                region = response_dict.get('region', 'unknown')
                content = response_dict.get('content', {})
                
                print(f"  Region: {region}")
                print(f"  Content keys: {list(content.keys()) if isinstance(content, dict) else type(content)}")
                
                # Show preview of content
                if isinstance(content, dict):
                    preview = {k: str(v)[:50] + "..." if len(str(v)) > 50 else v 
                              for k, v in list(content.items())[:3]}
                    print(f"  Content preview: {json.dumps(preview, indent=4, ensure_ascii=False)}")
                elif isinstance(content, list):
                    print(f"  Content: List with {len(content)} items")
                    if content:
                        print(f"  First item keys: {list(content[0].keys()) if isinstance(content[0], dict) else 'N/A'}")
            except json.JSONDecodeError:
                if len(response) > 200:
                    print(f"  {response[:200]}... (not JSON)")
                else:
                    print(f"  {response} (not JSON)")


def validate_structure(jsonl_path: str):
    """
    Validate that all samples have the expected structure.
    """
    jsonl_file = Path(jsonl_path)
    
    if not jsonl_file.exists():
        print(f"Error: File not found: {jsonl_path}")
        return
    
    print("=" * 60)
    print("Validating structure...")
    print("=" * 60)
    
    errors = []
    warnings = []
    valid_count = 0
    
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                sample = json.loads(line)
                
                # Check required fields
                if 'image' not in sample:
                    errors.append(f"Line {line_num}: Missing 'image' field")
                    continue
                
                if 'conversations' not in sample:
                    errors.append(f"Line {line_num}: Missing 'conversations' field")
                    continue
                
                conversations = sample['conversations']
                if not isinstance(conversations, list) or len(conversations) < 2:
                    errors.append(f"Line {line_num}: Invalid conversations format")
                    continue
                
                # Check conversation roles
                if conversations[0].get('role') != 'human':
                    warnings.append(f"Line {line_num}: First message should have role='human'")
                
                if conversations[1].get('role') != 'assistant':
                    warnings.append(f"Line {line_num}: Second message should have role='assistant'")
                
                # Validate response is JSON
                response = conversations[1].get('content', '')
                try:
                    response_dict = json.loads(response)
                    if 'region' not in response_dict:
                        warnings.append(f"Line {line_num}: Response missing 'region' field")
                    if 'content' not in response_dict:
                        warnings.append(f"Line {line_num}: Response missing 'content' field")
                except json.JSONDecodeError:
                    errors.append(f"Line {line_num}: Assistant response is not valid JSON")
                    continue
                
                valid_count += 1
                
            except json.JSONDecodeError as e:
                errors.append(f"Line {line_num}: Invalid JSON: {e}")
    
    print(f"\n✓ Valid samples: {valid_count}")
    
    if errors:
        print(f"\n✗ Errors: {len(errors)}")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    else:
        print("\n✓ No errors found!")
    
    if warnings:
        print(f"\n⚠ Warnings: {len(warnings)}")
        for warning in warnings[:10]:  # Show first 10 warnings
            print(f"  {warning}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more warnings")
    else:
        print("\n✓ No warnings!")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Inspect instruction-response pairs")
    parser.add_argument(
        "jsonl_file",
        type=str,
        help="Path to JSONL file with instruction pairs"
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="Number of samples to display (default: 5)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate structure of all samples"
    )
    
    args = parser.parse_args()
    
    if args.validate:
        validate_structure(args.jsonl_file)
    else:
        inspect_jsonl(args.jsonl_file, args.samples)


if __name__ == "__main__":
    main()

