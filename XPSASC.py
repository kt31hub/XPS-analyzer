#XPS ASC2コンバーター
import csv
import numpy as np

def load_allspe(path):
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
        with open(path, 'r', encoding='ascii') as f: # エンコーディングを指定
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
                        all_data_x.append(np.array(temp_x))
                        all_data_y.append(np.array(temp_y))
                        tags.append(current_tag)
                        temp_x = []
                        temp_y = []

                    # 新しいタグを取得
                    if len(row) == 1 and row[0].strip() not in ['1', '', ' ']:
                        current_tag = row[0].strip()

            # --- 最後のブロックを保存 ---
            if len(temp_x) > 0:
                all_data_x.append(np.array(temp_x))
                all_data_y.append(np.array(temp_y))
                tags.append(current_tag)
                
        return tags, all_data_x, all_data_y

    except FileNotFoundError:
        print("ファイルが見つかりませんでした。")
        return [], [], []