import pandas as pd
import os

def export_to_excel(save_path, tags, x_list, y_list, fit_results_list):
    """
    全データをExcelファイルに出力する関数
    save_path: 保存先のファイルパス (.xlsx)
    tags: タグのリスト
    x_list, y_list: 全データのx, yリスト
    fit_results_list: フィッティング結果の辞書リスト
    """
    
    # ExcelWriterを使ってファイルを作成
    try:
        with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
            print(f"\nExcel保存中: {os.path.basename(save_path)} ...")
            
            for i, tag in enumerate(tags):
                # 1. 基本データ (BE, Raw Intensity)
                data = {
                    'Binding Energy (eV)': x_list[i],
                    'Raw Intensity': y_list[i]
                }
                
                # 2. フィッティング結果がある場合、列を追加
                if fit_results_list[i] is not None:
                    res = fit_results_list[i]
                    
                    # バックグラウンド
                    data['Background'] = res['y_bg']
                    
                    # 全体のフィッティングカーブ (Envelope)
                    data['Total Fit'] = res['y_total']+res['y_bg']
                    
                    # 各成分 (Component)
                    for peak in res['peaks']:
                        col_name = f"Comp: {peak['name']}"
                        data[col_name] = peak['y_data']+res['y_bg']

                # 3. DataFrame作成
                df = pd.DataFrame(data)
                
                # 4. シート名はタグ名にする (Excelの制限で31文字以内)
                sheet_name = tag[:31] 
                
                # 5. 書き込み
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"  -> Sheet '{sheet_name}' output done.")

        print("Excel出力が完了しました。")
        
    except Exception as e:
        print(f"Excel保存中にエラーが発生しました: {e}")