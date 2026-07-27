import os
import time
import copy
import argparse
import importlib
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.optim.lr_scheduler import CosineAnnealingLR
from sklearn.model_selection import train_test_split

from model.TTFS import build_da_snn
from common.utils import setup_logger, custom_weight_init, save_model_torch
from common.trainer import train_epoch
from common.metrics import evaluate_model

# 针对不同数据集的默认特定参数 (特征路径、分类数、输入形状)
DATASET_DEFAULTS = {
    'seed': {
        'feature_dir': "Feature_SEED_AllData", 
        'output_size': 3, 'input_shape': (4, 8, 9)
    },
    'seed_iv': {
        'feature_dir': "Feature_SEEDIV_AllData", 
        'output_size': 4, 'input_shape': (4, 8, 9)
    },
    'seed_v': {
        'feature_dir': "Feature_SEEDV_AllData", 
        'output_size': 5, 'input_shape': (4, 8, 9)
    },
    'deap': {
        'feature_dir': "Feature_DEAP_AllData", 
        'output_size': 4, 'input_shape': (6, 7, 5)
    },
    'dreamer': {
        'feature_dir': "Feature_DREAMER_AllData", 
        'output_size': 4, 'input_shape': (9, 4, 5)
    }
}

def parse_args():
    parser = argparse.ArgumentParser(description="DA-SNN Training with Argparse Configuration")
    
    # 基础运行设置
    parser.add_argument('--dataset', type=str, required=True, choices=list(DATASET_DEFAULTS.keys()), help="Specify the dataset to train")
    parser.add_argument('--output_dir_base', type=str, default="DA_SNN_Experiment", help="Base directory for outputs")
    parser.add_argument('--random_seed', type=int, default=42, help="Random seed for reproducibility")
    
    # 数据集特有参数 (如果不传，则自动读取 DATASET_DEFAULTS)
    parser.add_argument('--feature_dir', type=str, default=None, help="Path to feature directory")
    parser.add_argument('--output_size', type=int, default=None, help="Number of classification classes")
    parser.add_argument('--input_shape', type=int, nargs='+', default=None, help="Input shape, e.g., --input_shape 4 8 9")
    parser.add_argument('--test_split_size', type=float, default=0.2, help="Validation/Test set split ratio")
    
    # 模型架构参数
    parser.add_argument('--conv_channels', type=int, nargs='+', default=[8, 8], help="Output channels for CNN blocks")
    parser.add_argument('--conv_kernel_size', type=int, default=3, help="Kernel size for CNN layers")
    parser.add_argument('--hidden_units_1', type=int, default=64, help="SpikingDense Layer 1 units")
    parser.add_argument('--hidden_units_2', type=int, default=32, help="SpikingDense Layer 2 units")
    parser.add_argument('--dropout_rate', type=float, default=0.0, help="Dropout rate before SpikingDense")
    
    # SNN 时间驱动参数
    parser.add_argument('--t_min_input', type=float, default=0.0, help="Minimum time for TTFS encoder")
    parser.add_argument('--t_max_input', type=float, default=1.0, help="Maximum time for TTFS encoder")
    parser.add_argument('--training_gamma', type=float, default=10.0, help="Gamma factor for dynamic time window update")
    
    # 训练超参数
    parser.add_argument('--num_epochs', type=int, default=200, help="Maximum number of training epochs")
    parser.add_argument('--batch_size', type=int, default=8, help="Batch size")
    parser.add_argument('--learning_rate', type=float, default=0.0005, help="Initial learning rate")
    parser.add_argument('--lambda_l2', type=float, default=0.0, help="L2 regularization (weight decay)")
    parser.add_argument('--early_stopping_patience', type=int, default=30, help="Early stopping patience epochs")
    parser.add_argument('--early_stopping_min_delta', type=float, default=0.0001, help="Early stopping minimum delta threshold")

    args = parser.parse_args()
    
    # 自动补齐未指定的特有参数
    defaults = DATASET_DEFAULTS[args.dataset]
    if args.feature_dir is None:
        args.feature_dir = defaults['feature_dir']
    if args.output_size is None:
        args.output_size = defaults['output_size']
    if args.input_shape is None:
        args.input_shape = defaults['input_shape']
    else:
        args.input_shape = tuple(args.input_shape)
        
    return args

