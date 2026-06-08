<div align="center">
<!-- TODO: ロゴができたら差し替え(static/img/ に配置)
<img src="static/img/karura-logo.png" alt="KARURA" width="200" />
-->

# KARURA
 
**ビジネス要求から保守運用まで、成果物を一貫生成する<br>エンタープライズ向けAI駆動開発総合ソリューション**
 
[![License](https://img.shields.io/github/license/Acceler-Digital/karura?style=flat-square)](LICENSE)
[![Release](https://img.shields.io/github/v/release/Acceler-Digital/karura?include_prereleases&label=release&style=flat-square)](https://github.com/Acceler-Digital/karura/releases)
[![Node](https://img.shields.io/badge/node-%E2%89%A518-339933?style=flat-square&logo=node.js&logoColor=white)](#前提条件)
[![pnpm](https://img.shields.io/badge/pnpm-%E2%89%A59-F69220?style=flat-square&logo=pnpm&logoColor=white)](#前提条件)
[![Docusaurus](https://img.shields.io/badge/docs-Docusaurus%203-3ECC5F?style=flat-square&logo=docusaurus)](https://docusaurus.io/)

[![成果物フロー](https://img.shields.io/badge/🗺_成果物フロー-181717?style=for-the-badge)](docs/D0.project-management/artifact-flow.md)
[![ハンドブック](https://img.shields.io/badge/📚_ハンドブック-181717?style=for-the-badge)](handbook/README.md)
[![corporate](https://img.shields.io/badge/🌐_corporate-acceler--digital.com-181717?style=for-the-badge)](https://www.acceler-digital.com/)
</div>

## KARURAとは

KARURAは、Acceler DigitalのAI駆動開発の知見を体系化した、エンタープライズ向けAI駆動開発総合ソリューションです。大規模、且つ、ミッションクリティカルなシステム開発を対象に、生成AI(Claude Code等)を使ってビジネス要求からリリース・保守運用までの成果物を一貫した体系として生成するための仕組み一式を提供します。

> [!TIP]
> **まず実物を見たい方へ** - KARURAで実際に生成した成果物一式は[成果物サンプル(生命保険 新契約システム)](https://github.com/Acceler-Digital/karura-sample-artifacts-individual-life-insurance-new-business)で公開しています。

| 収録要素 | 該当成果物 | 内容 |
| --- | --- | --- |
| **スキル定義** | [.claude/skills/](.claude/skills/) | Claudeが各成果物を生成・更新するための振る舞いルール。スラッシュコマンドで呼び出し。 |
| **成果物テンプレート** | [.claude/skills/](.claude/skills/) 配下の各スキルの `template.md` | 成果物の骨組み(章構成・書き方ヒント)。AIが読み込んで記入するフォーマット。 |
| **プロジェクト共通規約** | [CLAUDE.md](CLAUDE.md) | プレースホルダ・ID 表記・文体などの横断ルール。Claudeが自動参照。 |
| **成果物フロー** | [docs/D0.project-management/artifact-flow.md](docs/D0.project-management/artifact-flow.md) | 全成果物の input/outputの依存関係・生成順の定義 |
| **周辺スクリプト群** | [scripts/](scripts/) | セキュリティガードレールや、AIの挙動を支援する各種スクリプト |
| **Wiki(Docusaurus)** | [docusaurus.config.ts](docusaurus.config.ts) ・ [sidebars.ts](sidebars.ts)等 | プロジェクトで使用する成果物をWikiサイトとしてプレビュー(Confluence/Notion等を使う場合は不要) |
 
## 成果物フロー

KARURAにおいて、中核となる考え方が[成果物フロー](docs/D0.project-management/artifact-flow.drawio.svg)です。各成果物が何をインプットとし、何をアウトプットするのか、成果物同士の依存関係を定義したものであり、KARURAにおけるAIの挙動の根底になります。

各成果物はD0~D11のフェーズに分かれており、フェーズ単位の簡略版の全体像は以下の通りです。

```mermaid
flowchart LR
    classDef included fill:#2da44e,stroke:#2da44e,color:#fff
    classDef planned fill:#f6f8fa,stroke:#d0d7de,color:#57606a
 
    D1["D1 ビジネス要求"]:::included --> D2["D2 システム要件"]:::included
    D2 --> D3["D3 システム設計"]:::planned
    D3 --> D4["D4 実装・UT・内部結合テスト(ITa)"]:::planned
    D4 --> D5["D5 E2Eテスト(ITb)"]:::planned
    D5 --> D6["D6 システムテスト"]:::planned
    D6 --> D7["D7 リリース"]:::planned
    D2 --> D10["D10 システム運用要件"]:::planned
    D10 --> D11["D11 システム運用設計"]:::planned
    D11 --> D6
    D2 -->D8["D8 テスト計画"]:::planned
    D8 --> D4
    D8 -->D9["D9 テスト設計"]:::planned
    D9 --> D5 & D6
    D0["D0 プロジェクトマネジメント(全フェーズ横断)"]:::planned
```

🟩 = 本リポジトリに収録しているフェーズ

## ハンドブック

KARURA全体の考え方と、収録している各成果物の目的・作り込み/レビューの勘所は、リポジトリ直下の [handbook/](handbook/README.md) にまとめています。収録しているスキルの一覧もこちらで確認できます。

## クイックスタート

### 前提条件
 
- [Claude Code](https://code.claude.com/)(成果物の生成・更新に使用)
- Node.js 18 以上・pnpm 9 以上(Docusaurus での Wiki プレビューに使用)
### 1. セットアップ
 
```bash
git clone https://github.com/Acceler-Digital/karura.git
cd karura
pnpm install                          # Docusaurus を使う場合
git config core.hooksPath .githooks   # pre-commit セキュリティスキャン有効化(pnpm install 時に自動実行)
```
 
### 2. 最初の成果物を生成する
 
プロジェクト立ち上げの起点はビジネス要件定義書です。リポジトリ内で Claude Code を起動し、スラッシュコマンドを実行します。
 
```
/d1-business-requirement-document
```
 
以降は[成果物フロー](docs/D0.project-management/artifact-flow.md)に沿って、各成果物のスラッシュコマンド(`/d1-actor-list`、`/d2-function-list` など)を順に実行していきます。上流の成果物を入力として下流の成果物が生成されるため、生成順はフローに従ってください。
 
生成された成果物は、別リポジトリ(下記サンプル等)の `docs/` 配下に配置していく運用を想定しています。本リポジトリの `docs/` には、フェーズのプレースホルダとなる空ディレクトリと、成果物フロー等のメタ情報のみを置いています。

## 本リポジトリに含まれないもの

本リポジトリ(OSS 版)は、KARURA の全体像を理解し、上流工程を中心に体験していただくためのものです。以下は**含まれません**。

- **全フェーズ・全成果物のスキル / テンプレート一式** — 成果物フローには 80 種類以上の成果物を定義していますが、本リポジトリには一部のフェーズのみを収録しています。今後も拡張を続けますが、全量を収録する予定はありません
- **導入・伴走サポート** — プロジェクトへの導入支援、成果物のレビュー、プロジェクト特性に合わせたスキル / テンプレートのカスタマイズ

全フェーズに対応した完全版の提供や、導入・伴走サポートが必要な場合は、別途ご契約のうえで提供しています。[Acceler Digital](https://www.acceler-digital.com/) までお問い合わせください。
 
## 付属ツール
 
### 要確認マーカーの集計
 
AI は自身で生成した内容に自信がない場合、要確認マーカーを付けます。[docs/](docs/) 配下に残っている未確定マーカー(プレースホルダ `{{xxx}}` と要確認マーカー `要確認`)の件数・該当ファイルを以下で集計できます。レビュー時の気付き支援用で、CI で fail させる目的ではありません(スクリプトは常に exit 0)。
 
```bash
pnpm check:markers
```
 
実体は [scripts/check-markers.sh](scripts/check-markers.sh) です。マーカー記法は [CLAUDE.md](CLAUDE.md) §1〜§3 を参照してください。
 
### セキュリティ・スキャン
 
本リポジトリ(および KARURA で運用するリポジトリ)は、公開リポジトリにシークレットや機微情報が混入しないよう、二段でスキャンを行います。外部ツールのインストールは不要です(`grep` / `jq` のみ)。
 
1. **生成完了時(Claude Code の Stop フック)** — Claude が応答を終えると未コミットの変更を自動スキャンし、検出があれば警告します(停止はブロックしない、気付き目的)
2. **コミット時(git pre-commit / 最終防衛線)** — ステージ済みファイルをスキャンし、**high を検出するとコミットを中止**します
```bash
# 手動スキャン
pnpm check:security
```
 
検出対象・重大度・誤検知除外の詳細は [SECURITY.md](SECURITY.md) を参照してください。実体は [scripts/security-scan.sh](scripts/security-scan.sh) ・ [.githooks/pre-commit](.githooks/pre-commit) です。
 
### Wiki プレビュー(Docusaurus)
 
[docs/](docs/) 配下の Markdown は [Docusaurus 3](https://docusaurus.io/) で Wiki サイトとしてプレビューできます。プロジェクト側で Confluence や Notion を使う場合は不要です。サイドバー構成は [sidebars.ts](sidebars.ts) を参照してください。
 
```bash
pnpm start          # 開発サーバー起動(http://localhost:3000)
pnpm build          # 本番ビルド
pnpm serve          # ビルド後のプレビュー
pnpm build:offline  # オフライン閲覧用ビルド(hash router・検索インデックス同梱)
```

## リポジトリ構成
 
```
.
├── .claude/
│   ├── skills/                    # Claude スキル定義(フェーズ別、テンプレート同梱)
│   │   ├── d1-business-requirement-document/
│   │   │   ├── SKILL.md           # スキル本体(振る舞いルール)
│   │   │   └── template.md        # 成果物テンプレート(章構成・書き方ヒント入り)
│   │   └── ...                    # d1-* / d2-* 各スキル
│   └── settings.json              # Claude Code 設定(allowlist・Stop フック 等)
├── docs/                          # メタ情報・フェーズ用プレースホルダ
│   └── D0.project-management/     # 成果物フロー・プロジェクトインデックス
├── handbook/                      # KARURA の設計思想・方法論の解説(Docusaurus 非依存)
├── scripts/                       # 補助スクリプト
│   ├── check-markers.sh           # 未確定マーカー集計
│   └── security-scan.sh           # セキュリティスキャン本体
├── .githooks/
│   └── pre-commit                 # コミット時セキュリティスキャン
├── sidebars.ts                    # Docusaurus サイドバー定義
├── docusaurus.config.ts           # Docusaurus 設定
├── CLAUDE.md                      # プロジェクト共通の慣習(Claude が自動参照)
├── SECURITY.md                    # セキュリティスキャンの説明
└── package.json
```

## 成果物サンプル
KARURAを使用した成果物サンプルとして、以下リポジトリをご用意しております。実際にプロジェクトに適用する前に、各成果物に対するイメージを掴む際にご利用ください。

👉 **[KARURA 成果物サンプル - 生命保険 新契約システム](https://github.com/Acceler-Digital/karura-sample-artifacts-individual-life-insurance-new-business)**

## お問い合わせ
 
- **バグ報告・改善提案** — [GitHub Issues](https://github.com/Acceler-Digital/karura/issues)
- **完全版の提供・導入支援・伴走サポートのご相談** — Acceler Digitalのお問い合わせ窓口までお願いいたします。
[![corporate](https://img.shields.io/badge/🌐_corporate-acceler--digital.com-181717?style=for-the-badge)](https://www.acceler-digital.com/)


## ライセンス
 
本リポジトリに含まれるドキュメント・図・設定ファイル・スクリプトは [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) の下で提供されます。全文は同梱の [LICENSE](LICENSE) を参照してください。