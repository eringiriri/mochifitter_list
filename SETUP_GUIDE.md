# 自動チェック機能 セットアップガイド

## 1. Discord Webhook URLの取得と設定

### Webhook URLの取得方法

1. **Discordサーバーを開く**
   - 通知を受け取りたいサーバーを選択

2. **チャンネルの設定を開く**
   - 通知を受け取りたいチャンネルの歯車アイコン（⚙️）をクリック
   - 「チャンネルの編集」が開きます

3. **連携サービス → Webhook**
   - 左メニューから「連携サービス」を選択
   - 「ウェブフック」をクリック
   - 「新しいウェブフック」ボタンをクリック

4. **Webhookの設定**
   - 名前を設定（例: 「もちふぃったーチェッカー」）
   - アイコンを設定（オプション）
   - チャンネルを確認
   - 「ウェブフックURLをコピー」ボタンをクリック

5. **URLの例**
   ```
   https://discord.com/api/webhooks/1234567890123456789/abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ
   ```

### GitHub Secretsへの設定方法

1. **GitHubリポジトリを開く**
   - ブラウザでこのリポジトリのページを開く

2. **Settings タブをクリック**
   - リポジトリのメニューバーにある「Settings」をクリック

3. **Secrets and variables を開く**
   - 左メニューの「Secrets and variables」を展開
   - 「Actions」をクリック

4. **新しいシークレットを追加**
   - 「New repository secret」ボタンをクリック
   - Name: `DISCORD_WEBHOOK_URL`（この名前は必須）
   - Secret: コピーしたWebhook URLを貼り付け
   - 「Add secret」ボタンをクリック

5. **確認**
   - シークレット一覧に `DISCORD_WEBHOOK_URL` が表示されればOK
   - 値は `***` で隠されて表示されます

## 2. Artifactとは？

### 概要
**Artifact（アーティファクト）** は、GitHub Actionsのワークフロー実行時に生成されたファイルを保存する機能です。

### このプロジェクトでの使用
- **保存されるファイル**: `unregistered_avatars.txt`
- **内容**: 未登録のBooth商品URLのリスト
- **保存期間**: 30日間
- **目的**: ワークフロー実行後に結果を確認できるようにする

### Artifactのダウンロード方法

1. **Actions タブを開く**
   - GitHubリポジトリの「Actions」タブをクリック

2. **ワークフローの実行履歴を表示**
   - 「Check New Booth Profiles」をクリック
   - 過去の実行リストが表示されます

3. **特定の実行を選択**
   - 確認したい実行をクリック

4. **Artifactsセクション**
   - ページ下部に「Artifacts」セクションがあります
   - 新規プロファイルが見つかった場合のみ表示されます
   - 例: `unregistered-avatars-123`（数字は実行番号）

5. **ダウンロード**
   - Artifact名をクリックするとZIPファイルがダウンロードされます
   - ZIPを解凍すると `unregistered_avatars.txt` が入っています

### Artifactの見た目

```
Artifacts (保存期間: 30日)
📦 unregistered-avatars-123    [ダウンロード]
```

## 3. Booth検索URLについて

### 設定されているURL

現在、以下の2つのURLが設定されています：

```
https://booth.pm/ja/browse/3Dキャラクター?q=もちふぃった
https://booth.pm/ja/browse/3Dキャラクター?q=mochifitter
```

### URLの解説

1. **1つ目**: `もちふぃった` のキーワード検索（3Dキャラクターカテゴリ）
   - `browse/3Dキャラクター` で3Dキャラクターカテゴリに絞り込み
   - `?q=もちふぃった` でキーワード検索

2. **2つ目**: `mochifitter` のキーワード検索（3Dキャラクターカテゴリ）
   - 英語表記での検索
   - 同じく3Dキャラクターカテゴリ内で検索

3. **カテゴリ検索のメリット**
   - 3Dアバター関連商品に絞り込まれる
   - ノイズ（衣装のみ、テクスチャのみ等）が減少
   - より精度の高い検索が可能

### URLの確認方法

実際にブラウザで開いて確認できます：

1. **確認する**
   - URLをブラウザに貼り付けて開く
   - Boothの検索結果ページが表示される
   - 「もちふぃった」や「mochifitter」関連の商品が表示されることを確認

2. **検索結果が正しいか**
   - プロファイル配布ページが含まれているか
   - 意図しない商品が含まれていないか

### URLの変更方法

検索条件を変更したい場合：

```python
# scripts/check_new_profiles.py の 185-188行目
search_urls = [
    "https://booth.pm/ja/browse/3Dキャラクター?q=もちふぃった",
    "https://booth.pm/ja/browse/3Dキャラクター?q=mochifitter"
]
```

この部分を編集してコミット・プッシュすれば変更できます。

### タグ検索への変更（参考）

より正確に検索したい場合は、タグ検索URLを使用することも可能です：

```python
# タグ検索の例
search_urls = [
    "https://booth.pm/ja/items?tags%5B%5D=%E3%82%82%E3%81%A1%E3%81%B5%E3%81%83%E3%81%A3%E3%81%9F%E3%80%9C",
]
```

## 動作確認

### 手動テスト実行

1. **Actions タブを開く**
2. **「Check New Booth Profiles」を選択**
3. **「Run workflow」ボタンをクリック**
4. **ブランチを選択**（通常は `main`）
5. **「Run workflow」をクリック**
6. **実行状況を確認**
   - 実行中: 黄色の○
   - 成功: 緑色の✓
   - 失敗: 赤色の✗

### Discordで通知を確認

新規プロファイルが見つかると、以下のようなメッセージが送信されます：

```
🔔 新しいプロファイルが 3 件見つかりました

Boothで新しい「もちふぃった～」プロファイルが見つかりました。

- https://example.booth.pm/items/1234567
- https://example.booth.pm/items/2345678
- https://example.booth.pm/items/3456789

MochiFitter Profile Checker
```

## トラブルシューティング

### Discord通知が届かない

1. Webhook URLが正しく設定されているか確認
2. DiscordのWebhookが削除されていないか確認
3. GitHub Actionsのログを確認

### ワークフローが失敗する

1. **Actions タブ**で失敗した実行をクリック
2. **ログを確認**してエラーメッセージを読む
3. よくある原因：
   - Booth.pmのHTML構造変更（スクレイピングエラー）
   - ネットワークエラー
   - レート制限

### 検索結果が期待と違う

1. ブラウザでURLを開いて確認
2. 検索キーワードやタグを調整
3. `scripts/check_new_profiles.py` の `search_urls` を編集
