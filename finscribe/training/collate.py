"""
Completion-only data collator for PaddleOCR-VL fine-tuning
Masks loss on prompt tokens to ensure model only learns from assistant responses
"""

import torch
from typing import List, Dict, Any

IGNORE_INDEX = -100


def collate_fn(batch: List[Dict[str, Any]], processor) -> Dict[str, torch.Tensor]:
    """
    Collates a batch of instruction samples and masks loss on prompt tokens.
    
    This is critical for proper fine-tuning: we want the model to learn
    only from the assistant's response, not from the prompt itself.
    
    Args:
        batch: List of instruction samples with 'messages' and 'images' keys
        processor: PaddleOCR-VL processor (tokenizer + image processor)
        
    Returns:
        Dictionary with input_ids, attention_mask, pixel_values, and labels
        where labels have IGNORE_INDEX for prompt tokens
    """
    texts = []
    images = []
    
    for sample in batch:
        messages = sample.get("messages", [])
        if not messages:
            continue
        
        texts.append(messages)
        # Get images from sample
        sample_images = sample.get("images", [])
        if sample_images:
            images.append(sample_images[0])  # Take first image
        else:
            images.append(None)
    
    # Process with processor
    inputs = processor(
        text=texts,
        images=images if images[0] is not None else None,
        padding=True,
        return_tensors="pt",
    )
    
    # Create labels by cloning input_ids
    labels = inputs["input_ids"].clone()
    
    # Mask prompt tokens for each sample
    for i, messages in enumerate(texts):
        if len(messages) < 2:
            # No assistant message, mask everything
            labels[i, :] = IGNORE_INDEX
            continue
        
        # Find where user message ends and assistant message begins
        user_message = messages[0]
        assistant_message = messages[1]
        
        # Tokenize user message content
        user_content = user_message.get("content", [])
        user_text = ""
        for item in user_content:
            if isinstance(item, dict) and item.get("type") == "text":
                user_text += item.get("text", "")
        
        # Tokenize to get token count
        user_tokens = processor.tokenizer(
            user_text,
            add_special_tokens=False,
            return_tensors="pt",
        ).input_ids
        
        # Mask everything up to and including the user prompt
        # Add 1 for any special tokens that might be added
        cutoff = user_tokens.shape[1] + 1
        
        # Ensure cutoff doesn't exceed sequence length
        seq_len = labels.shape[1]
        cutoff = min(cutoff, seq_len)
        
        labels[i, :cutoff] = IGNORE_INDEX
    
    # Mask padding tokens
    if processor.tokenizer.pad_token_id is not None:
        labels[labels == processor.tokenizer.pad_token_id] = IGNORE_INDEX
    
    inputs["labels"] = labels
    
    return inputs


