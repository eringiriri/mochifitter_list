import json
import re
from datetime import datetime


def convert_date_format(date_str):
    """
    mm/dd/yyyyをyyyy-mm-ddに変換

    Args:
        date_str: 日付文字列（mm/dd/yyyy形式）

    Returns:
        str: yyyy-mm-dd形式の日付文字列
    """
    if not date_str or '/' not in date_str:
        return date_str

    try:
        # mm/dd/yyyy -> yyyy-mm-dd
        date_obj = datetime.strptime(date_str, "%m/%d/%Y")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        # 変換できない場合はそのまま返す
        return date_str


def fix_dates_in_profiles(input_file, output_file=None):
    """
    profiles.jsonの日付フォーマットを修正

    Args:
        input_file: 入力ファイルパス
        output_file: 出力ファイルパス（Noneの場合は上書き）
    """
    if output_file is None:
        output_file = input_file

    # JSONファイルを読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    fixed_count = 0

    # 各プロファイルの日付を変換
    for profile in data.get('profiles', []):
        # registeredDateを変換
        if 'registeredDate' in profile:
            old_date = profile['registeredDate']
            new_date = convert_date_format(old_date)
            if old_date != new_date:
                profile['registeredDate'] = new_date
                fixed_count += 1
                print(f"変換: {old_date} -> {new_date}")

        # updatedDateを変換
        if 'updatedDate' in profile:
            old_date = profile['updatedDate']
            new_date = convert_date_format(old_date)
            if old_date != new_date:
                profile['updatedDate'] = new_date
                fixed_count += 1
                print(f"変換: {old_date} -> {new_date}")

    # JSONファイルに書き込み
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n修正完了: {fixed_count}件の日付を変換しました")
    print(f"保存先: {output_file}")


if __name__ == "__main__":
    input_file = "../data/profiles.json"
    fix_dates_in_profiles(input_file)
