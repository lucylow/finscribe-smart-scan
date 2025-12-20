"""
Learning Rate Finder Utility

This module implements a learning rate finder to help identify optimal learning rates
for training. Based on the technique described in "Cyclical Learning Rates for Training
Neural Networks" by Leslie Smith.
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from transformers import Trainer, TrainingArguments
from typing import Optional, Dict, List, Tuple
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class LearningRateFinder:
    """
    Learning rate finder that tests a range of learning rates and identifies optimal values.
    """
    
    def __init__(
        self,
        model: nn.Module,
        train_dataloader: DataLoader,
        optimizer_class: type = torch.optim.AdamW,
        start_lr: float = 1e-8,
        end_lr: float = 1e-1,
        num_iterations: int = 100,
        beta: float = 0.98,
        device: Optional[torch.device] = None
    ):
        """
        Initialize learning rate finder.
        
        Args:
            model: Model to test
            train_dataloader: Training dataloader
            optimizer_class: Optimizer class to use
            start_lr: Starting learning rate (very small)
            end_lr: Ending learning rate (larger)
            num_iterations: Number of iterations to run
            beta: Smoothing factor for loss (0.98 recommended)
            device: Device to run on
        """
        self.model = model
        self.train_dataloader = train_dataloader
        self.optimizer_class = optimizer_class
        self.start_lr = start_lr
        self.end_lr = end_lr
        self.num_iterations = num_iterations
        self.beta = beta
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.lrs = []
        self.losses = []
        self.smoothed_losses = []
        self.best_lr = None
    
    def find(self) -> Tuple[List[float], List[float], Optional[float]]:
        """
        Run learning rate finder.
        
        Returns:
            Tuple of (learning_rates, losses, suggested_lr)
        """
        logger.info("Starting learning rate finder...")
        logger.info(f"Testing LRs from {self.start_lr:.2e} to {self.end_lr:.2e}")
        
        # Save original model state
        original_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
        original_state = {k: v for k, v in original_state.items()}
        
        # Move model to device
        self.model.to(self.device)
        self.model.train()
        
        # Create optimizer with initial learning rate
        optimizer = self.optimizer_class(self.model.parameters(), lr=self.start_lr)
        
        # Exponential learning rate schedule
        lr_mult = (self.end_lr / self.start_lr) ** (1.0 / self.num_iterations)
        
        # Initialize
        avg_loss = 0.0
        best_loss = float('inf')
        lr_iter = iter(self.train_dataloader)
        
        try:
            for iteration in range(self.num_iterations):
                # Get next batch
                try:
                    batch = next(lr_iter)
                except StopIteration:
                    lr_iter = iter(self.train_dataloader)
                    batch = next(lr_iter)
                
                # Move batch to device
                batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
                
                # Update learning rate
                current_lr = self.start_lr * (lr_mult ** iteration)
                for param_group in optimizer.param_groups:
                    param_group['lr'] = current_lr
                
                # Forward pass
                optimizer.zero_grad()
                
                # Extract inputs and labels
                inputs = {k: v for k, v in batch.items() if k != 'labels'}
                labels = batch.get('labels', None)
                
                if labels is not None:
                    outputs = self.model(**inputs, labels=labels)
                    loss = outputs.loss if hasattr(outputs, 'loss') else outputs[0]
                else:
                    outputs = self.model(**inputs)
                    loss = outputs.loss if hasattr(outputs, 'loss') else outputs[0]
                
                # Backward pass
                loss.backward()
                optimizer.step()
                
                # Smooth loss
                avg_loss = self.beta * avg_loss + (1 - self.beta) * loss.item()
                smoothed_loss = avg_loss / (1 - self.beta ** (iteration + 1))
                
                # Record
                self.lrs.append(current_lr)
                self.losses.append(loss.item())
                self.smoothed_losses.append(smoothed_loss)
                
                # Track best loss
                if smoothed_loss < best_loss:
                    best_loss = smoothed_loss
                
                # Stop if loss explodes
                if iteration > 10 and smoothed_loss > 4 * best_loss:
                    logger.warning(f"Loss exploded at iteration {iteration}, stopping early")
                    break
                
                if (iteration + 1) % 10 == 0:
                    logger.info(f"Iteration {iteration + 1}/{self.num_iterations}: LR={current_lr:.2e}, Loss={smoothed_loss:.4f}")
        
        except KeyboardInterrupt:
            logger.warning("Learning rate finder interrupted by user")
        
        # Restore original model state
        self.model.load_state_dict(original_state)
        self.model.to(torch.device("cpu"))  # Move back to CPU to avoid memory issues
        
        # Find suggested learning rate (typically where loss decreases fastest)
        suggested_lr = self._suggest_learning_rate()
        
        logger.info(f"Learning rate finder complete. Suggested LR: {suggested_lr:.2e}" if suggested_lr else "Could not determine suggested LR")
        
        return self.lrs, self.smoothed_losses, suggested_lr
    
    def _suggest_learning_rate(self) -> Optional[float]:
        """
        Suggest optimal learning rate based on loss curve.
        
        Strategy: Find the learning rate where loss decreases fastest (steepest negative slope).
        """
        if len(self.lrs) < 20:
            return None
        
        # Convert to numpy for easier computation
        lrs = np.array(self.lrs)
        losses = np.array(self.smoothed_losses)
        
        # Find minimum loss
        min_idx = np.argmin(losses)
        
        # Look for the steepest descent in the early part of training
        # Typically, we want a LR slightly smaller than where loss starts increasing
        search_end = min(min_idx + 10, len(losses) - 1)
        
        # Compute gradients (negative of loss gradient = descent rate)
        if search_end > 10:
            # Find point with steepest descent
            gradients = np.gradient(losses[:search_end])
            steepest_descent_idx = np.argmin(gradients)  # Most negative gradient
            
            # Suggest LR slightly lower than steepest descent point for safety
            suggested_idx = max(0, steepest_descent_idx - 5)
            return float(lrs[suggested_idx])
        
        # Fallback: use 1/10 of minimum loss LR
        return float(lrs[min_idx] / 10)
    
    def plot(
        self,
        output_path: Optional[Path] = None,
        show_plot: bool = False
    ) -> None:
        """
        Plot learning rate vs loss curve.
        
        Args:
            output_path: Optional path to save plot
            show_plot: Whether to display plot
        """
        if not self.lrs or not self.smoothed_losses:
            logger.warning("No data to plot. Run find() first.")
            return
        
        plt.figure(figsize=(10, 6))
        plt.plot(self.lrs, self.smoothed_losses, label='Smoothed Loss')
        plt.plot(self.lrs, self.losses, alpha=0.3, label='Raw Loss')
        
        if self.best_lr:
            plt.axvline(x=self.best_lr, color='r', linestyle='--', label=f'Suggested LR: {self.best_lr:.2e}')
        
        plt.xlabel('Learning Rate')
        plt.ylabel('Loss')
        plt.xscale('log')
        plt.title('Learning Rate Finder')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"Plot saved to {output_path}")
        
        if show_plot:
            plt.show()
        else:
            plt.close()


def find_optimal_lr(
    model: nn.Module,
    train_dataloader: DataLoader,
    start_lr: float = 1e-8,
    end_lr: float = 1e-1,
    num_iterations: int = 100,
    plot_path: Optional[Path] = None
) -> float:
    """
    Convenience function to find optimal learning rate.
    
    Args:
        model: Model to test
        train_dataloader: Training dataloader
        start_lr: Starting learning rate
        end_lr: Ending learning rate
        num_iterations: Number of iterations
        plot_path: Optional path to save plot
        
    Returns:
        Suggested learning rate
    """
    finder = LearningRateFinder(
        model=model,
        train_dataloader=train_dataloader,
        start_lr=start_lr,
        end_lr=end_lr,
        num_iterations=num_iterations
    )
    
    lrs, losses, suggested_lr = finder.find()
    
    if plot_path:
        finder.plot(output_path=plot_path, show_plot=False)
    
    return suggested_lr if suggested_lr else start_lr * 100  # Fallback

