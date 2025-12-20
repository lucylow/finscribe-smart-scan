"""
Advanced Loss Functions for Improved Model Training

This module implements several advanced loss functions and training techniques:
1. Focal Loss - Focuses on hard examples
2. Label Smoothing - Improves generalization
3. Combined Loss - Combines multiple loss components
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Dict


class FocalLoss(nn.Module):
    """
    Focal Loss for addressing class imbalance and hard example mining.
    
    Reference: "Focal Loss for Dense Object Detection" (Lin et al., 2017)
    """
    
    def __init__(
        self,
        alpha: float = 1.0,
        gamma: float = 2.0,
        ignore_index: int = -100,
        reduction: str = 'mean'
    ):
        """
        Initialize Focal Loss.
        
        Args:
            alpha: Weighting factor for rare class. Can be float or tensor of shape (num_classes,)
            gamma: Focusing parameter (gamma=0 is equivalent to CE loss)
            ignore_index: Index to ignore in loss calculation
            reduction: 'none', 'mean', or 'sum'
        """
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.ignore_index = ignore_index
        self.reduction = reduction
    
    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Compute focal loss.
        
        Args:
            logits: Model predictions [batch_size, seq_len, vocab_size] or [batch_size * seq_len, vocab_size]
            targets: Ground truth token IDs [batch_size, seq_len] or [batch_size * seq_len]
            
        Returns:
            Scalar loss value
        """
        # Flatten if needed
        if logits.dim() == 3:
            logits = logits.view(-1, logits.size(-1))
            targets = targets.view(-1)
        
        # Compute cross-entropy loss
        ce_loss = F.cross_entropy(logits, targets, reduction='none', ignore_index=self.ignore_index)
        
        # Compute probabilities
        pt = torch.exp(-ce_loss)  # pt = p_t from paper
        
        # Compute focal loss
        focal_loss = self.alpha * (1 - pt) ** self.gamma * ce_loss
        
        # Mask out ignored tokens
        mask = (targets != self.ignore_index).float()
        focal_loss = focal_loss * mask
        
        # Apply reduction
        if self.reduction == 'none':
            return focal_loss
        elif self.reduction == 'mean':
            return focal_loss.sum() / mask.sum().clamp(min=1)
        else:  # 'sum'
            return focal_loss.sum()


