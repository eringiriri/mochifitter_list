# もちふぃったープロファイル一覧

VRChat用3Dアバター向けの衣装自動調整ツール「もちふぃったー」のプロファイル情報をまとめた静的Webサイトです。

## 概要

もちふぃったーは、VRChat用の3Dアバター向けの衣装を自動で合わせるためのツールです。
このサイトでは、対応アバターのプロファイル情報を一覧で確認できます。

### もちふぃったーとは？

- **順方向**: Templateから別のアバターへ自動で合わせる
- **逆方向**: アバター用衣装をTemplateに自動で合わせる

アバター向けの衣装を、もちふぃったーTemplateに合わせることで、他のアバターにも着せることができます。

## 機能

- ✅ プロファイル一覧表示
- ✅ アバター名・作者名での検索機能
- ✅ 公式/非公式フィルター
- ✅ 順方向/逆方向対応フィルター
- ✅ レスポンシブデザイン（PC/タブレット/スマホ対応）
- ✅ 登録要望フォームリンク

## プロジェクト構成

```
mochifitter_list/
├── index.html              # メインページ
├── data/
│   └── profiles.json       # プロファイルデータ
├── css/
│   └── style.css          # スタイルシート
├── js/
│   └── main.js            # JavaScriptロジック
└── README.md              # このファイル
```

## セットアップ

### ローカルでの表示

1. リポジトリをクローン
```bash
git clone <repository-url>
cd mochifitter_list
```

2. ローカルサーバーを起動（推奨）

Python 3を使う場合:
```bash
python -m http.server 8000
```

Node.jsのhttp-serverを使う場合:
```bash
npx http-server -p 8000
```

3. ブラウザで http://localhost:8000 を開く

### GitHub Pagesでのホスティング

1. GitHubリポジトリの Settings > Pages に移動
2. Source で「Deploy from a branch」を選択
3. Branch で `main` (または `master`) ブランチを選択
4. 保存して数分待つと公開されます

## データの追加・編集方法

### 最終更新日時の更新

`data/profiles.json` を編集する際、`lastUpdated`フィールドも現在時刻（JST）に更新してください：

```json
{
  "lastUpdated": "2025-11-25 17:00:00 JST",
  "profiles": [...]
}
```

### プロファイルデータの追加

`data/profiles.json` ファイルを編集して、新しいプロファイルを追加できます。

```json
{
  "profiles": [
    {
      "id": "001",
      "registeredDate": "2025-11-25",
      "updatedDate": "2025-11-20",
      "avatarName": "アバター名",
      "profileVersion": "1.0.0",
      "avatarAuthor": "アバター作者",
      "profileAuthor": "プロファイル作者",
      "official": true,
      "downloadMethod": "Booth",
      "downloadLocation": "https://example.com",
      "forwardSupport": true,
      "reverseSupport": true
    }
  ]
}
```

### データ項目の説明

| 項目 | 説明 | 例 |
|------|------|-----|
| `id` | 一意のID | "001" |
| `registeredDate` | DB登録日 | "2025-11-25" |
| `updatedDate` | プロファイル更新日 | "2025-11-20" |
| `avatarName` | アバター名 | "桔梗" |
| `profileVersion` | プロファイルバージョン | "1.0.0" |
| `avatarAuthor` | アバター作者 | "ポンデロニウム研究所" |
| `profileAuthor` | プロファイル作者 | "サンプル作者" |
| `official` | 公式/非公式 | true / false |
| `downloadMethod` | DL方法 | "Booth", "GitHub" など |
| `downloadLocation` | DL場所URL | "https://..." |
| `forwardSupport` | 順方向対応 | true / false |
| `reverseSupport` | 逆方向対応 | true / false |

## Googleフォームの設定

登録要望フォームのURLを設定するには、`js/main.js` の以下の部分を編集してください：

```javascript
// Googleフォームリンクの設定
const GOOGLE_FORM_URL = 'https://docs.google.com/forms/d/e/YOUR_FORM_ID/viewform';
```

実際のGoogleフォームURLに置き換えてください。

## カスタマイズ

### デザインの変更

`css/style.css` のCSS変数を変更することで、簡単にカラーテーマを変更できます：

```css
:root {
    --primary-color: #6366f1;
    --secondary-color: #10b981;
    --bg-color: #f8fafc;
    /* ... */
}
```

### 機能の追加

`js/main.js` を編集して、新しい機能を追加できます。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

プロファイルの追加や修正は、以下の方法で行えます：

1. Googleフォームから登録要望を送信
2. GitHubでIssueを作成
3. Pull Requestを送信

## 注意事項

- 静的サイトのため、データベース機能はありません
- データは `data/profiles.json` で管理されます
- プロファイルの追加・更新には手動でのJSON編集が必要です

## サポート

問題が発生した場合は、GitHubのIssueで報告してください。
