import torch
import torch.nn as nn
import torch.nn.functional as F


class DeepConvNet_4x8x9(nn.Module):
    """
    输入:  (B, 4, 8, 9)
    内部:  reshape -> (B, 1, 32, 9)  (把 4*8 当作“电极/通道”，9 当作“时间”)
    输出:  (B, 3)
    """
    def __init__(self, num_classes=3, drop_prob=0.5):
        super().__init__()

        # Block 1: temporal conv + spatial conv
        self.conv_temporal = nn.Conv2d(1, 40, kernel_size=(1, 3), padding=(0, 1), bias=False)
        self.conv_spatial  = nn.Conv2d(40, 40, kernel_size=(32, 1), groups=1, bias=False)
        self.bn1 = nn.BatchNorm2d(40)

        self.pool1 = nn.MaxPool2d(kernel_size=(1, 2), stride=(1, 2))
        self.drop1 = nn.Dropout(drop_prob)

        # Block 2
        self.conv2 = nn.Conv2d(40, 80, kernel_size=(1, 3), padding=(0, 1), bias=False)
        self.bn2 = nn.BatchNorm2d(80)
        self.pool2 = nn.MaxPool2d(kernel_size=(1, 2), stride=(1, 2))
        self.drop2 = nn.Dropout(drop_prob)

        # Block 3
        self.conv3 = nn.Conv2d(80, 160, kernel_size=(1, 3), padding=(0, 1), bias=False)
        self.bn3 = nn.BatchNorm2d(160)
        self.pool3 = nn.MaxPool2d(kernel_size=(1, 2), stride=(1, 2))
        self.drop3 = nn.Dropout(drop_prob)

        # Block 4
        self.conv4 = nn.Conv2d(160, 290, kernel_size=(1, 3), padding=(0, 1), bias=False)
        self.bn4 = nn.BatchNorm2d(290)
        self.drop4 = nn.Dropout(drop_prob)

        self.classifier = nn.Linear(290, num_classes)

    def forward(self, x):
        # x: (B, 4, 8, 9) -> (B, 1, 32, 9)
        b = x.size(0)
        x = x.reshape(b, 1, 4 * 8, 9)

        # Block 1
        x = self.conv_temporal(x)
        x = self.conv_spatial(x)
        x = self.bn1(x)
        x = F.elu(x)
        x = self.pool1(x)
        x = self.drop1(x)

        # Block 2
        x = self.conv2(x)
        x = self.bn2(x)
        x = F.elu(x)
        x = self.pool2(x)
        x = self.drop2(x)

        # Block 3
        x = self.conv3(x)
        x = self.bn3(x)
        x = F.elu(x)
        x = self.pool3(x)
        x = self.drop3(x)

        # Block 4
        x = self.conv4(x)
        x = self.bn4(x)
        x = F.elu(x)
        x = self.drop4(x)

        x = x.flatten(1) 
        return self.classifier(x)

# -------------------------
# 一次随机输入样本
# -------------------------
if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = DeepConvNet_4x8x9(num_classes=3, drop_prob=0.5).to(device)
    model.eval()

    x = torch.randn(1, 4, 8, 9, device=device)

    with torch.no_grad():
        y = model(x)

    print("Input shape :", tuple(x.shape))   # (1,4,8,9)
    print("Output shape:", tuple(y.shape))   # (1,3)
    print("Output      :", y)