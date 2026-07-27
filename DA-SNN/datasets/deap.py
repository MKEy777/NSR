import os
import numpy as np
import torch
from torch.utils.data import Dataset
from scipy.io import loadmat
from typing import Tuple

def load_features_from_mat(feature_dir: str) -> Tuple[np.ndarray, np.ndarray]:
    fpath = os.path.join(feature_dir, "all_features.mat")
    print(f"Loading data from: {fpath}")
    if not os.path.exists(fpath):
        raise FileNotFoundError(f"Data file not found: {fpath}")

    mat_data = loadmat(fpath)
    features = mat_data['features'].astype(np.float32)
    labels = mat_data['labels'].flatten().astype(np.int64)
    
    print(f"Features loaded, shape: {features.shape}")
    print(f"Labels loaded, shape: {labels.shape}")
    print(f"Unique labels found: {np.unique(labels)}")

    return features, labels

class NumericalEEGDataset(Dataset):
    def __init__(self, features: torch.Tensor, labels: np.ndarray):
        self.features = features.to(dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.long)
    def __len__(self) -> int: return len(self.labels)
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.features[idx], self.labels[idx]