#!/bin/bash
# 最終更新日時を自動更新するスクリプト（JST）

TIMESTAMP=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S JST')
sed -i "s/const LAST_UPDATED = '.*';/const LAST_UPDATED = '$TIMESTAMP';/" js/main.js

echo "✅ 最終更新日時を更新しました: $TIMESTAMP"
