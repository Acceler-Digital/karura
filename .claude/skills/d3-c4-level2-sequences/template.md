<!--
振る舞いルールは`.claude/skills/d3-c4-level2-sequences/SKILL.md`、記法の骨格は`.claude/skills/d2-c4-level1-sequences/SKILL.md`、汎用規約はリポジトリ直下の`CLAUDE.md`を参照
-->

# {{UC-N}}: {{UC名}}
## 事前・事後処理
- **事前条件**: {{開始時点の業務状態}}
- **事後条件**: 
    * {{成立したときの結果}}
    * {{ガード節で打ち切られたときの返り方}}

## シーケンス図
```mermaid
sequenceDiagram
    actor {{actN}} as {{人の名称}}<br/>{{ACT-N}}
    participant {{cntN}} as {{業務サービス名}}<br/>{{CNT-N}}
    participant {{cntM}} as {{業務サービス名}}<br/>{{CNT-M}}
    participant {{cntL}}@{ "type" : "database" } as {{データストア名}}<br/>{{CNT-L}}
    participant {{extN}} as {{外部システム名}}<br/>{{EXT-N}}

    {{actN}}->>{{cntN}}: {{処理ID}}<br/>{{画面上の操作、または指示の内容}}
    activate {{cntN}}

    {{cntN}}->>{{extN}}: {{処理ID}}<br/>{{前提となる外部の操作}}
    activate {{extN}}
    {{extN}}-->>{{cntN}}: {{操作の結果}}
    deactivate {{extN}}

    break {{前提となる外部の操作に失敗する}}
        {{cntN}}-->>{{actN}}: {{失敗した旨と原因}}
    end

    {{cntN}}->>{{cntL}}: {{処理ID}}<br/>{{テーブル名}}に{{登録する内容}}を登録
    activate {{cntL}}
    {{cntL}}-->>{{cntN}}: 登録結果
    deactivate {{cntL}}

    critical {{外部システムへの一連の操作}}
        loop {{対象}}ごと
            {{cntN}}->>{{extN}}: {{処理ID}}<br/>{{外部システムへ渡すもの・求めるもの}}
            activate {{extN}}
            {{extN}}-->>{{cntN}}: {{受け取る結果}}
            deactivate {{extN}}

            Note over {{cntN}}: 【決定論的な判定】{{判定に使う項目}}
            {{cntN}}->>{{cntN}}: {{処理ID}}<br/>{{ルールによる判定の内容}}

            break {{外れる条件}}(次の{{対象}}へ)
                {{cntN}}->>{{cntL}}: {{処理ID}}<br/>{{テーブル名}}の{{更新する内容}}を更新
                activate {{cntL}}
                {{cntL}}-->>{{cntN}}: 更新結果
                deactivate {{cntL}}
            end

            {{cntN}}->>{{cntL}}: {{処理ID}}<br/>{{テーブル名}}から{{参照する内容}}を参照
            activate {{cntL}}
            {{cntL}}-->>{{cntN}}: {{参照した内容}}
            deactivate {{cntL}}
        end
    option {{一連の操作に共通する失敗}}
        {{cntN}}->>{{cntL}}: {{処理ID}}<br/>{{テーブル名}}の{{状態}}を「中断」へ更新
        activate {{cntL}}
        {{cntL}}-->>{{cntN}}: 更新結果
        deactivate {{cntL}}
        {{cntN}}-->>{{actN}}: {{中断した旨と原因}}
    end

    {{cntN}}-){{cntM}}: {{処理ID}}<br/>{{引き渡す内容}}
    {{cntN}}-->>{{actN}}: {{成果}}
    deactivate {{cntN}}

    activate {{cntM}}
    {{cntM}}->>{{cntM}}: {{処理ID}}<br/>{{判定の内容}}
    deactivate {{cntM}}
```

> ⚠️ **要確認**: {{推測・仮置きした前提}}

## 機能との対応

図の処理IDが、機能一覧のどの機能にあたるかを示します。

| 機能ID | 機能名 | 処理ID |
|---|---|---|
| {{FUNC-N}} | {{機能名}} | {{処理ID}}<br/>{{処理ID}} |
