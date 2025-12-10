import matplotlib.pyplot as plt
import math

def plot_spectra(tags, x_list, y_list):
    """
    データを受け取り、個数に合わせて自動的にレイアウトを調整して描画する関数
    """
    n = len(tags)
    if n == 0:
        print("プロットするデータがありません。")
        return

    # --- 1. レイアウトの自動計算 ---
    # データ数のルートをとって切り上げることで、正方形に近い列数を決める
    # 例: n=6 -> sqrt(6)=2.45 -> cols=3, rows=2
    # 例: n=10 -> sqrt(10)=3.16 -> cols=4, rows=3
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    # --- 2. ウィンドウサイズの調整 ---
    # グラフ1個あたり 横4インチ x 縦3インチ くらいのスペースを確保すると見やすい
    fig_width = 4 * cols
    fig_height = 3 * rows
    fig = plt.figure(figsize=(fig_width, fig_height))
    
    print(f"データ数: {n} -> レイアウト: {rows}行 x {cols}列")

    # --- 3. プロット実行 ---
    for i in range(n):
        ax = fig.add_subplot(rows, cols, i + 1)
        
        ax.plot(x_list[i], y_list[i])
        
        ax.set_title(tags[i])
        ax.set_xlabel('Binding Energy (eV)')
        ax.set_ylabel('Intensity (counts)')
        ax.invert_xaxis() # X軸反転

    plt.tight_layout()
    plt.show()