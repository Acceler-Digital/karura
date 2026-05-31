#!/bin/bash
# 未確定マーカー(プレースホルダ・要確認)の残存状況を表示する。
# CI fail は目的としない。レビュー時の気付き支援として、必ず exit 0 で終わる。
#
# 検査対象:
#   - プレースホルダ: {{xxx}}
#   - 要確認マーカー: ブロック記法 (> ⚠️ **要確認**: ...) / インライン記法 (【要確認】 ... 【要確認: ...】)
#     ※ どちらも文字列「要確認」を含むため grep '要確認' で一括検出
#
# 検査範囲: docs/ 配下のみ(.claude/skills/<name>/template.md はプレースホルダを含むのが正常なので除外)

set +e

TARGET_DIR="docs"

if [ ! -d "$TARGET_DIR" ]; then
  echo "ℹ️  $TARGET_DIR/ が存在しないため、チェックをスキップしました。"
  exit 0
fi

# grep -o で一致箇所ごとに1行出力されるので、出現回数=行数として正確にカウントできる
# 同一行に複数のマーカーがあっても過小カウントにならない
PLACEHOLDER_OCCURRENCES=$(grep -rEon '\{\{[^}]+\}\}' "$TARGET_DIR" 2>/dev/null)
TODO_OCCURRENCES=$(grep -ron '要確認' "$TARGET_DIR" 2>/dev/null)

if [ -z "$PLACEHOLDER_OCCURRENCES" ]; then
  PLACEHOLDER_COUNT=0
else
  PLACEHOLDER_COUNT=$(printf '%s\n' "$PLACEHOLDER_OCCURRENCES" | grep -c .)
fi

if [ -z "$TODO_OCCURRENCES" ]; then
  TODO_COUNT=0
else
  TODO_COUNT=$(printf '%s\n' "$TODO_OCCURRENCES" | grep -c .)
fi

TOTAL=$((PLACEHOLDER_COUNT + TODO_COUNT))

if [ "$TOTAL" -eq 0 ]; then
  echo "✅ 未確定マーカーは残っていません ($TARGET_DIR/)"
  exit 0
fi

echo "⚠️  未確定箇所が残っています (警告のみ・コミット可)"
echo ""
printf "  プレースホルダ {{...}}: %d件\n" "$PLACEHOLDER_COUNT"
printf "  要確認マーカー         : %d件\n" "$TODO_COUNT"
echo ""

print_file_breakdown() {
  local lines="$1"
  printf '%s\n' "$lines" | awk -F: 'NF>=2 {print $1}' | sort | uniq -c | sort -rn | while read -r count file; do
    printf "    %s (%d件)\n" "$file" "$count"
  done
}

if [ "$PLACEHOLDER_COUNT" -gt 0 ]; then
  echo "  ── プレースホルダのあるファイル ──"
  print_file_breakdown "$PLACEHOLDER_OCCURRENCES"
  echo ""
fi

if [ "$TODO_COUNT" -gt 0 ]; then
  echo "  ── 要確認マーカーのあるファイル ──"
  print_file_breakdown "$TODO_OCCURRENCES"
  echo ""
fi

echo "  詳細(全行表示):"
echo "    grep -rn '{{' $TARGET_DIR/"
echo "    grep -rn '要確認' $TARGET_DIR/"

exit 0
