"""
Custom Weighted Loss Function for Table Cell Tokens

This module implements special loss weighting for table cells vs regular text,
as specified in Phase 2 requirements. Table cell tokens (in line item tables)
receive higher loss weights to ensure better accuracy for structured data extraction.
"""

import torch
import torch.nn as nn
from typing import Dict, List, Optional, Tuple


class WeightedCrossEntropyLoss(nn.Module):
    """
    Cross-entropy loss with token-level weighting.
    
    Higher weights are applied to tokens that are part of table cells,
    financial summaries, and other critical structured fields.
    """
    
    def __init__(
        self,
        table_cell_weight: float = 2.0,
        regular_token_weight: float = 1.0,
        field_weights: Optional[Dict[str, float]] = None,
        ignore_index: int = -100
    ):
        """
        Initialize weighted cross-entropy loss.
        
        Args:
            table_cell_weight: Weight multiplier for table cell tokens
            regular_token_weight: Weight multiplier for regular text tokens
            field_weights: Optional field-specific weights (e.g., {"line_item_table": 2.5})
            ignore_index: Index to ignore in loss calculation (typically padding tokens)
        """
        super().__init__()
        self.table_cell_weight = table_cell_weight
        self.regular_token_weight = regular_token_weight
        self.field_weights = field_weights or {}
        self.ignore_index = ignore_index
        
        # Base cross-entropy loss (we'll weight it manually)
        self.ce_loss = nn.CrossEntropyLoss(reduction='none', ignore_index=ignore_index)
    
    def _identify_table_tokens(
        self,
        input_ids: torch.Tensor,
        token_metadata: Optional[Dict[str, List[Tuple[int, int]]]] = None
    ) -> torch.Tensor:
        """
        Identify which tokens are part of table cells.
        
        This is a simplified version. In a full implementation, you would:
        1. Use token position information to map tokens to fields
        2. Check if tokens are within table cell boundaries
        3. Use special tokens or markers to identify table regions
        
        Args:
            input_ids: Token IDs [batch_size, seq_len]
            token_metadata: Optional metadata mapping token positions to fields
            
        Returns:
            Boolean tensor [batch_size, seq_len] indicating table cell tokens
        """
        batch_size, seq_len = input_ids.shape
        is_table_token = torch.zeros(batch_size, seq_len, dtype=torch.bool, device=input_ids.device)
        
        # This is a placeholder - in practice, you would:
        # 1. Parse the response structure to identify table tokens
        # 2. Use position embeddings or special markers
        # 3. Check against known table-related tokens/patterns
        
        # Example: Identify tokens in JSON-like structures that might be tables
        # This is a heuristic approach - for production, use proper parsing
        
        return is_table_token
    
    def forward(
        self,
        logits: torch.Tensor,
        labels: torch.Tensor,
        token_metadata: Optional[Dict[str, List[Tuple[int, int]]]] = None,
        current_region: Optional[str] = None
    ) -> torch.Tensor:
        """
        Compute weighted cross-entropy loss.
        
        Args:
            logits: Model predictions [batch_size, seq_len, vocab_size]
            labels: Ground truth token IDs [batch_size, seq_len]
            token_metadata: Optional metadata for token-level weighting
            current_region: Current semantic region being processed (for field-level weighting)
            
        Returns:
            Scalar loss value
        """
        batch_size, seq_len, vocab_size = logits.shape
        
        # Reshape for cross-entropy: [batch_size * seq_len, vocab_size]
        logits_flat = logits.view(-1, vocab_size)
        labels_flat = labels.view(-1)
        
        # Compute per-token losses
        per_token_loss = self.ce_loss(logits_flat, labels_flat)
        
        # Reshape back to [batch_size, seq_len]
        per_token_loss = per_token_loss.view(batch_size, seq_len)
        
        # Create weight tensor
        weights = torch.ones_like(per_token_loss) * self.regular_token_weight
        
        # Apply table cell weighting if metadata is available
        if token_metadata is not None:
            is_table_token = self._identify_table_tokens(labels, token_metadata)
            weights[is_table_token] = self.table_cell_weight
        
        # Apply field-level weighting if region is specified
        if current_region and current_region in self.field_weights:
            field_weight = self.field_weights[current_region]
            weights = weights * field_weight
        
        # Apply weights and compute mean (ignoring padding tokens)
        masked_loss = per_token_loss * weights
        valid_tokens = (labels_flat != self.ignore_index).view(batch_size, seq_len)
        
        if valid_tokens.sum() > 0:
            loss = masked_loss[valid_tokens].sum() / valid_tokens.sum()
        else:
            loss = masked_loss.mean()
        
        return loss