def main():
    args = parse_args()
    
    # 动态加载对应数据集的读取逻辑
    dataset_module = importlib.import_module(f"datasets.{args.dataset}")
    load_features_from_mat = dataset_module.load_features_from_mat
    NumericalEEGDataset = dataset_module.NumericalEEGDataset

    # 初始化输出与日志
    run_timestamp = time.strftime("%Y%m%d_%HM%S")
    output_dir = os.path.join(args.output_dir_base, f"{args.dataset.upper()}_Run_{run_timestamp}")
    logger = setup_logger(output_dir)
    logger.info(f"Target Dataset: {args.dataset.upper()}")
    logger.info(f"Arguments: {vars(args)}")

    # 随机种子设定
    torch.manual_seed(args.random_seed)
    np.random.seed(args.random_seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == 'cuda': 
        torch.cuda.manual_seed_all(args.random_seed)
    logger.info(f"Using device: {device}")
    
    # 加载数据
    features_data, labels_data = load_features_from_mat(args.feature_dir)
    logger.info(f"Data loaded. Feature Shape: {features_data.shape}, Labels Shape: {labels_data.shape}")
    
    X_train_full, X_val_full, y_train, y_val = train_test_split(
        features_data, labels_data, test_size=args.test_split_size,
        random_state=args.random_seed, stratify=labels_data
    )

    train_dataset = NumericalEEGDataset(torch.tensor(X_train_full, dtype=torch.float32), y_train)
    val_dataset = NumericalEEGDataset(torch.tensor(X_val_full, dtype=torch.float32), y_val)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)

    # 构建网络
    model = build_da_snn(
        input_shape=args.input_shape,
        conv_channels=args.conv_channels,
        conv_kernel_size=args.conv_kernel_size,
        hidden_units_1=args.hidden_units_1,
        hidden_units_2=args.hidden_units_2,
        output_size=args.output_size,
        t_min=args.t_min_input,
        t_max=args.t_max_input,
        dropout_rate=args.dropout_rate
    )
    
    model.apply(custom_weight_init)
    model.to(device)
    
    # 优化器配置
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.learning_rate, weight_decay=args.lambda_l2)
    scheduler = CosineAnnealingLR(optimizer, T_max=args.num_epochs, eta_min=1e-6)
    
    best_val_acc = 0.0
    patience_counter = 0
    best_model_state_dict = None
    
    logger.info("Starting training loop.")
    
    # 训练循环
    for epoch in range(args.num_epochs):
        train_loss, train_acc = train_epoch(
            model, train_loader, criterion, optimizer, device, 
            args.training_gamma, args.t_min_input, args.t_max_input
        )
        val_loss, val_acc, _, _ = evaluate_model(model, val_loader, criterion, device)
        scheduler.step()
        
        logger.info(f"Epoch [{epoch+1}/{args.num_epochs}] Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} Acc: {val_acc:.4f}")
        
        if val_acc > best_val_acc + args.early_stopping_min_delta:
            best_val_acc = val_acc
            patience_counter = 0
            best_model_state_dict = copy.deepcopy(model.state_dict())
        else:
            patience_counter += 1
            if patience_counter >= args.early_stopping_patience:
                logger.info(f"Early stopping triggered at epoch {epoch+1}")
                break
                
    if best_model_state_dict: 
        model.load_state_dict(best_model_state_dict)
        logger.info(f"Best model validation accuracy: {best_val_acc:.4f}")
    
    save_model_torch(model, output_dir)
    logger.info("Training complete. Model saved.")

if __name__ == "__main__":
    main()