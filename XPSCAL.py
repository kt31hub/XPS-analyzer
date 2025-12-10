#計算用
import numpy as np

def find_stable_min(x, y):
    """
    データ列の中から安定した最小点を探す関数
    1. 3点移動平均を計算し、その値が最小になるウィンドウを探す
    2. そのウィンドウ内の3点のうち、平均値に最も近い点を選択する
       (突発的な外れ値ノイズを除外するため)
    """
    # データが少なすぎる場合は単純な最小値を返す
    if len(y) < 3:
        idx = np.argmin(y)
        return x[idx]

    # 1. 移動平均 (Window size = 3)
    # mode='valid' にすることで、端の計算できない部分を除外
    kernel = np.ones(3) / 3.0
    moving_avg = np.convolve(y, kernel, mode='valid')

    # 2. 平均値が最小となるウィンドウの開始インデックスを探す
    min_avg_idx = np.argmin(moving_avg) # ここがウィンドウの先頭(i)
    min_avg_val = moving_avg[min_avg_idx]

    # 3. そのウィンドウ(i, i+1, i+2)の中で、平均値に最も近い値を選ぶ
    # ウィンドウ内のインデックス
    candidates_idx = [min_avg_idx, min_avg_idx+1, min_avg_idx+2]
    candidates_y = y[candidates_idx]

    # 平均値との差分
    diffs = np.abs(candidates_y - min_avg_val)
    
    # 差分が最小のものを採用
    best_local_idx = np.argmin(diffs)
    best_global_idx = candidates_idx[best_local_idx]

    return x[best_global_idx]

#帯電補正用
def shift(tags, x_before, y_before, x_min, x_max, standard=284.4):
    """
    C1sのピーク位置を特定範囲(x_min ~ x_max)で探し、補正値(shift_value)を返す関数
    """
    tag_marker = -1
    shift_value = 0.0

    # 1. C1sタグを探す
    if "C1s" in tags:
        tag_marker = tags.index("C1s") # リストからインデックスを一発で検索
    else:
        print("Error: C1s tag not found.")
        return 0.0

    # 対象のデータを取得
    x_c1s = np.array(x_before[tag_marker])
    y_c1s = np.array(y_before[tag_marker])
    
    # 2. 指定範囲内のデータだけを抜き出す (Boolean Masking)
    # x_min以上 かつ x_max以下 の場所が True になるマスクを作成
    mask = (x_c1s >= x_min) & (x_c1s <= x_max)
    
    # 範囲内のデータが存在するか確認
    if not np.any(mask):
        print(f"Error: 指定範囲 ({x_min}-{x_max} eV) にデータがありません。")
        return 0.0

    # マスクを使って範囲内のデータのみ抽出
    x_focused = x_c1s[mask]
    y_focused = y_c1s[mask]

    # 3. 範囲内での最大値（ピーク）を探す
    max_index_local = np.argmax(y_focused)
    peak_position = x_focused[max_index_local]
    
    # 4. 補正値を計算 (基準値 - 実測値)
    shift_value = standard - peak_position    
    x_after = []
    y_after = [] # Yはそのままコピー

    for i in range(len(x_before)):
        # NumPy配列なので一括加算
        x_after.append(x_before[i] + shift_value)
        y_after.append(y_before[i])
        
    return x_after, y_after

# --- 使い方（例） ---
# x_min=280, x_max=290 の範囲でピークを探す
# shift_val = calculate_shift(tags, all_data_x, all_data_y, 280, 290)


#ベースライン描画用
def baseline(x, y, x_min=-1, x_max=-1):
    # NumPy配列であることを保証
    x = np.array(x)
    y = np.array(y)

    # 1. 範囲の自動設定
    if (x_min == -1) and (x_max == -1):
        index_max = np.argmax(y)
        # ピーク位置を中心に ±5eV
        x_min = x[index_max] - 5.0
        x_max = x[index_max] + 5.0

    # 2. 指定されたx_min, x_maxに「最も近い点」のインデックスを探す
    # np.abs(x - 値) が最小になる場所 = 一番近い場所
    index1 = np.abs(x - x_min).argmin()
    index2 = np.abs(x - x_max).argmin()

    # 3. 直線の式 (y = ax + b) を求める
    # 2点 (x1, y1) と (x2, y2) を通る直線
    x1, y1 = x[index1], y[index1]
    x2, y2 = x[index2], y[index2]

    if x2 == x1: # ゼロ除算のエラー回避
        a = 0
        b = y1
    else:
        a = (y2 - y1) / (x2 - x1)
        b = y1 - (a * x1)

    # 4. ベースライン計算 (forループを使わず一括計算)
    y_base = a * x + b
    
    return y_base, x_min, x_max

#x, y：データ、x_min, x_max：領域指定(オプション)既定はピークトップ±5 eV

