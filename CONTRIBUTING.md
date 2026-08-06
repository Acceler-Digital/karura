# コントリビューションガイド

KARURA へのご貢献に関心をお持ちいただき、ありがとうございます。

> **English**: All pull requests require agreement to the [CLA](CLA.md). The CLA
> Assistant bot will ask you to sign on your first pull request. You keep the
> copyright in your contribution.

## CLA への同意（必須）

**すべてのプルリクエストは、[CLA](CLA.md) への同意が前提です。**

- 初回のプルリクエスト時に、CLA Assistant が自動で同意を求めます
- 画面の指示に従って署名すると記録され、以降は求められません
- 同意が記録されるまで、プルリクエストはマージできません

コントリビューションの**著作権はあなたに残ります**。Acceler Digital に対して、再許諾を含む広範なライセンスを付与していただく形式です。

雇用契約または業務委託契約に基づいて貢献される場合は、所属先の許可を得たうえで署名してください（CLA §5.3）。

## 第三者コードの取り扱い

- 第三者のコードやドキュメントを含める場合は、**出典とライセンスをプルリクエストに明記**してください
- **GPL / LGPL / AGPL 等のコピーレフトライセンス**の成果物は取り込めません（本プロジェクトは Apache License 2.0 で提供されるため）
- 生成 AI の出力を含める場合も、上記の判断は貢献者の責任で行ってください

## プルリクエストの進め方

1. 大きな変更は、事前に Issue で方針を相談してください
2. ブランチを作成して変更を加えます
3. `pnpm check:security` と `pnpm check:markers` を実行して確認します
4. プルリクエストを作成します
5. CLA Assistant の指示に従って CLA に署名します
6. レビューのうえマージします

## 規約・慣習

プレースホルダ書式、要確認マーカー、ID 表記、文体などの横断規約は [CLAUDE.md](CLAUDE.md) に集約されています。スキルやテンプレートを変更する場合は、事前にご確認ください。

## セキュリティ

脆弱性やシークレットの混入を発見された場合は、公開 Issue ではなく [SECURITY.md](SECURITY.md) の手順に従ってご連絡ください。

---

ご不明な点は Issue でお尋ねください。