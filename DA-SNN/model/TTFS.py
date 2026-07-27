import torch
import torch.nn as nn
from typing import List, Optional, Tuple

torch.set_default_dtype(torch.float32)
EPSILON = 1e-9

class DepthwiseSeparableConv(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride=1):
        super().__init__()
        padding = (kernel_size - 1) // 2
        self.depthwise = nn.Conv2d(in_channels, in_channels, kernel_size=kernel_size, stride=stride, padding=padding, groups=in_channels)
        self.pointwise = nn.Conv2d(in_channels, out_channels, kernel_size=1)
        
    def forward(self, x):
        return self.pointwise(self.depthwise(x))

class HardSigmoid(nn.Module):
    def __init__(self, inplace=False):
        super(HardSigmoid, self).__init__()

    def forward(self, x):
        return torch.clamp(x * 0.125 + 0.5, 0.0, 1.0)

class DSGM(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size):
        super().__init__()
        if in_channels != out_channels:
            raise ValueError("Input and output channels must match.")
        
        padding = (kernel_size - 1) // 2
        
        self.main_path = nn.Sequential(
            nn.Conv2d(in_channels, in_channels, kernel_size=kernel_size, stride=1, padding=padding, groups=in_channels)
        )
        
        self.channel_gate_path = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, in_channels, kernel_size=1),
            HardSigmoid()
        )
        
        self.spatial_gate_path = nn.Sequential(
            nn.Conv2d(1, 1, kernel_size=kernel_size, stride=1, padding=padding),
            HardSigmoid()
        )
            
        self.final_act = nn.Sequential(
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        main_out = self.main_path(x)
        channel_gate = self.channel_gate_path(x)
        spatial_in = torch.mean(x, dim=1, keepdim=True)
        spatial_gate = self.spatial_gate_path(spatial_in)
        fused = main_out * channel_gate * spatial_gate
        return self.final_act(fused)

class DA_SNN(nn.Module):
    def __init__(self):
        super(DA_SNN, self).__init__()
        self.layers_list = nn.ModuleList()

    def add(self, layer: nn.Module):
        self.layers_list.append(layer)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, List[Optional[torch.Tensor]]]:
        current_input = x
        min_ti_list: List[Optional[torch.Tensor]] = []

        for layer in self.layers_list:
            if hasattr(layer, 'outputLayer'):
                current_input, min_ti = layer(current_input)
                if not layer.outputLayer and min_ti is not None:
                    min_ti_list.append(min_ti)
            else:
                current_input = layer(current_input)
        
        final_output = current_input
        return final_output, min_ti_list

class DF_TTFS_Encoder(nn.Module):
    def __init__(self, t_min: float = 0.0, t_max: float = 1.0, momentum=0.1, eps=1e-5):
        super().__init__()
        self.t_min = t_min
        self.t_max = t_max
        self.momentum = momentum
        self.eps = eps
        self.outputLayer = False

        self.register_buffer('running_min', torch.tensor(float('inf')))
        self.register_buffer('running_max', torch.tensor(float('-inf')))

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        if self.training:
            batch_min = torch.min(x.detach())
            batch_max = torch.max(x.detach())
            if not torch.isfinite(self.running_min): self.running_min.copy_(batch_min)
            if not torch.isfinite(self.running_max): self.running_max.copy_(batch_max)
            self.running_min.copy_((1 - self.momentum) * self.running_min + self.momentum * batch_min)
            self.running_max.copy_((1 - self.momentum) * self.running_max + self.momentum * batch_max)
        
        scale = self.running_max - self.running_min
        shift_bits = torch.ceil(torch.log2(scale + self.eps))
        power_of_2_scale = 2.0 ** shift_bits
        normalized_x = (x - self.running_min) / power_of_2_scale
        normalized_x = torch.clamp(normalized_x, 0, 1)

        time_range = self.t_max - self.t_min
        spike_times = self.t_max - normalized_x * time_range

        return spike_times, None
        
    def set_time_params(self, t_min_prev, t_min, t_max):
        pass