def shirley_baseline(x, y, x_min=-1, x_max=-1, 
                     search_width_high=10.0, search_width_low=10.0, 
                     max_iter=50, tol=1e-5):
    """
    Shirley法によるバックグラウンド計算 (ノイズ除去探索付き)
    search_width_high: ピークから高結合エネルギー側(左)の探索幅
    search_width_low:  ピークから低結合エネルギー側(右)の探索幅
    """
    x = np.array(x)
    y = np.array(y)

    # --- 1. 範囲の自動設定ロジック (改良版: ノイズ対策) ---
    if (x_min == -1) and (x_max == -1):
        # ピークトップを探す
        idx_peak = np.argmax(y)
        x_peak = x[idx_peak]
        
        # --- (A) 高エネルギー側 (Left / High BE) の探索 ---
        mask_high = (x > x_peak) & (x <= x_peak + search_width_high)
        
        if np.any(mask_high):
            # マスク範囲内のデータを抽出
            y_high_region = y[mask_high]
            x_high_region = x[mask_high]
            
            # ★変更: 単純minではなく、移動平均を使った安定探索
            x_start_cand = find_stable_min(x_high_region, y_high_region)
        else:
            x_start_cand = x_peak + 5.0

        # --- (B) 低エネルギー側 (Right / Low BE) の探索 ---
        mask_low = (x < x_peak) & (x >= x_peak - search_width_low)
        
        if np.any(mask_low):
            y_low_region = y[mask_low]
            x_low_region = x[mask_low]
            
            # ★変更: 移動平均を使った安定探索
            x_end_cand = find_stable_min(x_low_region, y_low_region)
        else:
            x_end_cand = x_peak - 5.0

        # 求めた候補をmin/maxに割り当て
        x_min = min(x_start_cand, x_end_cand)
        x_max = max(x_start_cand, x_end_cand)


    # --- 以下、通常のShirley計算処理 ---
    idx_start = np.abs(x - x_min).argmin()
    idx_end = np.abs(x - x_max).argmin()

    if idx_start > idx_end:
        idx_start, idx_end = idx_end, idx_start

    y_roi = y[idx_start : idx_end + 1]
    
    if len(y_roi) < 3:
        return np.linspace(y[idx_start], y[idx_end], len(x)), x_min, x_max

    y_start = y_roi[0]
    y_end = y_roi[-1]
    bg = np.linspace(y_start, y_end, len(y_roi))

    if y_start > y_end:
        target_high = y_start
        target_low = y_end
        reverse_cumsum = True
    else:
        target_high = y_end
        target_low = y_start
        reverse_cumsum = False

    for _ in range(max_iter):
        diff = y_roi - bg
        diff[diff < 0] = 0

        if reverse_cumsum:
            cumsum = np.cumsum(diff[::-1])[::-1]
        else:
            cumsum = np.cumsum(diff)
            
        total_sum = cumsum[0] if reverse_cumsum else cumsum[-1]
        
        if total_sum == 0:
            break

        bg_new = target_low + (target_high - target_low) * (cumsum / total_sum)

        if np.max(np.abs(bg_new - bg)) < tol:
            bg = bg_new
            break
            
        bg = bg_new

    y_base_full = np.zeros_like(y)
    y_base_full[idx_start : idx_end + 1] = bg
    y_base_full[:idx_start] = bg[0]
    y_base_full[idx_end+1:] = bg[-1]

    return y_base_full, x_min, x_max

#台形積分
def Aria(x, y, baseline_y, x_min, x_max):
   # 1. 範囲のインデックス取得
    idx1 = np.abs(x - x_min).argmin()
    idx2 = np.abs(x - x_max).argmin()
    start_idx = min(idx1, idx2)
    end_idx = max(idx1, idx2)
    
    # 2. スライシング
    x_slice = x[start_idx : end_idx + 1]
    y_slice = y[start_idx : end_idx + 1]
    bg_slice = baseline_y[start_idx : end_idx + 1]
    
    # 3. 差分をとる
    diff = y_slice - bg_slice
    
    # ★追加: バックグラウンドより下（マイナス）の部分を 0 に置き換える
    diff[diff < 0] = 0
    
    # 4. 積分 (diffは全て0以上なので、x軸の向きによる符号だけ気にすればOK)
    area = np.abs(np.trapz(diff, x_slice))
    
    return area

#元素比
def atomic_percent(x_all, y_all, tags, rsf_list):

    
    # 1. RSFを辞書形式に変換して検索しやすくする
    # 例: {"C1s": 0.314, "O1s": 0.733, ...}
    rsf_dict = {item["level"]: item["rsf"] for item in rsf_list}

    corrected_areas = []  # RSFで割った後の面積
    calc_flags = []       # 計算対象かどうかのフラグ

    # --- 面積計算とRSF補正 ---
    for i in range(len(tags)):
        tag = tags[i]
        
        # RSF設定がない、またはRSFが0の場合は計算対象外とする
        # (これで0番目や最後の不要なデータを自動でスキップできます)
        rsf = rsf_dict.get(tag, 0.0)
        
        if rsf > 0:
            # ベースラインと面積計算 
            y_base, x_min, x_max = shirley_baseline(x=x_all[i], y=y_all[i])
            raw_area = Aria(x=x_all[i], y=y_all[i], baseline_y=y_base, x_max=x_max, x_min=x_min)
            
            # 【重要】RSFで割って補正面積を出す
            norm_area = raw_area / rsf
            
            corrected_areas.append(norm_area)
            calc_flags.append(True)
        else:
            corrected_areas.append(0.0)
            calc_flags.append(False)

    # --- Atomic% の算出 ---
    # 計算対象の補正面積の合計
    total_norm_area = sum(corrected_areas)
    
    atomic_percentages = []
    
    for i in range(len(tags)):
        if calc_flags[i] and total_norm_area > 0:
            # (自分の補正面積 / 全体の補正面積) * 100
            percent = (corrected_areas[i] / total_norm_area) * 100
            atomic_percentages.append(percent)
        else:
            atomic_percentages.append(0.0)
            
    return atomic_percentages

