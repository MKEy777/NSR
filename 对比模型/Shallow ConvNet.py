import torch
import torch.nn as nn

class ShallowConvNet_4x8x9(nn.Module):
    def __init__(self, num_classes=3, drop_prob=0.5, F1=21, kernel_time=3, pool_time=2):
        super().__init__()
        self.conv_time = nn.Conv2d(1, F1, kernel_size=(1, kernel_time),
                                   padding=(0, kernel_time // 2), bias=False)
        self.conv_spat = nn.Conv2d(F1, F1, kernel_size=(32, 1), bias=False)
        self.bn = nn.BatchNorm2d(F1)
        self.pool = nn.AvgPool2d(kernel_size=(1, pool_time), stride=(1, pool_time))
        self.drop = nn.Dropout(drop_prob)
        self.flatten_dim = F1 * 1 * ((9 - pool_time) // pool_time + 1)  # = 4*F1
        self.fc = nn.Linear(self.flatten_dim, num_classes)

    def forward(self, x):
        b = x.size(0)
        x = x.reshape(b, 1, 32, 9)
        x = self.conv_time(x)
        x = self.conv_spat(x)
        x = self.bn(x)
        x = x * x
        x = self.pool(x)
        x = self.drop(x)
        x = torch.log(torch.clamp(x, min=1e-6))
        x = x.flatten(1)
        return self.fc(x)

if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ShallowConvNet_4x8x9().to(device).eval()
    x = torch.randn(1, 4, 8, 9, device=device)

    with torch.no_grad():
        y = model(x)

    params = sum(p.numel() for p in model.parameters())