class SpikingDense(nn.Module):
    def __init__(self, units: int, name: str, outputLayer: bool = False, input_dim: Optional[int] = None):
        super(SpikingDense, self).__init__()
        self.units = units
        self.name = name
        self.outputLayer = outputLayer
        self.input_dim = input_dim
        self.D_i = nn.Parameter(torch.zeros(units, dtype=torch.float32))
        self.kernel = None
        self.register_buffer('t_min_prev', torch.tensor(0.0, dtype=torch.float32))
        self.register_buffer('t_min', torch.tensor(0.0, dtype=torch.float32))
        self.register_buffer('t_max', torch.tensor(1.0, dtype=torch.float32))
        self.built = False
        if self.input_dim is not None:
            self.kernel = nn.Parameter(torch.empty(self.input_dim, self.units, dtype=torch.float32))
            self._initialize_weights()
            self.built = True

    def _initialize_weights(self):
        nn.init.xavier_uniform_(self.kernel)
        with torch.no_grad():
            self.D_i.zero_()

    def build(self, input_shape):
        if self.built: return
        in_dim = input_shape[-1]
        self.input_dim = in_dim
        self.kernel = nn.Parameter(torch.empty(self.input_dim, self.units, dtype=torch.float32))
        self._initialize_weights()
        self.built = True

    def set_time_params(self, t_min_prev, t_min, t_max):
        buffer_device = self.t_min_prev.device
        if not isinstance(t_min_prev, torch.Tensor): t_min_prev = torch.tensor(t_min_prev, dtype=torch.float32)
        if not isinstance(t_min, torch.Tensor): t_min = torch.tensor(t_min, dtype=torch.float32)
        if not isinstance(t_max, torch.Tensor): t_max = torch.tensor(t_max, dtype=torch.float32)
        self.t_min_prev.copy_(t_min_prev.to(buffer_device))
        self.t_min.copy_(t_min.to(buffer_device))
        self.t_max.copy_(t_max.to(buffer_device))

    def forward(self, tj: torch.Tensor) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        if not self.built: self.build(tj.shape)
        if self.outputLayer:
            W_mult_x = torch.matmul(self.t_min - tj, self.kernel)
            time_diff = self.t_min - self.t_min_prev
            safe_time_diff = torch.where(time_diff == 0, EPSILON, time_diff)
            alpha = self.D_i / safe_time_diff
            output = alpha * time_diff + W_mult_x
            min_ti_output = None
        else:
            threshold = self.t_max - self.t_min - self.D_i
            output = torch.matmul(tj - self.t_min, self.kernel) + threshold + self.t_min
            output = torch.where(output < self.t_max, output, self.t_max)
            with torch.no_grad():
                mask = torch.isfinite(output) & (output < self.t_max)
                spikes = output[mask]
                min_ti_output = torch.min(spikes).unsqueeze(0) if spikes.numel() > 0 else self.t_max.clone().unsqueeze(0)
        return output, min_ti_output

def build_da_snn(
    input_shape: Tuple[int, int, int], 
    conv_channels: List[int], 
    conv_kernel_size: int, 
    hidden_units_1: int, 
    hidden_units_2: int, 
    output_size: int, 
    t_min: float, 
    t_max: float, 
    dropout_rate: float
) -> DA_SNN:
    model = DA_SNN()
    in_channels = input_shape[0]
    ann_layers = []
    
    out_channels_1 = conv_channels[0]
    out_channels_2 = conv_channels[1]

    ann_layers.extend([
        DepthwiseSeparableConv(in_channels, out_channels_1, kernel_size=conv_kernel_size, stride=2),
        nn.BatchNorm2d(out_channels_1),
        nn.ReLU(inplace=True)
    ])
    in_channels = out_channels_1 

    ann_layers.append(DSGM(in_channels, out_channels_2, kernel_size=conv_kernel_size))
    
    model.add(nn.Sequential(*ann_layers))
    
    with torch.no_grad():
        dummy_input = torch.randn(1, *input_shape)
        cnn_part = nn.Sequential(*ann_layers)
        dummy_output = cnn_part(dummy_input)
        flattened_dim = dummy_output.numel()
    
    model.add(DF_TTFS_Encoder(t_min=t_min, t_max=t_max))
    model.add(nn.Flatten())
    
    if dropout_rate > 0: 
        model.add(nn.Dropout(p=dropout_rate))
    
    model.add(SpikingDense(hidden_units_1, 'dense_1', input_dim=flattened_dim))
    model.add(SpikingDense(hidden_units_2, 'dense_2', input_dim=hidden_units_1))
    model.add(SpikingDense(output_size, 'dense_output', input_dim=hidden_units_2, outputLayer=True))

    cur_t_min = 0.0
    cur_t_max = t_max
    for layer in model.layers_list:
        if isinstance(layer, SpikingDense):
            new_t_max = cur_t_max + 1.0
            layer.set_time_params(cur_t_min, cur_t_max, new_t_max)
            cur_t_min = cur_t_max
            cur_t_max = new_t_max

    return model