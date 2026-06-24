# 入力フォーマット

入力は次の列を持つ Markdown 表です。列順は入れ替え可能ですが、すべての列が必要です。

| 列 | 意味 |
|---|---|
| `正式表記` | Google 日本語入力へ出力する表記。必須です。 |
| `alias` | v1 では単一の metadata 文字列。デフォルトでは出力しません。 |
| `読み` | ひらがなの読み。必須です。 |
| `memo` | TSV comment。 |
| `scope候補` | review workflow 用 metadata。 |
| `出典` | metadata のみ。共有予定のファイルでは private URL、local path、account name、ticket ID、customer name、confidential source name を入れないでください。 |
| `status` | `candidate` または `reviewed` の行を出力します。 |

デフォルトは strict mode です。unknown status、必須列の空欄、不正な読み、duplicate `読み + 正式表記`、tab/newline を含む field を拒否します。

無効 status は無視します: `draft`, `rejected`, `hold`, `private`, `archived`。

`alias` はデフォルトでは出力しません。`--emit-aliases` は experimental で、alias cell 全体を追加の表記として扱います。

`読み` は、ひらがな、小書きかな、`ゔ` を受け付けます。`ー` を許可する場合は `--allow-long-vowel-mark` を使います。source 側の読みでは、漢字、カタカナ、Latin letters、space、tab、newline を拒否します。

出力は NFC normalization、周辺 whitespace trim、`読み` と `正式表記` の stable sort によって canonical 化されます。
