"""
URL調査ツール
URLを1つずつ調査し、ブロックするかスキップするかを判定するツール
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import webbrowser
import os


class URLInvestigationTool:
    def __init__(self, root):
        self.root = root
        self.root.title("URL調査ツール")
        self.root.geometry("800x600")

        self.block_urls_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "Block_URLs.txt")
        self.url_list = []
        self.current_url = ""

        self.setup_ui()

    def setup_ui(self):
        """UIのセットアップ"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # 現在調査中のURL表示エリア
        current_frame = ttk.LabelFrame(main_frame, text="現在調査中のURL", padding="10")
        current_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        current_frame.columnconfigure(0, weight=1)

        self.current_url_entry = ttk.Entry(current_frame, state="readonly", font=("", 10))
        self.current_url_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # ボタンフレーム
        button_frame = ttk.Frame(current_frame)
        button_frame.grid(row=1, column=0, sticky=tk.W)

        ttk.Button(button_frame, text="次へ", command=self.next_url, width=15).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="コピー", command=self.copy_url, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="ブロック", command=self.block_url, width=15).pack(side=tk.LEFT, padx=5)

        # URL一覧入力エリア
        list_frame = ttk.LabelFrame(main_frame, text="URL一覧", padding="10")
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        self.url_list_text = scrolledtext.ScrolledText(list_frame, width=80, height=20, wrap=tk.WORD)
        self.url_list_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def next_url(self):
        """次のURLへ移動"""
        # テキストエリアからURL一覧を取得
        text_content = self.url_list_text.get("1.0", tk.END).strip()

        if not text_content:
            return

        # 改行で分割してURL一覧を作成
        urls = [line.strip() for line in text_content.split('\n') if line.strip()]

        if not urls:
            return

        # 最初のURLを取得
        self.current_url = urls[0]

        # 現在のURLを表示
        self.current_url_entry.config(state="normal")
        self.current_url_entry.delete(0, tk.END)
        self.current_url_entry.insert(0, self.current_url)
        self.current_url_entry.config(state="readonly")

        # クリップボードにコピー
        self.root.clipboard_clear()
        self.root.clipboard_append(self.current_url)

        # デフォルトブラウザで開く
        webbrowser.open(self.current_url)

        # URL一覧から削除
        remaining_urls = urls[1:]
        self.url_list_text.delete("1.0", tk.END)
        if remaining_urls:
            self.url_list_text.insert("1.0", '\n'.join(remaining_urls))

    def copy_url(self):
        """現在のURLをクリップボードにコピー"""
        if self.current_url:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_url)

    def block_url(self):
        """現在のURLをBlock_URLs.txtに追加して次へ"""
        if not self.current_url:
            return

        # Block_URLs.txtに追加
        with open(self.block_urls_path, 'a', encoding='utf-8') as f:
            f.write(self.current_url + '\n')

        # 次のURLへ
        self.next_url()


def main():
    root = tk.Tk()
    app = URLInvestigationTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()
