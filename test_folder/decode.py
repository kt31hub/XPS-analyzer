import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import base64
import re
import struct  # 浮動小数点などのバイナリ変換用に追加

class DecodeLane(tk.LabelFrame):
    def __init__(self, parent, app, lane_id, start_val="0", end_val="EOF"):
        super().__init__(parent, text=f"レーン {lane_id}", padx=5, pady=5, font=("Arial", 10, "bold"), bg="#f8f9fa")
        self.app = app
        self.lane_id = lane_id

        ctrl_frame = tk.Frame(self, bg="#f8f9fa")
        ctrl_frame.pack(fill="x", pady=5)

        tk.Label(ctrl_frame, text="開始(Byte):", bg="#f8f9fa").pack(side="left")
        self.entry_start = tk.Entry(ctrl_frame, width=8)
        self.entry_start.insert(0, str(start_val))
        self.entry_start.pack(side="left", padx=(2, 10))

        tk.Label(ctrl_frame, text="終了(Byte):", bg="#f8f9fa").pack(side="left")
        self.entry_end = tk.Entry(ctrl_frame, width=8)
        self.entry_end.insert(0, str(end_val))
        self.entry_end.pack(side="left", padx=(2, 10))

        tk.Label(ctrl_frame, text="方式:", bg="#f8f9fa").pack(side="left")
        self.method_var = tk.StringVar(value="Hex (16進数)")
        
        # 浮動小数点の方式を追加（リトルエンディアンとビッグエンディアン）
        methods = [
            "Hex (16進数)", "10進数配列 (Decimal)", 
            "Float32 (Little Endian)", "Float32 (Big Endian)",
            "Float64 (Little Endian)", "Float64 (Big Endian)",
            "UTF-8", "Shift-JIS", "Base64", 
            "XOR暗号", "XOR解析 (1バイト)", "シーザー暗号", "文字列抽出 (Strings)"
        ]
        # 文字列が長くなったのでドロップダウンの幅を拡大
        self.combo = ttk.Combobox(ctrl_frame, textvariable=self.method_var, values=methods, state="readonly", width=22)
        self.combo.pack(side="left", padx=(2, 10))
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.process_data(self.app.binary_data))

        tk.Label(ctrl_frame, text="キー:", bg="#f8f9fa").pack(side="left")
        self.entry_key = tk.Entry(ctrl_frame, width=8)
        self.entry_key.pack(side="left", padx=(2, 10))
        self.entry_key.insert(0, "0")

        btn_del = tk.Button(ctrl_frame, text="✖ 削除", command=self.delete_lane, fg="white", bg="#ff5252", relief="flat")
        btn_del.pack(side="right", padx=5)

        btn_update = tk.Button(ctrl_frame, text="適用", command=lambda: self.process_data(self.app.binary_data), bg="#e0e0e0", relief="flat")
        btn_update.pack(side="right", padx=5)

        self.text_out = tk.Text(self, height=6, wrap="word", font=("Consolas", 10))
        self.text_out.pack(fill="both", expand=True)

    def delete_lane(self):
        self.app.remove_lane(self)
        self.destroy()

    def process_data(self, full_data):
        self.text_out.delete(1.0, tk.END)
        if not full_data:
            return

        try:
            start = int(self.entry_start.get(), 0)
        except ValueError:
            start = 0

        end_str = self.entry_end.get().strip().upper()
        try:
            if end_str in ("EOF", ""):
                end = len(full_data)
            else:
                end = int(end_str, 0)
        except ValueError:
            end = len(full_data)

        chunk = full_data[start:end]
        if not chunk:
            self.text_out.insert(tk.END, "指定された範囲にデータが存在しません。")
            return

        method = self.method_var.get()
        key_str = self.entry_key.get().strip()
        res = ""

        try:
            if method == "Hex (16進数)":
                res = chunk.hex(' ')
            elif method == "10進数配列 (Decimal)":
                res = " ".join(str(b) for b in chunk)
            
            # --- 浮動小数点 (Float) のデコード処理 ---
            elif method.startswith("Float32"):
                endian = "<" if "Little" in method else ">"
                res_list = []
                # 4バイトずつ区切って処理
                for i in range(0, len(chunk), 4):
                    b = chunk[i:i+4]
                    if len(b) == 4:
                        val = struct.unpack(f'{endian}f', b)[0]
                        res_list.append(f"{val:.6g}") # 見やすくフォーマット
                    else:
                        res_list.append("(端数バイト)")
                res = "\n".join(res_list)

            elif method.startswith("Float64"):
                endian = "<" if "Little" in method else ">"
                res_list = []
                # 8バイトずつ区切って処理
                for i in range(0, len(chunk), 8):
                    b = chunk[i:i+8]
                    if len(b) == 8:
                        val = struct.unpack(f'{endian}d', b)[0]
                        res_list.append(f"{val:.10g}")
                    else:
                        res_list.append("(端数バイト)")
                res = "\n".join(res_list)
            # ----------------------------------------

            elif method in ("UTF-8", "Shift-JIS"):
                res = chunk.decode(method.lower(), errors='replace')
            elif method == "Base64":
                try:
                    res = base64.b64decode(chunk).decode('utf-8', errors='replace')
                except Exception as e:
                    res = f"Base64デコードエラー: {e}"
            elif method == "XOR暗号":
                key_bytes = bytes.fromhex(key_str) if key_str else b'\x00'
                if not key_bytes: key_bytes = b'\x00'
                dec = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(chunk)])
                res = "[テキスト]\n" + dec.decode('utf-8', errors='replace') + "\n\n[10進数]\n" + " ".join(str(b) for b in dec)
            elif method == "XOR解析 (1バイト)":
                results = []
                for k in range(256):
                    dec = bytes([b ^ k for b in chunk])
                    printable_count = sum(1 for b in dec if 32 <= b <= 126 or b in (9, 10, 13))
                    score = printable_count / len(dec) if len(dec) > 0 else 0
                    results.append((score, k, dec))
                results.sort(key=lambda x: x[0], reverse=True)
                res_lines = ["【XOR解析 上位候補】\n"]
                for score, k, dec in results[:10]:
                    if score < 0.05: continue
                    preview = dec[:40].decode('ascii', errors='replace').replace('\n', ' ')
                    res_lines.append(f"Key: 0x{k:02X} -> {preview}")
                res = "\n".join(res_lines) if len(res_lines) > 1 else "有意なテキストが見つかりません。"
            elif method == "シーザー暗号":
                shift = int(key_str) if key_str else 0
                dec = bytes([(b + shift) % 256 for b in chunk])
                res = "[テキスト]\n" + dec.decode('utf-8', errors='replace') + "\n\n[10進数]\n" + " ".join(str(b) for b in dec)
            elif method == "文字列抽出 (Strings)":
                strings = re.findall(b'[ -~]{4,}', chunk)
                res = "\n".join(s.decode('ascii') for s in strings)
                if not res: res = "ASCII文字列が見つかりませんでした。"
        except Exception as e:
            res = f"エラー: {e}"

        self.text_out.insert(tk.END, res)


class DecoderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("バイナリ可視化・分割解読アプリ")
        self.root.geometry("1100x750")
        
        self.binary_data = b""
        self.lanes = []
        self.next_lane_id = 1

        self.setup_ui()

    def setup_ui(self):
        self.paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=5, bg="#ccc")
        self.paned_window.pack(fill="both", expand=True, padx=10, pady=10)

        self.left_frame = tk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, minsize=400)

        left_ctrl = tk.Frame(self.left_frame)
        left_ctrl.pack(fill="x", pady=(0, 5))
        
        tk.Button(left_ctrl, text="📂 ファイルを開く", command=self.open_file, bg="#bbdefb", relief="flat", padx=10).pack(side="left")
        self.lbl_file = tk.Label(left_ctrl, text="未選択", fg="gray")
        self.lbl_file.pack(side="left", padx=10)

        btn_extract = tk.Button(self.left_frame, text="➡ 選択した範囲からレーンを作成", command=self.create_lane_from_selection, bg="#c8e6c9", relief="flat", pady=5)
        btn_extract.pack(fill="x", pady=5)

        tk.Label(self.left_frame, text="ファイルプレビュー (マウスで文字をなぞって選択できます)", fg="#555").pack(anchor="w")
        self.text_preview = tk.Text(self.left_frame, wrap="none", font=("Consolas", 10), cursor="xterm")
        self.text_preview.pack(fill="both", expand=True)

        self.right_frame = tk.Frame(self.paned_window)
        self.paned_window.add(self.right_frame, minsize=550)

        right_ctrl = tk.Frame(self.right_frame)
        right_ctrl.pack(fill="x", pady=(0, 5))
        
        tk.Button(right_ctrl, text="＋ 空のレーンを追加", command=lambda: self.add_lane(), bg="#ffe082", relief="flat").pack(side="right")
        tk.Label(right_ctrl, text="解析レーン", font=("Arial", 12, "bold")).pack(side="left")

        self.canvas = tk.Canvas(self.right_frame)
        scrollbar = tk.Scrollbar(self.right_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def open_file(self):
        filepath = filedialog.askopenfilename(title="解析するファイルを選択")
        if filepath:
            self.lbl_file.config(text=filepath.split("/")[-1], fg="black")
            with open(filepath, "rb") as f:
                self.binary_data = f.read()
            self.update_preview()
            for lane in self.lanes: lane.destroy()
            self.lanes.clear()
            self.add_lane(0, "EOF")

    def update_preview(self):
        self.text_preview.delete(1.0, tk.END)
        if not self.binary_data: return

        limit = min(len(self.binary_data), 65536)
        lines = []
        for i in range(0, limit, 16):
            chunk = self.binary_data[i:i+16]
            hex_part = ' '.join(f"{b:02X}" for b in chunk)
            ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
            lines.append(f"{i:08X}  {hex_part:<47}  |{ascii_part}|")
        
        res = "\n".join(lines)
        if len(self.binary_data) > 65536:
            res += "\n\n... (ファイルサイズが大きいため、プレビューは最初の64KBで省略しています) ..."
            
        self.text_preview.insert(tk.END, res)

    def get_byte_offset(self, index_str):
        line, col = map(int, index_str.split('.'))
        base_offset = (line - 1) * 16
        
        if col < 10: byte_offset = 0
        elif 10 <= col < 57: byte_offset = (col - 10) // 3
        elif col >= 60:
            byte_offset = col - 60
            if byte_offset > 15: byte_offset = 16
        else: byte_offset = 16
            
        return base_offset + byte_offset

    def create_lane_from_selection(self):
        if not self.binary_data: return
        try:
            start_idx = self.text_preview.index(tk.SEL_FIRST)
            end_idx = self.text_preview.index(tk.SEL_LAST)
            
            start_byte = self.get_byte_offset(start_idx)
            end_byte = self.get_byte_offset(end_idx)
            
            if start_byte >= end_byte:
                messagebox.showinfo("お知らせ", "有効な範囲を選択してください。")
                return

            self.add_lane(start_byte, end_byte)
            
        except tk.TclError:
            messagebox.showinfo("お知らせ", "左側のプレビュー画面で、解析したい部分をマウスでなぞって選択してください。")

    def add_lane(self, start_val="0", end_val="EOF"):
        lane = DecodeLane(self.scrollable_frame, self, self.next_lane_id, start_val, end_val)
        lane.pack(fill="x", pady=5, expand=True)
        self.lanes.append(lane)
        self.next_lane_id += 1
        if self.binary_data:
            lane.process_data(self.binary_data)

    def remove_lane(self, lane):
        if lane in self.lanes:
            self.lanes.remove(lane)

if __name__ == "__main__":
    root = tk.Tk()
    app = DecoderApp(root)
    root.mainloop()