class LabelSmoothingCrossEntropy(nn.Module):
    """
    Cross-entropy loss with label smoothing for better generalization.
    
    Reference: "Rethinking the Inception Architecture for Computer Vision" (Szegedy et al., 2016)
    """
    
    def __init__(
        self,
        smoothing: float = 0.1,
        ignore_index: int = -100,
        reduction: str = 'mean'
    ):
        """
        Initialize label smoothing cross-entropy loss.
        
        Args:
            smoothing: Smoothing factor (0.0 = no smoothing, 1.0 = uniform distribution)
            ignore_index: Index to ignore in loss calculation
            reduction: 'none', 'mean', or 'sum'
        """
        super().__init__()
        self.smoothing = smoothing
        self.ignore_index = ignore_index
        self.reduction = reduction
    
    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Compute label smoothing cross-entropy loss.
        
        Args:
            logits: Model predictions [batch_size, seq_len, vocab_size] or [batch_size * seq_len, vocab_size]
            targets: Ground truth token IDs [batch_size, seq_len] or [batch_size * seq_len]
            
        Returns:
            Scalar loss value
        """
        # Flatten if needed
        if logits.dim() == 3:
            logits = logits.view(-1, logits.size(-1))
            targets = targets.view(-1)
        
        vocab_size = logits.size(-1)
        log_probs = F.log_softmax(logits, dim=-1)
        
        # Create smoothed targets
        # Instead of one-hot, we use (1 - smoothing) for correct class and smoothing/(vocab_size-1) for others
        with torch.no_grad():
            true_dist = torch.zeros_like(log_probs)
            true_dist.fill_(self.smoothing / (vocab_size - 1))
            true_dist.scatter_(1, targets.unsqueeze(1), 1.0 - self.smoothing)
            
            # Mask out ignored tokens
            mask = (targets != self.ignore_index).unsqueeze(1)
            true_dist = true_dist * mask.float()
            
            # Renormalize
            true_dist = true_dist / true_dist.sum(dim=1, keepdim=True).clamp(min=1e-8)
        
        # Compute KL divergence (which is equivalent to cross-entropy with smoothed labels)
        kl_div = F.kl_div(log_probs, true_dist, reduction='none').sum(dim=1)
        
        # Mask out ignored tokens
        mask = (targets != self.ignore_index).float()
        kl_div = kl_div * mask
        
        # Apply reduction
        if self.reduction == 'none':
            return kl_div
        elif self.reduction == 'mean':
            return kl_div.sum() / mask.sum().clamp(min=1)
        else:  # 'sum'
            return kl_div.sum()


class CombinedLoss(nn.Module):
    """
    Combined loss function that can mix multiple loss components.
    
    Supports:
    - Standard cross-entropy
    - Focal loss
    - Label smoothing
    - Weighted loss (by region/field)
    """
    
    def __init__(
        self,
        use_focal: bool = False,
        use_label_smoothing: bool = False,
        focal_alpha: float = 1.0,
        focal_gamma: float = 2.0,
        label_smoothing: float = 0.1,
        region_weights: Optional[Dict[str, float]] = None,
        ignore_index: int = -100
    ):
        """
        Initialize combined loss.
        
        Args:
            use_focal: Whether to use focal loss
            use_label_smoothing: Whether to use label smoothing
            focal_alpha: Focal loss alpha parameter
            focal_gamma: Focal loss gamma parameter
            label_smoothing: Label smoothing factor
            region_weights: Optional weights for different regions
            ignore_index: Index to ignore in loss calculation
        """
        super().__init__()
        self.use_focal = use_focal
        self.use_label_smoothing = use_label_smoothing
        self.region_weights = region_weights or {}
        self.ignore_index = ignore_index
        
        # Initialize base loss
        # Note: Focal loss and label smoothing can be used together, but we prioritize focal loss
        if use_focal:
            self.base_loss = FocalLoss(
                alpha=focal_alpha,
                gamma=focal_gamma,
                ignore_index=ignore_index
            )
            # Label smoothing can still be applied if both are enabled
            self.label_smoothing = label_smoothing if use_label_smoothing else 0.0
        elif use_label_smoothing:
            self.base_loss = LabelSmoothingCrossEntropy(
                smoothing=label_smoothing,
                ignore_index=ignore_index
            )
            self.label_smoothing = label_smoothing
        else:
            self.base_loss = nn.CrossEntropyLoss(
                ignore_index=ignore_index,
                reduction='none'
            )
            self.label_smoothing = 0.0
    
    def forward(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
        region: Optional[str] = None
    ) -> torch.Tensor:
        """
        Compute combined loss.
        
        Args:
            logits: Model predictions [batch_size, seq_len, vocab_size]
            targets: Ground truth token IDs [batch_size, seq_len]
            region: Optional region name for weighting
            
        Returns:
            Scalar loss value
        """
        # Apply label smoothing if needed (for standard CE or focal)
        if self.label_smoothing > 0 and not isinstance(self.base_loss, LabelSmoothingCrossEntropy):
            # Apply smoothing to targets
            vocab_size = logits.size(-1)
            if logits.dim() == 3:
                logits_flat = logits.view(-1, vocab_size)
                targets_flat = targets.view(-1)
            else:
                logits_flat = logits
                targets_flat = targets
            
            # Create smoothed targets
            with torch.no_grad():
                true_dist = torch.zeros_like(logits_flat)
                true_dist.fill_(self.label_smoothing / (vocab_size - 1))
                true_dist.scatter_(1, targets_flat.unsqueeze(1), 1.0 - self.label_smoothing)
                
                mask = (targets_flat != self.ignore_index).unsqueeze(1)
                true_dist = true_dist * mask.float()
                true_dist = true_dist / true_dist.sum(dim=1, keepdim=True).clamp(min=1e-8)
            
            # Use KL divergence
            log_probs = F.log_softmax(logits_flat, dim=-1)
            loss = F.kl_div(log_probs, true_dist, reduction='none').sum(dim=1)
            
            # Reshape and mask
            if logits.dim() == 3:
                loss = loss.view(targets.shape)
                mask = (targets != self.ignore_index).float()
            else:
                mask = (targets_flat != self.ignore_index).float()
            
            loss = (loss * mask).sum() / mask.sum().clamp(min=1)
        else:
            # Use base loss directly
            if logits.dim() == 3:
                # Standard cross-entropy expects flattened inputs
                if isinstance(self.base_loss, nn.CrossEntropyLoss):
                    loss = self.base_loss(logits.view(-1, logits.size(-1)), targets.view(-1))
                else:
                    loss = self.base_loss(logits, targets)
            else:
                loss = self.base_loss(logits, targets)
        
        # Apply region weighting if specified
        if region and region in self.region_weights:
            weight = self.region_weights[region]
            loss = loss * weight
        
        return loss


def create_loss_function(config: Dict) -> nn.Module:
    """
    Factory function to create loss function from config.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Loss function module
    """
    loss_config = config.get('loss', {})
    
    # Extract configuration
    use_focal = loss_config.get('use_focal', False)
    use_label_smoothing = loss_config.get('use_label_smoothing', False)
    focal_alpha = loss_config.get('focal_alpha', 1.0)
    focal_gamma = loss_config.get('focal_gamma', 2.0)
    label_smoothing = loss_config.get('label_smoothing', 0.0)
    region_weights = loss_config.get('region_weights', {})
    
    # If region weights are specified in weights.field_weights, use those
    if 'weights' in loss_config and 'field_weights' in loss_config['weights']:
        region_weights.update(loss_config['weights']['field_weights'])
    
    return CombinedLoss(
        use_focal=use_focal,
        use_label_smoothing=use_label_smoothing,
        focal_alpha=focal_alpha,
        focal_gamma=focal_gamma,
        label_smoothing=label_smoothing,
        region_weights=region_weights
    )

