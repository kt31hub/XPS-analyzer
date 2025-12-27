import struct
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import tkinter.filedialog as tkfl

def read_phi_spectrum_final(file_path):
    """
    XPSデータ(.spe)解析の最終修正版
    """
    regions_info = [] 
    binary_start_offset = 0
    
    # --- 1. テキストヘッダー解析 ---
    print("--- ヘッダー解析開始 ---")
    with open(file_path, 'rb') as f:
        while True:
            try:
                line = f.readline().decode('utf-8', errors='ignore').strip()
            except:
                break

            # 行の例: SpectralRegDef: 2 1 C1s 6 201 -0.1000 298.0000 278.0000 ...
            if line.startswith('SpectralRegDef:'):
                parts = line.split()
                if len(parts) > 8:
                    try:
                        # ★修正箇所1: インデックスを調整
                        name = parts[3]           # 3番目が元素名 (Su1s, C1s...)
                        points = int(parts[5])    # 5番目が点数
                        start_ev = float(parts[7])# 7番目が開始eV
                        end_ev = float(parts[8])  # 8番目が終了eV
                        
                        regions_info.append({
                            'name': name,
                            'points': points,
                            'start': start_ev,
                            'end': end_ev
                        })
                    except Exception as e:
                        print(f"ヘッダー読み取りエラー: {e}")
            
            if line == 'EOFH':
                binary_start_offset = f.tell()
                break
    
    # 確認用出力
    print(f"検出された領域名: {[r['name'] for r in regions_info]}")

    # --- 2. バイナリデータ解析 ---
    parsed_data = {} 
    
    with open(file_path, 'rb') as f:
        content = f.read()
    
    current_pos = binary_start_offset
    
    # ★修正箇所2: 'f4'ではなく、よりユニークな 'pnt' (point) を目印にする
    # データ構造は pnt -> sar -> c/s -> f4 -> [DATA] となっているため
    header_signature = b'pnt' 
    
    for info in regions_info:
        # 'pnt' を探す
        marker_index = content.find(header_signature, current_pos)
        
        if marker_index == -1:
            print(f"Error: {info['name']} の開始マーカー(pnt)が見つかりません。")
            break
        
        print(f"Processing {info['name']} (Points: {info['points']})...")
        
        # データ抽出
        # pntマーカーが見つかった場所から、30バイト～150バイト後ろにデータ本体があるはず
        # (pnt, sar, c/s, f4 の各ヘッダーブロックを飛び越える)
        found_y = None
        
        # 32バイト後から探索開始 (各ヘッダー4バイト+値4バイト x 4つ = 32バイトが最小構成のため)
        for offset in range(32, 200, 4): 
            start_idx = marker_index + offset
            end_idx = start_idx + (info['points'] * 4)
            
            if end_idx > len(content):
                break
                
            chunk = content[start_idx:end_idx]
            floats = np.frombuffer(chunk, dtype=np.float32)
            
            # 妥当性チェック
            # 1. NaN/Infなし
            # 2. 平均値が妥当 (0.1 count以上)
            # 3. 最大値が暴走していない (10^10以下)
            if not (np.any(np.isnan(floats)) or np.any(np.isinf(floats))):
                avg = np.mean(np.abs(floats))
                if 0.1 < avg < 1e10: 
                    found_y = floats
                    current_pos = end_idx # 次の検索位置を更新
                    print(f"  -> データ発見! オフセット: +{offset}, 平均強度: {avg:.1f}")
                    break
        
        if found_y is not None:
            # X軸作成
            x_axis = np.linspace(info['start'], info['end'], info['points'])
            
            df = pd.DataFrame({
                'Binding Energy (eV)': x_axis,
                'Intensity (c/s)': found_y
            })
            parsed_data[info['name']] = df
        else:
            print(f"  -> {info['name']} のデータ本体が見つかりませんでした。")

    return parsed_data

# --- 実行 ---
path_d = tkfl.askopenfilename()
if path_d:
    data_dict = read_phi_spectrum_final(path_d)
    
    # 取得できたキーを表示
    print("\n利用可能なデータ:", data_dict.keys())

    # C1sがあれば表示
    target = 'C1s'
    if target in data_dict:
        df = data_dict[target]
        
        plt.figure(figsize=(8, 5))
        plt.plot(df['Binding Energy (eV)'], df['Intensity (c/s)'])
        plt.title(f"XPS Spectrum: {target}")
        plt.xlabel("Binding Energy (eV)")
        plt.ylabel("Intensity (counts/s)")
        plt.gca().invert_xaxis() # 軸反転
        plt.grid(True)
        plt.show()
    elif len(data_dict) > 0:
        # C1sがなくても、とりあえず最初のデータを表示
        first_key = list(data_dict.keys())[0]
        print(f"{target} がないため、代わりに {first_key} を表示します。")
        df = data_dict[first_key]
        plt.plot(df['Binding Energy (eV)'], df['Intensity (c/s)'])
        plt.title(f"{first_key}")
        plt.gca().invert_xaxis()
        plt.show()