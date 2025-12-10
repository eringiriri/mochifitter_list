#!/usr/bin/env python3
"""
既存のprofiles.jsonに avatarshopname と profileshopname フィールドを追加する移行スクリプト
何度実行しても安全（既にフィールドがある場合はスキップ）
"""

import json
import os
import requests
from bs4 import BeautifulSoup


def fetch_shopname_from_url(url):
    """
    Booth URLにアクセスしてtitleタグからショップ名を取得

    Args:
        url: ショップURL

    Returns:
        str: ショップ名（取得できない場合は空文字）
    """
    if not url or "booth.pm" not in url:
        return ""

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        title_tag = soup.find('title')

        if title_tag:
            title_text = title_tag.string
            # " - BOOTH" を削除
            shopname = title_text.replace(" - BOOTH", "").strip()
            return shopname
    except Exception:
        pass

    return ""


def add_shopname_fields(json_path):
    """
    profiles.jsonに avatarshopname と profileshopname フィールドを追加

    Args:
        json_path: profiles.jsonのパス
    """
    print("=" * 80)
    print("avatarshopname / profileshopname フィールド追加スクリプト")
    print("=" * 80)

    # JSONファイルを読み込み
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    profiles = data.get("profiles", [])
    updated_count = 0
    skipped_count = 0

    print(f"\n総プロファイル数: {len(profiles)}")
    print("\n処理中...")
    print("-" * 80)

    for profile in profiles:
        profile_id = profile.get("id", "unknown")
        avatar_name = profile.get("avatarName", "")

        # 既に両方のフィールドが存在する場合はスキップ
        if "avatarshopname" in profile and "profileshopname" in profile:
            skipped_count += 1
            print(f"[{profile_id}] {avatar_name}: avatarshopname/profileshopname already exist, skipped")
            continue

        needs_update = False

        # avatarshopname を追加（存在しない場合のみ）
        if "avatarshopname" not in profile:
            avatar_author_url = profile.get("avatarAuthorUrl", "")
            avatarshopname = fetch_shopname_from_url(avatar_author_url)
            profile["avatarshopname"] = avatarshopname
            needs_update = True
            print(f"[{profile_id}] {avatar_name}: added avatarshopname = '{avatarshopname}'")

        # profileshopname を追加（存在しない場合のみ）
        if "profileshopname" not in profile:
            profile_author_url = profile.get("profileAuthorUrl", "")
            profileshopname = fetch_shopname_from_url(profile_author_url)
            profile["profileshopname"] = profileshopname
            needs_update = True
            print(f"[{profile_id}] {avatar_name}: added profileshopname = '{profileshopname}'")

        if needs_update:
            updated_count += 1

    print("-" * 80)
    print(f"\n更新されたプロファイル数: {updated_count}")
    print(f"スキップされたプロファイル数: {skipped_count}")

    # 更新がある場合のみ書き戻し
    if updated_count > 0:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ {json_path} を更新しました")
        return True
    else:
        print("\n✅ 更新は必要ありませんでした")
        return False


def main():
    # profiles.jsonのパス
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    json_path = os.path.join(repo_root, "data", "profiles.json")

    if not os.path.exists(json_path):
        print(f"エラー: {json_path} が見つかりません")
        return 1

    updated = add_shopname_fields(json_path)
    print("=" * 80)

    # 更新があった場合は終了コード0、なければ0（どちらも成功扱い）
    return 0


if __name__ == "__main__":
    exit(main())
