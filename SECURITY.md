# セキュリティポリシー

KARURA の脆弱性を発見された場合は、以下の手順でご報告ください。ご協力に感謝します。

> **English**: Please report vulnerabilities privately via GitHub's [Private vulnerability reporting](https://github.com/Acceler-Digital/karura/security/advisories/new). Do **not** open a public issue.

## 報告方法

**公開 Issue・プルリクエスト・SNS 等での報告はご遠慮ください。** 修正前に脆弱性が公開されると、利用者が危険にさらされます。

GitHub の **Private vulnerability reporting** をご利用ください。

👉 **[脆弱性を報告する](https://github.com/Acceler-Digital/karura/security/advisories/new)**

リポジトリの **Security** タブ →「**Report a vulnerability**」からも同じフォームを開けます。報告内容はメンテナーのみが閲覧でき、公開されません。

## 報告に含めていただきたい情報

- 脆弱性の概要と想定される影響
- 該当箇所(ファイルパス・行番号・スキル名・スクリプト名など)
- 再現手順(該当する場合は、再現に使ったコマンドや入力)
- 実行環境(OS・Claude Code のバージョン・シェル など)
- 差し支えなければ、想定される修正案

**再現手順に実在のシークレットや個人情報を含めないでください。** ダミー値(`{{プレースホルダ}}`・`example.com` 等)に置き換えてご報告ください。

## 対応の流れ

1. **受領連絡** — 5 営業日以内に受領のご連絡をします
2. **調査・影響範囲の確認** — 再現性と影響範囲を確認し、重大度を判断します
3. **修正** — 重大度に応じて修正版をリリースします
4. **公開** — 修正のリリース後、GitHub Security Advisory として公開します

進捗は、報告いただいたアドバイザリのスレッド上でご連絡します。

## 対象範囲

**対象** — 本リポジトリに含まれるもの

- スキル定義・テンプレート([plugin/skills/](plugin/skills/))
- セキュリティスキャン等のスクリプト([plugin/scripts/](plugin/scripts/) ・ [scripts/](scripts/) ・ [.githooks/](.githooks/))
- プラグイン設定・フック定義([plugin/hooks/](plugin/hooks/) ・ [.claude-plugin/](.claude-plugin/))
- Docusaurus 設定([docusaurus.config.ts](docusaurus.config.ts) ・ [sidebars.ts](sidebars.ts))

**対象外**

- **Claude Code / Anthropic 製品そのものの脆弱性** — [Anthropic のセキュリティ窓口](https://www.anthropic.com/responsible-disclosure-policy)へご報告ください
- **KARURA で生成した成果物の内容** — 生成物の妥当性は利用者側でのレビューを前提としています(生成結果の誤りや不足は [Issue](https://github.com/Acceler-Digital/karura/issues) へどうぞ)
- **依存パッケージの既知脆弱性** — 原則として上流へご報告ください(本リポジトリ側の対応が必要な場合はお知らせください)

## 対象バージョン

本リポジトリは常に最新版のみをサポートします。修正は `main` に対して行い、必要に応じて新しいリリースを作成します。過去バージョンへのバックポートは行いません。

## 謝辞

ご希望があれば、修正後に公開する Security Advisory に報告者としてお名前を記載します。報告時にその旨をお知らせください。

---

なお、本リポジトリに同梱している**シークレット混入防止のセキュリティスキャン**(生成完了時の Stop フック / コミット時の pre-commit)については、[README.md の「セキュリティ・スキャン」](README.md#セキュリティスキャン)を参照してください。
