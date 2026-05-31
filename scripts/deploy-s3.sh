#!/usr/bin/env bash
#
# KARURA サンプル成果物 Wiki をローカルから S3 へ手動デプロイする。
# GitHub Actions と同じ `aws s3 sync` を叩くため、結果は CI デプロイと一致する。
#
# 前提: ローカルの AWS CLI 認証が済んでいること(aws configure または SSO ログイン)。
# 設定値(バケット/リージョン)は aws/deploy.env から読み込み、環境変数で上書き可能。
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 設定読み込み(BUCKET / REGION)。環境変数 S3_BUCKET / AWS_REGION が優先。
# shellcheck disable=SC1091
source "${ROOT_DIR}/aws/deploy.env"
BUCKET="${S3_BUCKET:-${BUCKET}}"
REGION="${AWS_REGION:-${REGION}}"

# AWS 認証チェック(未設定なら案内して終了)
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "❌ AWS 認証が未設定です。先に以下のいずれかを実行してください:" >&2
  echo "   - IAM Identity Center(SSO): aws configure sso && aws sso login" >&2
  echo "   - IAM ユーザのアクセスキー  : aws configure" >&2
  exit 1
fi

echo "▶ Building (pnpm build)..."
pnpm build

echo "▶ Syncing build/ -> s3://${BUCKET}/ (${REGION})..."
aws s3 sync "${ROOT_DIR}/build/" "s3://${BUCKET}/" --delete --region "${REGION}"

echo "✅ Done: http://${BUCKET}.s3-website-${REGION}.amazonaws.com"
