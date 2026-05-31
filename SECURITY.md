# セキュリティ・スキャン(OSS 公開向け)

本リポジトリは Claude Code で成果物を生成します。公開リポジトリにシークレットや機微情報が
混入しないよう、**生成完了時**と**コミット時**の二段でスキャンを行います。外部ツールのインストールは不要です(`grep`/`jq` のみ)。

## 検出対象

| 系統 | 例 | 既定の重大度 |
|---|---|---|
| シークレット/認証情報 | 秘密鍵・AWS/Google/Slack/GitHub のキーやトークン・URL 埋め込み資格情報・`password=...` 等の代入 | high |
| 機微情報/固有名詞 | 長い数字列(マイナンバー/カード番号)・電話番号・実在メール | medium |
| 固有名詞(デナイリスト) | `.claude/security-denylist.txt` に列挙した語 | high |
| コード脆弱性(軽量) | `eval`/`exec`・危険な HTML 注入 等(コードファイルのみ) | medium |

`{{プレースホルダ}}` や `example.com` 等のダミーは誤検知として自動除外します。

## 二段の防御

1. **生成完了時(Claude Code の Stop フック)** — Claude が応答を終えると未コミットの変更を自動スキャンし、
   検出があれば警告を表示します。**停止はブロックしません(気付き目的)。**
   設定: [.claude/settings.json](.claude/settings.json) → [scripts/security-scan-hook.sh](scripts/security-scan-hook.sh)
2. **コミット時(git pre-commit / 最終防衛線)** — ステージ済みファイルをスキャンし、**high を検出するとコミットを中止**します。
   設定: [.githooks/pre-commit](.githooks/pre-commit)

## セットアップ(クローン後に一度だけ)

pre-commit フックを有効化するため、リポジトリ直下で次を実行します(`npm install` 時に `prepare` で自動実行されます):

```bash
git config core.hooksPath .githooks
```

## 手動実行

```bash
npm run check:security          # HEAD との差分 + 未追跡ファイルを検査
bash scripts/security-scan.sh --staged        # ステージ済みファイル
bash scripts/security-scan.sh path/to/file.md # 指定ファイル
```

## 運用メモ

- **固有名詞の管理**: 実在の顧客名・社内システム名など公開してはならない語は
  [.claude/security-denylist.txt](.claude/security-denylist.txt) に追記します(1 行 1 語)。
- **誤検知でコミットできない場合**: 確実に誤検知のときのみ `git commit --no-verify` で回避できます。
- **ブロック閾値の変更**: `SECURITY_BLOCK_LEVEL=medium` を付けると medium もブロック対象になります。
- **深いコード脆弱性レビュー**: 軽量パターンを超える解析が必要なときは Claude Code の `/security-review` を利用してください。
