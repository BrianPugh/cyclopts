"""Machine learning commands."""

import time

# Simulate expensive import (e.g., tensorflow, pytorch, sklearn)
print("[ml.py] Importing ML module... (simulating 2s delay)")
time.sleep(2)
print("[ml.py] Import complete!")


def train(model: str, *, epochs: int = 10, lr: float = 0.001):
    """Train a machine learning model.

    Parameters
    ----------
    model
        Model architecture: 'resnet', 'transformer', 'lstm'.
    epochs
        Number of training epochs.
    lr
        Learning rate.
    """
    print(f"Training {model} for {epochs} epochs (lr={lr})")


def predict(model_path: str, input_data: str):
    """Run inference with a trained model.

    Parameters
    ----------
    model_path
        Path to saved model weights.
    input_data
        Path to input data file.
    """
    print(f"Running prediction: {model_path} on {input_data}")
