import os
import numpy as np
import torch
from torch.utils.data import Dataset
from scipy.io import loadmat
from typing import Tuple

def load_features_from_mat(feature_dir: str) -> Tuple[np.ndarray, np.ndarray]:
    fpath = os.path.join(feature_dir, "all_features.mat")
    print(f"正在加载数据: {fpath}")
    if not os.path.exists(fpath):
        raise FileNotFoundError(f"数据文件未找到: {fpath}")
    mat_data = loadmat(fpath)
    combined_features = mat_data['features'].astype(np.float32)
    combined_labels = mat_data['labels'].flatten()
    labels_mapped = combined_labels.astype(np.int64)    
    print("数据加载完成。假设标签已为 0-4 的整数。")
    return combined_features, labels_mapped

class NumericalEEGDataset(Dataset):
    def __init__(self, features: torch.Tensor, labels: np.ndarray):
        self.features = features.to(dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.long)
    def __len__(self) -> int: return len(self.labels)
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.features[idx], self.labels[idx]