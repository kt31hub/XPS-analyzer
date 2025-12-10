import numpy as np
from scipy.optimize import curve_fit

# --- 1. フィッティング用関数定義 (Pseudo-Voigt) ---
def pseudo_voigt(x, amp, center, fwhm, mix_ratio):
    """
    Pseudo-Voigt関数 (ガウス関数とローレンツ関数の線形結合)
    mix_ratio: 0=Gaussian, 1=Lorentzian
    """
    # 半値幅(FWHM)から各パラメータへの変換
    sigma = fwhm / (2 * np.sqrt(2 * np.log(2))) # ガウス用
    gamma = fwhm / 2.0                          # ローレンツ用

    # ガウス関数
    g = np.exp(-((x - center)**2) / (2 * sigma**2))
    
    # ローレンツ関数
    l = 1 / (1 + ((x - center) / gamma)**2)
    
    # 混合
    return amp * ((1 - mix_ratio) * g + mix_ratio * l)

# --- 2. 複数のピークを足し合わせるモデル関数 ---
def multi_peak_model(x, *params):
    """
    curve_fitに渡すための、全ピークの合計を返す関数
    """
    y_sum = np.zeros_like(x)
    num_peaks = len(params) // 4
    
    for i in range(num_peaks):
        amp = params[i*4]
        cen = params[i*4+1]
        fwhm = params[i*4+2]
        mix = params[i*4+3]
        y_sum += pseudo_voigt(x, amp, cen, fwhm, mix)
        
    return y_sum

# --- 3. メインのフィッティング実行関数 ---
def perform_fitting(x, y, peak_infos, verbose=True):
    """
    x: エネルギー軸 (eV)
    y: バックグラウンドを引いた後の強度データ
    peak_infos: jsonから読み込んだピーク情報のリスト
    verbose: Trueなら結果をコンソールに表示する
    """
    x = np.array(x)
    y = np.array(y)
    
    initial_guesses = []
    bounds_min = []
    bounds_max = []
    
    # JSON情報から初期値と制約条件を作成
    for p in peak_infos:
        # --- Amplitude (高さ) ---
        nearest_idx = np.abs(x - p["center"]).argmin()
        init_amp = y[nearest_idx] if y[nearest_idx] > 0 else np.max(y) * 0.5
        
        initial_guesses.append(init_amp)
        bounds_min.append(0)
        bounds_max.append(np.inf)
        
        # --- Center (位置) ---
        initial_guesses.append(p["center"])
        bounds_min.append(p["center"] - p["center_error"])
        bounds_max.append(p["center"] + p["center_error"])
        
        # --- FWHM (半値幅) ---
        initial_guesses.append(p["FWHM"])
        bounds_min.append(p["FWHM"] - p["FWHM_error"])
        bounds_max.append(p["FWHM"] + p["FWHM_error"])
        
        # --- Mix Ratio (GL混合比 0~1) ---
        initial_guesses.append(0.3)
        bounds_min.append(0.0)
        bounds_max.append(1.0)

    # curve_fit 実行
    try:
        popt, pcov = curve_fit(
            multi_peak_model, 
            x, 
            y, 
            p0=initial_guesses, 
            bounds=(bounds_min, bounds_max),
            maxfev=10000
        )
    except RuntimeError:
        if verbose:
            print("Fitting failed to converge.")
        return None, None

    # 結果整理
    fitted_peaks = []
    num_peaks = len(peak_infos)
    
    # まず各成分を計算
    temp_peaks = []
    total_area = 0.0
    
    for i in range(num_peaks):
        amp, cen, fwhm, mix = popt[i*4 : (i+1)*4]
        
        # このピーク単体の波形
        y_comp = pseudo_voigt(x, amp, cen, fwhm, mix)
        
        # ★★★ 修正箇所: np.abs() を追加して絶対値にする ★★★
        area = np.abs(np.trapz(y_comp, x)) 
        
        total_area += area
        
        temp_peaks.append({
            "name": peak_infos[i]["name"],
            "amplitude": amp,
            "center": cen,
            "fwhm": fwhm,
            "mix_ratio": mix,
            "y_data": y_comp,
            "area": area
        })

    # 面積比を計算して格納
    if verbose:
        print("-" * 65)
        print(f"{'Name':<10} | {'Position':<10} | {'FWHM':<6} | {'Area':<10} | {'Ratio (%)':<10}")
        print("-" * 65)

    for p in temp_peaks:
        if total_area > 0:
            ratio = (p['area'] / total_area) * 100
        else:
            ratio = 0.0
        
        p['ratio'] = ratio # 辞書に追加
        fitted_peaks.append(p)
        
        if verbose:
            print(f"{p['name']:<10} | {p['center']:<7.2f} eV | {p['fwhm']:<6.2f} | {p['area']:<10.1f} | {ratio:>6.1f} %")
    
    if verbose:
        print("-" * 65)

    # 合計波形
    y_fit_total = multi_peak_model(x, *popt)
    
    return fitted_peaks, y_fit_total