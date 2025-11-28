# もちふぃったープロファイル一覧

VRChat用アバターの「もちふぃったー」対応プロファイル情報をまとめた静的Webサイトと管理ツール群。

## 内容

### Webページ

- **index.html** - メインの一覧ページ（検索・フィルター機能付き）
- **lite.html** - 軽量版一覧ページ

### 管理ツール

- **profile_editor.py** - プロファイル編集GUI（フル機能版、BeautifulSoup4依存）
- **profile_editor_lower.py** - プロファイル編集GUI（軽量版、依存少）
- **booth_url_extractor.py** - Booth URLを抽出
- **diff_checker.py** - プロファイルの差分チェック
- **url_investigation.py** - URL調査ツール

### データ

- **data/profiles.json** - プロファイル情報（アバター名、作者、配布場所など）

## 登録作業フロー

```mermaid
flowchart TD
    Start([事前準備]) --> Setup[profile_editor.py起動<br/>レコード追加をクリック]
    Setup --> Search[BOOTHでキーワード検索<br/>もちふぃった～ mochifitter等]
    Search --> Extract[booth_url_extractor.py実行<br/>→ booth_urls.txt]
    Extract --> Diff[diff_checker.py実行<br/>→ unregistered_avatars.txt]
    Diff --> Investigate[url_investigation.pyで次へ<br/>URLを開く]

    Investigate --> CheckURL{URL判定}
    CheckURL -->|非登録対象| Block[ブロック登録<br/>Block_URLs.txt]
    CheckURL -->|アバターURL| Input[プロファイル入力]

    Block --> Investigate

    Input --> Paste1[アバターURLペースト]
    Paste1 --> CheckPage[ページ確認<br/>□公式/非公式<br/>□順方向/逆方向]

    CheckPage --> Official{公式?}

    Official -->|Yes| GetOfficial[公式チェックON<br/>取得ボタン押下]
    GetOfficial --> AutoOfficial[自動入力:<br/>アバター名/作者/作者URL<br/>プロファイル作者/作者URL<br/>画像URL]
    AutoOfficial --> VerifyOfficial[入力内容を目視確認]
    VerifyOfficial --> Price

    Official -->|No| GetUnofficial[取得ボタン押下]
    GetUnofficial --> AutoUnofficial[自動入力:<br/>アバター名/作者/作者URL<br/>画像URL]
    AutoUnofficial --> DistCheck{配布場所}

    DistCheck -->|Booth| PasteBooth[配布場所URLペースト<br/>取得ボタン押下]
    PasteBooth --> AutoBooth[自動入力:<br/>プロファイル作者<br/>プロファイル作者URL]
    AutoBooth --> Price

    DistCheck -->|Booth以外| PasteOther[配布場所URLペースト<br/>手動入力:<br/>プロファイル作者<br/>プロファイル作者URL]
    PasteOther --> Price

    Price[価格情報入力]
    Price --> PriceType{価格区分}
    PriceType -->|無料| Free[価格 → 0]
    PriceType -->|単体有料| Paid[価格手動入力]
    PriceType -->|アバター同梱| Bundle[価格 → -<br/>配布場所=アバターURL]

    Free --> AvatarPrice
    Paid --> AvatarPrice
    Bundle --> AvatarPrice

    AvatarPrice[アバター価格入力]
    AvatarPrice --> Sale{セール?}
    Sale -->|Yes| SaleInfo[セール中チェックON<br/>開始日/終了日/セール価格]
    Sale -->|No| Notes
    SaleInfo --> Notes

    Notes[備考入力<br/>任意]
    Notes --> Validate[入力状況パネルで<br/>必須項目チェック]
    Validate --> Apply[変更を適用]
    Apply --> Save[保存]
    Save --> Push[GitHubプッシュ]

    Push --> Next{次のURL}
    Next -->|あり| Investigate
    Next -->|なし| End([完了])
```

## ライセンス

MIT License
