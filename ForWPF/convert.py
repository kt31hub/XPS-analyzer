import csv
import tkinter.filedialog as tkfd
#OK
def InterFromCSV(path):
    """
    指定されたパスのCSVファイルを読み込み、タグとデータをリストで返す関数
    """
    all_data_x = []
    all_data_y = []
    tags = []

    # 一時保存用
    temp_x = []
    temp_y = []
    current_tag = "Unknown"

    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f: # エンコーディングを指定
            reader = csv.reader(f, delimiter=',')
            
            for row in reader:
                # --- データ行 (2列) ---
                if len(row) == 2:
                    try:
                        temp_x.append(float(row[0]))
                        temp_y.append(float(row[1]))
                    except ValueError:
                        continue

                # --- 区切り/ヘッダー行 ---
                elif len(row) <= 1:
                    # データが溜まっていたら保存
                    if len(temp_x) > 0:
                        # np.array() を外してそのままリストを追加
                        all_data_x.append(temp_x)
                        all_data_y.append(temp_y)
                        tags.append(current_tag)
                        
                        # 新しいリストオブジェクトを割り当てる（前のデータは保持される）
                        temp_x = []
                        temp_y = []

                    # 新しいタグを取得
                    if len(row) == 1 and row[0].strip() not in ['1', '', ' ']:
                        current_tag = row[0].strip()

            # --- 最後のブロックを保存 ---
            if len(temp_x) > 0:
                # np.array() を外してそのままリストを追加
                all_data_x.append(temp_x)
                all_data_y.append(temp_y)
                tags.append(current_tag)
                
        return tags, all_data_x, all_data_y

    except FileNotFoundError:
        print("ファイルが見つかりませんでした。")
        return [], [], []

import re
import os
import struct
import json
import tkinter.filedialog as tkfl

def ReadSpeAndExportHeader(input_filepath, output_json_path):
    """
    PHIの.speファイルを読み込み、ヘッダーをJSONで保存しつつ、
    タグとX/Yデータを標準のリストで返す関数
    """
    print(f"処理を開始します: {input_filepath}")
    
    # 1. バイナリモードでファイル全体を読み込む
    with open(input_filepath, 'rb') as f:
        raw_data = f.read()

    # 2. ヘッダーの解析 (EOFHまで)
    header_end_idx = raw_data.find(b'EOFH')
    if header_end_idx == -1:
        raise ValueError("ファイル内に EOFH が見つかりません。")

    # ヘッダー部分をUTF-8でデコード
    header_bytes = raw_data[:header_end_idx]
    header_text = header_bytes.decode('utf-8', errors='replace')

    # ==========================================
    # ヘッダー情報のJSON出力処理
    # ==========================================
    header_dict = {}
    unmapped_lines = []

    for line in header_text.splitlines():
        line = line.strip()
        if not line:
            continue
        
        if ':' in line:
            parts = line.split(':', 1)
            key = parts[0].strip()
            value = parts[1].strip()
            
            if key in header_dict:
                if isinstance(header_dict[key], list):
                    header_dict[key].append(value)
                else:
                    header_dict[key] = [header_dict[key], value]
            else:
                header_dict[key] = value
        else:
            unmapped_lines.append(line)

    if unmapped_lines:
        header_dict["Other_Info"] = unmapped_lines

    # JSONファイルとして書き出し
    with open(output_json_path, 'w', encoding='utf-8') as json_file:
        json.dump(header_dict, json_file, ensure_ascii=False, indent=4)
        
    print(f"ヘッダー情報をJSONに出力しました: {output_json_path}")

    # ==========================================
    # データ抽出用のRegion情報取得と実データの読み込み
    # ==========================================
    # JSON化とは別に、波形生成用のデータを正確に取得するため正規表現を使用
    pattern = re.compile(r'SpectralRegDef:\s+\d+\s+\d+\s+(\S+)\s+\d+\s+(\d+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)')
    regions = []
    for line in header_text.splitlines():
        match = pattern.search(line)
        if match:
            regions.append({
                'name': match.group(1),
                'points': int(match.group(2)),
                'step_ev': float(match.group(3)),
                'start_ev': float(match.group(4)),
                'end_ev': float(match.group(5))
            })

    # EOFH以降のバイナリ開始位置を特定
    bin_start = header_end_idx + 4
    while bin_start < len(raw_data) and raw_data[bin_start:bin_start+1] in [b'\r', b'\n', b' ']:
        bin_start += 1
        
    bin_data = raw_data[bin_start:]
    num_regions = int.from_bytes(bin_data[4:8], byteorder='little')

    tags = []
    all_data_x = []
    all_data_y = []

    dir_start = 16 # Region記述子（ディレクトリ）の開始位置
    
    for i in range(min(num_regions, len(regions))):
        reg_info = regions[i]
        reg_name = reg_info['name']
        points = reg_info['points']
        
        offset = dir_start + i * 96
        byte_size = int.from_bytes(bin_data[offset+76:offset+80], byteorder='little')
        data_offset = int.from_bytes(bin_data[offset+80:offset+84], byteorder='little')
        
        # --- Y軸データ (強度) の抽出 ---
        data_start = data_offset
        data_end = data_start + byte_size
        data_bytes = bin_data[data_start:data_end]
        
        num_floats = byte_size // 4
        y_data = list(struct.unpack(f'<{num_floats}f', data_bytes))
        
        # --- X軸データ (結合エネルギー) の生成 ---
        start_ev = reg_info['start_ev']
        end_ev = reg_info['end_ev']
        
        if points > 1:
            step = (end_ev - start_ev) / (points - 1)
            x_data = [start_ev + j * step for j in range(points)]
        else:
            x_data = [start_ev]
            
        tags.append(reg_name)
        all_data_x.append(x_data)
        all_data_y.append(y_data)
        print(f" - [{reg_name}] を読み込みました。（{points} points）")

    print("\nすべての処理が完了しました！")
    return tags, all_data_x, all_data_y