import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import re
import json


def extract_wishlist_id(url):
    """
    ウィッシュリストURLからIDを抽出

    Args:
        url: ウィッシュリストURL

    Returns:
        str: ウィッシュリストID、見つからなければNone
    """
    match = re.search(r'/wish_list_names/([A-Za-z0-9]+)', url)
    if match:
        return match.group(1)
    return None


def extract_booth_urls_from_page(page_url, headers):
    """
    1ページ分の商品URLを抽出する

    Args:
        page_url: ページURL
        headers: HTTPリクエストヘッダー

    Returns:
        tuple: (商品URLのセット, 次のページが存在するか)
    """
    try:
        response = requests.get(page_url, headers=headers)
        response.raise_for_status()
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')

        # 商品リンクを抽出
        urls = set()

        # data-product-id と data-product-brand から商品URLを生成
        for item in soup.find_all(attrs={'data-product-id': True}):
            item_id = item.get('data-product-id')
            brand = item.get('data-product-brand')

            if item_id and brand:
                # ショップURLと商品IDを組み合わせた形式
                urls.add(f"https://{brand}.booth.pm/items/{item_id}")
            elif item_id:
                # brandがない場合は通常形式
                urls.add(f"https://booth.pm/ja/items/{item_id}")

        # 次のページが存在するか確認
        next_page = soup.find('a', {'rel': 'next'}) or soup.find('a', text=re.compile(r'次へ|Next'))
        has_next = next_page is not None

        return urls, has_next

    except Exception as e:
        print(f"エラー: {e}")
        return set(), False


def extract_wishlist_urls_from_api(wishlist_id, page, headers):
    """
    ウィッシュリストAPIから商品URLを抽出（JSON API使用）

    Args:
        wishlist_id: ウィッシュリストID
        page: ページ番号
        headers: HTTPリクエストヘッダー

    Returns:
        tuple: (商品URLのセット, 次のページが存在するか)
    """
    api_url = f"https://api.booth.pm/frontend/wish_list_names/{wishlist_id}/items.json?page={page}"

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # 商品URL抽出（shop_item_urlを優先）
        urls = set()
        for item in data.get('items', []):
            url = item.get('shop_item_url') or item.get('url')
            if url:
                urls.add(url)

        # ページネーション判定
        pagination = data.get('pagination', {})
        has_next = pagination.get('next_page') is not None

        return urls, has_next

    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
        print(f"エラー: {e}")
        return set(), False


def extract_booth_urls(search_url):
    """
    検索結果またはウィッシュリストから商品URLを抽出する

    Args:
        search_url: Boothの検索結果ページURLまたはウィッシュリストURL

    Returns:
        list: 商品URLのリスト
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # URL種別を判定
    is_wishlist = '/wish_list_names/' in search_url

    all_urls = set()
    page = 1
    has_next = True

    while has_next:
        if is_wishlist:
            # ウィッシュリストの場合（初回のみID抽出）
            if page == 1:
                wishlist_id = extract_wishlist_id(search_url)
                if not wishlist_id:
                    print("エラー: ウィッシュリストIDを抽出できませんでした")
                    break

            print(f"ウィッシュリスト ページ {page} を取得中...")
            urls, has_next = extract_wishlist_urls_from_api(wishlist_id, page, headers)
        else:
            # 検索結果の場合
            # ページ番号をURLに追加
            if '?' in search_url:
                page_url = f"{search_url}&page={page}"
            else:
                page_url = f"{search_url}?page={page}"

            print(f"ページ {page} を取得中...")

            urls, has_next = extract_booth_urls_from_page(page_url, headers)

        all_urls.update(urls)

        print(f"  -> {len(urls)} 件の商品を発見 (累計: {len(all_urls)} 件)")

        if has_next:
            page += 1
            time.sleep(1)  # サーバーに負荷をかけないよう待機

    return sorted(list(all_urls))




def main():
    # URLを入力
    print("=" * 80)
    print("Booth商品URL抽出ツール")
    print("=" * 80)
    print("\n検索URLまたはウィッシュリストURLを入力してください（Enter で デフォルト: もちふぃった～タグ）:")
    print("例1（検索）: https://booth.pm/ja/items?tags%5B%5D=VRChat")
    print("例2（ウィッシュリスト）: https://booth.pm/wish_list_names/830TkgGj")
    print()

    user_input = input("検索URL: ").strip()

    # デフォルトURL（もちふぃった～タグ）
    default_url = "https://booth.pm/ja/items?tags%5B%5D=%E3%82%82%E3%81%A1%E3%81%B5%E3%81%83%E3%81%A3%E3%81%9F%E3%80%9C"

    if user_input:
        search_url = user_input
    else:
        search_url = default_url
        print(f"デフォルトURLを使用: {search_url}")

    print("\nBooth商品URL抽出中...")
    print(f"検索URL: {search_url}")
    print("-" * 80)

    urls = extract_booth_urls(search_url)

    if urls:
        print(f"\n見つかった商品数: {len(urls)}\n")
        print("商品URL一覧:")
        print("-" * 80)
        for url in urls:
            print(url)

        # ファイルに保存
        output_file = "../booth_urls.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(url + '\n')

        print("-" * 80)
        print(f"\n結果を booth_urls.txt に保存しました")
    else:
        print("商品URLが見つかりませんでした")


if __name__ == "__main__":
    main()
