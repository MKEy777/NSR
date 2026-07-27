import os
import time
import logging
import sys
import torch
import torch.nn as nn
from model.TTFS import SpikingDense

def setup_logger(log_dir: str) -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger("DA_SNN")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(os.path.join(log_dir, 'training.log'))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

def custom_weight_init(m: nn.Module):
    if isinstance(m, SpikingDense) and m.kernel is not None:
        input_dim = m.kernel.shape[0]
        if input_dim > 0: 
            stddev = 1.0 / np.sqrt(input_dim)
            m.kernel.data.normal_(mean=0.0, std=stddev)
    elif isinstance(m, nn.Conv2d):
        nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
        if m.bias is not None: 
            nn.init.constant_(m.bias, 0)

def save_model_torch(model: nn.Module, save_dir: str):
    timestamp = time.strftime("%Y%m%d_%HM%S")
    save_path = os.path.join(save_dir, f"model_{timestamp}.pth")
    torch.save(model.state_dict(), save_path)