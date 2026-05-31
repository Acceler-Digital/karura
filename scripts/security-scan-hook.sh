#!/bin/bash
# Claude Code の Stop フック用ラッパ。
# Claude が応答を終えるタイミングで未コミットの変更を検査し、
# 検出があれば systemMessage としてユーザーに警告表示する(advisory)。
#
# 方針:
#   - 生成完了時は「気付き」を目的とし、停止をブロックしない(ループを避けるため常に exit 0)。
#   - ハードな防止は git pre-commit(最終防衛線)が担う。
#
# 入力: Claude Code から stdin に JSON が渡るが、ここでは未使用。
# 出力: 検出時のみ {"systemMessage": "..."} を stdout に出す(jq で組み立て)。

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# medium も含めて全件を拾いたいので、ブロック判定とは独立に全文を取得する
REPORT="$(SECURITY_BLOCK_LEVEL=high bash scripts/security-scan.sh --changed 2>/dev/null)"

# 「検出なし」なら静かに終了
case "$REPORT" in
  *"検出なし"*|"") exit 0 ;;
esac

MSG=$(printf '⚠️ セキュリティスキャンが生成物に懸念を検出しました。コミット前に確認してください。\n\n%s' "$REPORT")
jq -n --arg m "$MSG" '{systemMessage: $m}'
exit 0
