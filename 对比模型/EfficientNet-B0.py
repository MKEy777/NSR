import torch
import torch.nn as nn
from torchvision.models.efficientnet import EfficientNet, MBConvConfig


def efficientnet_b0(
    in_channels: int = 4,
    num_classes: int = 3,
    width_mult: float = 0.57,
    depth_mult: float = 1.0,
):
    setting = [
        MBConvConfig(1, 3, 1, 32, 16, 1, width_mult=width_mult, depth_mult=depth_mult),
        MBConvConfig(3, 3, 1, 16, 24, 2, width_mult=width_mult, depth_mult=depth_mult),
        MBConvConfig(3, 5, 1, 24, 40, 2, width_mult=width_mult, depth_mult=depth_mult),
        MBConvConfig(3, 3, 1, 40, 80, 3, width_mult=width_mult, depth_mult=depth_mult),
        MBConvConfig(3, 5, 1, 80, 112, 3, width_mult=width_mult, depth_mult=depth_mult),
        MBConvConfig(3, 5, 1, 112, 192, 5, width_mult=width_mult, depth_mult=depth_mult),
        MBConvConfig(3, 3, 1, 192, 320, 2, width_mult=width_mult, depth_mult=depth_mult),
    ]

    model = EfficientNet(
        inverted_residual_setting=setting,
        dropout=0.2,
        num_classes=num_classes,
        last_channel=None,
    )

    # 修改 stem 为 4 通道 + stride=1
    old_conv = model.features[0][0]
    model.features[0][0] = nn.Conv2d(
        in_channels=in_channels,
        out_channels=old_conv.out_channels,
        kernel_size=old_conv.kernel_size,
        stride=(1, 1),
        padding=old_conv.padding,
        bias=False,
    )

    return model


if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = efficientnet_b0().to(device)
    model.eval()

    # 一次样本测试
    x = torch.randn(1, 4, 8, 9).to(device)

    with torch.no_grad():
        y = model(x)

    print("Input shape :", x.shape)
    print("Output shape:", y.shape)