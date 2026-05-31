#!/bin/bash
# セキュリティ・スキャナ(外部ツール不要・grep ベースの自己完結実装)
#
# 検出対象を 3 系統に分類し、重大度(high / medium)を付与する:
#   1. シークレット/認証情報   … 秘密鍵・各種 API キー・トークン・URL 埋め込み資格情報 等  → 主に high
#   2. 機微情報/固有名詞        … 長い数字列(マイナンバー/カード番号)・電話番号・実メール  → medium
#                                 + .claude/security-denylist.txt の固有名詞(ユーザー管理)  → high
#   3. コード脆弱性(軽量)      … eval/exec・危険な HTML 注入 等(コードファイルのみ)        → medium
#
# 使い方:
#   scripts/security-scan.sh                 … HEAD との差分(未コミットの変更)+ 未追跡ファイルを検査
#   scripts/security-scan.sh --staged        … ステージ済みファイルを検査(pre-commit 用)
#   scripts/security-scan.sh <file> [file..] … 指定ファイルを検査
#
# 終了コード:
#   0 … ブロック対象(既定: high)なし
#   1 … ブロック対象あり(環境変数 SECURITY_BLOCK_LEVEL=high|medium で閾値を変更可、既定 high)
# medium は常に一覧表示するが、既定ではブロックしない(誤検知が混じり得るため警告に留める)。

set -uo pipefail

BLOCK_LEVEL="${SECURITY_BLOCK_LEVEL:-high}"
DENYLIST_FILE="${SECURITY_DENYLIST:-.claude/security-denylist.txt}"

# ── 対象ファイルの決定 ──────────────────────────────────────────
FILES=()
case "${1:-}" in
  --staged)
    while IFS= read -r f; do [ -n "$f" ] && FILES+=("$f"); done \
      < <(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)
    ;;
  --changed|"")
    while IFS= read -r f; do [ -n "$f" ] && FILES+=("$f"); done \
      < <(git diff --name-only HEAD --diff-filter=ACM 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null)
    ;;
  *)
    FILES=("$@")
    ;;
esac