class FieldAwareWeightedLoss(nn.Module):
    """
    Advanced loss function that uses response structure to identify field types.
    
    This loss function parses the JSON response to determine which tokens belong
    to which fields, then applies appropriate weights.
    """
    
    def __init__(
        self,
        field_weights: Dict[str, float],
        base_weight: float = 1.0,
        ignore_index: int = -100
    ):
        """
        Initialize field-aware weighted loss.
        
        Args:
            field_weights: Mapping of field names to weights
                          e.g., {"line_item_table": 2.5, "financial_summary": 2.0}
            base_weight: Base weight for unlabeled tokens
            ignore_index: Index to ignore in loss calculation
        """
        super().__init__()
        self.field_weights = field_weights
        self.base_weight = base_weight
        self.ignore_index = ignore_index
        self.ce_loss = nn.CrossEntropyLoss(reduction='none', ignore_index=ignore_index)
    
    def _parse_response_structure(self, response_text: str) -> Dict[str, List[Tuple[int, int]]]:
        """
        Parse JSON response to identify field boundaries.
        
        Returns mapping of field names to (start_token, end_token) positions.
        
        This is a conceptual implementation - in practice, you would:
        1. Tokenize the response text
        2. Parse the JSON structure
        3. Map JSON keys/paths to token positions
        4. Return field boundaries
        """
        # Placeholder implementation
        # In practice, integrate with your tokenizer and JSON parser
        return {}
    
    def forward(
        self,
        logits: torch.Tensor,
        labels: torch.Tensor,
        response_texts: Optional[List[str]] = None
    ) -> torch.Tensor:
        """
        Compute field-aware weighted loss.
        
        Args:
            logits: Model predictions [batch_size, seq_len, vocab_size]
            labels: Ground truth token IDs [batch_size, seq_len]
            response_texts: Optional response texts for parsing structure
            
        Returns:
            Scalar loss value
        """
        batch_size, seq_len, vocab_size = logits.shape
        
        logits_flat = logits.view(-1, vocab_size)
        labels_flat = labels.view(-1)
        
        per_token_loss = self.ce_loss(logits_flat, labels_flat)
        per_token_loss = per_token_loss.view(batch_size, seq_len)
        
        # Initialize weights
        weights = torch.ones_like(per_token_loss) * self.base_weight
        
        # If response texts are provided, parse structure and apply field weights
        if response_texts is not None:
            for batch_idx, response_text in enumerate(response_texts):
                field_boundaries = self._parse_response_structure(response_text)
                for field_name, boundaries in field_boundaries.items():
                    if field_name in self.field_weights:
                        field_weight = self.field_weights[field_name]
                        for start_token, end_token in boundaries:
                            if start_token < seq_len and end_token < seq_len:
                                weights[batch_idx, start_token:end_token] = field_weight
        
        # Apply weights
        masked_loss = per_token_loss * weights
        valid_tokens = (labels_flat != self.ignore_index).view(batch_size, seq_len)
        
        if valid_tokens.sum() > 0:
            loss = masked_loss[valid_tokens].sum() / valid_tokens.sum()
        else:
            loss = masked_loss.mean()
        
        return loss


def get_loss_function(config: dict) -> nn.Module:
    """
    Factory function to create appropriate loss function from config.
    
    Args:
        config: Configuration dictionary from finetune_config.yaml
        
    Returns:
        Loss function module
    """
    loss_config = config.get('loss', {})
    
    if not loss_config.get('weighted', False):
        # Standard cross-entropy loss
        return nn.CrossEntropyLoss(ignore_index=-100)
    
    # Weighted loss
    field_weights = loss_config.get('weights', {}).get('field_weights', {})
    
    if field_weights:
        # Use field-aware loss if field weights are specified
        return FieldAwareWeightedLoss(
            field_weights=field_weights,
            base_weight=loss_config.get('weights', {}).get('regular_token', 1.0)
        )
    else:
        # Use simple weighted loss
        return WeightedCrossEntropyLoss(
            table_cell_weight=loss_config.get('weights', {}).get('table_cell_token', 2.0),
            regular_token_weight=loss_config.get('weights', {}).get('regular_token', 1.0)
        )

