import os
import time
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.optim.lr_scheduler import CosineAnnealingLR
from sklearn.model_selection import train_test_split

from configs.dreamer import CONFIG
from datasets.dreamer import load_features_from_mat, NumericalEEGDataset
from model.TTFS import build_da_snn
from common.utils import setup_logger, custom_weight_init, save_model_torch
from common.trainer import train_epoch
from common.metrics import evaluate_model

def main():
    run_timestamp = time.strftime("%Y%m%d_%HM%S")
    output_dir = os.path.join(CONFIG['OUTPUT_DIR_BASE'], f"Run_{run_timestamp}")
    logger = setup_logger(output_dir)
    logger.info("Configuration loaded. Output directory initialized.")

    torch.manual_seed(CONFIG['RANDOM_SEED'])
    np.random.seed(CONFIG['RANDOM_SEED'])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == 'cuda': 
        torch.cuda.manual_seed_all(CONFIG['RANDOM_SEED'])
    logger.info(f"Using device: {device}")
    
    features_data, labels_data = load_features_from_mat(CONFIG['FEATURE_DIR'])
    logger.info(f"Data loaded. Shape: {features_data.shape}")
    
    X_train_full, X_val_full, y_train, y_val = train_test_split(
        features_data, labels_data, test_size=CONFIG['TEST_SPLIT_SIZE'],
        random_state=CONFIG['RANDOM_SEED'], stratify=labels_data
    )

    train_dataset = NumericalEEGDataset(torch.tensor(X_train_full, dtype=torch.float32), y_train)
    val_dataset = NumericalEEGDataset(torch.tensor(X_val_full, dtype=torch.float32), y_val)
    train_loader = DataLoader(train_dataset, batch_size=CONFIG['BATCH_SIZE'], shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=CONFIG['BATCH_SIZE'], shuffle=False, num_workers=0)

    model = build_da_snn(
        input_shape=CONFIG['INPUT_SHAPE'],
        conv_channels=CONFIG['CONV_CHANNELS'],
        conv_kernel_size=CONFIG['CONV_KERNEL_SIZE'],
        hidden_units_1=CONFIG['HIDDEN_UNITS_1'],
        hidden_units_2=CONFIG['HIDDEN_UNITS_2'],
        output_size=CONFIG['OUTPUT_SIZE'],
        t_min=CONFIG['T_MIN_INPUT'],
        t_max=CONFIG['T_MAX_INPUT'],
        dropout_rate=CONFIG['DROPOUT_RATE']
    )
    
    model.apply(custom_weight_init)
    model.to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=CONFIG['LEARNING_RATE'], weight_decay=CONFIG['LAMBDA_L2'])
    scheduler = CosineAnnealingLR(optimizer, T_max=CONFIG['NUM_EPOCHS'], eta_min=1e-6)
    
    best_val_acc, patience_counter, best_model_state_dict = 0.0, 0, None
    logger.info("Starting training loop.")
    
    for epoch in range(CONFIG['NUM_EPOCHS']):
        train_loss, train_acc = train_epoch(
            model, train_loader, criterion, optimizer, device, 
            CONFIG['TRAINING_GAMMA'], CONFIG['T_MIN_INPUT'], CONFIG['T_MAX_INPUT']
        )
        val_loss, val_acc, _, _ = evaluate_model(model, val_loader, criterion, device)
        scheduler.step()
        
        logger.info(f"Epoch [{epoch+1}/{CONFIG['NUM_EPOCHS']}] Loss: {train_loss:.4f} Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} Val Acc: {val_acc:.4f}")
        
        if val_acc > best_val_acc + CONFIG['EARLY_STOPPING_MIN_DELTA']:
            best_val_acc = val_acc
            patience_counter = 0
            best_model_state_dict = copy.deepcopy(model.state_dict())
        else:
            patience_counter += 1
            if patience_counter >= CONFIG['EARLY_STOPPING_PATIENCE']:
                logger.info(f"Early stopping triggered at epoch {epoch+1}")
                break
                
    if best_model_state_dict: 
        model.load_state_dict(best_model_state_dict)
    
    save_model_torch(model, output_dir)
    logger.info("Training complete. Model saved.")

if __name__ == "__main__":
    main()