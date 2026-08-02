from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Callable

import torch
import torch.nn as nn
import torch.nn.functional as F

from common.config import DATASET_CONFIGS
from model.TTFS import DA_SNN, DF_TTFS_Encoder, DSGM, DepthwiseSeparableConv, SpikingDense


BASELINE_DIR = Path(__file__).resolve().parents[2] / "对比模型"
MODEL_NAMES = (
    "da_snn",
    "eegnet",
    "deepconvnet",
    "dh_snn",
    "efficientnet_b0",
    "mobilenetv3_large",
    "mobilenetv3_small",
    "shallowconvnet",
    "shufflenetv2",
    "squeezenetv2",
)


class BaselineBuildError(RuntimeError):
    pass


class InputShapeAdapter(nn.Module):
    def __init__(self, model: nn.Module, source_shape: tuple[int, int, int], target_shape: tuple[int, int, int] = (4, 8, 9)):
        super().__init__()
        source_channels, _, _ = source_shape
        target_channels, self.target_height, self.target_width = target_shape
        self.channel_adapter = (
            nn.Identity()
            if source_channels == target_channels
            else nn.Conv2d(source_channels, target_channels, kernel_size=1)
        )
        self.model = model

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.channel_adapter(x)
        if x.shape[-2:] != (self.target_height, self.target_width):
            x = F.interpolate(x, size=(self.target_height, self.target_width), mode="bilinear", align_corners=False)
        return self.model(x)


def custom_weight_init(m: nn.Module) -> None:
    if isinstance(m, SpikingDense) and m.kernel is not None:
        input_dim = m.kernel.shape[0]
        if input_dim > 0:
            m.kernel.data.normal_(mean=0.0, std=1.0 / (input_dim ** 0.5))
    elif isinstance(m, nn.Conv2d):
        nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
        if m.bias is not None:
            nn.init.constant_(m.bias, 0)


def build_da_snn(
    dataset_name: str,
    device: torch.device,
    *,
    use_depthwise_separable: bool = True,
    use_dsgm: bool = True,
    use_ttfs_encoder: bool = True,
    use_dynamic_window: bool = True,
) -> DA_SNN:
    cfg = DATASET_CONFIGS[dataset_name]
    in_channels, height, width = cfg.input_shape
    conv_channels = 8 if dataset_name in {"seed", "seediv", "seedv"} else 18 if dataset_name == "dreamer" else 12
    model = DA_SNN(use_dynamic_window=use_dynamic_window)
    conv_cls = DepthwiseSeparableConv if use_depthwise_separable else nn.Conv2d
    ann_layers = [
        conv_cls(in_channels, conv_channels, kernel_size=3, stride=2),
        nn.BatchNorm2d(conv_channels),
        nn.ReLU(inplace=True),
    ]
    if use_dsgm:
        ann_layers.append(DSGM(conv_channels, conv_channels, kernel_size=3))
    model.add(nn.Sequential(*ann_layers))
    with torch.no_grad():
        dummy = torch.randn(1, in_channels, height, width)
        flattened_dim = nn.Sequential(*ann_layers)(dummy).numel()
    if use_ttfs_encoder:
        model.add(DF_TTFS_Encoder(t_min=0.0, t_max=1.0))
    model.add(nn.Flatten())
    model.add(SpikingDense(64, "dense_1", input_dim=flattened_dim))
    model.add(SpikingDense(32, "dense_2", input_dim=64))
    model.add(SpikingDense(cfg.num_classes, "dense_output", input_dim=32, outputLayer=True))
    model.apply(custom_weight_init)

    cur_t_min = 0.0
    cur_t_max = 1.0
    for layer in model.layers_list:
        if isinstance(layer, SpikingDense):
            new_t_max = cur_t_max + 1.0
            layer.set_time_params(cur_t_min, cur_t_max, new_t_max)
            cur_t_min = cur_t_max
            cur_t_max = new_t_max

    return model.to(device)


