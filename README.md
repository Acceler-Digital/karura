<div align="center">
<!-- TODO: ロゴができたら差し替え（static/img/ に配置）
<img src="static/img/karura-logo.png" alt="KARURA" width="200" />
-->

# KARURA

**ビジネス要求から保守運用まで、成果物を一貫生成する<br>エンタープライズ向け AI 駆動開発総合ソリューション**

[![License](https://img.shields.io/github/license/Acceler-Digital/karura)](LICENSE)
[![Release](https://img.shields.io/github/v/release/Acceler-Digital/karura?include_prereleases&label=release)](https://github.com/Acceler-Digital/karura/releases)
[![Node](https://img.shields.io/badge/node-%E2%89%A518-339933?logo=node.js&logoColor=white)](#前提条件)
[![pnpm](https://img.shields.io/badge/pnpm-%E2%89%A59-F69220?logo=pnpm&logoColor=white)](#前提条件)
[![Docusaurus](https://img.shields.io/badge/docs-Docusaurus%203-3ECC5F?logo=docusaurus)](https://docusaurus.io/)
 
[📘 成果物サンプルを見る](https://github.com/Acceler-Digital/karura-sample-artifacts-individual-life-insurance-new-business) ・ [🗺 成果物フロー](docs/D0.project-management/artifact-flow.md) ・ [🌐 Acceler Digital](https://www.acceler-digital.com/)
</div>

## KARURA とは
 
KARURAは、生成AI(Claude)を中心とした大規模AI駆動開発を、**ビジネス要求からリリース・保守運用まで一貫した成果物体系**として進めるための総合ソリューションです。成果物を生成・更新するための仕組み一式を収録しています。

| 収録要素 | 内容 |
| --- | --- |
| **スキル定義**（`.claude/skills/`） | Claude が各成果物を生成・更新するための振る舞いルール |
| **テンプレート**（各スキル同梱 `template.md`） | 成果物の骨組み（章構成・書き方ヒント） |
| **プロジェクト共通規約**（[CLAUDE.md](CLAUDE.md)） | プレースホルダ・ID 表記・文体などの横断ルール |
| **成果物フロー**（[artifact-flow.md](docs/D0.project-management/artifact-flow.md)） | フェーズ間の依存関係・生成順 |
| **セキュリティガードレール**（`scripts/` + git フック） | OSS 公開時のシークレット混入を二段スキャンで防止 |
| **Docusaurus** | 成果物を Wiki サイトとしてプレビュー |

## KARURAを使った成果物サンプルを見たい場合

KARURAを使った具体的な成果物は以下のリポジトリで参照できます。

👉 **[KARURA 成果物サンプル - 生命保険 新契約システム](https://github.com/Acceler-Digital/karura-sample-artifacts-individual-life-insurance-new-business)**

## 収録しているスキル

各成果物のスキルは [.claude/skills/](.claude/skills/) 配下にフェーズ別で収録しています。スキルディレクトリには `SKILL.md`(振る舞いルール）と `template.md`(章構成・書き方ヒントを埋め込んだ雛形）を同梱しており、スキル+テンプレートを 1 単位で他プロジェクトへ流用できます。

| フェーズ | スキル |
|---|---|
| **D1** ビジネス要求 | ビジネス要件定義書 / アクター一覧 / ドメイン定義書 / プロダクト要求仕様書 / ドメイン共通要求仕様書 / ドメイン要求仕様書 / ユーザーストーリー一覧 / ユースケース一覧 / 画面コンセプト集 |
| **D2** システム要件 | 機能一覧 / 外部システム一覧 / C4モデル レベル1(システムコンテキスト） |

Claude Code から `/d1-business-requirement-document` のようにスラッシュコマンドで呼び出すと、章構成・上下流の伝搬関係を踏まえた生成・更新ができます。フェーズ間の依存関係や生成順は [docs/D0.project-management/artifact-flow.md](docs/D0.project-management/artifact-flow.md) を参照してください。

## Claude で成果物を生成・更新する

本リポジトリは Claude（Claude Code 等）を介した成果物の生成・更新を前提に整備されています。

- **プロジェクト共通の慣習**: [CLAUDE.md](CLAUDE.md) にプレースホルダ書式（`{{xxx}}`）・要確認マーカー運用・ファイル配置規約・ID 表記規約・文体規約・サイドバー登録ルール・参照元の境界（D0 は明示指示なしには参照しない 等）が集約されており、Claude が自動で参照します
- **成果物固有の慣習**: 各成果物のスキルが [.claude/skills/](.claude/skills/) に配置されており、`/d1-business-requirement-document` のようにスラッシュコマンドで呼び出せます
- **テンプレート**: 各スキルディレクトリ `.claude/skills/<skill-name>/template.md` に、章構成と書き方ヒント（HINTコメント）を埋め込んだ雛形を同梱しています。本リポジトリは Claude を中核に据える前提のため、テンプレートはスキルが読み込む内部リソースとして扱います

生成された成果物は、別リポジトリ(上記サンプル等）の `docs/` 配下に配置していく運用を想定しています。本リポジトリの `docs/` には、フェーズのプレースホルダとなる空ディレクトリと、成果物フロー等のメタ情報のみを置いています。

## セキュリティ・スキャン

本リポジトリ(および KARURA で運用するリポジトリ）は、公開リポジトリにシークレットや機微情報が混入しないよう、**生成完了時**と**コミット時**の二段でスキャンを行います。外部ツールのインストールは不要です(`grep`/`jq` のみ）。

1. **生成完了時(Claude Code の Stop フック）** — Claude が応答を終えると未コミットの変更を自動スキャンし、検出があれば警告します(停止はブロックしない、気付き目的）
2. **コミット時(git pre-commit / 最終防衛線）** — ステージ済みファイルをスキャンし、**high を検出するとコミットを中止**します

```bash
# 手動スキャン
pnpm check:security

# pre-commit フックの有効化(pnpm install 時に prepare で自動実行）
git config core.hooksPath .githooks
```

検出対象・重大度・誤検知除外の詳細は [SECURITY.md](SECURITY.md) を参照してください。実体は [scripts/security-scan.sh](scripts/security-scan.sh) ・ [.githooks/pre-commit](.githooks/pre-commit) です。

## ドキュメントサイトをローカルで立ち上げる

[docs/](docs/) 配下のMarkdownは [Docusaurus 3](https://docusaurus.io/) でWikiサイトとしてプレビューできます。Wikiのサイドバー構成は [sidebars.ts](sidebars.ts) を参照してください。

```bash
# 依存関係インストール
pnpm install

# 開発サーバー起動（ホットリロード付き）
pnpm start
# http://localhost:3000 で閲覧

# 本番ビルド
pnpm build

# ビルド後のプレビュー
pnpm serve

# オフライン閲覧用ビルド（hash router・検索インデックス同梱）
pnpm build:offline
```

### 前提条件

- Node.js 18 以上
- pnpm 9 以上

## 成果物の整備状況を確認する

[docs/](docs/) 配下に残っている未確定マーカー（プレースホルダ `{{xxx}}` と要確認マーカー `要確認`）の件数・該当ファイルを表示します。レビュー時の気付き支援用で、CI で fail させる目的ではありません（スクリプトは常に exit 0）。

```bash
pnpm check:markers
```

実体は [scripts/check-markers.sh](scripts/check-markers.sh) です。マーカー記法そのものについては [CLAUDE.md](CLAUDE.md) §1〜§3 を参照してください。

## 画面・デザイン成果物の前提（Figma 併走）

KARURA では、**画面に関わる成果物は Figma を併走させることを前提**としています。Markdown 側は「画面体験の方向性・原則・代表シーンの言葉」を、Figma 側は「ムードボード・代表シーン・全画面ワイヤーの絵」を、それぞれフェーズ別に持つ役割分担です。

| 成果物 | Markdown 側の責務 | Figma 側の責務 |
|---|---|---|
| 画面コンセプト集（D1） | 画面体験のコンセプト宣言・体験原則（3-5）・代表シーン（2-3、最大5）の正本 | ムードボード/スタイルタイル + 代表シーン用ラフ（数枚） |
| 画面要件群（D2） | 全画面の画面要件項目（表示項目・状態・遷移・バリデーション）の正本 | 全画面のワイヤーフレーム（中忠実度） |
| デザインカンプ・デザインシステム（D3 以降） | — | ハイファイ・コンポーネント・トークン |

D1 段階は **ビジネスサイドが議論・合意できるサイズ**（数枚の代表シーン + 体験原則の合意）に Figma 投資を絞り、全画面のワイヤー網羅は D2 以降に降ろします。

### Figma MCP

Claude Code（claude.ai 経由）から Figma file を読み取り操作できます。本リポジトリには以下が設定済みです:

- **読み取り系ツール**（`whoami` / `get_metadata` / `get_design_context` / `get_screenshot` 等）を [.claude/settings.json](.claude/settings.json) で allowlist 済み（権限プロンプトを省略）
- **書き込み系ツール**（`use_figma` / `create_new_file` 等）は **意図的に allowlist 外**（設計成果物の生成・上書きは常に明示確認を経由）

初回利用時は claude.ai 経由の OAuth 認証が必要です。Figma file の作成・編集を Claude に依頼するには **Editor 以上のシート** が必要です（View シートでは書き込み不可）。

## リポジトリ構成

```
.
├── .claude/
│   ├── skills/                    # Claude スキル定義（フェーズ別、テンプレート同梱）
│   │   ├── d1-business-requirement-document/
│   │   │   ├── SKILL.md           # スキル本体(振る舞いルール）
│   │   │   └── template.md        # 成果物テンプレート（章構成・書き方ヒント入り）
│   │   └── ...                    # d1-* / d2-* 各スキル
│   └── settings.json              # Claude Code 設定(allowlist・Stop フック 等）
├── docs/                          # メタ情報・フェーズ用プレースホルダ
│   └── D0.project-management/     # 成果物フロー・プロジェクトインデックス
├── scripts/                       # 補助スクリプト
│   ├── check-markers.sh           # 未確定マーカー集計
│   └── security-scan.sh           # セキュリティスキャン本体
├── .githooks/
│   └── pre-commit                 # コミット時セキュリティスキャン
├── sidebars.ts                    # Docusaurus サイドバー定義
├── docusaurus.config.ts           # Docusaurus 設定
├── CLAUDE.md                      # プロジェクト共通の慣習（Claude が自動参照）
├── SECURITY.md                    # セキュリティスキャンの説明
└── package.json
```

## 関連リポジトリ

- [KARURA 成果物サンプル - 生命保険 新契約システム](https://github.com/Acceler-Digital/karura-sample-artifacts-individual-life-insurance-new-business)

## ライセンス

本リポジトリに含まれるドキュメント・図・設定ファイル・スクリプトは [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) の下で提供されます。全文は同梱の [LICENSE](LICENSE) を参照してください。
