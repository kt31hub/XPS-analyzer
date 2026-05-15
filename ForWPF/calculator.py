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

def Area(x, y, baseline_y, x_min, x_max):
    """
    指定範囲内のピーク面積 (y - baseline_y) をシンプソン法で計算する関数
    ※ Numpy不使用
    """
    # XPSは結合エネルギーが降順(左が大きい)の場合があるため、大小を整理
    lower_bound = min(x_min, x_max)
    upper_bound = max(x_min, x_max)
    
    x_f = []
    f_val = []
    
    # 1. 指定範囲内のデータを抽出し、正味の強度（y - baseline_y）を計算
    for i in range(len(x)):
        if lower_bound <= x[i] <= upper_bound:
            x_f.append(x[i])
            
            # バックグラウンドを引いた正味の強度（Net Intensity）
            net_y = y[i] - baseline_y[i]
            
            # ノイズでベースラインを下回った（マイナスになった）場合は0とみなす
            f_val.append(max(0.0, net_y))
            
    n = len(x_f)
    
    # 面積を計算できない場合
    if n < 2:
        print(f"Error: 指定範囲 ({x_min}-{x_max} eV) 内に十分なデータがありません。")
        return 0.0

    # X軸の刻み幅 (等間隔であることを前提)
    dx = abs(x_f[1] - x_f[0])
    area = 0.0
    
    # 2. 面積の計算
    if n == 2:
        # データが2点しかない場合は台形積分
        area = (f_val[0] + f_val[1]) * dx / 2.0
    else:
        # --- シンプソン積分 ---
        # シンプソン法はデータ数が奇数(区間数が偶数)のときのみ適用可能
        is_even_intervals = (n % 2 != 0)
        
        # シンプソン法を適用する範囲の限界（奇数個のデータポイントまで）
        limit = n if is_even_intervals else n - 1
        
        # シンプソン法の公式: (dx / 3) * (f[0] + 4*f[1] + 2*f[2] + ... + f[n-1])
        s = f_val[0] + f_val[limit - 1]
        for i in range(1, limit - 1):
            if i % 2 == 1:
                s += 4.0 * f_val[i]  # 奇数番目は4倍
            else:
                s += 2.0 * f_val[i]  # 偶数番目は2倍
                
        area = s * dx / 3.0
        
        # もしデータ数 n が偶数（区間数が奇数）だった場合、
        # はみ出た最後の1区間だけ「台形積分」で計算して足す
        if not is_even_intervals:
            last_trapz = (f_val[-2] + f_val[-1]) * dx / 2.0
            area += last_trapz
            
    return area

import json
from pathlib import Path

def Get_Corrected_RSF_List(tags, x_all, y_all, bg_all, header_json_path=None, photon_energy=1486.6, t_exp=-1.0, l_exp=0.5):
    """
    ドキュメントフォルダ内のRSF.jsonを読み込み、補正済みRSFのリストを返す。
    ※ヘッダーJSONが渡された場合、Sweeps(スキャン回数)とTime/Stepを抽出し、
      Area(Total Counts)との辻褄を合わせるための実効RSFを計算する。
    """
    # 1. パスの自動決定 (Documents/XPSAST/RSF.json)
    rsf_json_path = Path.home() / "Documents" / "XPSAST" / "RSF.json"
    
    # 2. RSF.jsonの読み込みと辞書化
    rsf_dict = {}
    if rsf_json_path.exists():
        with open(rsf_json_path, 'r', encoding='utf-8') as f:
            rsf_data = json.load(f)
            rsf_dict = {item["level"]: item["rsf"] for item in rsf_data}
    else:
        print(f"Warning: RSF file not found at {rsf_json_path}")

    # --- 3. JSONヘッダーから Sweeps と Time/Step を抽出 ---
    sweeps_dict = {}
    time_dict = {}
    
    if header_json_path and Path(header_json_path).exists():
        with open(header_json_path, 'r', encoding='utf-8') as f:
            header_data = json.load(f)
            
            reg_def = header_data.get("SpectralRegDef", [])
            reg_def2 = header_data.get("SpectralRegDef2", [])
            
            # Region ID をキーにして Tag 名を紐付ける
            id_to_tag = {}
            for line in reg_def:
                parts = line.split()
                if len(parts) >= 4:
                    reg_id = parts[0]       # "1", "2", "3"...
                    tag_name = parts[2]     # "C1s", "O1s"...
                    sweeps = float(parts[3]) # スキャン回数
                    id_to_tag[reg_id] = tag_name
                    sweeps_dict[tag_name] = sweeps
                    
            for line in reg_def2:
                parts = line.split()
                if len(parts) >= 2:
                    reg_id = parts[0]
                    time_ms = float(parts[1]) # ミリ秒
                    if reg_id in id_to_tag:
                        tag_name = id_to_tag[reg_id]
                        time_dict[tag_name] = time_ms / 1000.0 # 秒に変換

    corrected_rsf_list = []
    
    # 4. 各タグ（Region）ごとに計算を回す
    for i in range(len(tags)):
        tag = tags[i]
        base_rsf = rsf_dict.get(tag, 1.0) # 見つからない場合は1.0
        
        # 定量対象外（RSF=0）の場合は計算スキップ
        if base_rsf <= 0:
            corrected_rsf_list.append(0.0)
            continue

        # --- ピーク位置(BE)の特定 ---
        max_net_y = -float('inf')
        peak_be = x_all[i][0]
        for x_val, y_val, b_val in zip(x_all[i], y_all[i], bg_all[i]):
            net_y = y_val - b_val
            if net_y > max_net_y:
                max_net_y = net_y
                peak_be = x_val
        
        # --- RSFの運動エネルギー補正 ---
        ke = photon_energy - peak_be
        if ke > 0:
            # Corrected RSF = Base RSF * KE^(t_exp + l_exp)
            c_rsf = base_rsf * (ke ** (t_exp + l_exp))
        else:
            c_rsf = base_rsf
            
        # --- Area計算との相殺補正 (ここがキモ) ---
        sweeps = sweeps_dict.get(tag, 1.0)
        time_s = time_dict.get(tag, 1.0)
        
        # Area関数がいじられない前提なので、RSF側にSweepsとTimeを掛けて「実効RSF」とする
        effective_rsf = c_rsf * sweeps * time_s
        
        corrected_rsf_list.append(effective_rsf)
        
    return corrected_rsf_list

def Atom_per(tags, x_after, y_after, bg_all, corrected_rsf_list):
    """
    各ピークの面積と補正RSFから原子比率(Atomic %)を計算する
    """
    ap_tags = []      # 定量対象の元素名
    relative_ints = [] # Area / RSF の値（相対強度）

    # 1. 各要素の相対強度を計算
    for i in range(len(tags)):
        # RSFが0より大きい（定量対象）かつ名前がSurveyでない場合
        if corrected_rsf_list[i] > 0 and "Su" not in tags[i]:
            # Area関数を呼び出して面積を取得
            # (引数: x, y, baseline, x_min, x_max)
            # ※shirley_baselineで決まったx_min, x_maxを使う想定
            area_val = Area(x_after[i], y_after[i], bg_all[i], min(x_after[i]), max(x_after[i]))
            
            ap_tags.append(tags[i])
            relative_ints.append(area_val / corrected_rsf_list[i])

    # 2. 合計値で割ってパーセント(%)に変換
    total_int = sum(relative_ints)
    atom_percentages = []
    
    if total_int > 0:
        atom_percentages = [(val / total_int) * 100 for val in relative_ints]
    else:
        atom_percentages = [0.0] * len(relative_ints)

    return ap_tags, atom_percentages