def _has_import_side_effects(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    side_effect_markers = ("plt.show(", ".show()", "fig.savefig(", "plt.savefig(")
    return any(marker in text for marker in side_effect_markers)


def _load_module(path: Path):
    if _has_import_side_effects(path):
        raise ImportError(f"Skipping side-effectful baseline module: {path}")
    if path.name == "DH-SNN.py":
        sys.modules.setdefault("SNN_layers", types.ModuleType("SNN_layers"))
        sys.modules.setdefault("SNN_layers.spike_neuron", types.ModuleType("SNN_layers.spike_neuron"))
    spec = importlib.util.spec_from_file_location(path.stem.replace(" ", "_").replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import baseline module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _try_build_from_module(path: Path, class_names: tuple[str, ...], num_classes: int, input_shape: tuple[int, int, int]):
    module = _load_module(path)
    for class_name in class_names:
        target = getattr(module, class_name, None)
        if target is None:
            continue
        channels, height, width = input_shape
        constructor_attempts = (
            lambda: target(num_classes=num_classes, input_channels=channels, H=height, W=width),
            lambda: target(num_classes=num_classes, in_channels=channels),
            lambda: target(num_classes=num_classes),
            lambda: target(output_dim=num_classes),
        )
        for build in constructor_attempts:
            try:
                return build()
            except TypeError:
                continue
    return None


def _validate_output(model: nn.Module, cfg, model_name: str, device: torch.device | None = None) -> nn.Module:
    was_training = model.training
    model.eval()
    if device is None:
        params = list(model.parameters())
        device = params[0].device if params else torch.device("cpu")
    with torch.no_grad():
        out = model(torch.zeros(2, *cfg.input_shape, device=device))
    if isinstance(out, tuple):
        out = out[0]
    if tuple(out.shape) != (2, cfg.num_classes):
        raise BaselineBuildError(
            f"{model_name} output shape {tuple(out.shape)} does not match expected {(2, cfg.num_classes)}."
        )
    model.train(was_training)
    return model


def _baseline_model(path: str, class_names: tuple[str, ...], cfg, model_name: str) -> nn.Module:
    candidate = BASELINE_DIR / path
    if not candidate.exists():
        raise BaselineBuildError(f"Baseline file not found for {model_name}: {candidate}")
    model = _try_build_from_module(candidate, class_names, cfg.num_classes, cfg.input_shape)
    if model is None:
        raise BaselineBuildError(f"Could not construct {model_name} from {candidate}.")
    try:
        return _validate_output(model, cfg, model_name)
    except Exception as exc:
        if cfg.input_shape == (4, 8, 9):
            raise
        adapted = InputShapeAdapter(model, cfg.input_shape)
        try:
            return _validate_output(adapted, cfg, model_name)
        except Exception as adapted_exc:
            raise BaselineBuildError(f"{model_name} could not be adapted from {cfg.input_shape} to (4, 8, 9).") from adapted_exc


def _build_dh_snn(cfg, device: torch.device) -> nn.Module:
    module = _load_module(BASELINE_DIR / "DH-SNN.py")
    if not hasattr(module, "Dense_test"):
        raise BaselineBuildError("DH-SNN.py does not expose Dense_test.")
    channels, height, width = cfg.input_shape
    module.DEVICE = device
    module.INPUT_DIM = height * width
    module.OUTPUT_DIM = cfg.num_classes
    module.SEQ_LENGTH = channels
    model = module.Dense_test(
        input_dim=module.INPUT_DIM,
        hidden_dim=getattr(module, "HIDDEN_DIM", 256),
        output_dim=cfg.num_classes,
        branch_num=getattr(module, "BRANCH_NUM", 8),
        v_threshold=getattr(module, "V_THRESHOLD", 0.5),
    )
    model = model.to(device)
    for _mod in model.modules():
        if hasattr(_mod, "device"):
            _mod.device = device
    return model


def build_model(
    model_name: str,
    dataset_name: str,
    device: torch.device,
    *,
    da_snn_options: dict | None = None,
) -> nn.Module:
    cfg = DATASET_CONFIGS[dataset_name]
    builders: dict[str, Callable[[], nn.Module]] = {
        "da_snn": lambda: build_da_snn(dataset_name, device, **(da_snn_options or {})),
        "eegnet": lambda: _baseline_model("EEGNet.py", ("EEGNet",), cfg, "eegnet"),
        "deepconvnet": lambda: _baseline_model("Deep ConvNet.py", ("DeepConvNet_4x8x9",), cfg, "deepconvnet"),
        "dh_snn": lambda: _build_dh_snn(cfg, device),
        "efficientnet_b0": lambda: _baseline_model("EfficientNet-B0.py", ("efficientnet_b0",), cfg, "efficientnet_b0"),
        "mobilenetv3_large": lambda: _baseline_model("MobileNetV3-Large.py", ("MobileNetV3Large_4x8x9",), cfg, "mobilenetv3_large"),
        "mobilenetv3_small": lambda: _baseline_model("MobileNetV3-Small.py", ("MobileNetV3Small_4x8x9",), cfg, "mobilenetv3_small"),
        "shallowconvnet": lambda: _baseline_model("Shallow ConvNet.py", ("ShallowConvNet_4x8x9",), cfg, "shallowconvnet"),
        "shufflenetv2": lambda: _baseline_model("ShuffleNetV2 .py", ("ShuffleNetV2_4x8x9",), cfg, "shufflenetv2"),
        "squeezenetv2": lambda: _baseline_model("SqueezeNetV2.py", ("SqueezeNet",), cfg, "squeezenetv2"),
    }
    if model_name not in builders:
        raise ValueError(f"Unknown model {model_name}. Available: {', '.join(MODEL_NAMES)}")
    return builders[model_name]().to(device)
