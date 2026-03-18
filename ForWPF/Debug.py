import json
import tkinter as tk
import tkinter.filedialog as tkfl
import matplotlib.pyplot as plt
from pathlib import Path

# これまで作成した自作モジュールを読み込み
import initialsettings
import convert
import calculator

def main():
    # =========================================
    # 1. 設定ファイルの確認と読み込み
    # =========================================
    initialsettings.initialize_settings()
    
    settings_file = Path.home() / "Documents" / "XPSAST" / "settings.json"
    with open(settings_file, 'r', encoding='utf-8') as f:
        settings = json.load(f)

    # =========================================
    # 2. SPEファイルの選択とデータ読み込み
    # =========================================
    root = tk.Tk()
    root.withdraw() # 不要なウィンドウを隠す
    
    input_file = tkfl.askopenfilename(
        title="解析する SPE ファイルを選択してください",
        filetypes=[("SPE Files", "*.spe"), ("All Files", "*.*")]
    )
    
    if not input_file:
        print("ファイル選択がキャンセルされました。")
        return

    output_json = input_file.replace('.spe', '_header.json')
    
    # データの抽出 (タグ, X軸リスト, Y軸リスト)
    tags, x_raw, y_raw = convert.ReadSpeAndExportHeader(input_file, output_json)

    if not tags:
        print("データの読み込みに失敗しました。")
        return

    # =========================================
    # 3. 帯電補正 (シフト計算)
    # =========================================
    # 設定ファイルから補正パラメータを取得
    shift_standard = settings.get("shift_flag_energy", 284.4)
    shift_min = settings.get("shift_Xmin", 280)
    shift_max = settings.get("shift_Xmax", 290)

    # 補正の実行（アップロードしてもらった calculator.py の Shift を使用）
    x_shifted, y_shifted = calculator.Shift(
        tags=tags, 
        x_before=x_raw, 
        y_before=y_raw, 
        x_min=shift_min, 
        x_max=shift_max, 
        standard=shift_standard
    )

    # =========================================
    # 4. 各レベルごとの Shirley BG 計算とプロット
    # =========================================
    for i in range(len(tags)):
        tag = tags[i]
        x_data = x_shifted[i]
        y_data = y_shifted[i]
        
        # Shirleyバックグラウンド計算
        bg_data, x_min_bg, x_max_bg = calculator.shirley_baseline(x_data, y_data)
        
        # グラフの作成
        plt.figure(figsize=(8, 6))
        
        # プロット (元のスペクトル と Shirley BG)
        plt.plot(x_data, y_data, label=f"Spectrum ({tag})", color='blue')
        plt.plot(x_data, bg_data, label="Shirley BG", color='red', linestyle='--')
        
        plt.title(f"XPS Spectrum & Shirley Baseline: {tag}")
        plt.xlabel("Binding Energy (eV)")
        plt.ylabel("Intensity (c/s)")
        
        # ★重要: XPSの慣例に従い、X軸（結合エネルギー）を左から右へ小さくなるように反転
        plt.gca().invert_xaxis()
        
        plt.legend()
        plt.grid(True, linestyle=':', alpha=0.7)
        
        # グラフを表示（ウィンドウの「×」を閉じると、次のタグのグラフが表示されます）
        plt.show()

    print("すべてのグラフの表示が完了しました！")

if __name__ == "__main__":
    main()