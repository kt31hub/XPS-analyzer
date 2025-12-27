import struct
import numpy as np
import pandas as pd
import json
import csv
import tkinter.filedialog as tkfl
import os
import re

def read_phi_spectrum_final_v4(file_path):
    """
    PHI XPSファイル解析 V4 (全領域強制抽出版)
    ヘッダー位置を一括検索することで、データ間の隙間による読み取り漏れを防ぐ
    """
    regions_info = [] 
    header_metadata = {} 
    binary_start_offset = 0
    
    # --- 1. テキストヘッダー解析 ---
    print(f"解析開始: {os.path.basename(file_path)}")
    
    with open(file_path, 'rb') as f:
        while True:
            try:
                line_bytes = f.readline()
                line = line_bytes.decode('utf-8', errors='ignore').strip()
            except:
                break

            # メタデータ保存
            if ":" in line and not line.startswith("SpectralReg"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    header_metadata[parts[0].strip()] = parts[1].strip()

            # 領域定義の読み取り
            # SpectralRegDef: ID ID Name ... Points ... Start End ...
            if line.startswith('SpectralRegDef:'):
                parts = line.split()
                if len(parts) > 8:
                    try:
                        name = parts[3]           # 元素名 (C1s, O1s...)
                        points = int(parts[5])    # データ点数
                        start_ev = float(parts[7])# Start eV
                        end_ev = float(parts[8])  # End eV
                        
                        regions_info.append({
                            'name': name,
                            'points': points,
                            'start_ev': start_ev,
                            'end_ev': end_ev
                        })
                    except Exception:
                        pass
            
            if line == 'EOFH':
                binary_start_offset = f.tell()
                break
    
    region_names = [r['name'] for r in regions_info]
    print(f"テキストヘッダー上の領域: {region_names}")

    # --- 2. バイナリデータ解析 (新ロジック: ヘッダー全検索) ---
    parsed_data = {} 
    
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # バイナリ開始位置より後ろにある 'pnt' (0x70 0x6E 0x74) をすべて探す
    # ※ pntは各データブロックの先頭に必ずあるマーカー
    header_marker = b'pnt'
    
    # 全マーカーの位置リストを作成
    all_markers = [m.start() for m in re.finditer(header_marker, content)]
    
    # EOFHより前にある誤検出(テキスト部)を除外
    valid_markers = [pos for pos in all_markers if pos >= binary_start_offset]
    
    print(f"バイナリ内で発見したデータブロック数: {len(valid_markers)}")
    
    # 領域数とマーカー数が合わない場合の警告
    if len(valid_markers) < len(regions_info):
        print("警告: テキスト情報よりデータブロックが少ないです。ファイルが破損している可能性があります。")
    
    # --- 3. 順番にマッチング ---
    # テキストの1番目(Su1s) = バイナリの1番目のpnt ... と対応付けます
    
    for i, info in enumerate(regions_info):
        if i >= len(valid_markers):
            print(f"Error: {info['name']} に対応するデータブロックが見つかりません。")
            break
            
        marker_pos = valid_markers[i]
        
        # データ抽出: pntマーカーの後ろにある 'f4' (float型指定) を探し、その直後を読む
        # pnt ... (数十バイト) ... f4 ... [データ本体]
        
        # pnt位置から最大200バイト先までにある 'f4' を探す
        f4_marker = b'f4'
        f4_pos = content.find(f4_marker, marker_pos, marker_pos + 300)
        
        found_y = None
        
        if f4_pos != -1:
            # f4が見つかった場合、その直後(数バイトのパディング後)からデータ開始
            # 少しずつずらして「まともな数値」が出る場所を探る
            for offset in range(2, 32, 2): 
                start_idx = f4_pos + offset
                end_idx = start_idx + (info['points'] * 4)
                
                if end_idx > len(content):
                    break
                    
                chunk = content[start_idx:end_idx]
                floats = np.frombuffer(chunk, dtype=np.float32)
                
                # 妥当性チェック
                # 1. NaN/Infなし
                # 2. 平均値が 0.1 ～ 10^10 (XPSのカウント数として正常)
                if not (np.any(np.isnan(floats)) or np.any(np.isinf(floats))):
                    avg = np.mean(np.abs(floats))
                    if 0.1 < avg < 1e11: 
                        found_y = floats
                        # print(f"  -> {info['name']} 抽出成功 (平均強度: {avg:.1f})")
                        break
        else:
            # f4が見つからない場合の予備策 (pntから固定オフセットで探す)
            print(f"Warning: {info['name']} の f4タグが見つかりません。固定オフセットで試行します。")
            for offset in range(40, 200, 4):
                start_idx = marker_pos + offset
                end_idx = start_idx + (info['points'] * 4)
                chunk = content[start_idx:end_idx]
                floats = np.frombuffer(chunk, dtype=np.float32)
                if not (np.any(np.isnan(floats)) or np.any(np.isinf(floats))):
                     if 0.1 < np.mean(np.abs(floats)) < 1e11:
                        found_y = floats
                        break

        if found_y is not None:
            # X軸作成 (高エネルギー -> 低エネルギー)
            x_axis = np.linspace(info['start_ev'], info['end_ev'], info['points'])
            
            df = pd.DataFrame({
                'x': x_axis,
                'y': found_y
            })
            parsed_data[info['name']] = df
        else:
            print(f"Error: {info['name']} のデータデコードに失敗しました。")

    return parsed_data, regions_info, header_metadata

def save_files(parsed_data, regions_info, metadata, original_path):
    """
    JSON設定ファイルと、Python連携用CSVを出力
    """
    base_name = os.path.splitext(original_path)[0]
    
    # 1. JSON出力
    json_path = base_name + "_settings.json"
    output_json = {
        "file_info": metadata,
        "regions": regions_info
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output_json, f, indent=4, ensure_ascii=False)
    print(f"設定保存: {os.path.basename(json_path)}")

    # 2. CSV出力 (XPSASC.py 形式)
    csv_path = base_name + "_spectrum.csv"
    count_exported = 0
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # 順番通りに出力したいので regions_info の順序を守る
        for info in regions_info:
            name = info['name']
            if name in parsed_data:
                # タグ行
                writer.writerow([name])
                # データ行
                df = parsed_data[name]
                for _, row in df.iterrows():
                    writer.writerow([row['x'], row['y']])
                count_exported += 1
                
    print(f"スペクトル保存: {os.path.basename(csv_path)} ({count_exported}領域)")

# --- 実行部 ---
if __name__ == "__main__":
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()

    print("解析するPHI XPSファイル(.spe)を選択してください...")
    path_d = tkfl.askopenfilename()
    
    if path_d:
        try:
            data, regs, meta = read_phi_spectrum_final_v4(path_d)
            if data:
                save_files(data, regs, meta, path_d)
                print("\n=== 全処理が完了しました ===")
            else:
                print("有効なデータが見つかりませんでした。")
        except Exception as e:
            print(f"予期せぬエラー: {e}")
            import traceback
            traceback.print_exc()