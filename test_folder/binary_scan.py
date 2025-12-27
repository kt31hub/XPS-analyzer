import struct
import numpy as np
import pandas as pd
import json
import csv
import tkinter.filedialog as tkfl
import os
import re

def read_phi_spectrum_final_v6(file_path):
    """
    PHI XPSファイル解析 V6 (エッジ検出・完全版)
    パディング(0)とデータ(高強度)の境界線(エッジ)を検出し、
    正確な開始位置からデータを切り出す。
    """
    regions_info = [] 
    header_metadata = {} 
    binary_start_offset = 0
    
    print(f"解析開始: {os.path.basename(file_path)}")
    
    # --- 1. テキストヘッダー解析 ---
    with open(file_path, 'rb') as f:
        while True:
            try:
                line_bytes = f.readline()
                line = line_bytes.decode('utf-8', errors='ignore').strip()
            except:
                break

            if ":" in line and not line.startswith("SpectralReg"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    header_metadata[parts[0].strip()] = parts[1].strip()

            if line.startswith('SpectralRegDef:'):
                parts = line.split()
                if len(parts) > 8:
                    try:
                        name = parts[3]
                        points = int(parts[5])
                        start_ev = float(parts[7])
                        end_ev = float(parts[8])
                        regions_info.append({
                            'name': name,
                            'points': points,
                            'start_ev': start_ev,
                            'end_ev': end_ev
                        })
                    except:
                        pass
            
            if line == 'EOFH':
                binary_start_offset = f.tell()
                break
    
    # --- 2. バイナリデータ解析 (エッジ検出) ---
    parsed_data = {} 
    
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # pnt マーカーを全検索
    header_marker = b'pnt'
    all_markers = [m.start() for m in re.finditer(header_marker, content)]
    valid_markers = [pos for pos in all_markers if pos >= binary_start_offset]
    
    print(f"検出ブロック数: {len(valid_markers)} / 定義領域数: {len(regions_info)}")
    
    for i, info in enumerate(regions_info):
        if i >= len(valid_markers):
            print(f"Error: {info['name']} のデータブロックが見つかりません。")
            break
            
        marker_pos = valid_markers[i]
        
        # pntマーカーの後ろにある 'f4' を探す
        f4_marker = b'f4'
        f4_pos = content.find(f4_marker, marker_pos, marker_pos + 500)
        
        found_y = None
        
        # 探索開始位置 (f4が見つからなければpntから固定オフセット)
        search_start_base = f4_pos if f4_pos != -1 else (marker_pos + 40)
        
        # 4パターンのバイトズレを試行
        best_data = None
        
        for align_offset in range(4):
            # 余裕を持って広めに読む (点数 + 1000点分)
            read_start = search_start_base + 2 + align_offset
            read_count = info['points'] + 1000 
            
            read_end = read_start + (read_count * 4)
            if read_end > len(content):
                read_end = len(content)
            
            chunk = content[read_start:read_end]
            
            try:
                floats = np.frombuffer(chunk, dtype=np.float32)
            except ValueError:
                continue 
            
            # --- エッジ検出ロジック ---
            # 1. NaN/Inf チェック
            if np.any(np.isnan(floats)) or np.any(np.isinf(floats)):
                continue

            # 2. 閾値判定 (Thresholding)
            # パディングは通常 0 または 1e-40以下の極小値。データは通常 > 100。
            # 「値が 50 を超えた最初の場所」を探す
            threshold = 50.0 
            valid_indices = np.where(np.abs(floats) > threshold)[0]
            
            if len(valid_indices) > 0:
                start_index = valid_indices[0] # ここがデータの本当の開始点
                
                # データ長が足りているか確認
                if start_index + info['points'] <= len(floats):
                    candidate = floats[start_index : start_index + info['points']]
                    
                    # データの平均値が妥当か再確認
                    avg = np.mean(np.abs(candidate))
                    if 100 < avg < 1e11:
                        best_data = candidate
                        # print(f"  -> {info['name']}: Offset {start_index} points (Mean: {avg:.0f})")
                        break # 有効なデータが見つかったらこのオフセットで確定
        
        if best_data is not None:
            # X軸作成 (高エネルギー -> 低エネルギー)
            x_axis = np.linspace(info['start_ev'], info['end_ev'], info['points'])
            df = pd.DataFrame({'x': x_axis, 'y': best_data})
            parsed_data[info['name']] = df
        else:
            print(f"Error: {info['name']} のデータ抽出に失敗しました。閾値(50)を超えるデータが見つかりません。")

    return parsed_data, regions_info, header_metadata

def save_files(parsed_data, regions_info, metadata, original_path):
    base_name = os.path.splitext(original_path)[0]
    
    # JSON出力
    json_path = base_name + "_settings.json"
    output_json = {"file_info": metadata, "regions": regions_info}
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output_json, f, indent=4, ensure_ascii=False)
    print(f"設定保存: {os.path.basename(json_path)}")

    # CSV出力
    csv_path = base_name + "_spectrum.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for info in regions_info:
            name = info['name']
            if name in parsed_data:
                writer.writerow([name])
                df = parsed_data[name]
                for _, row in df.iterrows():
                    writer.writerow([row['x'], row['y']])
    print(f"スペクトル保存: {os.path.basename(csv_path)}")

if __name__ == "__main__":
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()

    print("解析するPHI XPSファイル(.spe)を選択してください...")
    path_d = tkfl.askopenfilename()
    if path_d:
        try:
            data, regs, meta = read_phi_spectrum_final_v6(path_d)
            if data:
                save_files(data, regs, meta, path_d)
                print("\n=== 修正完了: エッジ検出処理を実行しました ===")
            else:
                print("有効なデータが見つかりませんでした。")
        except Exception as e:
            print(f"予期せぬエラー: {e}")
            import traceback
            traceback.print_exc()