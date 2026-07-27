import os
import numpy as np
import torch
from torch.utils.data import Dataset
from scipy.io import loadmat
from typing import Tuple

def load_features_from_mat(feature_dir: str) -> Tuple[np.ndarray, np.ndarray]:
    fpath = os.path.join(feature_dir, "all_features.mat")
    if not os.path.exists(fpath):
        raise FileNotFoundError(f"Data file not found: {fpath}")
    mat_data = loadmat(fpath)
    combined_features = mat_data['features'].astype(np.float32)
    combined_labels = mat_data['labels'].flatten()
    label_mapping = {-1: 0, 0: 1, 1: 2}
    valid_labels_indices = np.isin(combined_labels, list(label_mapping.keys()))
    features_filtered = combined_features[valid_labels_indices]
    labels_mapped = np.array([label_mapping[lbl] for lbl in combined_labels[valid_labels_indices]], dtype=np.int64)
    return features_filtered, labels_mapped

class NumericalEEGDataset(Dataset):
    def __init__(self, features: torch.Tensor, labels: np.ndarray):
        self.features = features.to(dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.long)
    def __len__(self) -> int: return len(self.labels)
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.features[idx], self.labels[idx]