# ── 検査から除外するパス(プレースホルダが正常なテンプレート・生成物・自分自身 等)──
is_excluded() {
  case "$1" in
    .git/*|*/node_modules/*|node_modules/*) return 0 ;;
    build/*|.docusaurus/*) return 0 ;;
    .claude/skills/*/template.md) return 0 ;;            # プレースホルダを含むのが正常
    .claude/security-denylist.txt) return 0 ;;           # デナイリスト本体
    scripts/security-scan.sh|scripts/security-scan-hook.sh) return 0 ;;
    .githooks/*) return 0 ;;
    *.drawio.svg) return 0 ;;                            # ユーザーが手動管理(base64 で誤検知も多い)
    package-lock.json|pnpm-lock.yaml|yarn.lock) return 0 ;;
    SECURITY.md) return 0 ;;                             # 本仕組みの説明(パターン例を含む)
    *) return 1 ;;
  esac
}

is_code_file() {
  case "$1" in
    *.js|*.jsx|*.ts|*.tsx|*.mjs|*.cjs|*.py|*.rb|*.go|*.java|*.php|*.sh|*.bash) return 0 ;;
    *) return 1 ;;
  esac
}

# ── パターン定義(BSD/GNU 双方で動く ERE のみ。PCRE \d 等は使わない)──
# 形式: "severity§category§label§ERE"
SECRET_PATTERNS=(
  "high§secret§秘密鍵(PRIVATE KEY)§-----BEGIN [A-Z ]*PRIVATE KEY-----"
  "high§secret§AWS アクセスキー ID§AKIA[0-9A-Z]{16}"
  "high§secret§Google API キー§AIza[0-9A-Za-z_-]{35}"
  "high§secret§Slack トークン§xox[baprs]-[0-9A-Za-z-]{10,}"
  "high§secret§GitHub トークン§gh[posru]_[0-9A-Za-z]{36,}"
  "high§secret§Bearer トークン§[Bb]earer [A-Za-z0-9._-]{20,}"
  "high§secret§URL 埋め込み資格情報§://[^/:@[:space:]]+:[^/:@[:space:]]+@"
  "high§secret§資格情報の代入§(api[_-]?key|secret|client[_-]?secret|access[_-]?token|auth[_-]?token|passwd|password)[\"' ]*[:=] *[\"']?[A-Za-z0-9_.@#$%^&*!/+-]{12,}"
)
PII_PATTERNS=(
  "medium§pii§長い数字列(マイナンバー/カード番号の可能性)§[0-9]{12,16}"
  "medium§pii§区切り付きカード番号§[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4}"
  "medium§pii§電話番号§0[0-9]{1,3}-[0-9]{1,4}-[0-9]{4}"
  "medium§pii§メールアドレス§[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)
CODE_PATTERNS=(
  "medium§code§eval/exec の使用§(^|[^A-Za-z_])(eval|exec) *\("
  "medium§code§危険な HTML 注入§dangerouslySetInnerHTML"
  "medium§code§シェル経由の実行§shell *[:=] *[Tt]rue"
)

# 代入パターンの誤検知抑制: ダミー値・プレースホルダを除外
is_dummy_secret() {
  local line="$1"
  case "$line" in
    *'{{'*|*xxxx*|*XXXX*|*your_*|*example*|*dummy*|*changeme*|*redacted*|*'********'*|*'<'*'>'*) return 0 ;;
    *) return 1 ;;
  esac
}

# メールの誤検知抑制: example/test 系ドメインを除外
is_dummy_email() {
  case "$1" in
    *@example.com|*@example.org|*@example.net|*@example.jp|*@test|*@localhost|*@*.example) return 0 ;;
    *) return 1 ;;
  esac
}

mask() {
  local s="$1" n=${#1}
  if [ "$n" -le 8 ]; then printf '********'; else printf '%s…%s' "${s:0:4}" "${s: -2}"; fi
}

# ── スキャン本体 ────────────────────────────────────────────────
FINDINGS_FILE="$(mktemp)"
trap 'rm -f "$FINDINGS_FILE"' EXIT

record() { printf '%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" >> "$FINDINGS_FILE"; }

scan_with() {
  # $1=file  $2..=patterns
  local file="$1"; shift
  local entry sev cat label re out lineno matchtext rest
  for entry in "$@"; do
    sev="${entry%%§*}";   rest="${entry#*§}"
    cat="${rest%%§*}";    rest="${rest#*§}"
    label="${rest%%§*}";  re="${rest#*§}"
    # -I: バイナリ除外, -n: 行番号, -o: 一致箇所のみ, -E: ERE
    while IFS= read -r out; do
      [ -z "$out" ] && continue
      lineno="${out%%:*}"
      matchtext="${out#*:}"
      # カテゴリ別の誤検知抑制
      if [ "$cat" = "secret" ] && is_dummy_secret "$matchtext"; then continue; fi
      if [ "$label" = "メールアドレス" ] && is_dummy_email "$matchtext"; then continue; fi
      record "$sev" "$cat" "$file:$lineno" "$label" "$(mask "$matchtext")"
    done < <(grep -InoE -e "$re" "$file" 2>/dev/null)
  done
}

scan_denylist() {
  local file="$1" out lineno
  [ -f "$DENYLIST_FILE" ] || return 0
  while IFS= read -r term; do
    case "$term" in ''|\#*) continue ;; esac
    while IFS= read -r out; do
      [ -z "$out" ] && continue
      lineno="${out%%:*}"
      record "high" "denylist" "$file:$lineno" "固有名詞(デナイリスト)" "$term"
    done < <(grep -InoF -- "$term" "$file" 2>/dev/null)
  done < "$DENYLIST_FILE"
}

for file in "${FILES[@]:-}"; do
  [ -n "$file" ] || continue
  [ -f "$file" ] || continue
  is_excluded "$file" && continue
  scan_with "$file" "${SECRET_PATTERNS[@]}"
  scan_with "$file" "${PII_PATTERNS[@]}"
  is_code_file "$file" && scan_with "$file" "${CODE_PATTERNS[@]}"
  scan_denylist "$file"
done

# ── レポート出力 ────────────────────────────────────────────────
# grep -c は 0 件でも単一の数値「0」を stdout に出す(exit 1 だが値は正しい)。
# || で補わない(補うと二重出力で算術評価が壊れる)。
HIGH_COUNT=$(grep -c $'^high\t' "$FINDINGS_FILE" 2>/dev/null); HIGH_COUNT=${HIGH_COUNT:-0}
MED_COUNT=$(grep -c $'^medium\t' "$FINDINGS_FILE" 2>/dev/null); MED_COUNT=${MED_COUNT:-0}

if [ "$HIGH_COUNT" -eq 0 ] && [ "$MED_COUNT" -eq 0 ]; then
  echo "✅ セキュリティスキャン: 検出なし(検査 ${#FILES[@]} ファイル)"
  exit 0
fi

print_group() {
  local sev="$1" title="$2"
  grep -q $'^'"$sev"$'\t' "$FINDINGS_FILE" || return 0
  echo "  ── $title ──"
  awk -F'\t' -v s="$sev" '$1==s {printf "    [%s] %s  %s : %s\n", $2, $3, $4, $5}' "$FINDINGS_FILE"
  echo ""
}

echo "🔒 セキュリティスキャン結果"
echo ""
printf "  high(要対応): %d 件  /  medium(要確認): %d 件\n" "$HIGH_COUNT" "$MED_COUNT"
echo ""
print_group "high"   "high: シークレット・資格情報・固有名詞(デナイリスト)"
print_group "medium" "medium: 機微情報の可能性・コード脆弱性(誤検知を含み得る)"
echo "  対応方法:"
echo "    - 本物の秘匿情報なら、その値をファイルから除去し履歴に残さない(必要なら環境変数/シークレット管理へ)"
echo "    - 公開してよい固有名詞の誤検知は .claude/security-denylist.txt を見直す"
echo "    - medium の各行を目視確認(プレースホルダ {{...}} や example ドメインは安全)"
echo ""

# ブロック判定
if [ "$BLOCK_LEVEL" = "medium" ]; then
  [ $((HIGH_COUNT + MED_COUNT)) -gt 0 ] && exit 1
else
  [ "$HIGH_COUNT" -gt 0 ] && exit 1
fi
exit 0
