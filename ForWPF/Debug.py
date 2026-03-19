import convert
import calculator
import initialsettings
import tkinter as tk
import tkinter.filedialog as tkfd
from pathlib import Path

def run_debug_pipeline():
    print("=== XPSAST Debug Pipeline (To Atom%) ===")
    
    # 1. 初期設定の確認 (settings.jsonの生成/確認)
    initialsettings.initialize_settings()

    # 2. テスト用ファイルの選択
    root = tk.Tk()
    root.withdraw()
    filepath = tkfd.askopenfilename(
        title="テスト用のXPSデータを選択してください (.spe または .csv)",
        filetypes=[("SPE Files", "*.spe"), ("CSV Files", "*.csv"), ("All Files", "*.*")]
    )

    if not filepath:
        print("ファイルが選択されませんでした。デバッグを終了します。")
        return None, None

    file_path_obj = Path(filepath)
    print(f"\n[1/5] データの読み込み: {file_path_obj.name}")

    # 拡張子によって読み込み関数を切り替え
    if file_path_obj.suffix.lower() == '.spe':
        json_out = file_path_obj.with_suffix('.json')
        tags, x_all, y_all = convert.ReadSpeAndExportHeader(filepath, str(json_out))
    else:
        tags, x_all, y_all = convert.InterFromCSV(filepath)

    if not tags:
        print("エラー: データの読み込みに失敗しました。")
        return None, None

    # 3. 帯電補正 (C1s Shift)
    print("\n[2/5] 帯電補正 (C1s Shift) を実行中...")
    x_shifted, y_shifted = calculator.Shift(tags, x_all, y_all)

    # 4. Shirleyバックグラウンド計算
    print("\n[3/5] バックグラウンド計算 (Shirley法) を実行中...")
    bg_all = []
    for i in range(len(tags)):
        print(f"  - {tags[i]} のベースラインを計算中...")
        # 自動範囲設定を利用
        bg, x_min, x_max = calculator.shirley_baseline(x_shifted[i], y_shifted[i])
        bg_all.append(bg)

    # 5. 補正RSFの取得
    # ※ Documents/XPSAST/RSF.json が存在し、フォーマットが正しいことが前提です
    print("\n[4/5] 補正RSFリストを取得中...")
    corrected_rsf_list = calculator.Get_Corrected_RSF_List(tags, x_shifted, y_shifted, bg_all)
    for tag, rsf in zip(tags, corrected_rsf_list):
         print(f"  - {tag}: 補正RSF = {rsf:.4f}")

    # 6. Atom% (原子濃度) の計算
    print("\n[5/5] Atom% の計算を実行中...")
    ap_tags, atom_percentages = calculator.Atom_per(tags, x_shifted, y_shifted, bg_all, corrected_rsf_list)

    # 結果の出力
    print("\n===============================")
    print("      定量結果 (Atomic %)")
    print("===============================")
    for tag, percent in zip(ap_tags, atom_percentages):
        print(f" {tag:>6} : {percent:>6.2f} %")
    print("===============================\n")

    # 型の最終確認 (C#用)
    print(f"型の確認: ap_tags is {type(ap_tags)}, atom_percentages is {type(atom_percentages)}")
    if len(atom_percentages) > 0:
        print(f"要素の型確認: atom_percentages[0] is {type(atom_percentages[0])}")

    # C#へ返す想定のリストをリターン
    return ap_tags, atom_percentages

if __name__ == "__main__":
    result_tags, result_percents = run_debug_pipeline()