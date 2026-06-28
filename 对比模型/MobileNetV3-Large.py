import torch
import torch.nn as nn
import torch.nn.functional as F


class HSwish(nn.Module):
    def forward(self, x):
        return x * F.hardtanh(x + 3.0, 0.0, 6.0) / 6.0

class HSigmoid(nn.Module):
    def forward(self, x):
        return F.hardtanh(x + 3.0, 0.0, 6.0) / 6.0

class SEBlock(nn.Module):
    def __init__(self, channels, reduction=4):
        super().__init__()
        hidden = max(8, channels // reduction)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc1 = nn.Conv2d(channels, hidden, 1, bias=True)
        self.act = nn.ReLU(inplace=True)
        self.fc2 = nn.Conv2d(hidden, channels, 1, bias=True)
        self.gate = HSigmoid()

    def forward(self, x):
        s = self.pool(x)
        s = self.fc2(self.act(self.fc1(s)))
        s = self.gate(s)
        return x * s

class ConvBNAct(nn.Module):
    def __init__(self, cin, cout, k=3, s=1, p=1, groups=1, act="hswish"):
        super().__init__()
        self.conv = nn.Conv2d(cin, cout, k, s, p, groups=groups, bias=False)
        self.bn = nn.BatchNorm2d(cout)
        if act == "hswish":
            self.act = HSwish()
        elif act == "relu":
            self.act = nn.ReLU(inplace=True)
        elif act == "none":
            self.act = nn.Identity()
        else:
            raise ValueError("act must be one of: hswish/relu/none")

    def forward(self, x):
        return self.act(self.bn(self.conv(x)))

class InvertedResidualV3(nn.Module):
    def __init__(self, cin, exp, cout, k=3, se=False, nl="hswish"):
        super().__init__()
        self.use_res = (cin == cout)
        self.pw1 = ConvBNAct(cin, exp, k=1, s=1, p=0, act=nl)
        self.dw  = ConvBNAct(exp, exp, k=k, s=1, p=k//2, groups=exp, act=nl)
        self.se  = SEBlock(exp) if se else nn.Identity()
        self.pw2 = ConvBNAct(exp, cout, k=1, s=1, p=0, act="none")

    def forward(self, x):
        out = self.pw2(self.se(self.dw(self.pw1(x))))
        return x + out if self.use_res else out

class MobileNetV3Large_4x8x9(nn.Module):
    def __init__(self, num_classes=3, width_mult=0.32):
        super().__init__()

        def c(ch):
            # 保证至少为 8，且是 8 的倍数（更接近常见实现/统计）
            v = int(ch * width_mult)
            v = max(8, (v + 7) // 8 * 8)
            return v

        # Stem
        self.stem = ConvBNAct(4, c(16), k=3, s=1, p=1, act="hswish")

        # Blocks (stride 全 1，不下采样，适配 8×9)
        self.blocks = nn.Sequential(
            InvertedResidualV3(c(16),  c(16),  c(16),  k=3, se=False, nl="relu"),
            InvertedResidualV3(c(16),  c(64),  c(24),  k=3, se=False, nl="relu"),
            InvertedResidualV3(c(24),  c(72),  c(24),  k=3, se=False, nl="relu"),

            InvertedResidualV3(c(24),  c(72),  c(40),  k=5, se=True,  nl="relu"),
            InvertedResidualV3(c(40),  c(120), c(40),  k=5, se=True,  nl="relu"),
            InvertedResidualV3(c(40),  c(120), c(40),  k=5, se=True,  nl="relu"),

            InvertedResidualV3(c(40),  c(240), c(80),  k=3, se=False, nl="hswish"),
            InvertedResidualV3(c(80),  c(200), c(80),  k=3, se=False, nl="hswish"),
            InvertedResidualV3(c(80),  c(184), c(80),  k=3, se=False, nl="hswish"),
            InvertedResidualV3(c(80),  c(184), c(80),  k=3, se=False, nl="hswish"),

            InvertedResidualV3(c(80),  c(480), c(112), k=3, se=True,  nl="hswish"),
            InvertedResidualV3(c(112), c(672), c(112), k=3, se=True,  nl="hswish"),

            InvertedResidualV3(c(112), c(672), c(160), k=5, se=True,  nl="hswish"),
            InvertedResidualV3(c(160), c(960), c(160), k=5, se=True,  nl="hswish"),
            InvertedResidualV3(c(160), c(960), c(160), k=5, se=True,  nl="hswish"),
        )

        # Head
        self.head_conv = ConvBNAct(c(160), c(960), k=1, s=1, p=0, act="hswish")
        self.pool = nn.AdaptiveAvgPool2d(1)

        # 这里保持 MobileNetV3 的“large head”风格，但跟随 width_mult 缩放
        self.fc1 = nn.Linear(c(960), c(1280))
        self.act = HSwish()
        self.drop = nn.Dropout(0.2)
        self.fc2 = nn.Linear(c(1280), num_classes)

    def forward(self, x):
        x = self.stem(x)
        x = self.blocks(x)
        x = self.head_conv(x)
        x = self.pool(x).flatten(1)
        x = self.act(self.fc1(x))
        x = self.drop(x)
        return self.fc2(x)

# -------------------------
# 一次随机输入样本
# -------------------------
if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MobileNetV3Large_4x8x9(num_classes=3, width_mult=0.32).to(device)
    model.eval()

    x = torch.randn(1, 4, 8, 9, device=device)
    with torch.no_grad():
        y = model(x)

    print("Input shape :", tuple(x.shape))
    print("Output shape:", tuple(y.shape))
    print("Output      :", y)