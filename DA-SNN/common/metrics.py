import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from typing import Tuple, List

def evaluate_model(model: nn.Module, dataloader: DataLoader, criterion: nn.Module, device: torch.device) -> Tuple[float, float, List, List]:
    model.eval()
    running_loss, correct_predictions, total_samples = 0.0, 0, 0
    all_labels, all_preds = [], []
    with torch.no_grad():
        for features, labels in dataloader:
            features, labels = features.to(device), labels.to(device)
            outputs, _ = model(features)
            loss = criterion(outputs, labels)
            running_loss += loss.item() * features.size(0)
            _, predicted = torch.max(outputs.data, 1)
            correct_predictions += (predicted == labels).sum().item()
            total_samples += labels.size(0)
            all_labels.extend(labels.cpu().numpy())
            all_preds.extend(predicted.cpu().numpy())
    return running_loss / total_samples, correct_predictions / total_samples, all_labels, all_preds