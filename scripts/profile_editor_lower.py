"""
profiles.json編集用GUIツール
tkinterを使用してprofiles.jsonの編集を簡単に行えるツール
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import Calendar
from datetime import datetime
import os
import sys
from PIL import Image, ImageTk
import io
import urllib.request
import subprocess
import base64
import requests
import csv


def get_app_dir():
    """アプリケーションのベースディレクトリを取得"""
    if getattr(sys, 'frozen', False):
        # PyInstallerで実行ファイル化されている場合
        return os.path.dirname(sys.executable)
    else:
        # 通常のPythonスクリプトとして実行されている場合
        # scriptsフォルダから一つ上の階層を返す
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PlaceholderEntry(ttk.Entry):
    """プレースホルダー機能付きのEntryウィジェット"""
    def __init__(self, master=None, placeholder="", **kwargs):
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = 'grey'
        self.default_fg_color = 'black'

        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

        self._put_placeholder()

    def _put_placeholder(self):
        if not self.get():
            self.insert(0, self.placeholder)
            self.configure(foreground=self.placeholder_color)

    def _on_focus_in(self, event):
        if self.get() == self.placeholder:
            self.delete(0, tk.END)
            self.configure(foreground=self.default_fg_color)

    def _on_focus_out(self, event):
        if not self.get():
            self._put_placeholder()

    def get_value(self):
        """実際の値を取得（プレースホルダーでない場合のみ）"""
        value = self.get()
        return "" if value == self.placeholder else value

    def set_value(self, value):
        """値を設定"""
        self.delete(0, tk.END)
        if value:
            self.insert(0, value)
            self.configure(foreground=self.default_fg_color)
        else:
            self._put_placeholder()


class ProfileEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("もちふぃった～ プロファイルエディタ")
        self.root.geometry("1400x900")

        self.app_dir = get_app_dir()
        self.json_path = os.path.join(self.app_dir, "data", "profiles.json")
        self.data = None
        self.current_selection = None
        self.image_preview_label = None
        self.form_modified = False  # フォームが編集されたかどうか
        self.sort_column = "id"  # デフォルトのソート列
        self.sort_reverse = True  # ソート順（True=降順、ID001が下に）

        self.setup_ui()
        self.load_data()
        # 初期状態ではフィールドを無効化
        self.disable_form_fields()

    def setup_ui(self):
        """UIのセットアップ"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=3)  # フォーム欄の幅を広く
        main_frame.columnconfigure(2, weight=1)  # プレビュー欄
        main_frame.rowconfigure(1, weight=1)

        # 左側: リスト表示
        list_frame = ttk.LabelFrame(main_frame, text="プロファイル一覧", padding="5")
        list_frame.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        # ツリービュー
        self.tree = ttk.Treeview(list_frame, columns=("id", "avatar", "author", "profileAuthor"), show="headings", height=20)
        self.tree.heading("id", text="ID", command=lambda: self.sort_tree("id"))
        self.tree.heading("avatar", text="アバター名", command=lambda: self.sort_tree("avatar"))
        self.tree.heading("author", text="アバター作者", command=lambda: self.sort_tree("author"))
        self.tree.heading("profileAuthor", text="プロファイル作者", command=lambda: self.sort_tree("profileAuthor"))
        self.tree.column("#0", width=30)
        self.tree.column("id", width=50)
        self.tree.column("avatar", width=100)
        self.tree.column("author", width=100)
        self.tree.column("profileAuthor", width=100)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # 中央上部: ツールバー
        toolbar = ttk.Frame(main_frame)
        toolbar.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Button(toolbar, text="レコードを追加", command=self.add_profile).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="複製", command=self.duplicate_profile).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="削除", command=self.delete_profile).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="CSVインポート", command=self.import_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="CSVエクスポート", command=self.export_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="保存", command=self.save_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="再読み込み", command=self.load_data).pack(side=tk.LEFT, padx=2)

        # 中央下部: 編集フォーム
        form_frame = ttk.LabelFrame(main_frame, text="プロファイル編集", padding="10")
        form_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        # スクロール可能なフレーム
        canvas = tk.Canvas(form_frame)
        scrollbar_form = ttk.Scrollbar(form_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_form.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_form.pack(side=tk.RIGHT, fill=tk.Y)

        # フォームフィールド
        self.fields = {}
        self.field_trace_ids = []  # トレース用のID保存
        row = 0

        # ID（空欄なら自動採番、入力済みならその値を使用）
        ttk.Label(scrollable_frame, text="ID").grid(row=row, column=0, sticky=tk.W, pady=2)
        id_frame = ttk.Frame(scrollable_frame)
        id_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        self.fields["id"] = ttk.Entry(id_frame, width=50)
        self.fields["id"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(id_frame, text="※空欄で自動採番", font=("", 8), foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
        row += 1

        # 登録日（カレンダー付き）
        ttk.Label(scrollable_frame, text="登録日").grid(row=row, column=0, sticky=tk.W, pady=2)
        date_frame_registered = ttk.Frame(scrollable_frame)
        date_frame_registered.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        self.fields["registeredDate"] = ttk.Entry(date_frame_registered, width=40)
        self.fields["registeredDate"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(date_frame_registered, text="今日", width=6,
                   command=lambda: self.set_today("registeredDate")).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame_registered, text="📅", width=3,
                   command=lambda: self.open_calendar("registeredDate")).pack(side=tk.LEFT)
        row += 1

        # 更新日（カレンダー付き）
        ttk.Label(scrollable_frame, text="更新日").grid(row=row, column=0, sticky=tk.W, pady=2)
        date_frame_updated = ttk.Frame(scrollable_frame)
        date_frame_updated.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        self.fields["updatedDate"] = ttk.Entry(date_frame_updated, width=40)
        self.fields["updatedDate"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(date_frame_updated, text="今日", width=6,
                   command=lambda: self.set_today("updatedDate")).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame_updated, text="📅", width=3,
                   command=lambda: self.open_calendar("updatedDate")).pack(side=tk.LEFT)
        row += 1

        # チェックボックスフィールド
        checkbox_frame = ttk.Frame(scrollable_frame)
        checkbox_frame.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=10)

        self.fields["official"] = tk.BooleanVar()
        ttk.Checkbutton(checkbox_frame, text="公式", variable=self.fields["official"]).pack(side=tk.LEFT, padx=5)

        self.fields["forwardSupport"] = tk.BooleanVar()
        ttk.Checkbutton(checkbox_frame, text="順方向対応", variable=self.fields["forwardSupport"]).pack(side=tk.LEFT, padx=5)

        self.fields["reverseSupport"] = tk.BooleanVar()
        ttk.Checkbutton(checkbox_frame, text="逆方向対応", variable=self.fields["reverseSupport"]).pack(side=tk.LEFT, padx=5)
        row += 1

        # その他の通常フィールド
        normal_fields = [
            ("アバター名", "avatarName", False),
            ("プロファイルバージョン", "profileVersion", False),
            ("アバター作者", "avatarAuthor", False),
            ("アバターショップ名", "avatarshopname", False),
            ("アバター作者URL", "avatarAuthorUrl", True),
            ("共通素体", "bodyBase", False),
            ("プロファイル作者", "profileAuthor", False),
            ("プロファイルショップ名", "profileshopname", False),
            ("プロファイル作者URL", "profileAuthorUrl", True),
        ]

        # アバターURL
        ttk.Label(scrollable_frame, text="アバターURL").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.fields["avatarNameUrl"] = PlaceholderEntry(scrollable_frame, placeholder="https://", width=50)
        self.fields["avatarNameUrl"].grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        row += 1

        for label_text, field_name, is_url in normal_fields:
            ttk.Label(scrollable_frame, text=label_text).grid(row=row, column=0, sticky=tk.W, pady=2)
            if is_url:
                self.fields[field_name] = PlaceholderEntry(scrollable_frame, placeholder="https://", width=50)
            else:
                self.fields[field_name] = ttk.Entry(scrollable_frame, width=50)
            self.fields[field_name].grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
            row += 1

        # 配布方法（Boothボタン付き）
        ttk.Label(scrollable_frame, text="配布方法").grid(row=row, column=0, sticky=tk.W, pady=2)
        method_frame = ttk.Frame(scrollable_frame)
        method_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        self.fields["downloadMethod"] = ttk.Entry(method_frame, width=40)
        self.fields["downloadMethod"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(method_frame, text="Booth", width=8,
                   command=lambda: self.set_download_method("Booth")).pack(side=tk.LEFT, padx=2)
        row += 1

        # 残りのフィールド
        ttk.Label(scrollable_frame, text="配布場所URL").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.fields["downloadLocation"] = PlaceholderEntry(scrollable_frame, placeholder="https://", width=50)
        self.fields["downloadLocation"].grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        row += 1

        ttk.Label(scrollable_frame, text="画像URL").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.fields["imageUrl"] = PlaceholderEntry(scrollable_frame, placeholder="https://", width=50)
        self.fields["imageUrl"].grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        row += 1

        # 提供方法（ボタン付き）
        ttk.Label(scrollable_frame, text="提供方法").grid(row=row, column=0, sticky=tk.W, pady=2)
        pricing_frame = ttk.Frame(scrollable_frame)
        pricing_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))

        # 上段: 入力欄
        self.fields["pricing"] = ttk.Entry(pricing_frame, width=50)
        self.fields["pricing"].pack(side=tk.TOP, fill=tk.X, pady=(0, 5))

        # 下段: ボタン群
        pricing_button_frame = ttk.Frame(pricing_frame)
        pricing_button_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(pricing_button_frame, text="無料", width=10,
                   command=lambda: self.set_pricing("無料")).pack(side=tk.LEFT, padx=2)
        ttk.Button(pricing_button_frame, text="有料", width=10,
                   command=lambda: self.set_pricing("有料")).pack(side=tk.LEFT, padx=2)
        ttk.Button(pricing_button_frame, text="アバター同梱", width=12,
                   command=lambda: self.set_pricing("アバター同梱")).pack(side=tk.LEFT, padx=2)
        row += 1

        # プロファイル価格
        ttk.Label(scrollable_frame, text="プロファイル価格").grid(row=row, column=0, sticky=tk.W, pady=2)
        price_frame = ttk.Frame(scrollable_frame)
        price_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        self.fields["price"] = ttk.Entry(price_frame, width=50)
        self.fields["price"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(price_frame, text="※数字のみ(例: 500)", font=("", 8), foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
        row += 1

        # アバター価格
        ttk.Label(scrollable_frame, text="アバター価格").grid(row=row, column=0, sticky=tk.W, pady=2)
        avatar_price_frame = ttk.Frame(scrollable_frame)
        avatar_price_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        self.fields["avatarPrice"] = ttk.Entry(avatar_price_frame, width=50)
        self.fields["avatarPrice"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(avatar_price_frame, text="※数字のみ(例: 3000)", font=("", 8), foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
        row += 1

        # セールチェックボックス
        ttk.Label(scrollable_frame, text="セール").grid(row=row, column=0, sticky=tk.W, pady=2)
        sale_check_frame = ttk.Frame(scrollable_frame)
        sale_check_frame.grid(row=row, column=1, sticky=tk.W, pady=2, padx=(5, 0))
        self.fields["onSale"] = tk.BooleanVar()
        ttk.Checkbutton(sale_check_frame, text="セール中", variable=self.fields["onSale"],
                       command=self.toggle_sale_fields).pack(side=tk.LEFT)
        row += 1

        # セール開始日
        ttk.Label(scrollable_frame, text="セール開始日").grid(row=row, column=0, sticky=tk.W, pady=2)
        sale_start_frame = ttk.Frame(scrollable_frame)
        sale_start_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        self.fields["saleStartDate"] = ttk.Entry(sale_start_frame, width=40)
        self.fields["saleStartDate"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(sale_start_frame, text="📅", width=3,
                   command=lambda: self.open_calendar("saleStartDate")).pack(side=tk.LEFT, padx=2)
        row += 1

        # セール終了日
        ttk.Label(scrollable_frame, text="セール終了日").grid(row=row, column=0, sticky=tk.W, pady=2)
        sale_end_frame = ttk.Frame(scrollable_frame)
        sale_end_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        self.fields["saleEndDate"] = ttk.Entry(sale_end_frame, width=40)
        self.fields["saleEndDate"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(sale_end_frame, text="📅", width=3,
                   command=lambda: self.open_calendar("saleEndDate")).pack(side=tk.LEFT, padx=2)
        row += 1

        # セール価格
        ttk.Label(scrollable_frame, text="セール価格").grid(row=row, column=0, sticky=tk.W, pady=2)
        sale_price_frame = ttk.Frame(scrollable_frame)
        sale_price_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        self.fields["salePrice"] = ttk.Entry(sale_price_frame, width=50)
        self.fields["salePrice"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(sale_price_frame, text="※数字のみ(例: 2000)", font=("", 8), foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
        row += 1

        # 備考（複数行入力可能）
        ttk.Label(scrollable_frame, text="備考").grid(row=row, column=0, sticky=(tk.W, tk.N), pady=2)
        notes_frame = ttk.Frame(scrollable_frame)
        notes_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        self.fields["notes"] = tk.Text(notes_frame, width=50, height=4, wrap=tk.WORD)
        self.fields["notes"].pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        notes_scrollbar = ttk.Scrollbar(notes_frame, orient=tk.VERTICAL, command=self.fields["notes"].yview)
        notes_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.fields["notes"].configure(yscrollcommand=notes_scrollbar.set)
        row += 1

        scrollable_frame.columnconfigure(1, weight=1)

        # 入力状況表示
        row += 1
        validation_frame = ttk.LabelFrame(scrollable_frame, text="入力状況", padding="10")
        validation_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        self.validation_label = tk.Label(validation_frame, text="", fg="red", justify=tk.LEFT, anchor=tk.W)
        self.validation_label.pack(fill=tk.BOTH, expand=True)

        # 適用ボタン
        ttk.Button(scrollable_frame, text="変更を適用", command=self.apply_changes).grid(row=row+1, column=0, columnspan=2, pady=10)

        # 全てのEntryフィールドにキーイベントをバインド
        self.bind_field_changes()

        # 画像URLフィールドに自動プレビューをバインド
        self.fields["imageUrl"].bind("<FocusOut>", lambda e: self.preview_image())
        self.fields["imageUrl"].bind("<Return>", lambda e: self.preview_image())

        # 配布場所URLフィールドに配布方法自動判定をバインド
        self.fields["downloadLocation"].bind("<FocusOut>", lambda e: self.auto_detect_download_method())

        # 右側: プレビューエリア
        preview_panel = ttk.LabelFrame(main_frame, text="画像プレビュー", padding="10")
        preview_panel.grid(row=0, column=2, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.image_preview_label = ttk.Label(preview_panel, text="画像URLを入力すると\n自動でプレビュー表示",
                                            foreground="gray", anchor="center", justify="center")
        self.image_preview_label.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

    def bind_field_changes(self):
        """全フィールドの変更を検知するバインドを設定"""
        def mark_modified(event=None):
            self.form_modified = True
            # 入力状況を更新
            self.update_validation_status()

        # Entryフィールドにバインド
        for field_name, widget in self.fields.items():
            if isinstance(widget, ttk.Entry) or isinstance(widget, PlaceholderEntry):
                widget.bind("<KeyRelease>", mark_modified)
            elif isinstance(widget, tk.Text):
                widget.bind("<KeyRelease>", mark_modified)
            elif isinstance(widget, tk.BooleanVar):
                # チェックボックスは trace で監視
                widget.trace_add("write", lambda *args: setattr(self, "form_modified", True))

    def update_validation_status(self):
        """入力状況を更新"""
        # チェック対象フィールド（必須項目）
        required_fields = {
            "id": "ID",
            "avatarName": "アバター名",
            "avatarNameUrl": "アバターURL",
            "profileVersion": "プロファイルバージョン",
            "avatarAuthor": "アバター作者",
            "avatarAuthorUrl": "アバター作者URL",
            "profileAuthor": "プロファイル作者",
            "profileAuthorUrl": "プロファイル作者URL",
            "downloadMethod": "配布方法",
            "downloadLocation": "配布場所URL",
            "imageUrl": "画像URL",
            "pricing": "提供方法",
            "price": "プロファイル価格",
            "avatarPrice": "アバター価格",
        }

        missing_fields = []

        for field_name, display_name in required_fields.items():
            widget = self.fields.get(field_name)
            if not widget:
                continue

            has_value = False

            if isinstance(widget, tk.Text):
                has_value = bool(widget.get("1.0", tk.END).strip())
            elif isinstance(widget, PlaceholderEntry):
                has_value = bool(widget.get_value())
            elif isinstance(widget, ttk.Entry):
                # 無効化されている場合はスキップ
                if str(widget.cget("state")) == "disabled":
                    continue
                has_value = bool(widget.get().strip())

            if not has_value:
                missing_fields.append(f"× {display_name}")

        # 表示更新
        if missing_fields:
            self.validation_label.config(text="\n".join(missing_fields), fg="red")
        else:
            self.validation_label.config(text="✓ 全て入力済み", fg="green")

    def load_data(self):
        """JSONファイルを読み込み"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self.refresh_tree()
        except FileNotFoundError:
            messagebox.showerror("エラー", f"ファイルが見つかりません: {self.json_path}")
            self.data = {"lastUpdated": "", "profiles": []}
        except json.JSONDecodeError as e:
            messagebox.showerror("エラー", f"JSONの解析に失敗しました: {e}")
            self.data = {"lastUpdated": "", "profiles": []}

    def refresh_tree(self):
        """ツリービューを更新"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        if self.data and "profiles" in self.data:
            # ソート列に応じてソート
            sorted_profiles = self.get_sorted_profiles()
            for profile in sorted_profiles:
                self.tree.insert("", tk.END, values=(
                    profile.get("id", ""),
                    profile.get("avatarName", ""),
                    profile.get("avatarAuthor", ""),
                    profile.get("profileAuthor", "")
                ))

    def get_sorted_profiles(self):
        """ソート列と順序に基づいてプロファイルをソート"""
        if not self.data or "profiles" not in self.data:
            return []

        # ソートキーのマッピング
        key_map = {
            "id": lambda p: p.get("id", ""),
            "avatar": lambda p: p.get("avatarName", ""),
            "author": lambda p: p.get("avatarAuthor", ""),
            "profileAuthor": lambda p: p.get("profileAuthor", "")
        }

        sort_key = key_map.get(self.sort_column, key_map["id"])
        return sorted(self.data["profiles"], key=sort_key, reverse=self.sort_reverse)

    def sort_tree(self, column):
        """ツリービューをソート"""
        # 同じ列をクリックした場合は昇順/降順を切り替え
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False

        self.refresh_tree()

    def on_select(self, event):
        """リストアイテムが選択されたときの処理"""
        print("on_select called")  # デバッグ用
        selection = self.tree.selection()
        print(f"selection: {selection}")  # デバッグ用
        if not selection:
            return

        item = self.tree.item(selection[0])
        values = item["values"]
        print(f"values: {values}")  # デバッグ用

        if not values:
            return

        profile_id = str(values[0]).zfill(3) if isinstance(values[0], int) else values[0]
        print(f"profile_id: {profile_id}")  # デバッグ用

        # 既に選択中の同じプロファイルなら何もしない
        if self.current_selection and self.current_selection.get("id") == profile_id:
            return

        # 未保存の変更がある場合、確認ダイアログを表示
        if self.form_modified:
            result = messagebox.askyesno("確認", "未保存の変更があります。破棄しますか?")
            if not result:
                # キャンセル: イベントを一時的に無効化して元の選択に戻す
                self.tree.unbind("<<TreeviewSelect>>")
                if self.current_selection:
                    for item_id in self.tree.get_children():
                        item_values = self.tree.item(item_id)["values"]
                        if item_values and str(item_values[0]).zfill(3) if isinstance(item_values[0], int) else item_values[0] == self.current_selection.get("id"):
                            self.tree.selection_set(item_id)
                            break
                # イベントを再バインド
                self.tree.bind("<<TreeviewSelect>>", self.on_select)
                return

        # プロファイルを検索
        for profile in self.data["profiles"]:
            if profile.get("id") == profile_id:
                self.current_selection = profile
                self.load_profile_to_form(profile)
                self.form_modified = False  # 読み込み後は未編集状態
                break

    def load_profile_to_form(self, profile):
        """プロファイルデータをフォームに読み込み"""
        # フィールドを有効化
        self.enable_form_fields()

        # テキストフィールド
        for field_name, widget in self.fields.items():
            if field_name in ["official", "forwardSupport", "reverseSupport", "onSale"]:
                widget.set(profile.get(field_name, False))
            elif isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
                widget.insert("1.0", profile.get(field_name, ""))
            elif isinstance(widget, PlaceholderEntry):
                widget.set_value(profile.get(field_name, ""))
            elif isinstance(widget, ttk.Entry):
                widget.delete(0, tk.END)
                widget.insert(0, profile.get(field_name, ""))

        # セールフィールドの状態を更新
        self.toggle_sale_fields()

        # 入力状況を更新
        self.update_validation_status()

        # 画像プレビューを更新
        self.preview_image()

    def set_today(self, field_name):
        """今日の日付を設定"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.fields[field_name].delete(0, tk.END)
        self.fields[field_name].insert(0, today)

        # 入力状況を更新
        self.update_validation_status()

    def set_download_method(self, method):
        """配布方法を設定"""
        self.fields["downloadMethod"].delete(0, tk.END)
        self.fields["downloadMethod"].insert(0, method)

        # 入力状況を更新
        self.update_validation_status()

    def auto_detect_download_method(self):
        """配布場所URLから配布方法を自動判定"""
        url = self.fields["downloadLocation"].get_value()
        if not url:
            return

        # URLパターンによる判定
        if "booth.pm" in url:
            method = "Booth"
        elif "drive.google.com" in url or "docs.google.com" in url:
            method = "GoogleDrive"
        elif "github.com" in url:
            method = "GitHub"
        elif "discord.com" in url or "discord.gg" in url:
            method = "Discord"
        else:
            # 判定できない場合は何もしない
            return

        # 配布方法を自動設定
        self.set_download_method(method)

    def set_pricing(self, pricing):
        """提供方法を設定"""
        self.fields["pricing"].delete(0, tk.END)
        self.fields["pricing"].insert(0, pricing)

        # 「無料」の場合はプロファイル価格に0を自動入力
        if pricing == "無料":
            self.fields["price"].delete(0, tk.END)
            self.fields["price"].insert(0, "0")
        # 「アバター同梱」の場合はプロファイル価格に-を自動入力し、アバターURLを配布場所URLにコピー
        elif pricing == "アバター同梱":
            self.fields["price"].delete(0, tk.END)
            self.fields["price"].insert(0, "-")
            # アバターURLを配布場所URLにコピー
            avatar_url = self.fields["avatarNameUrl"].get_value()
            if avatar_url:
                self.fields["downloadLocation"].set_value(avatar_url)

        # 入力状況を更新
        self.update_validation_status()

    def toggle_sale_fields(self):
        """セール中チェックボックスの状態に応じてセール関連フィールドを有効/無効化"""
        is_on_sale = self.fields["onSale"].get()
        state = "normal" if is_on_sale else "disabled"

        # セール関連フィールドの状態を変更
        self.fields["saleStartDate"].config(state=state)
        self.fields["saleEndDate"].config(state=state)
        self.fields["salePrice"].config(state=state)

    def enable_form_fields(self):
        """全フォームフィールドを有効化"""
        for field_name, widget in self.fields.items():
            if field_name in ["official", "forwardSupport", "reverseSupport", "onSale"]:
                # チェックボックスは常に有効
                continue
            elif isinstance(widget, tk.Text):
                widget.config(state="normal")
            elif isinstance(widget, (ttk.Entry, PlaceholderEntry)):
                widget.config(state="normal")

    def disable_form_fields(self):
        """全フォームフィールドを無効化"""
        for field_name, widget in self.fields.items():
            if field_name in ["official", "forwardSupport", "reverseSupport", "onSale"]:
                # チェックボックスは常に無効化
                continue
            elif isinstance(widget, tk.Text):
                widget.config(state="disabled")
            elif isinstance(widget, (ttk.Entry, PlaceholderEntry)):
                widget.config(state="disabled")

    def preview_image(self):
        """画像URLからプレビューを表示"""
        image_url = self.fields["imageUrl"].get_value().strip()

        if not image_url:
            # 空欄の場合はプレビューをクリア
            self.image_preview_label.configure(image="", text="画像URLを入力すると\n自動でプレビュー表示")
            return

        try:
            # URLから画像をダウンロード
            with urllib.request.urlopen(image_url) as response:
                image_data = response.read()

            # 画像を読み込み
            image = Image.open(io.BytesIO(image_data))

            # アスペクト比を保ちながらリサイズ（最大300x300）
            max_size = (300, 300)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Tkinter用の画像に変換
            photo = ImageTk.PhotoImage(image)

            # ラベルに画像を設定
            self.image_preview_label.configure(image=photo, text="")
            self.image_preview_label.image = photo  # 参照を保持

        except urllib.error.URLError as e:
            self.image_preview_label.configure(image="", text=f"画像の取得に失敗:\n{str(e)[:50]}")
        except Exception as e:
            self.image_preview_label.configure(image="", text=f"画像の表示に失敗:\n{str(e)[:50]}")

    def open_calendar(self, field_name):
        """カレンダーダイアログを開く"""
        cal_window = tk.Toplevel(self.root)
        cal_window.title("日付を選択")
        cal_window.geometry("300x300")

        # 現在の値を取得
        current_value = self.fields[field_name].get()
        try:
            if current_value:
                year, month, day = map(int, current_value.split("-"))
                cal = Calendar(cal_window, selectmode="day", year=year, month=month, day=day)
            else:
                cal = Calendar(cal_window, selectmode="day")
        except:
            cal = Calendar(cal_window, selectmode="day")

        cal.pack(pady=20)

        def select_date():
            selected = cal.get_date()
            # カレンダーの日付フォーマットをYYYY-MM-DDに変換
            date_obj = datetime.strptime(selected, "%m/%d/%y")
            formatted_date = date_obj.strftime("%Y-%m-%d")
            self.fields[field_name].delete(0, tk.END)
            self.fields[field_name].insert(0, formatted_date)
            cal_window.destroy()

            # 入力状況を更新
            self.update_validation_status()

        ttk.Button(cal_window, text="選択", command=select_date).pack(pady=10)

    def apply_changes(self):
        """フォームの変更を適用"""
        if not self.current_selection:
            print("警告: プロファイルが選択されていません")
            return

        # 更新日を自動で今日の日付に設定
        today = datetime.now().strftime("%Y-%m-%d")
        self.fields["updatedDate"].delete(0, tk.END)
        self.fields["updatedDate"].insert(0, today)

        # フォームからデータを取得
        for field_name, widget in self.fields.items():
            if field_name == "id":
                # IDの処理: 空欄なら自動採番、入力済みならその値を使用
                input_id = widget.get().strip()
                if input_id:
                    # 入力されたIDが既に存在するか確認
                    existing_ids = [p.get("id") for p in self.data["profiles"] if p != self.current_selection]
                    if input_id in existing_ids:
                        messagebox.showerror("エラー", f"ID '{input_id}' は既に使用されています")
                        return
                    self.current_selection[field_name] = input_id
                else:
                    # 空欄の場合は自動採番
                    self.current_selection[field_name] = self.find_next_available_id()
            elif field_name in ["official", "forwardSupport", "reverseSupport", "onSale"]:
                self.current_selection[field_name] = widget.get()
            elif isinstance(widget, tk.Text):
                self.current_selection[field_name] = widget.get("1.0", tk.END).strip()
            elif isinstance(widget, PlaceholderEntry):
                self.current_selection[field_name] = widget.get_value()
            elif isinstance(widget, ttk.Entry):
                self.current_selection[field_name] = widget.get()

        self.refresh_tree()
        self.form_modified = False  # 適用後は未編集状態に

    def find_next_available_id(self):
        """空いている最も若いIDを見つける"""
        existing_ids = set()
        for profile in self.data["profiles"]:
            try:
                existing_ids.add(int(profile.get("id", "0")))
            except ValueError:
                continue

        # 1から順に空いているIDを探す
        next_id = 1
        while next_id in existing_ids:
            next_id += 1

        return str(next_id).zfill(3)

    def add_profile(self):
        """新しいレコードを追加（IDと登録日のみ入力済み）"""
        # IDを自動採番
        new_id = self.find_next_available_id()
        today = datetime.now().strftime("%Y-%m-%d")

        new_profile = {
            "id": new_id,
            "registeredDate": today,
            "updatedDate": today,
            "avatarName": "",
            "avatarNameUrl": "",
            "profileVersion": "1.0",
            "avatarAuthor": "",
            "avatarshopname": "",
            "avatarAuthorUrl": "",
            "bodyBase": "",
            "profileAuthor": "",
            "profileshopname": "",
            "profileAuthorUrl": "",
            "official": False,
            "downloadMethod": "Booth",
            "downloadLocation": "",
            "imageUrl": "",
            "pricing": "",
            "price": "",
            "avatarPrice": "",
            "onSale": False,
            "saleStartDate": "",
            "saleEndDate": "",
            "salePrice": "",
            "forwardSupport": False,
            "reverseSupport": False,
            "notes": ""
        }

        self.data["profiles"].append(new_profile)
        self.refresh_tree()

        # 新規追加したプロファイルを選択
        self.current_selection = new_profile
        self.load_profile_to_form(new_profile)
        self.form_modified = False  # 新規追加時は未編集状態

    def duplicate_profile(self):
        """選択中のプロファイルを複製"""
        if not self.current_selection:
            messagebox.showwarning("警告", "複製するプロファイルを選択してください")
            return

        # IDを自動採番
        new_id = self.find_next_available_id()
        today = datetime.now().strftime("%Y-%m-%d")

        # 現在のプロファイルをコピー
        new_profile = self.current_selection.copy()

        # 新しいIDと日付を設定
        new_profile["id"] = new_id
        new_profile["registeredDate"] = today
        new_profile["updatedDate"] = today

        # 指定されたフィールドをクリア
        new_profile["imageUrl"] = ""
        new_profile["avatarName"] = ""
        new_profile["avatarNameUrl"] = ""
        new_profile["downloadLocation"] = ""

        self.data["profiles"].append(new_profile)
        self.refresh_tree()

        # 新規複製したプロファイルを選択
        self.current_selection = new_profile
        self.load_profile_to_form(new_profile)
        self.form_modified = False

    def import_csv(self):
        """CSVファイルからプロファイルをインポート"""
        # CSVファイルを選択
        csv_path = filedialog.askopenfilename(
            title="CSVファイルを選択",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not csv_path:
            return

        try:
            imported_count = 0
            updated_count = 0
            error_count = 0
            error_messages = []

            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=2):  # ヘッダーが1行目なので2から
                    try:
                        # IDの処理
                        csv_id = row.get('id', '').strip()

                        if csv_id:
                            # IDが指定されている場合、既存レコードを検索
                            existing_profile = None
                            for profile in self.data["profiles"]:
                                if profile.get("id") == csv_id:
                                    existing_profile = profile
                                    break

                            if existing_profile:
                                # 既存レコードを更新
                                profile_data = existing_profile
                                updated_count += 1
                                # 更新日のみ今日の日付に
                                profile_data["updatedDate"] = datetime.now().strftime("%Y-%m-%d")
                            else:
                                # 指定されたIDで新規追加
                                profile_data = {"id": csv_id}
                                self.data["profiles"].append(profile_data)
                                imported_count += 1
                                # 新規の場合は登録日・更新日を今日に
                                profile_data["registeredDate"] = datetime.now().strftime("%Y-%m-%d")
                                profile_data["updatedDate"] = datetime.now().strftime("%Y-%m-%d")
                        else:
                            # IDが空の場合、自動採番で新規追加
                            new_id = self.find_next_available_id()
                            profile_data = {"id": new_id}
                            self.data["profiles"].append(profile_data)
                            imported_count += 1
                            # 新規の場合は登録日・更新日を今日に
                            profile_data["registeredDate"] = datetime.now().strftime("%Y-%m-%d")
                            profile_data["updatedDate"] = datetime.now().strftime("%Y-%m-%d")

                        # 各フィールドを設定
                        for field_name in ["avatarName", "avatarNameUrl", "profileVersion",
                                          "avatarAuthor", "avatarAuthorUrl", "bodyBase", "profileAuthor",
                                          "profileAuthorUrl", "downloadMethod", "downloadLocation",
                                          "imageUrl", "pricing", "price", "avatarPrice",
                                          "saleStartDate", "saleEndDate", "salePrice", "notes"]:
                            if field_name in row:
                                profile_data[field_name] = row[field_name].strip()

                        # 日付フィールド（CSVに値があればそれを使用、なければ既存値を維持）
                        if not csv_id or not existing_profile:
                            # 新規追加の場合は上で設定済み
                            pass
                        else:
                            # 更新の場合、CSVに日付があればそれを使用
                            if "registeredDate" in row and row["registeredDate"].strip():
                                profile_data["registeredDate"] = row["registeredDate"].strip()
                            if "updatedDate" in row and row["updatedDate"].strip():
                                profile_data["updatedDate"] = row["updatedDate"].strip()

                        # Boolean型フィールド
                        for field_name in ["official", "forwardSupport", "reverseSupport", "onSale"]:
                            if field_name in row:
                                value = row[field_name].strip().lower()
                                profile_data[field_name] = value in ["true", "1", "yes", "TRUE", "True"]

                    except Exception as e:
                        error_count += 1
                        error_messages.append(f"行{row_num}: {str(e)[:50]}")

            # インポート完了メッセージ
            self.refresh_tree()

            message = f"インポート完了\n\n"
            message += f"新規追加: {imported_count}件\n"
            message += f"更新: {updated_count}件\n"
            if error_count > 0:
                message += f"エラー: {error_count}件\n\n"
                message += "エラー詳細:\n" + "\n".join(error_messages[:5])
                if len(error_messages) > 5:
                    message += f"\n... 他 {len(error_messages) - 5}件"

            messagebox.showinfo("インポート完了", message)

        except Exception as e:
            messagebox.showerror("エラー", f"CSVファイルの読み込みに失敗しました:\n{str(e)}")



    def export_csv(self):
        """プロファイルをCSVファイルにエクスポート"""
        if not self.data or not self.data.get("profiles"):
            messagebox.showwarning("警告", "エクスポートするデータがありません")
            return

        # 保存先を選択
        csv_path = filedialog.asksaveasfilename(
            title="CSVファイルを保存",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="profiles.csv"
        )

        if not csv_path:
            return

        try:
            # フィールド名を定義（全項目）
            fieldnames = [
                "id", "registeredDate", "updatedDate",
                "avatarName", "avatarNameUrl", "profileVersion",
                "avatarAuthor", "avatarAuthorUrl", "bodyBase",
                "profileAuthor", "profileAuthorUrl",
                "official", "downloadMethod", "downloadLocation",
                "imageUrl", "pricing", "price", "avatarPrice",
                "onSale", "saleStartDate", "saleEndDate", "salePrice",
                "forwardSupport", "reverseSupport", "notes"
            ]

            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for profile in self.data["profiles"]:
                    # Boolean型を文字列に変換
                    row_data = {}
                    for field in fieldnames:
                        value = profile.get(field, "")
                        if isinstance(value, bool):
                            row_data[field] = str(value)
                        else:
                            row_data[field] = value
                    writer.writerow(row_data)

            messagebox.showinfo("完了", f"{len(self.data['profiles'])}件のプロファイルをエクスポートしました\n\n{csv_path}")

        except Exception as e:
            messagebox.showerror("エラー", f"CSVファイルの保存に失敗しました:\n{str(e)}")

    def delete_profile(self):
        """選択中のプロファイルを削除"""
        if not self.current_selection:
            return

        # 削除確認
        result = messagebox.askyesno("確認", f"ID: {self.current_selection['id']} を削除しますか?")
        if result:
            self.data["profiles"].remove(self.current_selection)
            self.current_selection = None
            self.refresh_tree()
            self.clear_form()
            self.form_modified = False

    def clear_form(self):
        """フォームをクリア"""
        for field_name, widget in self.fields.items():
            if field_name in ["official", "forwardSupport", "reverseSupport", "onSale"]:
                widget.set(False)
            elif isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
            elif isinstance(widget, PlaceholderEntry):
                widget.set_value("")
            elif isinstance(widget, ttk.Entry):
                widget.delete(0, tk.END)

    def load_config(self):
        """設定ファイルを読み込み"""
        config_path = os.path.join(self.app_dir, "config.json")

        if not os.path.exists(config_path):
            messagebox.showerror("設定エラー",
                "config.jsonが見つかりません。\n"
                "config.sample.jsonをコピーしてconfig.jsonを作成し、\n"
                "GitHubトークンを設定してください。")
            return None

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if not config.get("github_token") or config["github_token"] == "YOUR_GITHUB_TOKEN_HERE":
                messagebox.showerror("設定エラー",
                    "config.jsonにGitHubトークンが設定されていません。")
                return None

            return config
        except Exception as e:
            messagebox.showerror("設定エラー", f"config.jsonの読み込みに失敗しました:\n{str(e)}")
            return None

    def auto_git_push_api(self):
        """GitHub API経由でファイルを更新（Git CLI不要）"""
        # 設定を読み込み
        config = self.load_config()
        if not config:
            return False

        # 処理中ウィンドウを作成
        progress_window = tk.Toplevel(self.root)
        progress_window.title("処理中")
        progress_window.geometry("300x100")
        progress_window.transient(self.root)
        progress_window.grab_set()

        label = tk.Label(progress_window, text="GitHubにプッシュ中...", font=("", 12))
        label.pack(expand=True)

        progress_window.update()

        try:
            github_token = config["github_token"]

            # リポジトリ情報を取得（URLから抽出）
            repo_url = config.get("github_repo_url", "https://github.com/eringiriri/mochifitter_list.git")
            # "https://github.com/owner/repo.git" から "owner/repo" を抽出
            repo_path = repo_url.replace("https://github.com/", "").replace(".git", "")

            # profiles.jsonの内容を読み込み
            with open(self.json_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # GitHub APIのエンドポイント
            api_url = f"https://api.github.com/repos/{repo_path}/contents/data/profiles.json"

            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }

            # 現在のファイル情報を取得（SHAが必要）
            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                current_file = response.json()
                sha = current_file["sha"]
            else:
                progress_window.destroy()
                messagebox.showerror("エラー",
                    f"ファイル情報の取得に失敗しました: {response.status_code}\n{response.text}")
                return False

            # ファイルを更新
            commit_message = f"Update profiles.json - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            content_base64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')

            data = {
                "message": commit_message,
                "content": content_base64,
                "sha": sha
            }

            response = requests.put(api_url, headers=headers, json=data)

            progress_window.destroy()

            if response.status_code in [200, 201]:
                messagebox.showinfo("完了", "GitHubへのプッシュが完了しました。\nWebサイトは数分後に更新されます。")
                return True
            else:
                messagebox.showerror("プッシュエラー",
                    f"プッシュに失敗しました: {response.status_code}\n{response.text[:200]}")
                return False

        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("エラー", f"プッシュ処理でエラーが発生しました:\n{str(e)}")
            return False


    def save_data(self):
        """データをJSONファイルに保存"""
        try:
            # 最終更新日時を更新
            jst_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S JST")
            self.data["lastUpdated"] = jst_time

            # プロファイルをID順にソート
            self.data["profiles"] = sorted(self.data["profiles"], key=lambda p: p.get("id", ""))

            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)

            # 保存後に確認ダイアログを表示
            result = messagebox.askyesno("確認",
                                        "GitHubにプッシュしてWebサイトを更新しますか？")

            if result:
                self.auto_git_push_api()

        except Exception as e:
            messagebox.showerror("エラー", f"保存に失敗しました: {e}")


def main():
    root = tk.Tk()
    app = ProfileEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
