import numpy as np
import os
import glob
from scipy.io import savemat
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "raw_EEG"
OUTPUT_DIR = BASE_DIR / "processed_data_all"

labels = {
    1: [4, 1, 3, 2, 0, 4, 1, 3, 2, 0, 4, 1, 3, 2, 0],
    2: [2, 1, 3, 0, 4, 4, 0, 3, 2, 1, 3, 4, 1, 2, 0],
    3: [2, 1, 3, 0, 4, 4, 0, 3, 2, 1, 3, 4, 1, 2, 0]
}
timestamps = {
    1: {
        'start_second': [30, 132, 287, 555, 773, 982, 1271, 1628, 1730, 2025, 2227, 2435, 2667, 2932, 3204],
        'end_second':   [102, 228, 524, 742, 920, 1240, 1568, 1697, 1994, 2166, 2401, 2607, 2901, 3172, 3359]
    },
    2: {
        'start_second': [30, 299, 548, 646, 836, 1000, 1091, 1392, 1657, 1809, 1966, 2186, 2333, 2490, 2741],
        'end_second':   [267, 488, 614, 773, 967, 1059, 1331, 1622, 1777, 1908, 2153, 2302, 2428, 2709, 2817]
    },
    3: {
        'start_second': [30, 353, 478, 674, 825, 908, 1200, 1346, 1451, 1711, 2055, 2307, 2457, 2726, 2888],
        'end_second':   [321, 418, 643, 764, 877, 1147, 1284, 1418, 1679, 1996, 2275, 2425, 2664, 2857, 3066]
    }
}

def main():
    import mne

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_labels_dict = {
        'label_session1': np.array(labels[1], dtype=int),
        'label_session2': np.array(labels[2], dtype=int),
        'label_session3': np.array(labels[3], dtype=int)
    }
    labels_output_path = os.path.join(OUTPUT_DIR, 'all_session_labels.mat')
    savemat(labels_output_path, all_labels_dict)
    print(f"所有Session的标签已合并保存在一个文件里: '{labels_output_path}'")

    if not os.path.isdir(INPUT_DIR):
        print(f"错误：输入目录 '{INPUT_DIR}' 不存在。请检查路径。")
        return

    file_pattern = os.path.join(INPUT_DIR, '*.cnt')
    all_cnt_files = sorted(glob.glob(file_pattern))

    if not all_cnt_files:
        print(f"警告：在 '{INPUT_DIR}' 中未找到任何 .cnt 文件。")
        return

    print(f"\n找到 {len(all_cnt_files)} 个 .cnt 文件, 将开始全自动处理...")

    for filepath in all_cnt_files:
        filename = os.path.basename(filepath)
        file_base_name = os.path.splitext(filename)[0]

        try:
            parts = file_base_name.split('_')
            session_id = int(parts[1])
            if session_id not in [1, 2, 3]:
                raise ValueError("Session ID不在1, 2, 3范围内")
        except (IndexError, ValueError) as e:
            print(f"\n!!!!!! 文件名 '{filename}' 不符合 '[Subject]_[Session]_[Date]' 格式，已跳过。错误: {e} !!!!!!")
            continue

        print(f"\n{'='*20}\n正在处理文件: {filename} (自动识别为 Session {session_id})\n{'='*20}")

        start_seconds = timestamps[session_id]['start_second']
        end_seconds = timestamps[session_id]['end_second']

        try:
            raw = mne.io.read_raw_cnt(filepath, preload=True)
            print(f"原始采样率: {raw.info['sfreq']} Hz, 原始通道数: {len(raw.ch_names)}")
            
            channels_to_drop = ['M1', 'M2', 'VEO', 'HEO']
            
            existing_channels_to_drop = [ch for ch in channels_to_drop if ch in raw.ch_names]
            
            if existing_channels_to_drop:
                raw.drop_channels(existing_channels_to_drop)
                print(f"已丢弃通道: {existing_channels_to_drop}。剩余通道数: {len(raw.ch_names)}")
            else:
                print("数据中未找到需要丢弃的通道 (M1, M2, VEO, HEO)。")
            
            raw.resample(200)
            print(f"降采样至: {raw.info['sfreq']} Hz")

            raw.filter(l_freq=1., h_freq=75., fir_design='firwin')
            print("已应用 1-75 Hz 带通滤波器。")

            mat_output_dict = {}
            for i in range(len(start_seconds)):
                start_t, stop_t = start_seconds[i], end_seconds[i]
                
                start_sample, stop_sample = raw.time_as_index([start_t, stop_t])
                data_segment = raw.get_data(start=start_sample, stop=stop_sample)
                
                scene_name = f'scene{i+1}'
                mat_output_dict[scene_name] = data_segment

            print(f"数据已分割成 {len(mat_output_dict)} 个 scene。")
            if mat_output_dict:
                print(f"Scene1 的数据维度 (通道数 x 采样点数): {mat_output_dict['scene1'].shape}")

            mat_output_path = os.path.join(OUTPUT_DIR, f"{file_base_name}.mat")
            savemat(mat_output_path, mat_output_dict)
            print(f"处理完成，数据已保存至: {mat_output_path}")

        except Exception as e:
            print(f"!!!!!! 处理文件 {filename} 时发生错误: {e} !!!!!!")
            continue

    print(f"\n{'='*20}\n所有文件处理完毕！\n{'='*20}")


if __name__ == "__main__":
    main()
