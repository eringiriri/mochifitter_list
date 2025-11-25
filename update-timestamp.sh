#!/bin/bash
# 最終更新日時を自動更新するスクリプト

TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M:%S UTC')
sed -i "s/const LAST_UPDATED = '.*';/const LAST_UPDATED = '$TIMESTAMP';/" js/main.js

echo "✅ 最終更新日時を更新しました: $TIMESTAMP"
