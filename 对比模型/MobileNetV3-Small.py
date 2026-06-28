import torch
import torch.nn as nn
import torch.nn.functional as F

class HSwish(nn.Module):
    def forward(self, x):
        return x * F.hardtanh(x + 3.0, 0.0, 6.0) / 6.0

class ConvBNAct(nn.Module):
    def __init__(self, cin, cout, k=3, s=1, p=1, groups=1, act=True):
        super().__init__()
        self.conv = nn.Conv2d(cin, cout, k, s, p, groups=groups, bias=False)
        self.bn = nn.BatchNorm2d(cout)
        self.act = HSwish() if act else nn.Identity()

    def forward(self, x):
        return self.act(self.bn(self.conv(x)))

class InvertedResidual(nn.Module):
    """
    简化版 MobileNetV3 Inverted Residual:
    1x1 expand -> depthwise kxk -> 1x1 project
    """
    def __init__(self, cin, exp, cout, k=3):
        super().__init__()
        self.pw1 = ConvBNAct(cin, exp, k=1, s=1, p=0, act=True)
        self.dw  = ConvBNAct(exp, exp, k=k, s=1, p=k//2, groups=exp, act=True)
        self.pw2 = ConvBNAct(exp, cout, k=1, s=1, p=0, act=False)
        self.use_res = (cin == cout)

    def forward(self, x):
        out = self.pw2(self.dw(self.pw1(x)))
        return x + out if self.use_res else out

class MobileNetV3Small_4x8x9(nn.Module):
    """
    输入: (B, 4, 8, 9)
    输出: (B, 3)
    """
    def __init__(self, num_classes=3):
        super().__init__()
        # Stem
        self.stem = ConvBNAct(4, 16, k=3, s=1, p=1, act=True)          # (B,16,8,9)

        # Blocks（专门调参使 MACs 接近你给的 496.56K）
        self.block1 = InvertedResidual(16, 48, 24, k=3)               # (B,24,8,9)
        self.block2 = InvertedResidual(24, 64, 25, k=3)               # (B,25,8,9)

        # Head
        self.pool = nn.AdaptiveAvgPool2d((1, 1))                      # (B,25,1,1)
        self.fc1  = nn.Linear(25, 660)                                 # hidden=660
        self.act  = HSwish()
        self.drop = nn.Dropout(0.2)
        self.fc2  = nn.Linear(660, num_classes)

    def forward(self, x):
        x = self.stem(x)
        x = self.block1(x)
        x = self.block2(x)
        x = self.pool(x).flatten(1)
        x = self.act(self.fc1(x))
        x = self.drop(x)
        return self.fc2(x)

# -------------------------
# 仅一次随机输入样本
# -------------------------
if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MobileNetV3Small_4x8x9(num_classes=3).to(device)
    model.eval()

    x = torch.randn(1, 4, 8, 9, device=device)

    with torch.no_grad():
        y = model(x)

    print("Input shape :", tuple(x.shape))   # (1,4,8,9)
    print("Output shape:", tuple(y.shape))   # (1,3)
    print("Output      :", y)