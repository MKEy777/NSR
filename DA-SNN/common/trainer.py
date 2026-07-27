import torch
import torch.nn as nn
from typing import Tuple, List, Optional
from model.TTFS import SpikingDense

def update_snn_time_params(
    snn_layers: List[nn.Module], 
    min_ti_list: List[Optional[torch.Tensor]], 
    t_min_input: float, 
    t_max_input: float, 
    gamma_ttfs: float
) -> List[Tuple]:
    next_time_params = []
    prev_boundary = t_max_input
    prev_prev_boundary = t_min_input

    for layer, min_ti in zip(snn_layers, min_ti_list):
        if min_ti is None:
            continue
            
        curr_t_min = float(layer.t_min)
        curr_t_max = float(layer.t_max)
        new_t_max = curr_t_max

        if min_ti.numel() > 0:
            t_e = float(torch.min(min_ti))
            if t_e < curr_t_max:
                midpoint = (curr_t_max + curr_t_min) / 2
                new_t_max = curr_t_max + gamma_ttfs * (t_e - midpoint)
                new_t_max = max(new_t_max, curr_t_min + 1e-4)

        next_time_params.append((layer, prev_prev_boundary, prev_boundary, new_t_max))
        prev_prev_boundary = prev_boundary
        prev_boundary = new_t_max
        
    return next_time_params

def apply_time_params(next_time_params: List[Tuple], device: torch.device):
    for layer, tmin_prev, tmin, tmax in next_time_params:
        layer.set_time_params(
            torch.as_tensor(tmin_prev, device=device),
            torch.as_tensor(tmin, device=device),
            torch.as_tensor(tmax, device=device),
        )
    next_time_params.clear()

def train_epoch(model, train_loader, criterion, optimizer, device, gamma_ttfs, t_min_input, t_max_input):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    snn_layers = [layer for layer in model.layers_list if isinstance(layer, SpikingDense) and not layer.outputLayer]
    next_time_params = []

    for inputs, targets in train_loader:
        if next_time_params:
            apply_time_params(next_time_params, device)

        inputs = inputs.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        outputs, min_ti_list = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * targets.size(0)
        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()

        with torch.no_grad():
            next_time_params = update_snn_time_params(
                snn_layers, min_ti_list, t_min_input, t_max_input, gamma_ttfs
            )

    return running_loss / total, correct / total