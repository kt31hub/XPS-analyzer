#kt31hub
#1st file
import os
import sys
import tkinter as tkinter
import tkinter.filedialog as tkfd
import json

# --- モジュールの読み込み場所を現在のフォルダに設定 ---
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import XPSASC
import XPSCAL
import XPSPLOTUI
import XPSFIT
import XPSOUTPUTXL

# ==========================================
# 1. データファイルの選択と読み込み
# ==========================================
print("ファイルを選択してください...")
root = tkinter.Tk()
root.withdraw() # メインウィンドウを隠す
data_path = tkfd.askopenfilename(filetypes=[("CSV", ".csv")])

if not data_path:
    print("ファイルが選択されませんでした。プログラムを終了します。")
    sys.exit()

# ASCⅡデータの取り込み
tag, x, y = XPSASC.load_allspe(path=data_path)
print(f"読み込み完了: {os.path.basename(data_path)}")

# ==========================================
# 2. 帯電補正 (Charge Correction)
# ==========================================
# C1sのピーク位置を基準(standard)に合わせて全体をシフト
print("\n--- 帯電補正を実行中 (C1s基準) ---")
x, y = XPSCAL.shift(tags=tag, x_before=x, y_before=y, x_min=280, x_max=290, standard=284.4)


# ==========================================
# 3. 原子組成比の計算 (Atomic %)
# ==========================================
print("\n--- 原子組成比 (Atomic %) ---")
try:
    with open('RSF.json', 'r') as f:
        RSF = json.load(f)
    
    # ここでXPSCAL内のatomic_percentが呼ばれます
    # ※XPSCAL.pyのbaseline関数をShirley法に変えていれば、ここも精度が上がります
    pp = XPSCAL.atomic_percent(x_all=x, y_all=y, tags=tag, rsf_list=RSF)
    
    for i in range(len(tag)):
        print(f"{tag[i]:<10} : {pp[i]:.2f} %")

except FileNotFoundError:
    print("エラー: 'RSF.json' が見つかりません。原子組成比計算をスキップします。")


# ==========================================
# 4. ピークフィッティング (Peak Fitting)
# ==========================================
print("\n========================================")
print("       Peak Fitting & Area Ratios       ")
print("========================================")

try:
    with open('peakfit.json', 'r') as f:
        peak_db = json.load(f)

    # 結果保存用（後でグラフ描画などを拡張する場合に使用）
    fit_results_list = [None] * len(tag)

    for i in range(len(tag)):
        # --- スキップ条件 ---
        # 0番目 (Survey/Su1s) と 最後 (CuLMM) はフィッティングしない
        if i == 0:
            continue
        if tag[i]=="CuLMM":
            continue

        current_tag = tag[i]
        
        # JSONから設定を探す
        target_peaks_config = [p for p in peak_db if p["level"] == current_tag]

        if not target_peaks_config:
            # 設定がなければスキップ（サイレント）
            continue

        # --- バックグラウンド処理 (Shirley法) ---
        # フィッティング精度向上のため、バックグラウンドを引いたデータを使用する
        y_bg, _, _ = XPSCAL.shirley_baseline(x[i], y[i])
        y_pure = y[i] - y_bg
        
        # マイナス値は0にクリップ（計算エラー防止）
        y_pure[y_pure < 0] = 0

        # --- フィッティング実行 ---
        # XPSFIT側で計算結果の表(print)を出力してくれる
        print(f"\n【 {current_tag} Fitting Results 】")
        fitted_peaks, y_total_fit = XPSFIT.perform_fitting(x[i], y_pure, target_peaks_config, verbose=True)

        if fitted_peaks:
            fit_results_list[i] = {
                "peaks": fitted_peaks,
                "y_total": y_total_fit,
                "y_bg": y_bg
            }

except FileNotFoundError:
    print("エラー: 'peakfit.json' が見つかりません。フィッティングをスキップします。")

# ==========================================
# 5. Excelへのデータ出力
# ==========================================
print("\n--- Excel出力 ---")
save = input("データをExcelに保存しますか？ (y/n): ")

if save.lower() == 'y':
    root = tkinter.Tk()
    root.withdraw()
    save_path = tkfd.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel Files", "*.xlsx")],
        initialfile="XPS_Analysis_Result.xlsx",
        title="保存先を選択してください"
    )

    if save_path:
        XPSOUTPUTXL.export_to_excel(
            save_path=save_path,
            tags=tag,
            x_list=x,
            y_list=y,
            fit_results_list=fit_results_list
        )

# ==========================================
# 6. グラフ描画
# ==========================================
print("\nグラフを描画します...")
XPSPLOTUI.plot_spectra(tags=tag, x_list=x, y_list=y)