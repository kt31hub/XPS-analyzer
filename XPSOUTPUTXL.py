import pandas as pd
import os

def export_to_excel(save_path, tags, x_list, y_list, fit_results_list, atomic_percent):
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
        # --- 2. 解析結果のまとめシート (Summary) 作成 ---
            # ここからインデントを1つ戻す (forループの外へ)
            
            # (A) 原子組成比 (Atomic %)
            atomic_data = []
            for i in range(len(tags)):
                atomic_data.append({
                    'Element': tags[i],
                    'Atomic %': atomic_percent[i]
                })
            df_atomic = pd.DataFrame(atomic_data)
            
            # (B) ピークフィッティング詳細 (Ratioなど)
            fit_summary_data = []
            for i, tag in enumerate(tags):
                res = fit_results_list[i]
                if res is not None:
                    # そのスペクトルに含まれるピーク情報をすべて抽出
                    for peak in res['peaks']:
                        fit_summary_data.append({
                            'Spectrum': tag,
                            'Component Name': peak['name'],
                            'Area Ratio (%)': peak['ratio'],
                            'Position (eV)': peak['center'],
                            'FWHM (eV)': peak['fwhm'],
                            'Area': peak['area']
                        })
            
            df_fit_summary = pd.DataFrame(fit_summary_data)

            # --- Summaryシートへの書き込み ---
            summary_sheet_name = "Summary_Result"
            
            # Atomic % を書き込み (開始位置: 行0, 列0)
            df_atomic.to_excel(writer, sheet_name=summary_sheet_name, startrow=0, startcol=0, index=False)
            
            # タイトル等のために少しスペースを空けて Fitting Result を書き込み
            start_row_fit = len(df_atomic) + 4
            
            df_fit_summary.to_excel(writer, sheet_name=summary_sheet_name, startrow=start_row_fit, startcol=0, index=False)

        print("Excel出力が完了しました。")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Excel保存中にエラーが発生しました: {e}")