import torch
import torch.nn as nn
import torch.nn.functional as F


class EEGNet(nn.Module):
    """
    输入: (B, 4, 8, 9)
    输出: (B, 3)
    """
    def __init__(self, num_classes=3, input_channels=4, H=8, W=9,
                 F1=16, D=2, F2=32, K_time=5, K_sep=3,
                 pool_time1=1, pool_time2=1,
                 drop_rate=0.1):
        super(EEGNet, self).__init__()

        # -------- Block 1 --------
        self.conv_time = nn.Conv2d(
            input_channels, F1,
            kernel_size=(1, K_time),
            padding=(0, K_time // 2),
            bias=False
        )
        self.bn1 = nn.BatchNorm2d(F1)

        self.conv_space_depthwise = nn.Conv2d(
            F1, F1 * D,
            kernel_size=(H, 1),
            groups=F1,
            bias=False
        )
        self.bn2 = nn.BatchNorm2d(F1 * D)

        self.elu1 = nn.ELU()
        self.pool1 = nn.AvgPool2d(kernel_size=(1, pool_time1), stride=(1, pool_time1))
        self.dropout1 = nn.Dropout(p=drop_rate)

        w_out_1 = (W - pool_time1) // pool_time1 + 1

        # -------- Block 2 --------
        self.conv_sep_depthwise = nn.Conv2d(
            F1 * D, F1 * D,
            kernel_size=(1, K_sep),
            padding=(0, K_sep // 2),
            groups=F1 * D,
            bias=False
        )

        self.conv_sep_pointwise = nn.Conv2d(
            F1 * D, F2,
            kernel_size=(1, 1),
            bias=False
        )
        self.bn3 = nn.BatchNorm2d(F2)

        self.elu2 = nn.ELU()
        self.pool2 = nn.AvgPool2d(kernel_size=(1, pool_time2), stride=(1, pool_time2))
        self.dropout2 = nn.Dropout(p=drop_rate)

        w_out_2 = (w_out_1 - pool_time2) // pool_time2 + 1
        self.flattened_dim = F2 * 1 * w_out_2

        self.classifier = nn.Linear(self.flattened_dim, num_classes)

    def forward(self, x):
        # Block 1
        x = self.conv_time(x)
        x = self.bn1(x)
        x = self.conv_space_depthwise(x)
        x = self.bn2(x)
        x = self.elu1(x)
        x = self.pool1(x)
        x = self.dropout1(x)

        # Block 2
        x = self.conv_sep_depthwise(x)
        x = self.conv_sep_pointwise(x)
        x = self.bn3(x)
        x = self.elu2(x)
        x = self.pool2(x)
        x = self.dropout2(x)

        # Classifier
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x


# -------------------------
# 一次随机输入测试
# -------------------------
if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = EEGNet().to(device)
    model.eval()

    x = torch.randn(1, 4, 8, 9, device=device)  # (B=1, C=4, H=8, W=9)

    with torch.no_grad():
        y = model(x)

    print("Input shape :", tuple(x.shape))
    print("Output shape:", tuple(y.shape))  # 期望 (1, 3)
    print("Output      :", y)