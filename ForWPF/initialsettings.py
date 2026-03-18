import json
import os
import tkinter as tk
import tkinter.filedialog as tkfl
from pathlib import Path

def initialize_settings():
    docs_path = Path.home() / "Documents"
    app_folder = docs_path / "XPSAST"
    settings_file = app_folder / "settings.json"

    # フォルダが存在しなければ作成
    app_folder.mkdir(parents=True, exist_ok=True)

    # 1. ファイルが存在しない場合のみ初期データを保存
    if not settings_file.exists():
        initial_data = {
            "Python_bin_Path": "NA",
            "shift_flag_level": "C1s",
            "shift_flag_energy": 284.4,
            "shift_Xmax": 290,
            "shift_Xmin": 280,
            "Excel_out":False
        }
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=4)
        print("初期設定ファイルを作成しました。")

    # 2. 設定の読み込み
    with open(settings_file, 'r', encoding='utf-8') as f:
        settings = json.load(f)

    # 3. Python DLL パスの検証と指定
    bin_path_str = settings.get("Python_bin_Path", "NA")
    bin_path = Path(bin_path_str)

    if bin_path_str == "NA" or not bin_path.is_file() or bin_path.suffix.lower() != '.dll':
        print("Python DLLのパスが未設定、または無効です。python310.dll などを指定してください。")
        
        root = tk.Tk()
        root.withdraw()

        # --- 初期ディレクトリの算出 ---
        local_appdata = os.environ.get('LOCALAPPDATA')
        init_dir = "" # デフォルトは空（OSの標準動作に任せる）
        
        if local_appdata:
            default_python_dir = Path(local_appdata) / "Programs" / "Python" / "Python310"
            # そのフォルダが実際に存在する場合のみ、初期ディレクトリとして設定
            if default_python_dir.exists():
                init_dir = str(default_python_dir)

        # ファイル選択ダイアログを表示
        selected_path = tkfl.askopenfilename(
            title="PythonのDLLファイル (python310.dll など) を選択してください",
            filetypes=[("DLL Files", "*.dll"), ("All Files", "*.*")],
            initialdir=init_dir  # ここで初期ディレクトリを指定！
        )

        if selected_path:
            settings["Python_bin_Path"] = selected_path
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            print(f"Python_bin_Path を更新し、検証を完了しました: {selected_path}")
        else:
            print("パスの指定がキャンセルされました。処理を実行するには有効なDLLパスが必要です。")
    else:
        print(f"有効な Python DLL パスが確認されました: {bin_path_str}")

# 実行
if __name__ == "__main__":
    initialize_settings()