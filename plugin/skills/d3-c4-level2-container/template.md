<!--
振る舞いルールは `.claude/skills/d3-c4-level2-container/SKILL.md`、汎用規約はリポジトリ直下の `CLAUDE.md` を参照
-->

# C4モデル レベル2: コンテナ

{{本図のスコープ(対象システム内部をコンテナ単位で描いたこと・業務サービスの分け方・各サービスのデータを図で省略していること)を1段落で記載}}

```mermaid
flowchart LR
    classDef person fill:#08427b,color:#ffffff,stroke:#052e56;
    classDef container fill:#438dd5,color:#ffffff,stroke:#2e6295;
    classDef extsys fill:#8c8c8c,color:#ffffff,stroke:#5c5c5c;

    subgraph {{利用者グループ}}
        direction TB
        {{actN}}["{{アクター名}}<br/>{{ACT-N}}"]
    end

    subgraph sys["{{対象システム名}}"]
        direction TB
        {{uiN}}["<b>{{利用者名}}用SPA</b><br/>{{CNT-N}}"]
        {{bffN}}["<b>{{利用者名}}用BFF</b><br/>{{CNT-N}}"]
        subgraph svc["{{業務工程の囲みの名称}}"]
            direction TB
            {{svcN}}["<b>{{業務名}}サービス</b><br/>{{CNT-N}}"]
            {{svcM}}["<b>{{業務名}}サービス</b><br/>{{CNT-M}}"]
        end
        {{cmnN}}["<b>{{共通のコンテナ名}}</b><br/>{{CNT-N}}"]
    end

    subgraph {{外部システムグループ}}
        direction TB
        {{extN}}["{{外部システム名}}<br/>{{EXT-N}}"]
    end

    {{actN}} -->|"{{やり取りする内容}}<br/>(同期)"| {{uiN}}
    {{uiN}} -->|"{{やり取りする内容}}<br/>(同期)"| {{bffN}}
    {{bffN}} -->|"{{やり取りする内容}}<br/>(同期)"| {{svcN}}
    {{svcN}} -->|"{{引き渡す内容}}<br/>(非同期)"| {{svcM}}
    svc -->|"{{やり取りする内容}}<br/>({{同期 / 非同期}})"| {{cmnN}}
    {{svcN}} -->|"{{やり取りする内容}}<br/>({{同期 / 非同期}})"| {{extN}}

    class {{actN}} person;
    class {{uiN}},{{bffN}},{{svcN}},{{svcM}},{{cmnN}} container;
    class {{extN}} extsys;
    style sys fill:none,stroke:#1168bd,stroke-width:2px,stroke-dasharray:6 4;
    style svc fill:none,stroke:#438dd5,stroke-width:1px;
```

> ⚠️ **要確認**: {{ADR に基づかない連携方式・根拠となる UC が無い線}}

## コンテナ

<!-- HINT:
- 種別: SPA / BFF / 業務サービス / 非同期処理
- 設計根拠: ADR に基づく場合は ADR の ID、それ以外は分割の理由と末尾に【要確認】
-->

| ID | 種別 | 名称 | 責務 | 設計根拠 | 関連 UC |
|---|---|---|---|---|---|
| {{CNT-N}} | {{種別}} | {{コンテナ名}} | {{責務}} | {{設計根拠}} | {{UC-N〜M}} |
