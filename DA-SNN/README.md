

# DA-SNN

This repository contains the official PyTorch implementation of the paper “ An Asynchronous Neuromorphic Architecture for Wearable EEG Emotion Recognition”

## Repository Structure

The codebase is designed to be highly modular. All hyperparameters, model configurations, and dataset selections are decoupled and can be controlled entirely via the command-line interface (CLI).

```text
DA-SNN/
├── main.py              
├── README.md              
├── requirements.txt       
├── .gitignore           
├── model/                 
├── common/              
└── datasets/        
```

## Installation

Ensure you have Python installed, then install the required scientific computing and deep learning libraries:

```bash
pip install -r requirements.txt
```

## Data Preparation

This framework supports 5 mainstream EEG emotion recognition datasets. You must prepare the preprocessed EEG feature files in `.mat` format.

By default, `main.py` looks for specific directory names and shapes. The expected filenames, default feature dimensions (`--input_shape`), and the number of classification categories (`--output_size`) for each dataset are listed below:

| **Dataset** | **Default Directory (--feature_dir)** | **Expected Filename** | **Feature Shape** | **Classes** |
| ----------- | ------------------------------------- | --------------------- | ----------------- | ----------- |
| **SEED**    | `Feature_SEED_AllData`                | `all_features.mat`    | `4 8 9`           | 3           |
| **SEED-IV** | `Feature_SEEDIV_AllData`              | `all_features.mat`    | `4 8 9`           | 4           |
| **SEED-V**  | `Feature_SEEDV_AllData`               | `all_features.mat`    | `4 8 9`           | 5           |
| **DEAP**    | `Feature_DEAP_AllData`                | `all_features.mat`    | `6 7 5`           | 4           |
| **DREAMER** | `Feature_DREAMER_AllData`             | `all_features.mat`    | `9 4 5`           | 4           |

## Training and Evaluation

All training tasks are initiated through the unified `main.py` script located in the root directory.

### 1. Basic Training (Default Hyperparameters)

To train the model using the default optimal hyperparameters, specify the target dataset using the `--dataset` argument. The script will automatically load the corresponding feature dimensions and network output size.

```Bash
python main.py --dataset seed
python main.py --dataset seed_iv
python main.py --dataset deap
```

### 2. Custom Data Paths and Input Dimensions

If your preprocessed data is located in a custom directory or the input shape differs from the default, override the settings directly in the CLI:

```Bash
python main.py --dataset seed --feature_dir /path/to/your/custom_data --input_shape 4 16 16
```

### 3. Advanced Configuration (Ablation Studies)

The `argparse` integration allows you to modify learning rates, batch sizes, hidden units, and SNN dynamic time-window parameters on the fly, without altering the source code:

```Bash
python main.py --dataset seed \
    --learning_rate 1e-4 \
    --batch_size 16 \
    --num_epochs 300 \
    --hidden_units_1 128 \
    --hidden_units_2 64 \
    --dropout_rate 0.2 \
    --training_gamma 15.0
```

### Available Arguments

You can view the full list of supported command-line arguments by running:

```Bash
python main.py --help
```

- **Basic Settings**: `--dataset`, `--output_dir_base`, `--random_seed`
- **Data Settings**: `--feature_dir`, `--output_size`, `--input_shape`, `--test_split_size`
- **Architecture Settings**: `--conv_channels`, `--conv_kernel_size`, `--hidden_units_1`, `--hidden_units_2`, `--dropout_rate`
- **SNN Dynamics**: `--t_min_input`, `--t_max_input`, `--training_gamma`
- **Optimization**: `--num_epochs`, `--batch_size`, `--learning_rate`, `--lambda_l2`, `--early_stopping_patience`, `--early_stopping_min_delta`

## Experimental Outputs

Upon starting the training process, the framework will automatically generate an isolated directory stamped with the execution time (e.g., `DA_SNN_Experiment/SEED_Run_20231026_143000`) specified by `--output_dir_base`.

This directory will contain:

1. `training.log`: A comprehensive console output log tracking Loss and Accuracy across all epochs.
2. `*.pth`: The best model weights saved based on the highest validation accuracy .