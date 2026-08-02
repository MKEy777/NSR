from scipy.io import loadmat, savemat
import numpy as np
from scipy import signal
import os
import re
import time
from multiprocessing import Pool, cpu_count
from pathlib import Path

FS = 200
WINDOW_S = 4
STEP_S = 4
BASELINE_S = 30

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "PerSession_MAT_BaselineCorrected_Variable_MP" 

SESSION_LABELS = {
    '1': [1,2,3,0,2,0,0,1,0,1,2,1,1,1,2,3,2,2,3,3,0,3,0,3],
    '2': [2,1,3,0,0,2,0,2,3,3,2,3,2,0,1,1,2,1,0,3,0,1,3,1],
    '3': [1,2,2,1,3,3,3,1,1,2,1,0,2,3,3,0,2,3,0,0,2,0,1,0]
}

def bandpass_filter(data, fs=FS, lowcut=1.0, highcut=75.0, order=4):
    nyq = 0.5 * fs
    b, a = signal.butter(order, [lowcut / nyq, highcut / nyq], btype='band')
    return signal.filtfilt(b, a, data, axis=1).astype(np.float32)

def segment_trial(trial_data, window_s=WINDOW_S, step_s=STEP_S, fs=FS):
    win = int(window_s * fs)
    step = int(step_s * fs)
    n_ch = trial_data.shape[0]
    total_frames = 4
    pts_per_frame = fs
    segments = []
    _, T = trial_data.shape
    if T < win:
        return segments
    num_seg = (T - win) // step + 1
    for i in range(num_seg):
        seg = trial_data[:, i*step : i*step + win]
        seg = seg.reshape(n_ch, total_frames, pts_per_frame)
        seg = np.transpose(seg, (1, 0, 2))
        segments.append(seg.astype(np.float32))
    return segments

def process_session_data(data_file, session_label_list, session_folder_str, baseline_s=BASELINE_S, fs=FS, window_s=WINDOW_S, step_s=STEP_S): 
    
    pid = os.getpid() 
    filename = os.path.basename(data_file) 
    try:
        mat = loadmat(data_file) 
    except Exception as e:
        print(f"PID {pid}: 错误：无法加载 {filename}：{e}") 
        return None 

    parts = filename.split('_') 
    try:
        subj = int(parts[0]) 
        session_id_str = parts[1].split('.')[0] 
    except (IndexError, ValueError) as e:
        print(f"PID {pid}: 错误：解析文件名 {filename} 失败：{e}") 
        return None

    session_key = session_folder_str 
    if session_key not in SESSION_LABELS: 
        print(f"PID {pid}: 错误：文件夹 {session_key} 不存在于 SESSION_LABELS") 
        return None

    labels_arr = np.array(SESSION_LABELS[session_key], dtype=np.int32) 
    
    trial_keys = sorted( 
        [k for k in mat.keys() if re.match(r'.*_eeg\d+', k)], 
        key=lambda x: int(re.search(r'\d+', x.split('_eeg')[1]).group()) 
    )

    segments_list = []
    seg_labels_list = []
    segs_per_trial_list = []

    for trial_key in trial_keys:
        trial_num = int(re.search(r'\d+', trial_key.split('_eeg')[1]).group())
        idx = trial_num - 1
        if idx >= len(labels_arr):
            continue
        label_val = labels_arr[idx]

        data_trial = mat[trial_key]
        if data_trial.shape[0] != 62:
            continue
        if data_trial.shape[1] < int(baseline_s * fs):
            continue

        data_trial = bandpass_filter(data_trial)

        baseline_len = int(baseline_s * fs)
        baseline_mean = np.mean(data_trial[:, :baseline_len], axis=1, keepdims=True)
        baseline_std = np.std(data_trial[:, :baseline_len], axis=1, keepdims=True)
        corrected_data = (data_trial - baseline_mean) / (baseline_std + 1e-8)
        corrected_data = np.nan_to_num(corrected_data.astype(np.float32))

        trial_segments_list = segment_trial(corrected_data, window_s, step_s, fs)
        n_segs = len(trial_segments_list)

        segments_list.extend(trial_segments_list)
        seg_labels_list.extend([label_val] * n_segs)
        segs_per_trial_list.append(n_segs)

    if not segments_list: 
        
        return None

    X_arr = np.array(segments_list, dtype=np.float32)
    y_arr = np.array(seg_labels_list, dtype=np.int32)
    segs_per_trial_arr = np.array(segs_per_trial_list, dtype=np.int32)
    out_filename_str = f"subject_{subj:02d}_session_{session_id_str}_baseline_varlen.mat"

    return {'output_dir': OUTPUT_DIR, 'out_name': out_filename_str, 'data_X': X_arr, 'data_y': y_arr, 'segs_per_trial': segs_per_trial_arr, 'original_file': filename, 'pid': pid}

def save_processed_data(result):
    if result is None:
        return False 

    try:
        savemat(os.path.join(result['output_dir'], result['out_name']), {'seg_X': result['data_X'], 'seg_y': result['data_y'], 'segs_per_trial': result['segs_per_trial']}, do_compression=True) 
        print(f"PID {result['pid']} (saved by main): 已保存：{result['out_name']} (源文件: {result['original_file']})，片段数：{result['data_X'].shape[0]}") 
        return True
    except Exception as e:
        print(f"PID {result['pid']} (save failed by main): 保存 {result['out_name']} 时出错 (源文件: {result['original_file']})：{e}")
        return False

def main_multiprocess(): 
    
    overall_start_time = time.time()
    data_dir_root = BASE_DIR / "eeg_raw_data" 
    os.makedirs(OUTPUT_DIR, exist_ok=True) 

    tasks_to_process = []
    for session_folder_name in ['1', '2', '3']: 
        
        current_session_path = os.path.join(data_dir_root, session_folder_name) 
        if not os.path.exists(current_session_path): 
            print(f"警告：文件夹 {current_session_path} 不存在，跳过") 
            continue

        mat_file_names = [f for f in os.listdir(current_session_path) if f.lower().endswith('.mat')] 
        if not mat_file_names: 
            print(f"警告：在 {current_session_path} 中未找到 .mat 文件") 
            continue

        print(f"\n收集会话文件夹 {session_folder_name} 中的任务，找到 {len(mat_file_names)} 个文件") 
        for mat_file_name_only in mat_file_names: 
            full_file_path = os.path.join(current_session_path, mat_file_name_only) 
            
            tasks_to_process.append((full_file_path, SESSION_LABELS[session_folder_name], session_folder_name, BASELINE_S, FS, WINDOW_S, STEP_S))

    if not tasks_to_process:
        print("没有找到需要处理的文件。")
        return

    num_processes = 4  
    print(f"\n开始使用 {num_processes} 个进程处理 {len(tasks_to_process)} 个文件...")

    successful_saves = 0
    failed_processing_or_save = 0

    with Pool(processes=num_processes) as pool:

        results_from_workers = pool.starmap(process_session_data, tasks_to_process)

    print("\n所有工作进程已完成，开始保存结果...")
    for result_data in results_from_workers:
        if result_data: 
            if save_processed_data(result_data):
                successful_saves +=1
            else:
                failed_processing_or_save +=1
        else: 
            failed_processing_or_save +=1

    overall_end_time = time.time()
    print(f"\n处理完成。总耗时：{overall_end_time - overall_start_time:.2f} 秒")
    print(f"成功保存文件数: {successful_saves}")
    print(f"处理或保存失败/跳过的文件数: {failed_processing_or_save}")

if __name__ == '__main__':

    main_multiprocess()
