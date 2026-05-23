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
import threading
import subprocess
import base64
import requests
import csv
import re
from bs4 import BeautifulSoup


def get_app_dir():
    """アプリケーションのベースディレクトリを取得"""
    if getattr(sys, 'frozen', False):
        # PyInstallerで実行ファイル化されている場合
        return os.path.dirname(sys.executable)
    else:
        # 通常のPythonスクリプトとして実行されている場合（scriptsフォルダ内から1つ上）
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
        self.status_labels = {}  # ステータス表示ラベル

        # URL調査用
        self.current_investigation_url = ""
        self.current_investigation_id = ""
        self.block_urls_path = os.path.join(self.app_dir, "data", "Block_URLs.txt")

        self.search_var = None  # setup_uiで作成
        self._current_preview_url = ""  # 現在プレビュー中のURL

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

        # 検索フレーム
        search_frame = ttk.Frame(list_frame)
        search_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Label(search_frame, text="検索:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.filter_profiles())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # クリアボタン
        ttk.Button(search_frame, text="✕", width=3, command=self.clear_search).pack(side=tk.LEFT, padx=(5, 0))

        # ID振り直しボタン
        id_reassign_frame = ttk.Frame(list_frame)
        id_reassign_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Button(id_reassign_frame, text="ID振り直し", command=self.reassign_ids).pack(side=tk.LEFT, padx=2)

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

        self.tree.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=2, column=1, sticky=(tk.N, tk.S))

        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(2, weight=1)

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
        ttk.Button(toolbar, text="GitHubからPull", command=self.pull_from_github).pack(side=tk.LEFT, padx=2)

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
        self.fields["id"].bind("<FocusOut>", self.check_id_duplicate)
        ttk.Label(id_frame, text="※空欄で自動採番", font=("", 8), foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
        row += 1

        # 登録日（カレンダー付き、時間入力可能）
        ttk.Label(scrollable_frame, text="登録日").grid(row=row, column=0, sticky=tk.W, pady=2)
        date_frame_registered = ttk.Frame(scrollable_frame)
        date_frame_registered.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        self.fields["registeredDate"] = ttk.Entry(date_frame_registered, width=40)
        self.fields["registeredDate"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(date_frame_registered, text="今日", width=6,
                   command=lambda: self.set_today("registeredDate")).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame_registered, text="📅", width=3,
                   command=lambda: self.open_calendar("registeredDate")).pack(side=tk.LEFT)
        ttk.Label(date_frame_registered, text="※YYYY-MM-DD または YYYY-MM-DD HH:MM:SS", font=("", 8), foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
        row += 1

        # 更新日（カレンダー付き、時間入力可能）
        ttk.Label(scrollable_frame, text="更新日").grid(row=row, column=0, sticky=tk.W, pady=2)
        date_frame_updated = ttk.Frame(scrollable_frame)
        date_frame_updated.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        self.fields["updatedDate"] = ttk.Entry(date_frame_updated, width=40)
        self.fields["updatedDate"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(date_frame_updated, text="今日", width=6,
                   command=lambda: self.set_today("updatedDate")).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame_updated, text="📅", width=3,
                   command=lambda: self.open_calendar("updatedDate")).pack(side=tk.LEFT)
        ttk.Label(date_frame_updated, text="※YYYY-MM-DD または YYYY-MM-DD HH:MM:SS", font=("", 8), foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
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

        # アバターURL（取得ボタン付き）
        ttk.Label(scrollable_frame, text="アバターURL").grid(row=row, column=0, sticky=tk.W, pady=2)
        avatar_url_frame = ttk.Frame(scrollable_frame)
        avatar_url_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        self.fields["avatarNameUrl"] = PlaceholderEntry(avatar_url_frame, placeholder="https://", width=40)
        self.fields["avatarNameUrl"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(avatar_url_frame, text="取得", width=6,
                   command=self.fetch_from_url).pack(side=tk.LEFT, padx=2)
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

        # 配布場所URL（取得ボタン付き）
        ttk.Label(scrollable_frame, text="配布場所URL").grid(row=row, column=0, sticky=tk.W, pady=2)
        download_url_frame = ttk.Frame(scrollable_frame)
        download_url_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        self.fields["downloadLocation"] = PlaceholderEntry(download_url_frame, placeholder="https://", width=40)
        self.fields["downloadLocation"].pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(download_url_frame, text="取得", width=6,
                   command=self.fetch_from_download_url).pack(side=tk.LEFT, padx=2)
        row += 1

        ttk.Label(scrollable_frame, text="画像URL").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.fields["imageUrl"] = PlaceholderEntry(scrollable_frame, placeholder="https://", width=50)
        self.fields["imageUrl"].grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        row += 1

        # 価格区分（ボタン付き）
        ttk.Label(scrollable_frame, text="価格区分").grid(row=row, column=0, sticky=tk.W, pady=2)
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

        # 右側: コンテナフレーム（プレビュー + URL調査を縦配置）
        right_container = ttk.Frame(main_frame)
        right_container.grid(row=0, column=2, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))

        # 画像プレビューエリア（上部）
        preview_panel = ttk.LabelFrame(right_container, text="画像プレビュー", padding="10")
        preview_panel.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 5))

        self.image_preview_label = ttk.Label(preview_panel, text="画像URLを入力すると\n自動でプレビュー表示",
                                            foreground="gray", anchor="center", justify="center")
        self.image_preview_label.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # URL調査パネル（下部）
        url_investigation_panel = ttk.LabelFrame(right_container, text="URL調査", padding="10")
        url_investigation_panel.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.setup_url_investigation_panel(url_investigation_panel)

    def add_status_to_frame(self, frame, field_name, always_gray=False):
        """フレームにステータスインジケーターを追加"""
        status_label = tk.Label(frame, text="●", fg="gray", width=2)
        status_label.pack(side=tk.LEFT, padx=(0, 5))

        self.status_labels[field_name] = {
            "label": status_label,
            "always_gray": always_gray
        }

        return status_label

    def update_status_color(self, field_name):
        """ステータス色を更新"""
        if field_name not in self.status_labels:
            return

        status_info = self.status_labels[field_name]

        # 常にグレーのフィールド
        if status_info["always_gray"]:
            status_info["label"].config(fg="gray")
            return

        # フィールドの値を取得
        widget = self.fields.get(field_name)
        if not widget:
            return

        # 値の有無を確認
        has_value = False
        if isinstance(widget, tk.BooleanVar):
            # チェックボックスは常にグレー
            status_info["label"].config(fg="gray")
            return
        elif isinstance(widget, tk.Text):
            has_value = bool(widget.get("1.0", tk.END).strip())
        elif isinstance(widget, PlaceholderEntry):
            has_value = bool(widget.get_value())
        elif isinstance(widget, ttk.Entry):
            # 無効化されているか確認
            if str(widget.cget("state")) == "disabled":
                status_info["label"].config(fg="gray")
                return
            has_value = bool(widget.get().strip())

        # 色を設定
        status_info["label"].config(fg="green" if has_value else "red")

    def update_all_status_colors(self):
        """全ステータス色を更新"""
        for field_name in self.status_labels.keys():
            self.update_status_color(field_name)

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
            "avatarshopname": "アバターショップ名",
            "profileAuthor": "プロファイル作者",
            "profileAuthorUrl": "プロファイル作者URL",
            "profileshopname": "プロファイルショップ名",
            "downloadMethod": "配布方法",
            "downloadLocation": "配布場所URL",
            "imageUrl": "画像URL",
            "pricing": "価格区分",
            "price": "プロファイル価格",
            "avatarPrice": "アバター価格",
        }

        # downloadLocation/profileshopname は Booth URL のときのみ必須
        download_url = self.fields.get("downloadLocation").get_value() if self.fields.get("downloadLocation") else ""
        is_booth_download = "booth.pm" in download_url if download_url else False

        missing_fields = []

        for field_name, display_name in required_fields.items():
            widget = self.fields.get(field_name)
            if not widget:
                continue

            # Booth でない配布URLの場合は profileshopname をスキップ必須判定
            if field_name == "profileshopname" and not is_booth_download:
                continue
            # Booth でない配布URLの場合は downloadLocation もスキップ必須判定
            if field_name == "downloadLocation" and not is_booth_download:
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
        if hasattr(self, 'search_var') and self.search_var:
            # 検索機能が有効な場合はfilter_profilesを使用
            self.filter_profiles()
        else:
            # 初期化中は従来通り
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

    def filter_profiles(self):
        """検索キーワードに基づいてプロファイル一覧をフィルタリング"""
        search_text = self.search_var.get().lower().strip()

        # ツリービューをクリア
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.data or "profiles" not in self.data:
            return

        # ソート済みプロファイルを取得
        sorted_profiles = self.get_sorted_profiles()

        # 検索フィルタ適用
        for profile in sorted_profiles:
            # 検索テキストが空なら全て表示
            if not search_text:
                self.tree.insert("", tk.END, values=(
                    profile.get("id", ""),
                    profile.get("avatarName", ""),
                    profile.get("avatarAuthor", ""),
                    profile.get("profileAuthor", "")
                ))
                continue

            # 各フィールドを検索
            id_match = search_text in profile.get("id", "").lower()
            name_match = search_text in profile.get("avatarName", "").lower()
            author_match = search_text in profile.get("avatarAuthor", "").lower()
            profile_author_match = search_text in profile.get("profileAuthor", "").lower()
            note_match = search_text in profile.get("notes", "").lower()
            body_base_match = search_text in profile.get("bodyBase", "").lower()
            avatar_url_match = search_text in profile.get("avatarNameUrl", "").lower()
            download_url_match = search_text in profile.get("downloadLocation", "").lower()

            # いずれかにマッチすれば表示
            if id_match or name_match or author_match or profile_author_match or note_match or body_base_match or avatar_url_match or download_url_match:
                self.tree.insert("", tk.END, values=(
                    profile.get("id", ""),
                    profile.get("avatarName", ""),
                    profile.get("avatarAuthor", ""),
                    profile.get("profileAuthor", "")
                ))

    def clear_search(self):
        """検索をクリアして全件表示"""
        self.search_var.set("")
        # filter_profiles は trace により自動的に呼ばれる

    def _id_sort_key(self, id_val):
        """IDをソート用キーに変換。数値なら数値順、そうでなければ文字列順（数値の後）"""
        s = str(id_val).strip()
        if s.isdigit():
            return (0, int(s))
        return (1, s)

    def get_sorted_profiles(self):
        """ソート列と順序に基づいてプロファイルをソート"""
        if not self.data or "profiles" not in self.data:
            return []

        # ソートキーのマッピング
        key_map = {
            "id": lambda p: self._id_sort_key(p.get("id", "")),
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

        # 未保存の変更がある場合、確認
        if self.form_modified and self.current_selection:
            result = messagebox.askyesno("確認", "未保存の変更があります。破棄しますか?")
            if not result:
                # キャンセル: イベントを一時的に無効化して元の選択に戻す
                self.tree.unbind("<<TreeviewSelect>>")
                if self.current_selection:
                    current_id_key = self._id_sort_key(self.current_selection.get("id", ""))
                    for item_id in self.tree.get_children():
                        item_values = self.tree.item(item_id)["values"]
                        if item_values and self._id_sort_key(item_values[0]) == current_id_key:
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

    def load_profile_by_id(self, profile_id: str) -> bool:
        """ID指定でプロファイルをロードし、ツリー選択も合わせる"""
        if not profile_id:
            return False
        profile_id = str(profile_id).zfill(3)
        target = None
        for profile in self.data.get("profiles", []):
            if str(profile.get("id")).zfill(3) == profile_id:
                target = profile
                break
        if not target:
            return False

        # ツリーの選択を更新
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id)["values"]
            if not values:
                continue
            vid = str(values[0]).zfill(3) if isinstance(values[0], int) else str(values[0])
            if vid == profile_id:
                self.tree.selection_set(item_id)
                self.tree.see(item_id)
                break

        self.current_selection = target
        self.load_profile_to_form(target)
        self.form_modified = False
        return True

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
        """今日の日付と時刻を設定"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.fields[field_name].delete(0, tk.END)
        self.fields[field_name].insert(0, now)

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
        """価格区分を設定"""
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
        """画像URLからプレビューを表示 (非同期)"""
        if isinstance(self.fields["imageUrl"], PlaceholderEntry):
            image_url = self.fields["imageUrl"].get_value().strip()
        else:
            image_url = self.fields["imageUrl"].get().strip()

        if not image_url:
            # 空欄の場合はプレビューをクリア
            self.image_preview_label.configure(image="", text="画像URLを入力すると\n自動でプレビュー表示")
            return

        # ローディング表示
        self.image_preview_label.configure(image="", text="読み込み中...")
        self._current_preview_url = image_url

        def load_thread():
            try:
                # URLから画像をダウンロード
                headers = {'User-Agent': 'Mozilla/5.0'}
                req = urllib.request.Request(image_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    image_data = response.read()

                # このスレッドが開始された時のURLと現在のURLが一致するか確認
                if self._current_preview_url != image_url:
                    return

                # 画像を読み込み
                image = Image.open(io.BytesIO(image_data))

                # アスペクト比を保ちながらリサイズ（最大250x250）
                max_size = (250, 250)
                image.thumbnail(max_size, Image.Resampling.LANCZOS)

                # Tkinter用の画像に変換
                photo = ImageTk.PhotoImage(image)

                # メインスレッドでUI更新
                self.root.after(0, lambda: self._update_image_preview(image_url, photo))

            except Exception as e:
                # エラー時もメインスレッドでUI更新
                self.root.after(0, lambda: self._handle_preview_error(image_url, e))

        threading.Thread(target=load_thread, daemon=True).start()

    def _update_image_preview(self, url, photo):
        """プレビュー画像を更新 (メインスレッドで実行)"""
        if self._current_preview_url == url:
            self.image_preview_label.configure(image=photo, text="")
            self.image_preview_label.image = photo

    def _handle_preview_error(self, url, e):
        """画像取得エラーを処理 (メインスレッドで実行)"""
        if self._current_preview_url == url:
            self.image_preview_label.configure(image="", text=f"画像の取得に失敗:\n{str(e)[:50]}")

    def open_calendar(self, field_name):
        """カレンダーダイアログを開く"""
        cal_window = tk.Toplevel(self.root)
        cal_window.title("日付を選択")
        cal_window.geometry("300x350")

        # 現在の値を取得
        current_value = self.fields[field_name].get()
        existing_time = None
        try:
            if current_value:
                # 時間が含まれているかチェック
                if " " in current_value and len(current_value.split()) == 2:
                    date_part, time_part = current_value.split()
                    existing_time = time_part
                    year, month, day = map(int, date_part.split("-"))
                    cal = Calendar(cal_window, selectmode="day", year=year, month=month, day=day)
                else:
                    # 日付のみの場合
                    year, month, day = map(int, current_value.split("-"))
                    cal = Calendar(cal_window, selectmode="day", year=year, month=month, day=day)
            else:
                cal = Calendar(cal_window, selectmode="day")
        except:
            cal = Calendar(cal_window, selectmode="day")

        cal.pack(pady=20)

        # 時間入力欄を追加
        time_frame = ttk.Frame(cal_window)
        time_frame.pack(pady=10)
        ttk.Label(time_frame, text="時間 (HH:MM:SS):").pack(side=tk.LEFT, padx=5)
        time_entry = ttk.Entry(time_frame, width=10)
        if existing_time:
            time_entry.insert(0, existing_time)
        else:
            # 現在時刻をデフォルト値として設定
            time_entry.insert(0, datetime.now().strftime("%H:%M:%S"))
        time_entry.pack(side=tk.LEFT, padx=5)

        def select_date():
            selected = cal.get_date()
            # カレンダーの日付フォーマットをYYYY-MM-DDに変換
            date_obj = datetime.strptime(selected, "%m/%d/%y")
            formatted_date = date_obj.strftime("%Y-%m-%d")
            
            # 時間を取得
            time_value = time_entry.get().strip()
            if time_value:
                # 時間の形式を検証
                try:
                    # HH:MM:SS形式を検証
                    datetime.strptime(time_value, "%H:%M:%S")
                    formatted_date = f"{formatted_date} {time_value}"
                except ValueError:
                    # 形式が正しくない場合は日付のみ
                    pass
            
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

        # 更新日を自動で今日の日付と時刻に設定
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.fields["updatedDate"].delete(0, tk.END)
        self.fields["updatedDate"].insert(0, now)

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
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        new_profile = {
            "id": new_id,
            "registeredDate": now,
            "updatedDate": now,
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
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 現在のプロファイルをコピー
        new_profile = self.current_selection.copy()

        # 新しいIDと日付を設定
        new_profile["id"] = new_id
        new_profile["registeredDate"] = now
        new_profile["updatedDate"] = now

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
                                # 更新日のみ今日の日付と時刻に
                                profile_data["updatedDate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            else:
                                # 指定されたIDで新規追加
                                profile_data = {"id": csv_id}
                                self.data["profiles"].append(profile_data)
                                imported_count += 1
                                # 新規の場合は登録日・更新日を今日に
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                profile_data["registeredDate"] = now
                                profile_data["updatedDate"] = now
                        else:
                            # IDが空の場合、自動採番で新規追加
                            new_id = self.find_next_available_id()
                            profile_data = {"id": new_id}
                            self.data["profiles"].append(profile_data)
                            imported_count += 1
                            # 新規の場合は登録日・更新日を今日に
                            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            profile_data["registeredDate"] = now
                            profile_data["updatedDate"] = now

                        # 各フィールドを設定
                        for field_name in ["avatarName", "avatarNameUrl", "profileVersion",
                                          "avatarAuthor", "avatarAuthorUrl", "bodyBase", "profileAuthor",
                                          "profileAuthorUrl", "downloadMethod", "downloadLocation",
                                          "imageUrl", "pricing", "price", "notes"]:
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
                        for field_name in ["official", "forwardSupport", "reverseSupport"]:
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

    def fetch_from_url(self):
        """URLから情報を取得してフォームに自動入力"""
        # アバターURLを取得
        url = self.fields["avatarNameUrl"].get_value()

        if not url:
            messagebox.showwarning("警告", "アバターURLを入力してください")
            return

        # Booth判定
        if "booth.pm" not in url:
            messagebox.showerror("エラー", "現在はBoothのURLのみ対応しています")
            return

        try:
            # URL調整を実行
            adjusted_url = self.adjust_booth_url(url)
            
            # 調整後のURLをフィールドに反映
            if adjusted_url != url:
                self.fields["avatarNameUrl"].set_value(adjusted_url)
            
            # スクレイピング実行（調整後のURLで）
            data = self.scrape_booth(adjusted_url)

            if data:
                # フォームに自動入力
                self.fields["avatarName"].delete(0, tk.END)
                self.fields["avatarName"].insert(0, data.get("avatarName", ""))

                self.fields["avatarAuthor"].delete(0, tk.END)
                self.fields["avatarAuthor"].insert(0, data.get("avatarAuthor", ""))

                self.fields["avatarshopname"].delete(0, tk.END)
                self.fields["avatarshopname"].insert(0, data.get("avatarshopname", ""))

                self.fields["avatarAuthorUrl"].set_value(data.get("avatarAuthorUrl", ""))

                # 解決後URLがあればアバターURLも更新
                resolved_url = data.get("resolvedUrl")
                if resolved_url:
                    self.fields["avatarNameUrl"].set_value(resolved_url)

                self.fields["imageUrl"].set_value(data.get("imageUrl", ""))

                # アバター価格を設定（取得できた場合のみ）
                if data.get("avatarPrice"):
                    self.fields["avatarPrice"].delete(0, tk.END)
                    self.fields["avatarPrice"].insert(0, data.get("avatarPrice", ""))

                # 公式トグルがONの場合、プロファイル作者情報を自動設定
                if self.fields["official"].get():
                    self.fields["profileAuthor"].delete(0, tk.END)
                    self.fields["profileAuthor"].insert(0, data.get("avatarAuthor", ""))

                    self.fields["profileshopname"].delete(0, tk.END)
                    self.fields["profileshopname"].insert(0, data.get("avatarshopname", ""))

                    self.fields["profileAuthorUrl"].set_value(data.get("avatarAuthorUrl", ""))

                # 画像プレビューを更新
                self.preview_image()

                # 入力状況を更新
                self.update_validation_status()
            else:
                messagebox.showerror("エラー", "情報の取得に失敗しました")

        except Exception as e:
            messagebox.showerror("エラー", f"取得中にエラーが発生しました:\n{str(e)}")

    def fetch_from_download_url(self):
        """配布場所URLから情報を取得してプロファイル作者情報を自動入力"""
        # 配布場所URLを取得
        url = self.fields["downloadLocation"].get_value()

        if not url:
            messagebox.showwarning("警告", "配布場所URLを入力してください")
            return

        # Booth判定
        if "booth.pm" not in url:
            messagebox.showerror("エラー", "現在はBoothのURLのみ対応しています")
            return

        try:
            # URL調整を実行
            adjusted_url = self.adjust_booth_url(url)
            
            # 調整後のURLをフィールドに反映
            if adjusted_url != url:
                self.fields["downloadLocation"].set_value(adjusted_url)
            
            # スクレイピング実行（調整後のURLで）
            data = self.scrape_booth(adjusted_url)

            if data:
                # プロファイル作者情報を自動入力
                self.fields["profileAuthor"].delete(0, tk.END)
                self.fields["profileAuthor"].insert(0, data.get("avatarAuthor", ""))

                self.fields["profileshopname"].delete(0, tk.END)
                self.fields["profileshopname"].insert(0, data.get("avatarshopname", ""))

                self.fields["profileAuthorUrl"].set_value(data.get("avatarAuthorUrl", ""))

                # 入力状況を更新
                self.update_validation_status()
            else:
                messagebox.showerror("エラー", "情報の取得に失敗しました")

        except Exception as e:
            messagebox.showerror("エラー", f"取得中にエラーが発生しました:\n{str(e)}")

    def adjust_booth_url(self, url):
        """
        BoothのURLを正規化（ショップ名付き形式に変換）
        
        Args:
            url: 変換対象のURL
            
        Returns:
            str: 変換後のURL
        """
        # 既にショップ名が含まれているかチェック
        if re.match(r'https://[^/]+\.booth\.pm/items/\d+', url):
            return url
        
        # https://booth.pm/ja/items/123 形式の場合のみ処理
        match = re.match(r'https://booth\.pm/ja/items/(\d+)', url)
        if not match:
            return url
        
        item_id = match.group(1)
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # ショップリンクを取得
            shop_link = soup.find('a', href=re.compile(r'https://[^/]+\.booth\.pm/?$'))
            
            if shop_link and shop_link.get('href'):
                shop_url = shop_link.get('href').rstrip('/')
                shop_match = re.match(r'https://([^/]+)\.booth\.pm', shop_url)
                if shop_match:
                    shop_name = shop_match.group(1)
                    return f"https://{shop_name}.booth.pm/items/{item_id}"
            
            return url
        except Exception:
            return url

    def scrape_booth(self, url):
        """BoothページからHTMLをパース"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            resolved_url = url
            response = requests.get(resolved_url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # booth.pm (サブドメインなし) の場合、ショップリンクから実URLを再構築して再取得
            from urllib.parse import urlparse
            parsed = urlparse(resolved_url)
            if parsed.netloc == "booth.pm":
                print(f"[scrape_booth] サブドメインなしURLを検出: {resolved_url}")
                path_parts = [p for p in parsed.path.split("/") if p]
                item_id = path_parts[-1] if path_parts else ""
                shop_base = ""

                # 優先: data-product-list を持つショップリンク
                shop_anchor = soup.find("a", attrs={"data-product-list": True}, href=True)
                # フォールバック: .booth.pm を含む href
                if not shop_anchor:
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if ".booth.pm" in href and "/items/" not in href:
                            shop_anchor = a
                            break
                # さらにフォールバック: 正規表現で .booth.pm ドメインを探索
                if not shop_anchor:
                    import re
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if re.search(r"https?://[a-zA-Z0-9-]+\\.booth\\.pm/?", href):
                            shop_anchor = a
                            break

                if shop_anchor:
                    shop_href = shop_anchor.get("href", "")
                    shop_parsed = urlparse(shop_href)
                    if shop_parsed.netloc and shop_parsed.netloc != "booth.pm":
                        shop_base = f"{shop_parsed.scheme}://{shop_parsed.netloc}"

                if shop_base and item_id:
                    candidate_url = f"{shop_base}/items/{item_id}"
                    try:
                        candidate_resp = requests.get(candidate_url, headers=headers)
                        candidate_resp.raise_for_status()
                        # 取得成功時に置き換え
                        resolved_url = candidate_url
                        response = candidate_resp
                        soup = BeautifulSoup(response.content, 'html.parser')
                        print(f"[scrape_booth] サブドメイン付きURLに置換: {resolved_url}")
                    except Exception as e:
                        print(f"[scrape_booth] 置換候補への再取得に失敗: {candidate_url} ({e})")
                else:
                    print("[scrape_booth] ショップリンクを検出できず、置換をスキップ")

            # アバター名を取得（titleタグから）
            title_tag = soup.find('title')
            avatar_name = ""
            if title_tag:
                title_text = title_tag.string
                # " - BOOTH" を削除
                avatar_name = title_text.replace(" - BOOTH", "").strip()
                # ショップ名も削除（最後の " - " 以降を削除）
                parts = avatar_name.rsplit(" - ", 1)
                if len(parts) > 1:
                    avatar_name = parts[0].strip()

                # 不要な文字列を削除
                import re
                avatar_name = avatar_name.replace("オリジナル3Dモデル", "").strip()
                avatar_name = avatar_name.replace("3Dモデル", "").strip()
                avatar_name = avatar_name.replace("オリジナル", "").strip()
                avatar_name = avatar_name.replace("3D", "").strip()
                avatar_name = avatar_name.replace("3Ｄ", "").strip()
                avatar_name = avatar_name.replace("３Ｄ", "").strip()
                avatar_name = avatar_name.replace("３D", "").strip()
                avatar_name = avatar_name.replace("モデル", "").strip()
                avatar_name = avatar_name.replace("VRChat", "").strip()
                avatar_name = avatar_name.replace("VRchat", "").strip()
                avatar_name = avatar_name.replace("アバター", "").strip()
                avatar_name = avatar_name.replace("想定", "").strip()
                avatar_name = avatar_name.replace("向け", "").strip()
                avatar_name = avatar_name.replace("無料", "").strip()

                # ver~~ を削除（大文字小文字区別なし）
                avatar_name = re.sub(r'\s*ver\s*[^\s\(\)\[\]【】]*', '', avatar_name, flags=re.IGNORECASE).strip()

                # #以降の1単語を削除（例: #Marycia3D）
                avatar_name = re.sub(r'\s*#\S+', '', avatar_name).strip()

                # カッコと引用符を削除（全角・半角）
                avatar_name = re.sub(r'[\(\)\[\]【】「」『』""\'\'"]', '', avatar_name).strip()

                # 複数の空白を1つに
                avatar_name = re.sub(r'\s+', ' ', avatar_name).strip()

            # OGタグから画像URLを取得
            og_image = soup.find('meta', property='og:image')
            image_url = og_image['content'] if og_image else ""

            # 入力URLからショップのベースURLを抽出
            # 例: https://alua7.booth.pm/items/3978893 -> https://alua7.booth.pm/
            parsed = urlparse(resolved_url)
            avatar_author_url = f"{parsed.scheme}://{parsed.netloc}/"

            # home-link-container__nicknameから作者名を取得
            nickname_div = soup.find('div', class_='home-link-container__nickname')
            avatar_author = ""

            if nickname_div:
                link = nickname_div.find('a', class_='nav')
                if link:
                    avatar_author = link.get_text(strip=True)

            shopname_from_label = ""
            # 取得できなかった場合はshop-name-labelから取得（後方互換性）
            if not avatar_author:
                shop_name_span = soup.find('span', class_='shop-name-label')
                if shop_name_span:
                    shopname_from_label = shop_name_span.get_text(strip=True)
                    avatar_author = shopname_from_label
            else:
                # 作者名は取れていてもショップ名として利用できそうなら保持
                shop_name_span = soup.find('span', class_='shop-name-label')
                if shop_name_span:
                    shopname_from_label = shop_name_span.get_text(strip=True)

            # ショップ名は shop-name-label を優先し、なければ作者名で代替
            avatarshopname = shopname_from_label or avatar_author

            # アバター価格を取得
            # ダウンロード商品が1つだけの場合、その価格を取得
            avatar_price = ""
            try:
                # variation-itemのうち、ダウンロード商品のみを抽出
                variation_items = soup.find_all('li', class_='variation-item')
                download_variations = []

                for item in variation_items:
                    # ダウンロードアイコンがあるかチェック
                    icon = item.find('i', class_='icon-download')
                    if icon:
                        # 価格を取得
                        price_div = item.find('div', class_='variation-price')
                        if price_div:
                            price_text = price_div.get_text(strip=True)
                            # "¥ 3,000" から数値のみ抽出
                            import re
                            price_match = re.search(r'[\d,]+', price_text)
                            if price_match:
                                price_num = price_match.group().replace(',', '')
                                # 0円でない場合のみリストに追加
                                if int(price_num) > 0:
                                    download_variations.append(price_num)

                # ダウンロード商品が1つだけの場合、その価格を設定
                if len(download_variations) == 1:
                    avatar_price = download_variations[0]

            except Exception:
                # 価格取得に失敗しても処理は続行
                pass

            return {
                "avatarName": avatar_name,
                "avatarAuthor": avatar_author,
                "avatarshopname": avatarshopname,
                "avatarAuthorUrl": avatar_author_url,
                "imageUrl": image_url,
                "avatarPrice": avatar_price,
                "resolvedUrl": resolved_url
            }

        except requests.RequestException as e:
            raise Exception(f"ページの取得に失敗しました: {str(e)}")
        except Exception as e:
            raise Exception(f"解析エラー: {str(e)}")

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
                "imageUrl", "pricing", "price",
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

    def check_id_duplicate(self, event=None):
        """IDフィールドのフォーカスが外れた時に重複チェック"""
        if not self.current_selection:
            return

        new_id = self.fields["id"].get().strip()
        old_id = self.current_selection.get("id", "")

        # IDが変更されていない場合は何もしない
        if new_id == old_id or not new_id:
            return

        # 重複チェック
        duplicate_found = False
        for profile in self.data["profiles"]:
            if profile != self.current_selection and profile.get("id") == new_id:
                duplicate_found = True
                break

        if duplicate_found:
            # 重複が見つかった - 自動調整を提案
            result = messagebox.askyesnocancel(
                "ID重複",
                f"ID {new_id} は既に使用されています。\n\n"
                f"はい: {new_id} 以降のIDを自動的にずらす\n"
                f"いいえ: 元のID ({old_id}) に戻す\n"
                f"キャンセル: そのまま編集を続ける"
            )

            if result is None:  # キャンセル
                pass  # そのまま編集を続ける
            elif result:  # はい - 自動調整
                self.adjust_ids_from(new_id)
                self.current_selection["id"] = new_id
                self.refresh_tree()
                messagebox.showinfo("完了", f"ID {new_id} 以降のIDをずらしました")
            else:  # いいえ - 元に戻す
                self.fields["id"].delete(0, tk.END)
                self.fields["id"].insert(0, old_id)

    def adjust_ids_from(self, start_id):
        """指定されたID以降のIDを全て+1する

        Args:
            start_id: 調整開始ID（例: "002"）
        """
        try:
            start_num = int(start_id)
        except ValueError:
            return

        # start_id以降のプロファイルを取得
        profiles_to_adjust = []
        for profile in self.data["profiles"]:
            try:
                profile_num = int(profile.get("id", "0"))
                if profile_num >= start_num:
                    profiles_to_adjust.append(profile)
            except ValueError:
                continue

        # IDの大きい順にソート（後ろから処理して重複を避ける）
        profiles_to_adjust.sort(key=lambda p: int(p.get("id", "0")), reverse=True)

        # IDを+1
        for profile in profiles_to_adjust:
            old_id = profile.get("id", "")
            try:
                new_id = str(int(old_id) + 1).zfill(3)
                profile["id"] = new_id
            except ValueError:
                continue

    def reassign_ids(self):
        """現在のツリービュー順序に基づいてIDを001から順に振り直す"""
        result = messagebox.askyesno(
            "確認",
            "現在の表示順序でIDを001から順に振り直します。\n"
            "この操作は元に戻せません。\n"
            "実行しますか？"
        )

        if not result:
            return

        tree_items = self.tree.get_children()

        if not tree_items:
            messagebox.showwarning("警告", "振り直すレコードがありません")
            return

        id_changes = []

        # 新しいIDを001から順に割り当て
        for index, tree_item in enumerate(tree_items, start=1):
            new_id = str(index).zfill(3)

            item_values = self.tree.item(tree_item)["values"]
            old_id = str(item_values[0]).zfill(3) if isinstance(item_values[0], int) else item_values[0]

            # データ内のIDを更新
            for profile in self.data["profiles"]:
                if profile.get("id") == old_id:
                    profile["id"] = new_id
                    id_changes.append(f"{old_id} -> {new_id}")
                    break

            # ツリービューを更新
            self.tree.item(tree_item, values=(
                new_id,
                item_values[1],
                item_values[2],
                item_values[3]
            ))

        # データの順序を更新
        tree_items = self.tree.get_children()
        new_profiles_order = []

        for tree_item in tree_items:
            item_values = self.tree.item(tree_item)["values"]
            profile_id = str(item_values[0]).zfill(3) if isinstance(item_values[0], int) else item_values[0]

            for profile in self.data["profiles"]:
                if profile.get("id") == profile_id:
                    new_profiles_order.append(profile)
                    break

        self.data["profiles"] = new_profiles_order

        # 選択中プロファイルのIDフィールドを更新
        if self.current_selection:
            self.fields["id"].delete(0, tk.END)
            self.fields["id"].insert(0, self.current_selection.get("id", ""))

        messagebox.showinfo(
            "完了",
            f"IDの振り直しが完了しました。\n"
            f"{len(id_changes)}件のレコードを更新しました。\n\n"
            f"変更を保存するには「保存」ボタンをクリックしてください。"
        )

    def clear_form(self):
        """フォームをクリア"""
        for field_name, widget in self.fields.items():
            if field_name in ["official", "forwardSupport", "reverseSupport"]:
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
        """GitHub API経由でdata以下のすべてのファイルを更新（Git CLI不要）"""
        # 設定を読み込み
        config = self.load_config()
        if not config:
            return False

        # 処理中ウィンドウを作成
        progress_window = tk.Toplevel(self.root)
        progress_window.title("処理中")
        progress_window.geometry("300x150")
        progress_window.transient(self.root)
        progress_window.grab_set()

        label = tk.Label(progress_window, text="GitHubにプッシュ中...", font=("", 12))
        label.pack(expand=True, pady=10)

        status_label = tk.Label(progress_window, text="", font=("", 9))
        status_label.pack(expand=True)

        progress_window.update()

        try:
            github_token = config["github_token"]

            # リポジトリ情報を取得（URLから抽出）
            repo_url = config.get("github_repo_url", "https://github.com/eringiriri/mochifitter_list.git")
            # "https://github.com/owner/repo.git" から "owner/repo" を抽出
            repo_path = repo_url.replace("https://github.com/", "").replace(".git", "")

            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }

            # dataディレクトリ内のすべてのファイルを取得
            data_dir = os.path.join(self.app_dir, "data")
            data_files = []
            for root, dirs, files in os.walk(data_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # dataディレクトリからの相対パスを取得
                    rel_path = os.path.relpath(file_path, self.app_dir)
                    data_files.append((rel_path, file_path))

            if not data_files:
                progress_window.destroy()
                messagebox.showwarning("警告", "dataディレクトリにファイルが見つかりません")
                return False

            # 各ファイルを更新
            updated_count = 0
            failed_files = []

            for rel_path, file_path in data_files:
                try:
                    status_label.config(text=f"処理中: {os.path.basename(file_path)}")
                    progress_window.update()

                    # ファイルの内容を読み込み
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # GitHub APIのエンドポイント
                    api_url = f"https://api.github.com/repos/{repo_path}/contents/{rel_path.replace(os.sep, '/')}"

                    # 現在のファイル情報を取得（SHAが必要）
                    response = requests.get(api_url, headers=headers)
                    if response.status_code == 200:
                        current_file = response.json()
                        sha = current_file["sha"]
                    elif response.status_code == 404:
                        # ファイルが存在しない場合は新規作成
                        sha = None
                    else:
                        failed_files.append(f"{rel_path}: {response.status_code}")
                        continue

                    # ファイルを更新
                    content_base64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')

                    data = {
                        "message": f"Update {os.path.basename(rel_path)} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        "content": content_base64
                    }

                    if sha:
                        data["sha"] = sha

                    response = requests.put(api_url, headers=headers, json=data)

                    if response.status_code in [200, 201]:
                        updated_count += 1
                    else:
                        failed_files.append(f"{rel_path}: {response.status_code} - {response.text[:100]}")

                except Exception as e:
                    failed_files.append(f"{rel_path}: {str(e)[:100]}")

            progress_window.destroy()

            # 結果を表示
            if updated_count == len(data_files):
                messagebox.showinfo("完了", 
                    f"GitHubへのプッシュが完了しました。\n{updated_count}個のファイルを更新しました。\nWebサイトは数分後に更新されます。")
                return True
            elif updated_count > 0:
                error_msg = f"{updated_count}個のファイルを更新しましたが、{len(failed_files)}個のファイルでエラーが発生しました:\n\n"
                error_msg += "\n".join(failed_files[:5])
                if len(failed_files) > 5:
                    error_msg += f"\n... 他 {len(failed_files) - 5}件"
                messagebox.showwarning("一部エラー", error_msg)
                return True
            else:
                error_msg = "すべてのファイルの更新に失敗しました:\n\n"
                error_msg += "\n".join(failed_files[:5])
                if len(failed_files) > 5:
                    error_msg += f"\n... 他 {len(failed_files) - 5}件"
                messagebox.showerror("エラー", error_msg)
                return False

        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("エラー", f"プッシュ処理でエラーが発生しました:\n{str(e)}")
            return False

    def pull_from_github(self):
        """GitHub APIからdata以下のファイルを取得（Git CLI不要）"""
        # 確認ダイアログ
        result = messagebox.askyesno("確認",
            "GitHubから最新データを取得します。\n"
            "ローカルの未保存の変更は上書きされます。\n\n"
            "続行しますか？")
        if not result:
            return

        # 設定を読み込み
        config = self.load_config()
        if not config:
            return

        # 処理中ウィンドウを作成
        progress_window = tk.Toplevel(self.root)
        progress_window.title("処理中")
        progress_window.geometry("300x150")
        progress_window.transient(self.root)
        progress_window.grab_set()

        label = tk.Label(progress_window, text="GitHubからPull中...", font=("", 12))
        label.pack(expand=True, pady=10)

        status_label = tk.Label(progress_window, text="", font=("", 9))
        status_label.pack(expand=True)

        progress_window.update()

        try:
            github_token = config["github_token"]

            # リポジトリ情報を取得
            repo_url = config.get("github_repo_url", "https://github.com/eringiriri/mochifitter_list.git")
            repo_path = repo_url.replace("https://github.com/", "").replace(".git", "")

            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }

            # 取得対象ファイル
            target_files = [
                "data/profiles.json",
                "data/Block_URLs.txt",
                "data/Avatar_URLs.txt"
            ]

            updated_count = 0
            failed_files = []

            for rel_path in target_files:
                try:
                    status_label.config(text=f"取得中: {os.path.basename(rel_path)}")
                    progress_window.update()

                    # GitHub APIでファイル内容を取得
                    api_url = f"https://api.github.com/repos/{repo_path}/contents/{rel_path}"
                    response = requests.get(api_url, headers=headers)

                    if response.status_code == 200:
                        file_data = response.json()
                        # base64デコード
                        content = base64.b64decode(file_data["content"]).decode('utf-8')

                        # ローカルファイルに保存
                        local_path = os.path.join(self.app_dir, rel_path.replace("/", os.sep))

                        # ディレクトリが存在しない場合は作成
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)

                        with open(local_path, 'w', encoding='utf-8') as f:
                            f.write(content)

                        updated_count += 1
                    elif response.status_code == 404:
                        # ファイルが存在しない場合はスキップ
                        pass
                    else:
                        failed_files.append(f"{rel_path}: {response.status_code}")

                except Exception as e:
                    failed_files.append(f"{rel_path}: {str(e)[:50]}")

            progress_window.destroy()

            # 結果を表示
            if updated_count > 0:
                # データを再読み込み
                self.load_data()
                messagebox.showinfo("完了",
                    f"GitHubから{updated_count}個のファイルを取得しました。")
            else:
                messagebox.showwarning("警告", "取得できたファイルがありませんでした。")

            if failed_files:
                error_msg = "一部のファイルの取得に失敗しました:\n\n"
                error_msg += "\n".join(failed_files)
                messagebox.showwarning("警告", error_msg)

        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("エラー", f"Pull処理でエラーが発生しました:\n{str(e)}")

    def save_data(self):
        """データをJSONファイルに保存"""
        try:
            # 最終更新日時を更新
            jst_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S JST")
            self.data["lastUpdated"] = jst_time

            # プロファイルをID順にソート
            self.data["profiles"] = sorted(self.data["profiles"], key=lambda p: self._id_sort_key(p.get("id", "")))

            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)

            # 保存後に確認ダイアログを表示
            result = messagebox.askyesno("確認",
                                        "GitHubにプッシュしてWebサイトを更新しますか？")

            if result:
                self.auto_git_push_api()

        except Exception as e:
            messagebox.showerror("エラー", f"保存に失敗しました: {e}")

    def setup_url_investigation_panel(self, panel):
        """URL調査パネルのUIをセットアップ"""
        # 現在調査中のURL表示エリア
        current_frame = ttk.Frame(panel)
        current_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(current_frame, text="現在調査中:").pack(anchor=tk.W)
        self.current_url_entry = ttk.Entry(current_frame, state="readonly")
        self.current_url_entry.pack(fill=tk.X, pady=(5, 0))

        # ボタンフレーム
        button_frame = ttk.Frame(panel)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        # 1行目: 次へ、ブロック、アバター保存
        button_row1 = ttk.Frame(button_frame)
        button_row1.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(button_row1, text="次へ", command=self.investigation_next_url).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_row1, text="ブロック", command=self.investigation_block_url).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_row1, text="アバター保存", command=self.investigation_save_avatar_url).pack(side=tk.LEFT, padx=5)

        # 2行目: 登録、プロ登録、アバター読取
        button_row2 = ttk.Frame(button_frame)
        button_row2.pack(fill=tk.X)
        ttk.Button(button_row2, text="登録", command=self.investigation_register_url).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_row2, text="プロ登録", command=self.investigation_register_profile_url).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_row2, text="アバター読取", command=self.investigation_load_avatar_urls).pack(side=tk.LEFT, padx=5)

        # URL一覧入力エリア
        ttk.Label(panel, text="URL一覧:").pack(anchor=tk.W, pady=(0, 5))

        from tkinter import scrolledtext
        self.url_list_text = scrolledtext.ScrolledText(panel, width=40, height=15, wrap=tk.WORD)
        self.url_list_text.pack(fill=tk.BOTH, expand=True)

    def investigation_next_url(self):
        """次のURLへ移動（URL調査パネル）"""
        text_content = self.url_list_text.get("1.0", tk.END).strip()

        # URL一覧が空の場合
        if not text_content:
            # 現在調査中のURLがあればクリア
            if self.current_investigation_url:
                self.current_investigation_url = ""
                self.current_url_entry.config(state="normal")
                self.current_url_entry.delete(0, tk.END)
                self.current_url_entry.config(state="readonly")
            return

        # 改行で分割してURL一覧を作成
        urls = [line.strip() for line in text_content.split('\n') if line.strip()]

        if not urls:
            # 現在調査中のURLがあればクリア
            if self.current_investigation_url:
                self.current_investigation_url = ""
                self.current_url_entry.config(state="normal")
                self.current_url_entry.delete(0, tk.END)
                self.current_url_entry.config(state="readonly")
            return

        # 最初のエントリを取得
        first = urls[0]

        # 3桁数字ならIDとしてプロファイルを開く
        if first.isdigit() and len(first) == 3:
            target_id = first
            if self.load_profile_by_id(target_id):
                self.current_investigation_id = target_id
                self.current_investigation_url = ""
                self.current_url_entry.config(state="normal")
                self.current_url_entry.delete(0, tk.END)
                self.current_url_entry.insert(0, target_id)
                self.current_url_entry.config(state="readonly")
            else:
                messagebox.showwarning("警告", f"ID {target_id} は見つかりません")
                return
        else:
            # URLとして扱う
            self.current_investigation_url = first

            # 現在のURLを表示
            self.current_url_entry.config(state="normal")
            self.current_url_entry.delete(0, tk.END)
            self.current_url_entry.insert(0, self.current_investigation_url)
            self.current_url_entry.config(state="readonly")

            # デフォルトブラウザで開く
            import webbrowser
            webbrowser.open(self.current_investigation_url)

        # URL一覧から削除
        remaining_urls = urls[1:]
        self.url_list_text.delete("1.0", tk.END)
        if remaining_urls:
            self.url_list_text.insert("1.0", '\n'.join(remaining_urls))
        # remaining_urlsが空でも現在調査中のURLは保持される

    def investigation_register_url(self):
        """現在のURLで新規レコードを作成（URL調査パネル）"""
        if not self.current_investigation_url:
            return

        # 新規レコードを作成
        self.add_profile()

        # avatarNameUrl に URL を挿入
        self.fields["avatarNameUrl"].set_value(self.current_investigation_url)

        # 取得ボタンを自動実行
        self.fetch_from_url()

    def investigation_register_profile_url(self):
        """現在のURLを配布場所URLとして新規レコードを作成（URL調査パネル）"""
        if not self.current_investigation_url:
            return

        self.add_profile()
        self.fields["downloadLocation"].set_value(self.current_investigation_url)
        self.fetch_from_download_url()

    def investigation_block_url(self):
        """現在のURLをブロックリストに追加して次へ（URL調査パネル）"""
        if not self.current_investigation_url:
            return

        # Avatar_URLs.txt にURLがあれば削除
        avatar_urls_path = os.path.join(self.app_dir, "data", "Avatar_URLs.txt")
        if os.path.exists(avatar_urls_path):
            with open(avatar_urls_path, 'r', encoding='utf-8') as f:
                avatar_urls = f.readlines()

            # 現在のURLを除外
            avatar_urls = [url for url in avatar_urls if url.strip() != self.current_investigation_url]

            # Avatar_URLs.txt を更新
            with open(avatar_urls_path, 'w', encoding='utf-8') as f:
                f.writelines(avatar_urls)

        # Block_URLs.txt に追加
        with open(self.block_urls_path, 'a', encoding='utf-8') as f:
            f.write(self.current_investigation_url + '\n')

        # 次のURLへ
        self.investigation_next_url()

    def investigation_save_avatar_url(self):
        """現在のURLをAvatar_URLs.txtに保存して次へ（URL調査パネル）"""
        if not self.current_investigation_url:
            return

        # Block_URLs.txt にURLがあれば削除
        if os.path.exists(self.block_urls_path):
            with open(self.block_urls_path, 'r', encoding='utf-8') as f:
                block_urls = f.readlines()

            # 現在のURLを除外
            block_urls = [url for url in block_urls if url.strip() != self.current_investigation_url]

            # Block_URLs.txt を更新
            with open(self.block_urls_path, 'w', encoding='utf-8') as f:
                f.writelines(block_urls)

        # Avatar_URLs.txt のパスを定義
        avatar_urls_path = os.path.join(self.app_dir, "data", "Avatar_URLs.txt")

        # Avatar_URLs.txt に追加
        with open(avatar_urls_path, 'a', encoding='utf-8') as f:
            f.write(self.current_investigation_url + '\n')

        # 次のURLへ
        self.investigation_next_url()

    def investigation_load_avatar_urls(self):
        """Avatar_URLs.txtの内容をURL一覧に読み込む（URL調査パネル）"""
        avatar_urls_path = os.path.join(self.app_dir, "data", "Avatar_URLs.txt")

        # ファイルが存在しない場合は何もしない
        if not os.path.exists(avatar_urls_path):
            messagebox.showwarning("警告", "Avatar_URLs.txt が見つかりません")
            return

        # ファイルを読み込み
        with open(avatar_urls_path, 'r', encoding='utf-8') as f:
            avatar_urls = f.read().strip()

        if not avatar_urls:
            messagebox.showinfo("情報", "Avatar_URLs.txt は空です")
            return

        # 現在のURL一覧を取得
        current_content = self.url_list_text.get("1.0", tk.END).strip()

        # 追加または上書き
        if current_content:
            # 既存データがある場合は最下部に追加
            self.url_list_text.insert(tk.END, '\n' + avatar_urls)
        else:
            # 空の場合は上書き
            self.url_list_text.delete("1.0", tk.END)
            self.url_list_text.insert("1.0", avatar_urls)


def main():
    root = tk.Tk()
    app = ProfileEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
