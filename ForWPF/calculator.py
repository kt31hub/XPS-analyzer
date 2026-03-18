#Simpson積分
#Shirley法
#RSF計算
#帯電補正

def Shift(tags, x_before, y_before, x_min=280, x_max=290, standard=284.4):
    # 1. C1sタグを探す
    if "C1s" in tags:
        tag_marker = tags.index("C1s")
    else:
        print("Error: C1s tag not found.")
        # エラー時はクラッシュを防ぐため、シフト前のデータをそのまま返す
        return x_before, y_before

    # 対象のデータを取得
    x_c1s = x_before[tag_marker]
    y_c1s = y_before[tag_marker]
    
    # 2 & 3. 指定範囲内のデータを抜き出しつつ、最大値（ピーク）を探す
    max_y = -float('inf')
    peak_position = None
    
    # zipを使ってXとYのリストを同時に回す
    for x_val, y_val in zip(x_c1s, y_c1s):
        if x_min <= x_val <= x_max:  # 指定範囲内かどうか判定
            if y_val > max_y:        # 今までの最大値より大きければ更新
                max_y = y_val
                peak_position = x_val
                
    # 範囲内のデータが存在しなかった場合
    if peak_position is None:
        print(f"Error: 指定範囲 ({x_min}-{x_max} eV) にデータがありません。")
        return x_before, y_before

    # 4. 補正値を計算 (基準値 - 実測値)
    shift_value = standard - peak_position    
    print(f"ピーク位置: {peak_position} eV -> 補正値: {shift_value} eV")
    
    x_after = []
    y_after = []

    # 5. 全てのリストに対して補正値を加算
    for i in range(len(x_before)):
        # リスト内包表記で各要素に一括加算
        shifted_x = [x + shift_value for x in x_before[i]]
        x_after.append(shifted_x)
        
        # Y軸データはそのままコピー（別のリストオブジェクトとして独立させる）
        y_after.append(list(y_before[i]))
        
    return x_after, y_after

import numpy as np

def find_stable_min(x_region, y_region, window_size=3):
    """
    指定範囲内で移動平均をかけ、ノイズに強い最小値のX座標を返す関数
    """
    if len(y_region) < window_size:
        return x_region[np.argmin(y_region)]
    
    # 移動平均を計算してノイズを平滑化
    kernel = np.ones(window_size) / window_size
    smoothed_y = np.convolve(y_region, kernel, mode='valid')
    
    # 平滑化されたデータの中の最小値インデックスを取得
    min_idx = np.argmin(smoothed_y)
    
    # convolveでサイズが縮むため、元のx_regionとインデックスを合わせる
    # mode='valid'の場合、(window_size - 1) // 2 だけずれる
    offset = (window_size - 1) // 2
    return float(x_region[min_idx + offset])

def shirley_baseline(x_list, y_list, x_min=-1.0, x_max=-1.0, 
                     search_width_high=10.0, search_width_low=10.0, 
                     max_iter=50, tol=1e-5):
    """
    Shirley法によるバックグラウンド計算 (入出力は標準のリスト)
    """
    # 内部計算用にnumpy配列へ変換
    x = np.array(x_list, dtype=float)
    y = np.array(y_list, dtype=float)

    # --- 1. 範囲の自動設定ロジック ---
    if (x_min == -1.0) and (x_max == -1.0):
        idx_peak = np.argmax(y)
        x_peak = x[idx_peak]
        
        # (A) 高エネルギー側 (Left / High BE)
        mask_high = (x > x_peak) & (x <= x_peak + search_width_high)
        if np.any(mask_high):
            x_start_cand = find_stable_min(x[mask_high], y[mask_high])
        else:
            x_start_cand = float(x_peak + 5.0)

        # (B) 低エネルギー側 (Right / Low BE)
        mask_low = (x < x_peak) & (x >= x_peak - search_width_low)
        if np.any(mask_low):
            x_end_cand = find_stable_min(x[mask_low], y[mask_low])
        else:
            x_end_cand = float(x_peak - 5.0)

        # 候補をmin/maxに割り当て（標準のfloatとして保持）
        x_min = float(min(x_start_cand, x_end_cand))
        x_max = float(max(x_start_cand, x_end_cand))

    # --- 2. 通常のShirley計算処理 ---
    idx_start = np.abs(x - x_min).argmin()
    idx_end = np.abs(x - x_max).argmin()

    if idx_start > idx_end:
        idx_start, idx_end = idx_end, idx_start

    y_roi = y[idx_start : idx_end + 1]
    
    if len(y_roi) < 3:
        bg_short = np.linspace(y[idx_start], y[idx_end], len(x))
        return bg_short.tolist(), x_min, x_max

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

    # 全体のバックグラウンド配列を作成
    y_base_full = np.zeros_like(y)
    y_base_full[idx_start : idx_end + 1] = bg
    y_base_full[:idx_start] = bg[0]
    y_base_full[idx_end+1:] = bg[-1]

    # ★ 最後に numpy.ndarray を標準の list に変換して返す
    return y_base_full.tolist(), x_min, x_max
