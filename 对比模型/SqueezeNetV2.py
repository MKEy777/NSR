import torch
import torch.nn as nn

# --- SqueezeNet 模型定义 ---
class FireModule(nn.Module):
    def __init__(self, in_channels, squeeze_planes, expand1x1_planes, expand3x3_planes):
        super().__init__()
        self.squeeze = nn.Conv2d(in_channels, squeeze_planes, kernel_size=1)
        self.squeeze_activation = nn.ReLU(inplace=True)

        self.expand1x1 = nn.Conv2d(squeeze_planes, expand1x1_planes, kernel_size=1)
        self.expand1x1_activation = nn.ReLU(inplace=True)

        self.expand3x3 = nn.Conv2d(squeeze_planes, expand3x3_planes, kernel_size=3, padding=1)
        self.expand3x3_activation = nn.ReLU(inplace=True)

    def forward(self, x):
        x = self.squeeze_activation(self.squeeze(x))
        return torch.cat(
            [
                self.expand1x1_activation(self.expand1x1(x)),
                self.expand3x3_activation(self.expand3x3(x)),
            ],
            dim=1,
        )

class SqueezeNet(nn.Module):
    def __init__(self, num_classes=3):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(4, 64, kernel_size=3, stride=1, padding=1),  # (B,64,8,9)
            nn.ReLU(inplace=True),
            FireModule(64, 16, 64, 64),    # (B,128,8,9)
            FireModule(128, 16, 64, 64),   # (B,128,8,9)
            nn.MaxPool2d(kernel_size=2, stride=2),  # (B,128,4,4)
            FireModule(128, 32, 128, 128), # (B,256,4,4)
            FireModule(256, 32, 128, 128), # (B,256,4,4)
            nn.MaxPool2d(kernel_size=2, stride=2),  # (B,256,2,2)
        )
        final_conv = nn.Conv2d(256, num_classes, kernel_size=1)
        self.classifier = nn.Sequential(
            nn.Dropout(p=0.5),
            final_conv,
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x.flatten(start_dim=1)  # (B, num_classes)

if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SqueezeNet(num_classes=3).to(device)
    model.eval()

    # 一次随机输入样本：形状与原始数据一致 (batch, channels=4, height=8, width=9)
    x = torch.randn(1, 4, 8, 9, device=device)

    with torch.no_grad():
        y = model(x)

    print("Input shape :", tuple(x.shape))
    print("Output shape:", tuple(y.shape))  # 期望: (1, 3)
    print("Output      :", y)