#!/usr/bin/env python3
"""
新しいプロファイルをBoothから自動的にチェックするスクリプト
GitHub Actionsから実行されることを想定
"""

import sys
import os
import json
import requests
from datetime import datetime

# 既存モジュールをインポート
sys.path.append(os.path.dirname(__file__))
from booth_url_extractor import extract_booth_urls
from diff_checker import (
    extract_item_id_from_url,
    extract_shop_name_from_url,
    load_profiles_urls,
    load_block_urls
)


def collect_urls_from_searches(search_urls):
    """
    複数の検索URLから商品URLを収集
    
    Args:
        search_urls: 検索URLのリスト
        
    Returns:
        set: すべての商品IDのセット
    """
    all_urls = {}  # item_id -> url のマッピング
    
    for search_url in search_urls:
        print(f"\n検索URL: {search_url}")
        print("-" * 80)
        
        urls = extract_booth_urls(search_url)
        
        for url in urls:
            item_id = extract_item_id_from_url(url)
            if item_id:
                all_urls[item_id] = url
        
        print(f"この検索で {len(urls)} 件の商品を発見")
    
    return all_urls


def find_unregistered_items(booth_mapping, profiles_file, block_file, avatar_file):
    """
    未登録のアイテムを検出
    
    Args:
        booth_mapping: item_id -> url のマッピング
        profiles_file: profiles.jsonのパス
        block_file: Block_URLs.txtのパス
        avatar_file: Avatar_URLs.txtのパス
        
    Returns:
        list: 未登録アイテムの (shop_name, url) のタプルリスト
    """
    booth_ids = set(booth_mapping.keys())
    
    # profiles.jsonから登録済みIDを取得
    profile_ids = load_profiles_urls(profiles_file)
    
    # Block_URLs.txtから除外IDを取得
    block_ids = load_block_urls(block_file)
    
    # Avatar_URLs.txtから除外IDを取得
    avatar_ids = load_block_urls(avatar_file)
    
    print(f"\nbooth検索の商品数: {len(booth_ids)}")
    print(f"profiles.json の登録済み商品数: {len(profile_ids)}")
    print(f"Block_URLs.txt のブロック数: {len(block_ids)}")
    print(f"Avatar_URLs.txt のブロック数: {len(avatar_ids)}")
    
    # 差分を計算
    diff_ids = booth_ids - profile_ids - block_ids - avatar_ids
    
    if not diff_ids:
        return []
    
    # URLとショップ名のリストを作成
    url_list = []
    for item_id in diff_ids:
        url = booth_mapping[item_id]
        shop_name = extract_shop_name_from_url(url)
        url_list.append((shop_name, url))
    
    # ショップ名でソート
    url_list.sort(key=lambda x: x[0])
    
    return url_list


def send_discord_notification(webhook_url, unregistered_items):
    """
    Discord Webhookで通知を送信
    
    Args:
        webhook_url: Discord WebhookのURL
        unregistered_items: 未登録アイテムの (shop_name, url) のタプルリスト
        
    Returns:
        bool: 送信が成功したかどうか
    """
    if not webhook_url:
        print("警告: Discord Webhook URLが設定されていません")
        return False
    
    # メッセージを作成
    count = len(unregistered_items)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 最初の10件のみをメッセージに含める（長すぎる場合の対策）
    items_to_show = unregistered_items[:10]
    items_text = "\n".join([f"- {url}" for _, url in items_to_show])
    
    if count > 10:
        items_text += f"\n\n...他 {count - 10} 件"
    
    embed = {
        "title": f"🔔 新しいプロファイルが {count} 件見つかりました",
        "description": f"Boothで新しい「もちふぃった～」プロファイルが見つかりました。\n\n{items_text}",
        "color": 3447003,  # 青色
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {
            "text": "MochiFitter Profile Checker"
        }
    }
    
    payload = {
        "embeds": [embed]
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        print(f"\nDiscord通知を送信しました（{count}件）")
        return True
    except requests.exceptions.RequestException as e:
        print(f"\nエラー: Discord通知の送信に失敗しました: {e}")
        return False


def main():
    """メイン処理"""
    print("=" * 80)
    print("新規プロファイルチェッカー")
    print("=" * 80)
    
    # 検索URL（環境変数から取得、なければデフォルト）
    search_urls = [
        "https://booth.pm/ja/search/もちふぃった",
        "https://booth.pm/ja/search/mochifitter"
    ]
    
    # ファイルパス（リポジトリルートから実行される想定）
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    profiles_file = os.path.join(base_dir, "data", "profiles.json")
    block_file = os.path.join(base_dir, "data", "Block_URLs.txt")
    avatar_file = os.path.join(base_dir, "data", "Avatar_URLs.txt")
    output_file = os.path.join(base_dir, "unregistered_avatars.txt")
    
    # Discord Webhook URL（環境変数から取得）
    discord_webhook = os.environ.get("DISCORD_WEBHOOK_URL", "")
    
    # 商品URLを収集
    print("\n商品URL収集中...")
    booth_mapping = collect_urls_from_searches(search_urls)
    print(f"\n合計 {len(booth_mapping)} 件の商品を収集しました")
    
    # 未登録アイテムを検出
    print("\n差分チェック中...")
    print("=" * 80)
    unregistered_items = find_unregistered_items(
        booth_mapping, profiles_file, block_file, avatar_file
    )
    
    if unregistered_items:
        print(f"\n未登録のアバター数: {len(unregistered_items)}")
        print("\n未登録アバターURL一覧:")
        print("-" * 80)
        
        for shop_name, url in unregistered_items:
            print(url)
        
        # ファイルに保存
        with open(output_file, 'w', encoding='utf-8') as f:
            for shop_name, url in unregistered_items:
                f.write(url + '\n')
        
        print("-" * 80)
        print(f"\n結果を {output_file} に保存しました")
        
        # Discord通知
        if discord_webhook:
            send_discord_notification(discord_webhook, unregistered_items)
        else:
            print("\n注意: DISCORD_WEBHOOK_URL 環境変数が設定されていないため、通知はスキップされました")
        
        # 新規アイテムがある場合は終了コード1を返す（GitHub Actionsで検出可能）
        sys.exit(1)
    else:
        print("\n全てのアバターが登録済みです")
        sys.exit(0)


if __name__ == "__main__":
    main()
