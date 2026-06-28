import torch
import torch.nn as nn


def channel_shuffle(x, groups=2):
    b, c, h, w = x.size()
    assert c % groups == 0
    x = x.view(b, groups, c // groups, h, w)
    x = x.transpose(1, 2).contiguous()
    return x.view(b, c, h, w)

class ConvBNReLU(nn.Module):
    def __init__(self, cin, cout, k=1, s=1, p=0, groups=1):
        super().__init__()
        self.conv = nn.Conv2d(cin, cout, k, s, p, groups=groups, bias=False)
        self.bn = nn.BatchNorm2d(cout)
        self.act = nn.ReLU(inplace=True)

    def forward(self, x):
        return self.act(self.bn(self.conv(x)))

class DWConvBN(nn.Module):
    def __init__(self, c, k=3, s=1, p=1):
        super().__init__()
        self.conv = nn.Conv2d(c, c, k, s, p, groups=c, bias=False)
        self.bn = nn.BatchNorm2d(c)

    def forward(self, x):
        return self.bn(self.conv(x))

class ShuffleV2Unit(nn.Module):
    def __init__(self, channels):
        super().__init__()
        assert channels % 2 == 0
        c_half = channels // 2

        self.branch2 = nn.Sequential(
            ConvBNReLU(c_half, c_half, k=1, s=1, p=0),
            DWConvBN(c_half, k=3, s=1, p=1),
            ConvBNReLU(c_half, c_half, k=1, s=1, p=0),
        )

    def forward(self, x):
        c = x.size(1)
        x1, x2 = x[:, : c // 2, :, :], x[:, c // 2 :, :, :]
        out2 = self.branch2(x2)
        out = torch.cat([x1, out2], dim=1)
        return channel_shuffle(out, groups=2)

class ShuffleV2Downsample(nn.Module):
    def __init__(self, cin, cout):
        super().__init__()
        # 此处使用简单的步长为2的普通卷积进行降采样并转换通道
        self.down = ConvBNReLU(cin, cout, k=3, s=2, p=1)
        
    def forward(self, x):
        return self.down(x)

class ShuffleNetV2_4x8x9(nn.Module):
    def __init__(self, num_classes=3):
        super().__init__()

        stage1_c = 64
        stage2_c = 232  
        
        # Stem（下采样：8x9 -> 4x5）
        self.stem = ConvBNReLU(4, stage1_c, k=3, s=2, p=1)

        # Stage 1: 重复 4 次 Shuffle Unit
        self.stage1 = nn.Sequential(*[ShuffleV2Unit(stage1_c) for _ in range(4)])
        
        # Downsample（下采样：4x5 -> 2x3，提升通道）
        self.ds = ShuffleV2Downsample(stage1_c, stage2_c)

        # Stage 2: 重复 2 次 Shuffle Unit
        self.stage2 = nn.Sequential(*[ShuffleV2Unit(stage2_c) for _ in range(2)])

        # Head
        self.head = nn.Sequential(
            ConvBNReLU(stage2_c, stage2_c, k=1, s=1, p=0),
            nn.AdaptiveAvgPool2d(1),
        )
        self.fc = nn.Linear(stage2_c, num_classes)

    def forward(self, x):
        x = self.stem(x)
        x = self.stage1(x)
        x = self.ds(x)
        x = self.stage2(x)
        x = self.head(x).flatten(1)
        return self.fc(x)



if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = ShuffleNetV2_4x8x9(num_classes=3).to(device)
    model.eval()

    x = torch.randn(1, 4, 8, 9, device=device)

    with torch.no_grad():
        y = model(x)

    print("Input shape :", tuple(x.shape))   # (1, 4, 8, 9)
    print("Output shape:", tuple(y.shape))   # (1, 3)
    print("Output      :", y) 
