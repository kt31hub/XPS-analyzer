import numpy as np
import pandas as pd
import re
import os

def convert_phi_spe_to_excel(input_filepath, output_filepath):
    print(f"ファイルの読み込みを開始します: {input_filepath}")
    
    # バイナリモードでファイル全体を読み込む
    with open(input_filepath, 'rb') as f:
        raw_data = f.read()

    # 1. ヘッダーの解析 (EOFHまで)
    header_end_idx = raw_data.find(b'EOFH')
    if header_end_idx == -1:
        raise ValueError("ファイル内に EOFH が見つかりません。形式を確認してください。")

    # ヘッダーをテキストとしてデコード
    header_text = raw_data[:header_end_idx].decode('latin-1', errors='ignore')
    
    # 正規表現でRegion情報（測定領域、ポイント数、エネルギー範囲）を抽出
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

    # 2. バイナリデータの解析 (EOFH以降のディレクトリ構造と実データ)
    bin_start = header_end_idx + 4
    # 制御文字（改行など）をスキップして実際のバイナリの開始位置を探す
    while bin_start < len(raw_data) and raw_data[bin_start:bin_start+1] in [b'\r', b'\n', b' ']:
        bin_start += 1
        
    bin_data = raw_data[bin_start:]

    # ディレクトリヘッダからRegion総数を取得
    num_regions = int.from_bytes(bin_data[4:8], byteorder='little')
    print(f"検出された測定領域(Region)数: {num_regions}")

    # 3. データの結合とExcel出力
    print(f"Excelファイルへの書き出しを開始します: {output_filepath}")
    with pd.ExcelWriter(output_filepath, engine='openpyxl') as writer:
        dir_start = 16 # Region記述子（ディレクトリ）の開始位置
        
        for i in range(min(num_regions, len(regions))):
            reg_info = regions[i]
            reg_name = reg_info['name']
            
            # 各Regionのディレクトリ情報へのオフセット
            offset = dir_start + i * 96
            
            # ディレクトリから実データのバイトサイズと絶対オフセット位置を取得
            byte_size = int.from_bytes(bin_data[offset+76:offset+80], byteorder='little')
            data_offset = int.from_bytes(bin_data[offset+80:offset+84], byteorder='little')
            
            # 実データ（Y軸：強度）を32bit float (リトルエンディアン) として読み込み
            data_start = data_offset
            data_end = data_start + byte_size
            y_data = np.frombuffer(bin_data[data_start:data_end], dtype='<f4')
            
            # ヘッダー情報からX軸（結合エネルギー）を生成
            x_data = np.linspace(reg_info['start_ev'], reg_info['end_ev'], reg_info['points'])
            
            # DataFrameを作成
            df = pd.DataFrame({
                'Binding Energy (eV)': x_data,
                'Intensity (c/s)': y_data
            })
            
            # Excelのシート名として設定（文字数制限31文字と禁止文字に配慮）
            safe_name = re.sub(r'[\\/*?:\[\]]', '_', reg_name)
            sheet_name = f"Region_{i+1}_{safe_name}"[:31]
            
            # シートごとに書き出し
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f" - [{sheet_name}] を書き出しました。（{reg_info['points']} points）")

    print("\nすべての処理が完了しました！")

# ==========================================
# 実行部分（ここをご自身の環境に合わせて書き換えてください）
# ==========================================
import tkinter.filedialog as tkfl
if __name__ == "__main__":
    # 読み込む .spe ファイルのフルパス
    input_file = tkfl.askopenfilename()
    
    # 出力する Excelファイルのフルパス（同じフォルダに _Converted.xlsx として保存する例）
    output_file = input_file.replace('.spe', '_Converted.xlsx')
    
    if os.path.exists(input_file):
        convert_phi_spe_to_excel(input_file, output_file)
    else:
        print(f"エラー: 指定されたファイルが見つかりません -> {input_file}")